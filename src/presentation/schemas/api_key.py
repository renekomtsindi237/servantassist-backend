from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    scopes: List[str] = Field(default_factory=list)


class ApiKeyResponse(BaseModel):
    id: UUID
    name: str
    user_id: UUID
    scopes: List[str]
    is_active: bool
    last_used_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Réponse à la création — contient la clé brute (une seule fois)."""

    raw_key: str = Field(description="Clé brute à conserver — jamais retransmise par le serveur")
