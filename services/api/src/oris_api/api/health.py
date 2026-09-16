"""Santé du service : processus (`/health`) et dépendances (`/health/ready`)."""

from __future__ import annotations

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from oris_api import __version__
from oris_api.config import AppEnv, Settings, get_settings
from oris_api.db.session import get_session

router = APIRouter(tags=["health"])
logger = logging.getLogger("oris.health")


class ProviderStatus(BaseModel):
    speech_to_text: str
    clinical_extraction: str
    document_generation: str
    clinical_validation: str


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: Literal["oris-api"]
    version: str
    environment: AppEnv
    providers: ProviderStatus


class ReadinessResponse(BaseModel):
    status: Literal["ready", "unavailable"]
    database: Literal["ok", "unreachable"]


@router.get("/health", response_model=HealthResponse)
def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="oris-api",
        version=__version__,
        environment=settings.app_env,
        providers=ProviderStatus(
            speech_to_text=settings.stt_provider,
            clinical_extraction=settings.clinical_extraction_provider,
            document_generation=settings.document_generation_provider,
            clinical_validation=settings.clinical_validation_provider,
        ),
    )


@router.get("/health/ready", response_model=ReadinessResponse)
def ready(
    session: Annotated[Session, Depends(get_session)], response: Response
) -> ReadinessResponse:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.warning("health.database_unreachable", extra={"component": "database"})
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(status="unavailable", database="unreachable")
    return ReadinessResponse(status="ready", database="ok")
