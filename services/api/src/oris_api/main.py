"""Point d'entrée FastAPI.

Lancement local : `uvicorn oris_api.main:app --reload --no-access-log`
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from oris_api import __version__
from oris_api.api import health
from oris_api.config import get_settings
from oris_api.observability import configure_logging, request_logging_middleware
from oris_api.providers import build_providers


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    app = FastAPI(title="Oris API", version=__version__)
    # Refuse de démarrer si un fournisseur configuré n'est pas disponible.
    app.state.providers = build_providers(settings)
    app.middleware("http")(request_logging_middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(health.router)
    return app


app = create_app()
