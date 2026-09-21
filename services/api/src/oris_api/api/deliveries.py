"""Routes des envois : noter à qui un document est parti, et le retirer si c'est une erreur."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from oris_api.api.dependencies import ActorDep, SessionDep
from oris_api.api.schemas import DeliveryIn, DeliveryOut
from oris_api.services import deliveries, encounters

router = APIRouter(tags=["deliveries"])


@router.get("/encounters/{encounter_id}/deliveries", response_model=list[DeliveryOut])
def list_deliveries(encounter_id: UUID, session: SessionDep, actor: ActorDep) -> list[DeliveryOut]:
    encounter = encounters.get_encounter(session, actor, encounter_id)
    return [DeliveryOut.model_validate(e) for e in deliveries.envois_de(session, encounter.id)]


@router.post(
    "/documents/{document_id}/deliveries",
    response_model=DeliveryOut,
    status_code=status.HTTP_201_CREATED,
)
def note_delivery(
    document_id: UUID, body: DeliveryIn, session: SessionDep, actor: ActorDep
) -> DeliveryOut:
    envoi = deliveries.noter(
        session,
        actor,
        document_id,
        body.recipient_kind,
        body.channel,
        body.correspondent_id,
        body.recipient_label,
    )
    return DeliveryOut.model_validate(envoi)


@router.delete("/deliveries/{delivery_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_delivery(delivery_id: UUID, session: SessionDep, actor: ActorDep) -> None:
    deliveries.annuler(session, actor, delivery_id)
