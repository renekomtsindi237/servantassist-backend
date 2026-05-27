"""
Query handlers (CQRS — côté lecture).

Les queries lisent l'état du système sans le modifier.
Elles sont indépendantes des services d'écriture (commands) et peuvent
être optimisées séparément (cache, vues dénormalisées, etc.).
"""

from .user_queries import UserListQuery, UserStatsQuery
from .dashboard_queries import DashboardQuery

__all__ = [
    "DashboardQuery",
    "UserListQuery",
    "UserStatsQuery",
]
