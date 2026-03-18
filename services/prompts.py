from models import JiraInput, TestRailInput, BatchItem


TITLE_SYSTEM_PROMPT = """You are a QA expert specializing in test case naming conventions.
Your task is to generate clear, professional test case titles in English.

STRICT RULES:
- Titles must NOT contain the words "verify", "validate", or "confirm" (in any form or capitalization).
- Titles must NOT include sensitive data (passwords, tokens, personal information, credentials).
- Each title must clearly indicate the specific purpose of the test, describing what is being checked or evaluated.
- All titles must be in English.
- Titles should be concise but descriptive (max 120 characters).
- Use action verbs such as: "Check", "Ensure", "Test", "Assert", "Evaluate", "Examine", "Display", "Prevent", "Allow", "Handle", "Return", "Submit", "Navigate", etc.
- If images are provided, analyze them to understand the feature being tested and use that context.

Respond ONLY with a valid JSON array of strings (the titles), no explanations, no markdown code blocks.
Example: ["Check that the login page displays an error for incorrect credentials", "Ensure the dashboard loads after a successful authentication"]
"""

SYSTEM_PROMPT = """Eres un experto en QA y testing de software especializado en metodología BDD (Behavior Driven Development).
Tu tarea es generar casos de prueba en formato Gherkin listos para importar en TestRail usando el template "Behaviour Driven Development".

REGLAS IMPORTANTES:
- Determina la cantidad óptima de casos de prueba según la complejidad del requerimiento (mínimo 3, máximo 15).
- Cada caso debe cubrir un escenario distinto (happy path, casos borde, errores, seguridad, etc.).
- Si se incluyen imágenes, analízalas detalladamente y úsalas como contexto visual para generar mejores escenarios.
- Si se incluyen fragmentos de código o JSON, analízalos para entender la estructura de datos y generar escenarios precisos.
- Responde ÚNICAMENTE con un array JSON válido, sin explicaciones adicionales, sin bloques de código markdown.
- El JSON debe seguir exactamente el esquema indicado.
- TODOS los textos del JSON (títulos, precondiciones, pasos, resultados esperados) deben estar en INGLÉS.

FORMATO DE PRIORIDADES (usar exactamente estos valores):
- "1 - Must Test"
- "2 - Run Before Release"
- "3 - Normal"
- "4 - Nice to Have"

FORMATO custom_bdd_scenarios: Escenario Gherkin completo con Feature, Background (si aplica) y Scenario.
Usa \\n para saltos de línea y dos espacios de indentación.
Ejemplo:
  Feature: User Login\\n  Background:\\n    Given the user is on the login page\\n  Scenario: Successful login\\n    When the user enters valid credentials\\n    Then the user is redirected to the dashboard
"""


def prompt_from_jira(data: JiraInput) -> str:
    return f"""Generate BDD test cases from the following Jira user story.

USER STORY:
{data.description}

ACCEPTANCE CRITERIA:
{data.acceptance_criteria}

REFERENCE TICKET: {data.jira_ticket or "N/A"}

Return a JSON array where each object has EXACTLY these keys:
- "title": Descriptive test case title (max 120 chars)
- "section": Section/suite name (e.g. "Login", "Checkout", etc.)
- "template": Always use "Behaviour Driven Development"
- "type": Test type ("Functional", "Integration", "Security", "Regression", "Acceptance")
- "priority": Exactly one of: "1 - Must Test", "2 - Run Before Release", "3 - Normal", "4 - Nice to Have"
- "estimate": Time estimate in minutes (e.g. "3m", "5m", "10m")
- "refs": Reference to Jira ticket (use the ticket provided or leave empty)
- "custom_preconds": Preconditions required to run the test case
- "custom_bdd_scenarios": Complete Gherkin scenario (Feature + optional Background + Scenario) with newlines as \\n
"""


def prompt_from_testrail(data: TestRailInput) -> str:
    steps_text = "\n".join(
        f"Step {i+1}: {s.step}\n  Validation: {s.validation}"
        for i, s in enumerate(data.steps)
    )
    return f"""Transform the following manual test case into improved BDD test cases.

TITLE / CONTEXT: {data.title_hint or "Not specified"}

PRECONDITIONS:
{data.preconditions}

TEST DATA:
{data.test_data or "Not specified"}

STEPS AND VALIDATIONS:
{steps_text}

Analyze these steps and generate multiple BDD scenarios covering:
1. The main flow (happy path)
2. Variations with test data
3. Relevant error or edge cases

Return a JSON array where each object has EXACTLY these keys:
- "title": Descriptive test case title (max 120 chars)
- "section": Section/suite name inferred from context
- "template": Always use "Behaviour Driven Development"
- "type": Test type ("Functional", "Integration", "Security", "Regression", "Acceptance")
- "priority": Exactly one of: "1 - Must Test", "2 - Run Before Release", "3 - Normal", "4 - Nice to Have"
- "estimate": Time estimate in minutes (e.g. "3m", "5m", "10m")
- "refs": Leave empty ("")
- "custom_preconds": Required preconditions
- "custom_bdd_scenarios": Complete Gherkin scenario (Feature + optional Background + Scenario) with newlines as \\n
"""


def prompt_from_batch_item(item: BatchItem) -> str:
    desc_block = f"\nDESCRIPTION / CONTEXT:\n{item.description}" if item.description else ""
    return f"""Generate BDD test cases for the following requirement.

TITLE / CONTEXT: {item.title}
SECTION: {item.section or "Not specified"}
REFERENCE: {item.refs or "N/A"}{desc_block}

Return a JSON array where each object has EXACTLY these keys:
- "title": Descriptive BDD test case title based on the context (max 120 chars)
- "section": Use "{item.section or 'General'}" as the section name
- "template": Always use "Behaviour Driven Development"
- "type": Test type ("Functional", "Integration", "Security", "Regression", "Acceptance")
- "priority": Exactly one of: "1 - Must Test", "2 - Run Before Release", "3 - Normal", "4 - Nice to Have"
- "estimate": Time estimate in minutes (e.g. "3m", "5m", "10m")
- "refs": Use "{item.refs}" as reference
- "custom_preconds": Preconditions required to run the test case
- "custom_bdd_scenarios": Complete Gherkin scenario (Feature + optional Background + Scenario) with newlines as \\n
"""
