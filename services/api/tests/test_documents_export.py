"""Sortie des documents : PDF, texte pour le dossier, statut `exported` (spec §78–79)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

from oris_api.documents.export import LAYOUTS, ExportContext, render_pdf, render_text
from tests.conftest import documents_by_type, run_synthetic


def context(**overrides: Any) -> ExportContext:
    base = {
        "document_type": "consultation_note",
        "content": (
            "Motif de consultation\nRapporté par le patient : douleur au froid (16).\n\n"
            "Examen clinique\nConstaté : fissure (16).\n"
        ),
        "practitioner": "Dr Praticien Démo",
        "organization": "Cabinet de démonstration",
        "patient": "Léa Fictive",
        "encounter_date": datetime(2026, 9, 19, 9, 30, tzinfo=UTC),
        "validated_at": None,
        "version": 1,
    }
    return ExportContext(**{**base, **overrides})


def test_text_export_is_the_document_itself() -> None:
    plain = render_text(context(), structured=False)
    assert plain.startswith("Motif de consultation")
    assert "Cabinet" not in plain  # rien n'est ajouté au texte brut


def test_structured_text_says_who_for_whom_and_whether_it_is_validated() -> None:
    draft = render_text(context(), structured=True)
    assert "Cabinet de démonstration — Dr Praticien Démo" in draft
    assert "Patient : Léa Fictive" in draft
    assert "Consultation du 19/09/2026" in draft
    assert "Brouillon — non validé par le praticien." in draft

    validated = render_text(
        context(validated_at=datetime(2026, 9, 19, 10, 0, tzinfo=UTC)), structured=True
    )
    assert "Validé par le praticien le 19/09/2026 à 10:00." in validated
    assert "Brouillon" not in validated


def test_pdf_is_a_real_pdf_and_paginates_long_documents() -> None:
    short = render_pdf(context())
    assert short.startswith(b"%PDF")
    long_content = "Examen clinique\n" + "\n".join(
        f"Constaté : fissure (1{index % 8 + 1})." for index in range(200)
    )
    long = render_pdf(context(content=long_content))
    assert long.count(b"/Type /Page\n") > short.count(b"/Type /Page\n")


def test_exporting_a_draft_does_not_change_its_status(api: Any) -> None:
    eid = run_synthetic(api, "ORIS-SYN-092")["id"]
    note = documents_by_type(api, eid)["consultation_note"]
    assert note["status"] == "draft_ai"
    response = api.get(f"/documents/{note['id']}/export", params={"format": "pdf"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    # Le nom de fichier ne porte pas le patient.
    assert 'filename="oris-compte-rendu-' in response.headers["content-disposition"]
    assert documents_by_type(api, eid)["consultation_note"]["status"] == "draft_ai"


def test_exporting_validated_documents_marks_the_consultation_exported(api: Any) -> None:
    eid = run_synthetic(api, "ORIS-SYN-092")["id"]
    docs = documents_by_type(api, eid)
    for document in docs.values():
        api.post(f"/documents/{document['id']}/validate", json={"acknowledged_warning_codes": []})
    assert api.post(f"/encounters/{eid}/validate").json()["status"] == "validated"

    for index, document in enumerate(docs.values()):
        exported = api.get(f"/documents/{document['id']}/export", params={"format": "structured"})
        assert exported.status_code == 200
        assert "Validé par le praticien" in exported.text
        remaining = len(docs) - index - 1
        expected = "validated" if remaining else "exported"
        assert api.get(f"/encounters/{eid}").json()["status"] == expected
    assert all(d["status"] == "exported" for d in documents_by_type(api, eid).values())


def test_unknown_document_cannot_be_exported(api: Any) -> None:
    response = api.get(
        "/documents/00000000-0000-0000-0000-000000000000/export", params={"format": "text"}
    )
    assert response.status_code == 404
    assert response.json()["code"] == "DOCUMENT_NOT_FOUND"


def test_each_document_type_has_its_own_layout() -> None:
    from oris_api.documents.export import layout_for

    titles = {
        kind: layout_for(kind).title
        for kind in (
            "consultation_note",
            "treatment_plan_text",
            "operative_note",
            "referral_letter",
            "patient_summary",
        )
    }
    assert titles["consultation_note"] == "Compte rendu de consultation"
    assert titles["operative_note"] == "Compte rendu opératoire"
    assert titles["referral_letter"] == "Courrier d’adressage"
    assert len(set(titles.values())) == len(titles)
    assert layout_for("inconnu").title == "Document"


def test_a_letter_to_a_colleague_opens_and_closes_like_a_letter() -> None:
    from oris_api.documents.export import body_blocks, layout_for

    layout = layout_for("referral_letter")
    lines = [line for _, line in body_blocks(context(document_type="referral_letter"), layout, 400)]
    assert lines[0] == "Cher confrère,"
    assert "Bien confraternellement," in lines
    assert lines[-1] == "Dr Praticien Démo"  # la signature est le praticien


def test_the_patient_summary_is_bigger_and_says_what_it_is() -> None:
    from oris_api.documents.export import body_blocks, layout_for

    patient = layout_for("patient_summary")
    clinical = layout_for("consultation_note")
    assert patient.body_size > clinical.body_size
    assert patient.leading > clinical.leading
    lines = [
        line for _, line in body_blocks(context(document_type="patient_summary"), patient, 400)
    ]
    assert any("résume" in line for line in lines)
    assert "information" in patient.footer_note


def test_every_layout_produces_a_pdf() -> None:
    for kind in LAYOUTS:
        pdf = render_pdf(context(document_type=kind))
        assert pdf.startswith(b"%PDF"), kind


def test_a_cabinet_without_configuration_still_prints(tmp_path: Any) -> None:
    from oris_api.documents.theme import Cabinet

    missing = Cabinet.load(tmp_path / "absent.json")
    assert missing.name == "Cabinet" and missing.logo is None
    assert missing.contact_lines() == []
    # Un document sort quand même, sans logo ni coordonnées.
    assert render_pdf(context(), cabinet=missing).startswith(b"%PDF")


def test_configured_cabinet_details_are_printed(tmp_path: Any) -> None:
    import json

    from oris_api.documents.theme import Cabinet

    path = tmp_path / "cabinet.json"
    path.write_text(
        json.dumps(
            {
                "name": "Cabinet des Lilas",
                "address": "12 rue des Lilas, 75000 Paris",
                "phone": "01 23 45 67 89",
                "email": "",
                "legal": "RPPS 10101010101",
                "logo_path": "",
            }
        ),
        encoding="utf-8",
    )
    cabinet = Cabinet.load(path)
    assert cabinet.name == "Cabinet des Lilas"
    # Les champs vides ne laissent pas de ligne vide sur la page.
    assert cabinet.contact_lines() == [
        "12 rue des Lilas, 75000 Paris",
        "01 23 45 67 89",
        "RPPS 10101010101",
    ]


def test_the_patient_block_says_who_referred_the_patient_only_when_known() -> None:
    from oris_api.documents.export import layout_for, patient_rows

    layout = layout_for("consultation_note")
    sans = patient_rows(context(), layout)
    assert [label for label, _ in sans] == ["Patient(e)", "Date de consultation"]

    avec = patient_rows(replace(context(), referred_by="Dr Claire Martin · ODF"), layout)
    assert ("Adressé(e) par", "Dr Claire Martin · ODF") in avec


def test_a_letter_names_its_recipient_instead_of_the_referrer() -> None:
    from oris_api.documents.export import layout_for, patient_rows

    lettre = replace(
        context(), document_type="referral_letter", referred_by="Dr A", recipient="Dr B"
    )
    rows = patient_rows(lettre, layout_for("referral_letter"))
    assert ("Destinataire", "Dr B") in rows
    assert all(label != "Adressé(e) par" for label, _ in rows)


def test_the_title_is_never_printed_twice() -> None:
    from oris_api.documents.export import signature
    from oris_api.documents.theme import Cabinet

    cabinet = Cabinet(practitioner_title="Dr")
    assert signature(context(practitioner="Franck Moyal"), cabinet) == "Dr Franck Moyal"
    assert signature(context(practitioner="Dr Franck Moyal"), cabinet) == "Dr Franck Moyal"
