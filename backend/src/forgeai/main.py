from fastapi import FastAPI

from forgeai.api.health import router as health_router
from forgeai.api.tasks import router as tasks_router
from forgeai.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.include_router(health_router)
app.include_router(tasks_router)

@app.get("/")
def root() -> dict[str, str]:
    return {"name": settings.app_name, "version": settings.app_version}
