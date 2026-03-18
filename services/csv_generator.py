import csv
import io
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import List, Optional

import openpyxl


# ─── Generador de CSV ─────────────────────────────────────────────────────────

BASE_CSV_COLUMNS = [
    "title", "section", "template", "type", "priority", "estimate",
    "refs", "custom_preconds", "custom_bdd_scenarios"
]


def cases_to_csv(cases: List[dict]) -> str:
    extra_keys = []
    for case in cases:
        for k in case.keys():
            if k not in BASE_CSV_COLUMNS and k not in extra_keys:
                extra_keys.append(k)
    extra_keys.sort()
    columns = BASE_CSV_COLUMNS + extra_keys

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=columns,
        quoting=csv.QUOTE_ALL,
        lineterminator="\r\n",
        extrasaction='ignore',
    )
    writer.writeheader()

    for case in cases:
        row = {col: case.get(col, '') for col in columns}
        row['template'] = case.get('template', 'Behaviour Driven Development')
        row['type']     = case.get('type', 'Functional')
        row['priority'] = case.get('priority', '3 - Normal')
        row['estimate'] = case.get('estimate', '5m')
        writer.writerow(row)

    return output.getvalue()


# ─── Generador de XML (formato TestRail) ─────────────────────────────────────

# Campos estándar de TestRail a nivel de <case> (fuera de <custom>)
_TR_STANDARD = {'title', 'section', 'template', 'type', 'priority', 'estimate', 'refs'}


def _priority_id(priority_str: str) -> str:
    """Convierte '2 - Run Before Release' → '2' (TestRail espera ID numérico en XML)."""
    part = priority_str.strip().split(' ')[0]
    return part if part.isdigit() else '3'


def cases_to_xml(cases: List[dict], section_path: str = "") -> str:
    """Genera XML en formato TestRail probado:
       - Raíz <sections> (import en suite existente)
       - <references> (no <refs>)
       - <priority> como número
       - CDATA para contenido Gherkin
       - section_path: ruta padre opcional, ej: "Configurable Forms/Enhanced Save"
    """
    # Agrupar por sección manteniendo orden de aparición
    sections: dict = {}
    for case in cases:
        sec = case.get('section', 'General') or 'General'
        sections.setdefault(sec, []).append(case)

    root = ET.Element('sections')

    for section_name, section_cases in sections.items():
        sec_el   = ET.SubElement(root, 'section')
        ET.SubElement(sec_el, 'name').text = section_name
        cases_el = ET.SubElement(sec_el, 'cases')

        for case in section_cases:
            case_el = ET.SubElement(cases_el, 'case')

            ET.SubElement(case_el, 'title').text    = case.get('title', '')
            ET.SubElement(case_el, 'type').text     = case.get('type', 'Functional')
            ET.SubElement(case_el, 'priority').text = _priority_id(case.get('priority', '3 - Normal'))
            refs = case.get('refs', '').strip()
            # Siempre incluir <references> (campo requerido en TestRail).
            # Si no hay ticket, usar "-" para evitar que TestRail lo valide contra Jira.
            ET.SubElement(case_el, 'references').text = refs if refs else '-'

            estimate = case.get('estimate', '')
            if estimate:
                ET.SubElement(case_el, 'estimate').text = estimate

            # Bloque <custom>
            custom_el = ET.SubElement(case_el, 'custom')

            preconds = case.get('custom_preconds', '')
            if preconds:
                ET.SubElement(custom_el, 'preconds').text = preconds

            bdd = case.get('custom_bdd_scenarios', '')
            if bdd:
                ET.SubElement(custom_el, 'bdd_scenarios').text = bdd  # → CDATA en minidom

            # Campos extra (implementation, domain, etc.)
            skip = _TR_STANDARD | {'custom_preconds', 'custom_bdd_scenarios'}
            for key, value in case.items():
                if key not in skip and value:
                    field_name = key[7:] if key.startswith('custom_') else key
                    ET.SubElement(custom_el, field_name).text = str(value)

    # Convertir a DOM de minidom para aplicar CDATA en bdd_scenarios y pretty-print
    raw = ET.tostring(root, encoding='unicode')
    dom = minidom.parseString(raw)

    # Envolver contenido de <bdd_scenarios> y <preconds> en CDATA (sin whitespace extra)
    for tag in ('bdd_scenarios', 'preconds'):
        for el in dom.getElementsByTagName(tag):
            if el.firstChild and el.firstChild.nodeType == el.firstChild.TEXT_NODE:
                text = el.firstChild.data.strip()
                el.removeChild(el.firstChild)
                el.appendChild(dom.createCDATASection(text))

    pretty = dom.toprettyxml(indent='  ', encoding='UTF-8')
    return pretty.decode('UTF-8') if isinstance(pretty, bytes) else pretty


