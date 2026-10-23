"""Se connecter à Oris : mail et mot de passe, en échange d'un jeton d'appareil.

Jusqu'au 24 octobre 2026, relier un iPhone demandait de recopier à la main un jeton de
quarante-huit caractères depuis le Mac. C'était un défaut de conception, et il a coûté
deux semaines à Franck : son téléphone joignait le serveur, se faisait refuser, et
l'écran annonçait « serveur injoignable ».

Ce qui circule à chaque appel ne change pas — c'est toujours le jeton, et lui seul a
fait ses preuves. Ce qui change, c'est qu'on l'obtient en se connectant. Un jeton par
appareil : un téléphone perdu se déconnecte depuis « Appareils connectés », sans toucher
aux autres.

**Cette route ne demande aucun jeton** : c'est elle qui en délivre. Elle est donc la
seule porte ouverte, et c'est pour ça qu'elle compte les essais manqués.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter
from pydantic import BaseModel, Field, StringConstraints

from oris_api.api.dependencies import SessionDep
from oris_api.services import authentication

router = APIRouter(prefix="/auth", tags=["auth"])


class ConnexionIn(BaseModel):
    email: Annotated[str, StringConstraints(max_length=320)]
    mot_de_passe: Annotated[str, StringConstraints(max_length=200)]
    #: Le nom de l'appareil, tel qu'il apparaîtra dans « Appareils connectés ».
    appareil: Annotated[str, Field(max_length=100)] = "appareil"


class ConnexionOut(BaseModel):
    #: Le jeton à garder, et à présenter à chaque appel. Donné une seule fois.
    jeton: str
    #: Pour que l'appareil puisse le nommer dans ses réglages et le révoquer.
    appareil_id: str
    praticien: str
    email: str


@router.post("/login", response_model=ConnexionOut)
def login(body: ConnexionIn, session: SessionDep) -> ConnexionOut:
    user, emis = authentication.connecter(
        session, body.email, body.mot_de_passe, body.appareil.strip()
    )
    session.commit()
    return ConnexionOut(
        jeton=emis.secret,
        appareil_id=str(emis.token_id),
        praticien=user.name,
        email=user.email,
    )
