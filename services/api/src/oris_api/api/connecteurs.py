"""Voyants Doctolib et SmileCloud (colonne de gauche du site, Paramètres de l'iPhone)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

from oris_api.api.dependencies import ActorDep, depuis_cette_machine
from oris_api.services import connecteurs
from oris_api.services.errors import Forbidden, Unprocessable

router = APIRouter(tags=["connecteurs"])


class VoyantOut(BaseModel):
    etat: str
    ton: Literal["actif", "alerte", "travail", "neutre"]
    detail: str
    ouvrir: Literal["doctolib", "smilecloud"] | None


class ConnecteursOut(BaseModel):
    doctolib: VoyantOut
    smilecloud: VoyantOut
    #: Seul ce Mac peut ouvrir Chrome : l'iPhone voit l'état, sans le bouton.
    peut_ouvrir: bool


class OuvrirIn(BaseModel):
    site: Literal["doctolib", "smilecloud"]


@router.get("/connecteurs", response_model=ConnecteursOut)
def etat(request: Request, actor: ActorDep) -> ConnecteursOut:
    v = connecteurs.voyants(connecteurs.lire_etat_dental_lens())
    return ConnecteursOut(
        doctolib=VoyantOut(**v["doctolib"]),
        smilecloud=VoyantOut(**v["smilecloud"]),
        peut_ouvrir=depuis_cette_machine(request),
    )


@router.post("/connecteurs/ouvrir", status_code=204)
def ouvrir(body: OuvrirIn, request: Request, actor: ActorDep) -> None:
    """Ouvre Doctolib (ou SmileCloud) dans Chrome, sur le Mac : c'est ainsi qu'on se
    reconnecte. Réservé à ce Mac — un iPhone n'ouvre pas Chrome à distance."""
    if not depuis_cette_machine(request):
        raise Forbidden("CONNECTEUR_DEPUIS_CE_MAC")
    if not connecteurs.ouvrir(body.site):
        raise Unprocessable("DENTAL_LENS_INJOIGNABLE")
