"""
Utilitaire de pagination.

Fournit deux stratégies :
- **OffsetPagination** : classique (skip/limit), simple mais lente sur grands datasets.
- **CursorPagination** : basée sur un curseur opaque (UUID encodé en base64),
  performante quelque soit la taille de la table.

Usage CursorPagination dans un endpoint :
```python
from src.core.pagination import CursorPage, decode_cursor, encode_cursor

@router.get("/", response_model=CursorPage[MySchema])
async def list_items(
    limit: int = Query(50, ge=1, le=200),
    cursor: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db_session),
):
    after_id = decode_cursor(cursor)
    stmt = select(MyModel).order_by(MyModel.created_at.desc(), MyModel.id.desc())
    if after_id:
        stmt = stmt.where(MyModel.id < after_id)
    stmt = stmt.limit(limit + 1)
    result = await session.exec(stmt)
    items = list(result.all())

    has_next = len(items) > limit
    if has_next:
        items = items[:limit]

    next_cursor = encode_cursor(items[-1].id) if has_next else None
    return CursorPage(items=items, next_cursor=next_cursor, limit=limit)
```
"""
import base64
from typing import Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel

T = TypeVar("T")


# ── Schémas de réponse ─────────────────────────────────────────────────────


class OffsetPage(BaseModel, Generic[T]):
    """Page paginée par offset (classique)."""

    items: List[T]
    total: int
    limit: int
    offset: int

    @property
    def has_next(self) -> bool:
        return self.offset + self.limit < self.total

    @property
    def has_prev(self) -> bool:
        return self.offset > 0


class CursorPage(BaseModel, Generic[T]):
    """Page paginée par curseur (performante sur grands datasets)."""

    items: List[T]
    next_cursor: Optional[str] = None
    limit: int

    @property
    def has_next(self) -> bool:
        return self.next_cursor is not None


# ── Helpers curseur ────────────────────────────────────────────────────────


def encode_cursor(uuid_value: UUID) -> str:
    """Encode un UUID en curseur opaque base64url."""
    return base64.urlsafe_b64encode(uuid_value.bytes).rstrip(b"=").decode()


def decode_cursor(cursor: Optional[str]) -> Optional[UUID]:
    """Décode un curseur base64url en UUID. Retourne None si invalide."""
    if not cursor:
        return None
    try:
        padding = 4 - len(cursor) % 4
        padded = cursor + "=" * (padding % 4)
        raw = base64.urlsafe_b64decode(padded)
        return UUID(bytes=raw)
    except Exception:
        return None