# ─── Step-by-step CSV converter ───────────────────────────────────────────────

COLUMN_ALIASES: dict = {
    'title':          ['title', 'test case', 'case name', 'name', 'título', 'caso', 'test_case', 'case title', 'case'],
    'steps_step':     ['steps (step)', 'step', 'action', 'steps', 'paso', 'pasos', 'step description', 'steps description', 'action step'],
    'steps_expected': ['steps (expected result)', 'expected result', 'expected', 'resultado esperado', 'validation',
                       'expected results', 'steps (expected results)', 'result', 'expected outcome'],
    'priority':       ['priority', 'prioridad'],
    'refs':           ['references', 'refs', 'reference', 'jira', 'ticket', 'jira ticket', 'jira_ticket'],
    'preconditions':  ['preconditions', 'precondiciones', 'pre-conditions', 'precondition', 'custom_preconds', 'preconds'],
    'description':    ['description', 'descripción', 'desc'],
    'test_data':      ['test data', 'testdata', 'datos de prueba', 'test_data'],
    'estimate':       ['estimate', 'estimado'],
    'type':           ['type', 'tipo', 'test type'],
    'automation_review': ['automation review', 'automation', 'automatización', 'automation_review'],
}


def match_column(headers_lower: dict, field: str) -> Optional[str]:
    for alias in COLUMN_ALIASES.get(field, []):
        if alias in headers_lower:
            return headers_lower[alias]
    return None


def read_excel_or_csv(content: bytes, filename: str):
    if filename.lower().endswith(('.xlsx', '.xls')):
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        ws = wb.active
        all_rows = list(ws.iter_rows(values_only=True))
        if not all_rows:
            return [], []
        headers = [str(h).strip() if h is not None else f'col_{i}' for i, h in enumerate(all_rows[0])]
        rows = []
        for raw in all_rows[1:]:
            if any(c is not None and str(c).strip() for c in raw):
                rows.append({headers[i]: (str(raw[i]).strip() if raw[i] is not None else '') for i in range(len(headers))})
        return headers, rows
    else:
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = content.decode('latin-1')
        reader = csv.DictReader(io.StringIO(text))
        headers = list(reader.fieldnames or [])
        return headers, [dict(r) for r in reader]


def build_testrail_cases(rows: List[dict], col_map: dict, defaults: dict) -> List[dict]:
    cases = []
    current: Optional[dict] = None
    for row in rows:
        title_col = col_map.get('title')
        title = row.get(title_col, '').strip() if title_col else ''
        step_col = col_map.get('steps_step')
        step = row.get(step_col, '').strip() if step_col else ''
        exp_col = col_map.get('steps_expected')
        expected = row.get(exp_col, '').strip() if exp_col else ''

        def _get(field, default=''):
            col = col_map.get(field)
            return row.get(col, default).strip() if col else default

        if title:
            current = {
                'Title':             title,
                'Template':          'Test Case (Steps)',
                'Type':              _get('type') or defaults.get('type', 'Functional'),
                'Priority':          _get('priority') or defaults.get('priority', '2 - Run Before Release'),
                'Estimate':          _get('estimate'),
                'Automation Review': _get('automation_review') or 'Not',
                'References':        _get('refs') or defaults.get('refs', ''),
                'Description':       _get('description'),
                'Preconditions':     _get('preconditions'),
                'Test Data':         _get('test_data'),
                'steps':             [],
            }
            if step or expected:
                current['steps'].append({'step': step, 'expected': expected})
            cases.append(current)
        elif current and (step or expected):
            current['steps'].append({'step': step, 'expected': expected})
    return cases


def cases_to_testrail_steps_csv(cases: List[dict]) -> str:
    COLS = ['Title', 'Template', 'Type', 'Priority', 'Estimate',
            'Automation Review', 'References', 'Description',
            'Preconditions', 'Test Data', 'Steps (Step)', 'Steps (Expected Result)']
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=COLS, quoting=csv.QUOTE_ALL,
                       lineterminator='\r\n', extrasaction='ignore')
    w.writeheader()
    for case in cases:
        steps = case.get('steps', [])
        if not steps:
            row = {c: case.get(c, '') for c in COLS}
            row['Steps (Step)'] = ''
            row['Steps (Expected Result)'] = ''
            w.writerow(row)
        else:
            for i, s in enumerate(steps):
                row = {c: case.get(c, '') for c in COLS} if i == 0 else {c: '' for c in COLS}
                row['Steps (Step)'] = s.get('step', '')
                row['Steps (Expected Result)'] = s.get('expected', '')
                w.writerow(row)
    return out.getvalue()
