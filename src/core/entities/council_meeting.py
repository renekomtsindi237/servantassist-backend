"""
Entités pour le suivi des réunions du Conseil des Responsables (Art 12).
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class CouncilMeeting(SQLModel, table=True):
    """
    Réunion du conseil des responsables (dernier samedi du mois).
    """
    __tablename__ = "council_meetings"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    meeting_date: datetime = Field(index=True)
    location: str = Field(max_length=200)
    agenda: Optional[str] = Field(default=None, max_length=1000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: UUID = Field(foreign_key="users.id")


class CouncilAttendanceStatus(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    EXCUSE = "EXCUSE"


class CouncilAttendance(SQLModel, table=True):
    """
    Présence d'un responsable à une réunion du conseil.
    """
    __tablename__ = "council_attendances"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    meeting_id: UUID = Field(foreign_key="council_meetings.id", index=True)
    responsable_id: UUID = Field(foreign_key="users.id", index=True)
    status: CouncilAttendanceStatus = Field(default=CouncilAttendanceStatus.PRESENT)
    excuse: Optional[str] = Field(default=None, max_length=500)
    recorded_at: datetime = Field(default_factory=datetime.utcnow)
    recorded_by: UUID = Field(foreign_key="users.id")
