from fastapi import APIRouter

from app.config.settings import settings
from app.services.data_service import data_service

router = APIRouter()


@router.get("/health")
def health_check():
    """Check API and data service health."""
    data_loaded = (
        data_service.df is not None and len(data_service.df) > 0
    )

    return {
        "status": "ok",
        "version": settings.VERSION,
        "data_loaded": data_loaded,
    }
