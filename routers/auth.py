from fastapi import APIRouter, HTTPException
from config import APP_PASSWORD

router = APIRouter()


@router.post("/api/login")
def login(payload: dict):
    if not APP_PASSWORD:
        return {"token": "open"}
    if payload.get("password") == APP_PASSWORD:
        return {"token": APP_PASSWORD}
    raise HTTPException(status_code=401, detail="Contraseña incorrecta")
