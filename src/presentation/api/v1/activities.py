"""
Endpoints de gestion des evenements et des participants.

Evenements (Admin / Aumonier) :
    POST   /                          Creer un evenement (avec participants)
    PATCH  /{event_id}                Modifier un evenement
    DELETE /{event_id}                Supprimer un evenement

Evenements (tous les utilisateurs authentifies) :
    GET    /                          Liste paginee des evenements
    GET    /me                        Mes evenements (en tant que participant)
    GET    /{event_id}                Detail d'un evenement + participants

Participants (Admin / Aumonier) :
    POST   /{event_id}/participants                Ajouter un participant
    PATCH  /{event_id}/participants/{id}           Modifier un participant
    DELETE /{event_id}/participants/{id}            Retirer un participant

Participants (self-service) :
    PATCH  /{event_id}/my-participation            Confirmer/decliner ma participation
"""

from datetime import datetime
from src.core.utils import utc_now
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Body,
    Depends,
    Header,
    HTTPException,
    Query,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.event_service import EventService
from src.core.entities.event import EventStatus, EventType, ParticipantStatus
from src.core.entities.user import User
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.event_repository import EventRepository
from src.infrastructure.repositories.user_repository import UserRepository
from src.presentation.dependencies.auth_deps import (
    get_current_active_user,
    get_current_admin_or_aumonier,
)
from src.presentation.schemas.event import (
    EventCreate,
    EventDetailResponse,
    EventResponse,
    EventUpdate,
    ParticipantAdd,
    ParticipantResponse,
    ParticipantUpdate,
)
from src.presentation.schemas.user import PaginatedResponse

router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────────────────
def _get_event_service(session: AsyncSession) -> EventService:
    return EventService(
        event_repository=EventRepository(session),
        user_repository=UserRepository(session),
    )


