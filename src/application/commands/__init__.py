"""
Command handlers (CQRS — côté écriture).

Les commands modifient l'état du système et émettent des événements.
Elles sont indépendantes des queries (lectures) et peuvent être
distribuées, retentées ou journalisées séparément.
"""
from .user_commands import (
    ActivateUserCommand,
    DeactivateUserCommand,
    RegisterUserCommand,
    ResetPasswordCommand,
)
from .auth_commands import CreateInvitationCommand

__all__ = [
    "ActivateUserCommand",
    "CreateInvitationCommand",
    "DeactivateUserCommand",
    "RegisterUserCommand",
    "ResetPasswordCommand",
]
