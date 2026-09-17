"""Aucune donnée de santé dans les journaux (spec §67)."""

from __future__ import annotations

import io
import json
import logging

from fastapi.testclient import TestClient

from oris_api.main import app
from oris_api.observability import PhiSafeJsonFormatter

PHI = "Dupont-Synthétique fracture 27"


def capture() -> tuple[io.StringIO, logging.Handler]:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(PhiSafeJsonFormatter())
    logging.getLogger().addHandler(handler)
    return stream, handler


def test_non_allowlisted_extra_fields_are_dropped() -> None:
    stream, handler = capture()
    try:
        logging.getLogger("oris.test").info(
            "encounter.processed",
            extra={"encounter_id": "enc-1", "patient_name": PHI, "transcript": PHI},
        )
    finally:
        logging.getLogger().removeHandler(handler)
    line = json.loads(stream.getvalue().strip())
    assert line["event"] == "encounter.processed"
    assert line["encounter_id"] == "enc-1"
    assert PHI not in stream.getvalue()


def test_exception_messages_are_not_logged() -> None:
    stream, handler = capture()
    try:
        try:
            raise ValueError(PHI)
        except ValueError:
            logging.getLogger("oris.test").exception("extraction.failed")
    finally:
        logging.getLogger().removeHandler(handler)
    line = json.loads(stream.getvalue().strip())
    assert line["exception_type"] == "ValueError"
    assert line["exception_frames"]
    assert PHI not in stream.getvalue()


def test_request_log_uses_route_template_without_query_string() -> None:
    stream, handler = capture()
    try:
        with TestClient(app) as client:
            client.get("/health", params={"patient": PHI})
            client.get("/patients/Dupont-Synthétique")
    finally:
        logging.getLogger().removeHandler(handler)
    output = stream.getvalue()
    assert "Dupont" not in output
    routes = [json.loads(line).get("route") for line in output.splitlines() if line]
    assert "/health" in routes
    # Chemin brut contenant un nom : seul le gabarit de route est écrit.
    assert "/patients/{patient_id}" in routes


def test_full_consultation_flow_logs_no_clinical_content(api: object) -> None:
    from oris_api.synthetic.corpus import default_corpus
    from tests.conftest import documents_by_type, run_synthetic

    case = default_corpus().get("ORIS-SYN-001")
    assert case is not None
    forbidden = [case.patient_first_name, case.patient_last_name, "diastème", "asymétrie"]
    forbidden += [segment.text[:30] for segment in case.segments]

    stream, handler = capture()
    try:
        encounter = run_synthetic(api, case.case_id)
        docs = documents_by_type(api, encounter["id"])
        api.post(f"/documents/{docs['consultation_note']['id']}/validate", json={})  # type: ignore[attr-defined]
        api.get("/patients", params={"q": case.patient_last_name})  # type: ignore[attr-defined]
    finally:
        logging.getLogger().removeHandler(handler)
    output = stream.getvalue()
    assert "pipeline.completed" in output
    for text in forbidden:
        assert text not in output
