from fastapi import APIRouter, HTTPException, UploadFile, File, Depends

from services.auth import verify_token
from services.xml_parser import parse_xml_content, parse_testrail_xml_full
from services.csv_generator import match_column, read_excel_or_csv
from services.gemini import get_gemini_client

router = APIRouter()


@router.post("/api/parse-xml")
async def parse_xml_endpoint(file: UploadFile = File(...), _: None = Depends(verify_token)):
    """Parsea XML de TestRail export, Jira RSS o formato simple."""
    content = await file.read()
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        text = content.decode('latin-1')

    items = parse_xml_content(text)
    if not items:
        raise HTTPException(
            status_code=400,
            detail=(
                "No se encontraron items en el XML. "
                "Formatos soportados: TestRail XML export (<sections>), "
                "Jira RSS export (<rss>), o formato simple (<cases><case>)."
            )
        )
    return {"items": items, "count": len(items)}


@router.post("/api/load-xml")
async def load_xml_cases(file: UploadFile = File(...), _: None = Depends(verify_token)):
    """Carga un XML de TestRail y devuelve todos los casos con todos sus campos."""
    content = await file.read()
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        text = content.decode('latin-1')
    cases = parse_testrail_xml_full(text)
    return {"cases": cases, "count": len(cases)}


@router.post("/api/parse-stepbystep")
async def parse_stepbystep(file: UploadFile = File(...), _: None = Depends(verify_token)):
    """Parse uploaded Excel/CSV for step-by-step conversion to TestRail CSV."""
    content = await file.read()
    headers, rows = read_excel_or_csv(content, file.filename or 'file.csv')
    if not headers or not rows:
        raise HTTPException(status_code=400, detail="El archivo está vacío o no tiene el formato esperado")

    headers_lower = {h.lower().strip(): h for h in headers}
    col_map = {}
    for field in ['title', 'steps_step', 'steps_expected', 'priority', 'refs',
                   'preconditions', 'description', 'test_data', 'estimate', 'type', 'automation_review']:
        matched = match_column(headers_lower, field)
        if matched:
            col_map[field] = matched

    missing = []
    if not col_map.get('priority'):
        missing.append({'field': 'priority', 'label': 'Priority (global)', 'required': True, 'input_type': 'select',
                        'options': ['1 - Must Test', '2 - Run Before Release', '3 - Normal', '4 - Nice to Have'],
                        'default': '2 - Run Before Release'})
    if not col_map.get('type'):
        missing.append({'field': 'type', 'label': 'Type (global)', 'required': False, 'input_type': 'select',
                        'options': ['Functional', 'Acceptance', 'Regression', 'Integration', 'Security', 'Performance'],
                        'default': 'Functional'})
    if not col_map.get('refs'):
        missing.append({'field': 'refs', 'label': 'References (global)', 'required': False, 'input_type': 'text',
                        'placeholder': 'Ej: CC-1764', 'default': ''})

    return {
        'headers':    headers,
        'col_map':    col_map,
        'missing':    missing,
        'total_rows': len(rows),
        'preview':    rows[:5],
        'rows':       rows,
        'has_steps':  bool(col_map.get('steps_step')),
        'filename':   file.filename,
    }


@router.get("/api/models")
def list_models(_: None = Depends(verify_token)):
    try:
        client  = get_gemini_client()
        models  = [m.name for m in client.models.list()]
        return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
