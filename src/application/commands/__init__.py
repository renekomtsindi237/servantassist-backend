"""
Command handlers (CQRS — côté écriture).

Les commands modifient l'état du système et émettent des événements.
Elles sont indépendantes des queries (lectures) et peuvent être
distribuées, retentées ou journalisées séparément.
"""

from .auth_commands import CreateInvitationCommand
from .user_commands import (
    ActivateUserCommand,
    DeactivateUserCommand,
    RegisterUserCommand,
    ResetPasswordCommand,
)

__all__ = [
    "ActivateUserCommand",
    "CreateInvitationCommand",
    "DeactivateUserCommand",
    "RegisterUserCommand",
    "ResetPasswordCommand",
]
