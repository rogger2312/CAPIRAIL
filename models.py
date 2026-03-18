from typing import List, Optional
from pydantic import BaseModel


# ─── Modelos de entrada ────────────────────────────────────────────────────────

class JiraInput(BaseModel):
    description: str
    acceptance_criteria: str
    jira_ticket: Optional[str] = ""
    images: List[str] = []   # base64 data-URLs (máx 3)


class StepInput(BaseModel):
    step: str
    validation: str


class TestRailInput(BaseModel):
    preconditions: str
    test_data: Optional[str] = ""
    steps: List[StepInput]
    title_hint: Optional[str] = ""
    images: List[str] = []   # base64 data-URLs (máx 3)


class TitleGeneratorInput(BaseModel):
    test_cases: str          # descripciones de casos, una por línea o texto libre
    images: List[str] = []   # base64 data-URLs opcionales (máx 3)


class BatchItem(BaseModel):
    title: str
    section: str
    refs: str
    description: Optional[str] = ""


class BatchGenerateInput(BaseModel):
    items: List[BatchItem]
    type_override: str = "Functional"
    priority_override: str = "3 - Normal"
    extra_fields: dict = {}


class StepByStepConvertInput(BaseModel):
    rows: List[dict]
    col_map: dict
    defaults: dict = {}


# ─── Modelo de salida (caso de prueba) ────────────────────────────────────────

class TestCase(BaseModel):
    title: str
    section: str
    template: str
    type: str
    priority: str
    estimate: str
    refs: str
    custom_preconds: str
    custom_bdd_scenarios: str
