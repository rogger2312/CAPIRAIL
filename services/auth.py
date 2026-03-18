from typing import Optional
from fastapi import HTTPException, Header
from config import APP_PASSWORD


def verify_token(authorization: Optional[str] = Header(None)):
    if not APP_PASSWORD:
        return  # sin contraseña configurada, acceso libre
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No autorizado")
    if authorization.split(" ", 1)[1] != APP_PASSWORD:
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")
