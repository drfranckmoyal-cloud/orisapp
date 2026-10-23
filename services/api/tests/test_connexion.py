"""Se connecter avec un mail et un mot de passe (étape 1 de la commercialisation).

Franck, le 24/10/2026 : « j'en ai marre de mettre des jetons, c'est chiant ». Ces essais
gardent la porte qui les remplace : elle délivre un jeton à qui prouve son identité, et
rien à personne d'autre.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from oris_api.db.models import ApiToken, User
from oris_api.services import authentication

MOT_DE_PASSE = "un-vrai-mot-de-passe"


def praticien(api: Any, engine: Any, mot_de_passe: str | None = MOT_DE_PASSE) -> str:
    """Pose un mot de passe sur le praticien du cabinet, et rend son mail.

    Le praticien naît au premier appel servi : on en fait donc un avant de le chercher.
    """
    api.get("/patients")
    with Session(engine) as session:
        user = session.scalars(select(User)).first()
        assert user is not None, "aucun praticien en base"
        if mot_de_passe is not None:
            authentication.poser_mot_de_passe(session, user, mot_de_passe)
        session.commit()
        return user.email


def test_the_right_password_hands_out_a_token_that_actually_works(
    api: Any, migrated_engine: Any
) -> None:
    email = praticien(api, migrated_engine)

    reponse = api.post(
        "/auth/login",
        json={"email": email, "mot_de_passe": MOT_DE_PASSE, "appareil": "iPhone de Franck"},
    )

    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["email"] == email
    assert corps["jeton"].startswith("oris_")
    # Le jeton délivré ouvre vraiment les portes : c'est tout l'intérêt.
    avec = api.get("/patients", headers={"Authorization": f"Bearer {corps['jeton']}"})
    assert avec.status_code == 200
    # Et il porte le nom de l'appareil, pour pouvoir le déconnecter plus tard.
    with Session(migrated_engine) as session:
        jeton = session.get(ApiToken, corps["appareil_id"])
        assert jeton is not None and jeton.label == "iPhone de Franck"


def test_a_wrong_password_says_nothing_about_what_was_wrong(api: Any, migrated_engine: Any) -> None:
    """Compte inconnu, compte sans mot de passe et mot de passe faux se ressemblent de
    l'extérieur : sinon la porte apprend à qui écrire."""
    email = praticien(api, migrated_engine)

    refus = [
        api.post("/auth/login", json={"email": email, "mot_de_passe": "pas-le-bon-du-tout"}),
        api.post(
            "/auth/login", json={"email": "inconnu@nulle-part.fr", "mot_de_passe": MOT_DE_PASSE}
        ),
    ]

    assert [r.status_code for r in refus] == [403, 403]
    assert {r.json()["code"] for r in refus} == {"IDENTIFIANTS_REFUSES"}


def test_a_compte_without_password_cannot_be_opened(api: Any, migrated_engine: Any) -> None:
    email = praticien(api, migrated_engine, mot_de_passe=None)
    refus = api.post("/auth/login", json={"email": email, "mot_de_passe": MOT_DE_PASSE})
    assert (refus.status_code, refus.json()["code"]) == (403, "IDENTIFIANTS_REFUSES")


def test_guessing_stops_being_worth_it(api: Any, migrated_engine: Any) -> None:
    """Après cinq essais manqués, le compte cesse de répondre — même au bon mot de passe.
    C'est ce qui rend la devinette vaine sur une porte ouverte à tout Internet."""
    email = praticien(api, migrated_engine)

    for _ in range(authentication.ESSAIS_AVANT_BLOCAGE):
        api.post("/auth/login", json={"email": email, "mot_de_passe": "faux"})

    bloque = api.post("/auth/login", json={"email": email, "mot_de_passe": MOT_DE_PASSE})
    assert (bloque.status_code, bloque.json()["code"]) == (403, "COMPTE_BLOQUE")


def test_a_password_too_short_is_refused_when_it_is_set() -> None:
    from oris_api.services.errors import Unprocessable

    user = User(email="x@y.fr", name="Essai", role="practitioner")
    try:
        authentication.poser_mot_de_passe(Session(), user, "court")
    except Unprocessable as refus:
        assert refus.code == "PASSWORD_TOO_SHORT"
    else:
        raise AssertionError("un mot de passe trop court doit être refusé")


def test_the_door_itself_needs_no_token(api: Any) -> None:
    """Évident, et c'est bien pour ça qu'il faut le figer : une connexion qui exigerait
    un jeton ne servirait à rien."""
    sans_jeton = api.post("/auth/login", json={"email": "x@y.fr", "mot_de_passe": "x" * 12})
    assert sans_jeton.status_code != 401
