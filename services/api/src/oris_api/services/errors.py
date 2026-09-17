"""Erreurs métier exposées par l'API : un code stable, jamais de donnée clinique."""

from __future__ import annotations


class ServiceError(Exception):
    status_code = 400

    def __init__(self, code: str, subject_id: str | None = None, details: list[str] | None = None):
        self.code = code
        self.subject_id = subject_id
        self.details = details or []
        super().__init__(code)


class NotFound(ServiceError):
    status_code = 404


class Conflict(ServiceError):
    status_code = 409


class Unprocessable(ServiceError):
    status_code = 422


class Forbidden(ServiceError):
    status_code = 403
