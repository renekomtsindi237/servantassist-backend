"""
Auth commands — création d'invitations (CQRS).
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from src.core.entities.invitation import InvitationCode
from src.core.entities.user import UserRole
from src.core.interfaces.repositories import IInvitationRepository
from src.core.events.domain_events import UserInvited
from src.infrastructure.events.bus import event_bus


@dataclass
class CreateInvitationCommand:
    """
    Crée un code d'invitation et émet l'événement UserInvited.

    Utilisation :
        cmd = CreateInvitationCommand(
            created_by_id=admin.id,
            email="parent@example.com",
            role=UserRole.PARENT,
        )
        invitation = await cmd.execute(invitation_repo)
    """

    created_by_id: UUID
    role: UserRole
    email: Optional[str] = None
    phone_number: Optional[str] = None

    async def execute(self, invitation_repo: IInvitationRepository) -> InvitationCode:
        import secrets
        from src.core.utils import utc_now

        code = secrets.token_urlsafe(16)
        invitation = InvitationCode(
            code=code,
            created_by=self.created_by_id,
            email=self.email,
            phone_number=self.phone_number,
            role=self.role,
            created_at=utc_now(),
        )
        created = await invitation_repo.create(invitation)
        await event_bus.publish(
            UserInvited(
                invitation_id=created.id,
                created_by_id=self.created_by_id,
                email=self.email,
                phone_number=self.phone_number,
                role=self.role.value,
            )
        )
        return created
