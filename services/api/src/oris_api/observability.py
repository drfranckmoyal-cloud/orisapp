"""Journalisation sans données de santé (spec §67, docs/SECURITY.md).

Règles :
- sortie JSON, une ligne par événement ;
- seuls les champs de la liste blanche sont émis : identifiants stables, codes,
  durées. Tout autre attribut passé via `extra=` est ignoré ;
- une requête HTTP est journalisée par son gabarit de route
  (`/patients/{patient_id}`), jamais par son chemin brut ni sa query string ;
- une exception est journalisée par son type et ses emplacements dans le code,
  jamais par son message (les erreurs de validation recopient les valeurs).

Le message d'un événement doit être un code fixe (`request.completed`), pas du
texte construit à partir de données.
"""

from __future__ import annotations

import json
import logging
import sys
import time
import traceback
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import uuid4

from starlette.requests import Request
from starlette.responses import Response

ALLOWED_FIELDS = frozenset(
    {
        "request_id",
        "method",
        "route",
        "status_code",
        "duration_ms",
        "organization_id",
        "user_id",
        "patient_id",
        "encounter_id",
        "document_id",
        "provider",
        "component",
        "error_code",
    }
)

logger = logging.getLogger("oris")


class PhiSafeJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.msg if isinstance(record.msg, str) else type(record.msg).__name__,
        }
        for key in ALLOWED_FIELDS:
            if key in record.__dict__:
                payload[key] = record.__dict__[key]
        if record.exc_info and record.exc_info[1] is not None:
            exc = record.exc_info[1]
            payload["exception_type"] = type(exc).__name__
            payload["exception_frames"] = [
                f"{frame.filename}:{frame.lineno}:{frame.name}"
                for frame in traceback.extract_tb(exc.__traceback__)
            ]
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(PhiSafeJsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    # Le journal d'accès d'uvicorn écrit le chemin brut et la query string.
    logging.getLogger("uvicorn.access").disabled = True
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True


async def request_logging_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = str(uuid4())
    started = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        route = request.scope.get("route")
        logger.info(
            "request.completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "route": getattr(route, "path", "unmatched"),
                "status_code": status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 1),
            },
        )
