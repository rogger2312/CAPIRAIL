from fastapi import APIRouter, HTTPException, Depends

from models import JiraInput, TestRailInput, BatchGenerateInput, TitleGeneratorInput
from services.auth import verify_token
from services.gemini import call_gemini, call_titles_gemini
from services.prompts import prompt_from_jira, prompt_from_testrail, prompt_from_batch_item

router = APIRouter()


@router.post("/api/generate/jira")
def generate_from_jira(data: JiraInput, _: None = Depends(verify_token)):
    prompt = prompt_from_jira(data)
    cases  = call_gemini(prompt, images=data.images)
    return {"test_cases": cases, "count": len(cases)}


@router.post("/api/generate/testrail")
def generate_from_testrail(data: TestRailInput, _: None = Depends(verify_token)):
    if not data.steps:
        raise HTTPException(status_code=400, detail="Debes proporcionar al menos un paso")
    prompt = prompt_from_testrail(data)
    cases  = call_gemini(prompt, images=data.images)
    return {"test_cases": cases, "count": len(cases)}


@router.post("/api/generate/batch")
def generate_batch(config: BatchGenerateInput, _: None = Depends(verify_token)):
    if not config.items:
        raise HTTPException(status_code=400, detail="No hay items para procesar")

    all_cases = []
    errors    = []

    for item in config.items:
        try:
            prompt = prompt_from_batch_item(item)
            cases  = call_gemini(prompt)
            for case in cases:
                case['type']     = config.type_override
                case['priority'] = config.priority_override
                if item.refs:
                    case['refs'] = item.refs
                for key, value in config.extra_fields.items():
                    if value:
                        case[key] = value
            all_cases.extend(cases)
        except Exception as e:
            errors.append({"item": item.title, "error": str(e)})

    return {"test_cases": all_cases, "count": len(all_cases), "errors": errors}


@router.post("/api/generate/titles")
def generate_titles(data: TitleGeneratorInput, _: None = Depends(verify_token)):
    """Genera títulos de casos de prueba siguiendo convenciones estrictas de naming."""
    user_prompt = f"""Generate test case titles for the following test cases or feature description:

{data.test_cases}

Return a JSON array of strings where each string is a title for one test case.
Generate as many titles as needed to cover the described scenarios thoroughly."""

    titles = call_titles_gemini(user_prompt, images=data.images)
    return {"titles": titles, "count": len(titles)}
