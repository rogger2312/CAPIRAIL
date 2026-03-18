import xml.etree.ElementTree as ET
from typing import List

from fastapi import HTTPException


def parse_xml_content(content: str) -> List[dict]:
    """
    Soporta tres formatos:
      1. TestRail XML export: <sections><section><cases><case>
      2. Jira RSS export:     <rss><channel><item>
      3. Formato simple:      <cases><case> / <test-cases><test-case> / etc.
    """
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        raise HTTPException(status_code=400, detail=f"XML inválido: {str(e)}")

    items = []

    # ── 1. TestRail XML export: <suite><sections>... o <sections>... ──────────
    # Detectar por root tag o presencia de <section>/<cases>/<case>
    tr_sections = root.findall('.//section')
    has_tr_cases = root.find('.//cases/case') is not None
    if (root.tag in ('suite', 'sections') or has_tr_cases) and tr_sections:
        for section_el in root.findall('.//section'):
            section_name = (section_el.findtext('name') or '').strip()
            # Solo casos directos de esta section (no de subsecciones)
            cases_el = section_el.find('cases')
            if cases_el is None:
                continue
            for case_el in cases_el.findall('case'):
                title = (case_el.findtext('title') or '').strip()
                refs  = (case_el.findtext('refs')  or '').strip()
                # Buscar descripción en custom fields
                custom_el = case_el.find('custom')
                description = ''
                if custom_el is not None:
                    description = (
                        custom_el.findtext('bdd_scenarios') or
                        custom_el.findtext('preconds') or
                        custom_el.findtext('steps') or ''
                    ).strip()
                if title:
                    items.append({
                        'title':       title,
                        'section':     section_name,
                        'refs':        refs,
                        'description': description,
                    })
        if items:
            return items

    # ── 2. Jira RSS export: <rss><channel><item> ──────────────────────────────
    jira_items = root.findall('.//item')
    if jira_items:
        for item in jira_items:
            summary   = (item.findtext('summary') or '').strip()
            raw_title = (item.findtext('title')   or '').strip()
            if raw_title.startswith('[') and '] ' in raw_title:
                raw_title = raw_title.split('] ', 1)[1]
            title = summary or raw_title

            key         = (item.findtext('key')         or '').strip()
            description = (item.findtext('description') or '').strip()

            component_el = item.find('component')
            section = (component_el.text if component_el is not None else '').strip()

            if title:
                items.append({
                    'title':       title,
                    'section':     section,
                    'refs':        key,
                    'description': description,
                })
        return items

    # ── 3. Formato simple ─────────────────────────────────────────────────────
    for tag in ['case', 'test-case', 'testcase', 'story', 'issue', 'requirement']:
        elements = root.findall(f'.//{tag}')
        if elements:
            for el in elements:
                title = (
                    el.findtext('title') or
                    el.findtext('summary') or
                    el.get('title') or ''
                ).strip()
                section = (el.findtext('section') or el.findtext('component') or '').strip()
                refs    = (
                    el.findtext('refs') or
                    el.findtext('references') or
                    el.findtext('key') or ''
                ).strip()
                description = (el.findtext('description') or el.findtext('body') or '').strip()
                if title:
                    items.append({
                        'title':       title,
                        'section':     section,
                        'refs':        refs,
                        'description': description,
                    })
            return items

    return items


def parse_testrail_xml_full(content: str) -> List[dict]:
    """Parsea XML de TestRail completo: extrae TODOS los campos de cada caso."""
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        raise HTTPException(status_code=400, detail=f"XML inválido: {str(e)}")

    cases = []
    for section_el in root.findall('.//section'):
        section_name = (section_el.findtext('name') or 'General').strip()
        cases_el = section_el.find('cases')
        if cases_el is None:
            continue
        for case_el in cases_el.findall('case'):
            case = {
                'title':    (case_el.findtext('title')    or '').strip(),
                'section':  section_name,
                'template': (case_el.findtext('template') or 'Behaviour Driven Development').strip(),
                'type':     (case_el.findtext('type')     or 'Functional').strip(),
                'priority': (case_el.findtext('priority') or '3 - Normal').strip(),
                'estimate': (case_el.findtext('estimate') or '').strip(),
                'refs':     (case_el.findtext('refs') or case_el.findtext('references') or '').strip(),
                'custom_preconds':      '',
                'custom_bdd_scenarios': '',
            }
            custom_el = case_el.find('custom')
            if custom_el is not None:
                case['custom_preconds']      = (custom_el.findtext('preconds')      or '').strip()
                case['custom_bdd_scenarios'] = (custom_el.findtext('bdd_scenarios') or '').strip()
                # Campos custom extra (implementation, domain, automation_review, etc.)
                known = {'preconds', 'bdd_scenarios'}
                for child in custom_el:
                    if child.tag not in known:
                        case[f'custom_{child.tag}'] = (child.text or '').strip()
            if case['title']:
                cases.append(case)

    if not cases:
        raise HTTPException(
            status_code=400,
            detail="No se encontraron casos en el XML. Verifica que sea un XML exportado por esta herramienta o por TestRail."
        )

    return cases
