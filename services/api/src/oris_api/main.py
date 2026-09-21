"""Point d'entrée FastAPI.

Lancement local : `uvicorn oris_api.main:app --reload --no-access-log`
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from oris_api import __version__
from oris_api.api import (
    audio,
    connecteurs,
    correspondents,
    deliveries,
    encounters,
    envoi,
    figures,
    health,
    journee,
    maintenance,
    patients,
    personalization,
    smilecloud,
    synthetic,
)
from oris_api.api.schemas import ApiErrorBody
from oris_api.config import get_settings
from oris_api.observability import configure_logging, request_logging_middleware
from oris_api.providers import build_providers
from oris_api.services.audio_sink import build_sink
from oris_api.services.courriel import messagerie_de
from oris_api.services.errors import ServiceError
from oris_api.services.live import LiveTranscription


async def service_error_handler(request: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, ServiceError)  # noqa: S101
    body = ApiErrorBody(code=error.code, subject_id=error.subject_id, details=error.details)
    return JSONResponse(status_code=error.status_code, content=body.model_dump())


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """L'écoute en direct a besoin de la boucle de l'application : on la lui donne ici."""
    app.state.live.bind_loop(asyncio.get_running_loop())
    yield
    app.state.live.shutdown()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    app = FastAPI(title="Oris API", version=__version__, lifespan=lifespan)
    app.state.live = LiveTranscription()
    # Refuse de démarrer si un fournisseur configuré n'est pas disponible.
    app.state.providers = build_providers(settings)
    app.state.audio_sink = build_sink(settings)
    app.state.messagerie = messagerie_de(settings)
    app.middleware("http")(request_logging_middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Chunk-Timestamp-Ms", "X-Chunk-Checksum"],
        # Sans cela, le site ne peut pas lire le nom du PDF et le télécharge « document ».
        expose_headers=["Content-Disposition"],
    )
    app.add_exception_handler(ServiceError, service_error_handler)
    app.include_router(health.router)
    app.include_router(patients.router)
    app.include_router(correspondents.router)
    app.include_router(journee.router)
    app.include_router(connecteurs.router)
    app.include_router(smilecloud.router)
    app.include_router(encounters.router)
    app.include_router(deliveries.router)
    app.include_router(envoi.router)
    app.include_router(figures.router)
    app.include_router(synthetic.router)
    app.include_router(audio.router)
    app.include_router(personalization.router)
    app.include_router(maintenance.router)
    return app


app = create_app()
