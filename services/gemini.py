import base64
import json
from typing import List

from fastapi import HTTPException
from google import genai
from google.genai import types as genai_types

from config import GEMINI_API_KEY
from services.prompts import SYSTEM_PROMPT


def get_gemini_client():
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY no configurada en el archivo .env")
    return genai.Client(api_key=GEMINI_API_KEY, http_options={"api_version": "v1beta"})


def call_gemini(user_prompt: str, images: List[str] = []) -> List[dict]:
    try:
        client = get_gemini_client()

        # Construir contenido multimodal si hay imágenes
        if images:
            parts: list = [genai_types.Part.from_text(text=user_prompt)]
            for img_b64 in images[:3]:
                if ',' in img_b64:
                    header, data = img_b64.split(',', 1)
                    mime = header.split(';')[0].split(':')[1]
                else:
                    data = img_b64
                    mime = 'image/jpeg'
                parts.append(genai_types.Part.from_bytes(
                    data=base64.b64decode(data),
                    mime_type=mime,
                ))
            contents = parts
        else:
            contents = user_prompt

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            config=genai_types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
            ),
            contents=contents,
        )
        text_content = response.text
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al llamar a Gemini: {type(e).__name__}: {str(e)}")

    if not text_content:
        raise HTTPException(status_code=500, detail="El modelo no devolvió contenido de texto")

    text_content = text_content.strip()
    if text_content.startswith("```"):
        lines = text_content.split("\n")
        text_content = "\n".join(lines[1:])
        if text_content.endswith("```"):
            text_content = text_content[:-3].strip()

    try:
        test_cases = json.loads(text_content)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"El modelo devolvió JSON inválido: {str(e)}\n\nRespuesta: {text_content[:500]}"
        )

    if not isinstance(test_cases, list):
        raise HTTPException(status_code=500, detail="El modelo no devolvió un array de casos")

    return test_cases


call_claude = call_gemini  # alias


def call_titles_gemini(user_prompt: str, images: List[str] = []) -> List[str]:
    from services.prompts import TITLE_SYSTEM_PROMPT

    try:
        client = get_gemini_client()

        if images:
            parts: list = [genai_types.Part.from_text(text=user_prompt)]
            for img_b64 in images[:3]:
                if ',' in img_b64:
                    header, d = img_b64.split(',', 1)
                    mime = header.split(';')[0].split(':')[1]
                else:
                    d, mime = img_b64, 'image/jpeg'
                parts.append(genai_types.Part.from_bytes(data=base64.b64decode(d), mime_type=mime))
            contents = parts
        else:
            contents = user_prompt

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            config=genai_types.GenerateContentConfig(system_instruction=TITLE_SYSTEM_PROMPT),
            contents=contents,
        )
        text_content = (response.text or '').strip()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al llamar a Gemini: {type(e).__name__}: {str(e)}")

    if text_content.startswith("```"):
        lines = text_content.split("\n")
        text_content = "\n".join(lines[1:])
        if text_content.endswith("```"):
            text_content = text_content[:-3].strip()

    try:
        titles = json.loads(text_content)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"El modelo devolvió JSON inválido: {str(e)}\n\nRespuesta: {text_content[:500]}"
        )

    if not isinstance(titles, list):
        raise HTTPException(status_code=500, detail="El modelo no devolvió una lista de títulos")

    return [str(t) for t in titles]