# ═══════════════════════════════════════════════════════════════════════════
#  CRUD EVENEMENTS
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/", response_model=PaginatedResponse[EventResponse])
async def list_events(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    event_type: Optional[EventType] = Query(None, description="Filtrer par type"),
    event_status: Optional[EventStatus] = Query(None, alias="status", description="Filtrer par statut"),
    start_date: Optional[datetime] = Query(None, description="Date de debut minimum"),
    end_date: Optional[datetime] = Query(None, description="Date de debut maximum"),
    search: Optional[str] = Query(None, max_length=100, description="Recherche par titre ou lieu"),
    page: int = Query(1, ge=1, description="Numero de page"),
    page_size: int = Query(20, ge=1, le=100, description="Taille de page"),
):
    """
    Liste paginee des evenements avec filtres.

    Accessible a **tous les utilisateurs authentifies**.
    """
    service = _get_event_service(session)
    return await service.list_events(
        event_type=event_type,
        event_status=event_status,
        start_date=start_date,
        end_date=end_date,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get("/me", response_model=List[EventResponse])
async def get_my_events(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Mes evenements (ceux auxquels je participe).

    Accessible a **tous les utilisateurs authentifies**.
    """
    service = _get_event_service(session)
    return await service.get_my_events(current_user.id)


@router.get(
    "/calendar.ics",
    summary="Exporter tous les événements au format iCal",
    description="Retourne un fichier .ics compatible avec Google Calendar, Outlook, etc.",
    tags=["Events"],
)
async def export_all_events_ical(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Export iCal de tous les événements publiés à venir."""
    from icalendar import Calendar, Event as IEvent
    from src.core.entities.event import EventStatus

    service = _get_event_service(session)
    events_page = await service.list_events(event_status=EventStatus.PUBLIE, page=1, page_size=200)
    events = events_page.items if hasattr(events_page, "items") else []

    cal = Calendar()
    cal.add("PRODID", "-//ServantAssist//ServantAssist//FR")
    cal.add("VERSION", "2.0")
    cal.add("CALSCALE", "GREGORIAN")
    cal.add("X-WR-CALNAME", "ServantAssist — Événements")

    for ev in events:
        vevent = IEvent()
        vevent.add("UID", f"{ev.id}@servantassist")
        vevent.add("SUMMARY", ev.title)
        vevent.add("DTSTART", ev.start_time)
        vevent.add("DTEND", ev.end_time)
        vevent.add("LOCATION", getattr(ev, "location", ""))
        if ev.description:
            vevent.add("DESCRIPTION", ev.description)
        cal.add_component(vevent)

    ical_bytes = cal.to_ical()
    return Response(
        content=ical_bytes,
        media_type="text/calendar",
        headers={"Content-Disposition": 'attachment; filename="servantassist.ics"'},
    )


@router.get("/{event_id}", response_model=EventDetailResponse)
async def get_event(
    event_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Detail d'un evenement avec la liste de ses participants.

    Accessible a **tous les utilisateurs authentifies**.
    """
    service = _get_event_service(session)
    return await service.get_event(event_id)


@router.post("/", response_model=EventDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_data: EventCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Creer un evenement avec des participants optionnels.

    **Accessible a :** Admin, Aumonier.

    On peut passer une liste de `participants` directement a la creation
    pour eviter de faire plusieurs appels.
    """
    service = _get_event_service(session)
    return await service.create_event(event_data, created_by=current_user.id)


@router.patch("/{event_id}", response_model=EventDetailResponse)
async def update_event(
    event_id: UUID,
    event_data: EventUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Modifier un evenement existant (modification partielle).

    **Accessible a :** Admin, Aumonier.
    """
    service = _get_event_service(session)
    return await service.update_event(event_id, event_data, updated_by=current_user.id)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Supprimer un evenement et tous ses participants.

    **Accessible a :** Admin, Aumonier.
    """
    service = _get_event_service(session)
    await service.delete_event(event_id)


# ═══════════════════════════════════════════════════════════════════════════
#  GESTION DES PARTICIPANTS
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/{event_id}/participants", response_model=List[ParticipantResponse])
async def list_participants(
    event_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Liste des participants d'un evenement.

    Accessible a **tous les utilisateurs authentifies**.
    """
    service = _get_event_service(session)
    return await service.get_event_participants(event_id)


@router.post(
    "/{event_id}/participants",
    response_model=ParticipantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_participant(
    event_id: UUID,
    data: ParticipantAdd,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Ajouter un participant a un evenement.

    **Accessible a :** Admin, Aumonier.

    Le participant recevra le statut `INVITE` par defaut.
    """
    service = _get_event_service(session)
    return await service.add_participant(event_id, data, added_by=current_user.id)


@router.patch(
    "/{event_id}/participants/{participant_id}",
    response_model=ParticipantResponse,
)
async def update_participant(
    event_id: UUID,
    participant_id: UUID,
    data: ParticipantUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Modifier un participant (role, statut, notes).

    **Accessible a :** Admin, Aumonier.
    """
    service = _get_event_service(session)
    return await service.update_participant(event_id, participant_id, data)


@router.delete(
    "/{event_id}/participants/{participant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_participant(
    event_id: UUID,
    participant_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Retirer un participant d'un evenement.

    **Accessible a :** Admin, Aumonier.
    """
    service = _get_event_service(session)
    await service.remove_participant(event_id, participant_id)


# ═══════════════════════════════════════════════════════════════════════════
#  SELF-SERVICE PARTICIPANT
# ═══════════════════════════════════════════════════════════════════════════


@router.patch("/{event_id}/my-participation", response_model=ParticipantResponse)
async def update_my_participation(
    event_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    new_status: ParticipantStatus = Query(..., description="Nouveau statut : CONFIRME ou DECLINE"),
):
    """
    Confirmer ou decliner ma participation a un evenement.

    **Accessible a :** Tout utilisateur authentifie qui est participant.
    """
    service = _get_event_service(session)
    return await service.update_my_participation(event_id, current_user.id, new_status)


# ═══════════════════════════════════════════════════════════════════════════
#  EXPORT CALENDRIER iCal (par événement)
# ═══════════════════════════════════════════════════════════════════════════


@router.get(
    "/{event_id}/calendar.ics",
    summary="Exporter un événement au format iCal",
    description="Retourne un fichier .ics pour un événement spécifique.",
    tags=["Events"],
)
async def export_single_event_ical(
    event_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Export iCal d'un événement unique."""
    from icalendar import Calendar, Event as IEvent

    service = _get_event_service(session)
    ev = await service.get_event(event_id)
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Événement introuvable.")

    cal = Calendar()
    cal.add("PRODID", "-//ServantAssist//ServantAssist//FR")
    cal.add("VERSION", "2.0")
    cal.add("CALSCALE", "GREGORIAN")

    vevent = IEvent()
    vevent.add("UID", f"{ev.id}@servantassist")
    vevent.add("SUMMARY", ev.title)
    vevent.add("DTSTART", ev.start_time)
    vevent.add("DTEND", ev.end_time)
    vevent.add("LOCATION", getattr(ev, "location", ""))
    if ev.description:
        vevent.add("DESCRIPTION", ev.description)
    cal.add_component(vevent)

    filename = f"event_{event_id}.ics"
    return Response(
        content=cal.to_ical(),
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ═══════════════════════════════════════════════════════════════════════════
#  QR CODE — Validation de présence sans papier
# ═══════════════════════════════════════════════════════════════════════════


@router.get(
    "/{event_id}/qr-code",
    summary="Générer le QR Code de présence",
    description=(
        "Génère un QR Code PNG pour valider la présence à un événement. "
        "Le QR encode un token JWT signé valable 4 heures."
    ),
    tags=["Events"],
)
async def get_event_qr_code(
    event_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_admin_or_aumonier)],
):
    """
    Génère un QR Code PNG unique pour l'événement.

    Le QR Code encode un token JWT signé :
        {"event_id": "...", "type": "checkin", "exp": <now+4h>}

    Ce token est scanné par les servants via le check-in endpoint.
    """
    import io
    from datetime import timedelta

    import qrcode
    from jose import jwt

    from src.infrastructure.config.settings import get_settings

    settings = get_settings()

    # Vérifier que l'événement existe
    service = _get_event_service(session)
    ev = await service.get_event(event_id)
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Événement introuvable.")

    # Créer le token de check-in
    from datetime import timezone

    now = utc_now()
    payload = {
        "event_id": str(event_id),
        "type": "checkin",
        "exp": now + timedelta(hours=4),
        "iat": now,
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    # Générer le QR Code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(token)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return Response(
        content=buf.read(),
        media_type="image/png",
        headers={"Content-Disposition": f'inline; filename="qr_event_{event_id}.png"'},
    )


@router.post(
    "/{event_id}/check-in",
    summary="Valider une présence via QR Code",
    description=("Valide la présence du servant connecté à un événement " "en vérifiant le token issu du QR Code."),
    tags=["Events"],
)
async def check_in_event(
    event_id: UUID,
    token: str | None = Query(
        None,
        description="Deprecated: utilisez le header X-Checkin-Token ou le body JSON {token}",
    ),
    token_body: str | None = Body(None, embed=True, description="Token QR Code scanné"),
    token_header: str | None = Header(None, alias="X-Checkin-Token"),
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    """
    Valide la présence via le token QR Code.

    - Vérifie la signature et l'expiration du token
    - Vérifie que le token correspond à cet événement
    - Marque l'assignment du servant comme PRESENT
    """
    from jose import ExpiredSignatureError, JWTError, jwt
    from sqlmodel import select

    from src.core.entities.assignment import Assignment, AssignmentStatus
    from src.infrastructure.config.settings import get_settings

    settings = get_settings()

    # Valider le token
    token_value = token_header or token_body or token
    if not token_value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token QR Code manquant.")

    try:
        payload = jwt.decode(token_value, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="QR Code expiré. Demandez un nouveau QR Code.",
        )
    except JWTError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="QR Code invalide.")

    if payload.get("type") != "checkin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token invalide.")
    if payload.get("event_id") != str(event_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce QR Code ne correspond pas à cet événement.",
        )

    # Trouver l'assignment du servant pour cet événement
    stmt = select(Assignment).where(
        Assignment.event_id == event_id,
        Assignment.user_id == current_user.id,
        Assignment.status == AssignmentStatus.ACCEPTED,
    )
    result = await session.exec(stmt)
    assignment = result.first()

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune affectation acceptée trouvée pour cet événement.",
        )

    # Marquer comme présent
    assignment.status = AssignmentStatus.PRESENT
    from datetime import timezone

    assignment.updated_at = utc_now()
    session.add(assignment)
    await session.commit()

    return {
        "message": "Présence validée avec succès.",
        "event_id": str(event_id),
        "user_id": str(current_user.id),
        "assignment_id": str(assignment.id),
    }
