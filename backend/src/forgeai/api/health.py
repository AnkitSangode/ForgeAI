from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from forgeai.infrastructure.session import engine

router = APIRouter(prefix="/api/v1/health",tags=["health"])


@router.get("/live")
def liveness() -> dict[str, str]:
    return {"status": "alive"}

@router.get("/ready")
def readiness() -> dict[str,str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code= 503,
            detail= "database in unavailable",
        ) from exc
    return {"status":"ready"}