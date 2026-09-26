import time
from fastapi import APIRouter
from backend.app.core.config import settings

router = APIRouter(tags=["Health"])

START_TIME = time.time()

@router.get("/health", summary="Application Health Check")
async def health_check():
    """
    Returns the operational status, application version, environment, and uptime.
    """
    uptime_seconds = round(time.time() - START_TIME, 2)
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "uptime_seconds": uptime_seconds,
        "llm_provider": settings.LLM_PROVIDER,
        "embedding_model": settings.EMBEDDING_MODEL,
        "vector_db_type": settings.VECTOR_DB_TYPE
    }
