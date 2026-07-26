"""042 backfill nominations from legacy users.position

Migration de donnees (idempotente) : convertit chaque users.position
(ancien enum ServantPosition) en une Nomination active (PosteResponsable),
avant que la colonne legacy ne soit supprimee par la migration 043.

Les cas ambigus ou en conflit sont ignores silencieusement et doivent etre
extraits AVANT le deploiement en production via la requete de controle :

    SELECT id, position FROM users WHERE position IS NOT NULL;

...comparee aux nominations effectivement creees par cette migration, pour
arbitrage manuel par l'Aumonier (poste deja occupe, poste non mappable).

Revision ID: 042
Revises: 041
Create Date: 2026-07-16
"""
import sqlalchemy as sa
from alembic import op

revision = "042"
down_revision = "041"
branch_labels = None
depends_on = None

# Mapping ServantPosition (legacy, 15 valeurs) -> PosteResponsable (cible).
# Les valeurs sans equivalent univoque (SERVANT_AUTEL : role de base, pas un
# poste de responsabilite ; CHARGE_CLASSEMENT : ambigu, Dimanche ou Semaine ?)
# sont volontairement absentes de ce mapping et donc ignorees.
_MAPPING = {
    "DELEGUE": "DELEGUE",
    "VICE_DELEGUE": "VICE_DELEGUE",
    "CENSEUR": "CENSEUR",
    "CENSEUR_ADJOINT": "CENSEUR_ADJOINT",
    "SECRETAIRE_GENERAL": "SECRETAIRE_GENERAL",
    "SECRETAIRE_GENERAL_ADJOINT": "SECRETAIRE_GENERAL_ADJOINT",
    "ECONOME": "ECONOME",
    "COMMISSAIRE_AUX_COMPTES": "COMMISSAIRE_AUX_COMPTES",
    "INTENDANT": "INTENDANT",
    "CHARGE_LITURGIE": "CHARGE_LITURGIE",
    "CEREMONIARE": "CEREMONIAIRE",  # orthographe legacy differente
    "CHARGE_SPORTS_CULTURE": "CHARGE_SPORT_CULTURE",
    "CONSEILLER": "CONSEILLER",
}


def upgrade() -> None:
    conn = op.get_bind()

    # Utilisateur ADMIN ou AUMONIER de reference pour tracer nominated_by.
    system_admin = conn.execute(sa.text(
        "SELECT id FROM users WHERE role IN ('ADMIN', 'AUMÔNIER') ORDER BY created_at LIMIT 1"
    )).scalar()
    if system_admin is None:
        # Base sans admin/aumonier (ex. base de test vide) : rien a migrer.
        return

    rows = conn.execute(sa.text(
        "SELECT id, position FROM users WHERE position IS NOT NULL"
    )).fetchall()

    for user_id, legacy_position in rows:
        target_poste = _MAPPING.get(legacy_position)
        if target_poste is None:
            continue  # poste legacy non mappable : ignore, a traiter manuellement

        poste_taken = conn.execute(sa.text(
            "SELECT 1 FROM nominations WHERE poste = :poste AND status = 'ACTIVE' LIMIT 1"
        ), {"poste": target_poste}).first()
        if poste_taken:
            continue  # conflit : deja occupe, ne pas ecraser

        already_nominated = conn.execute(sa.text(
            "SELECT 1 FROM nominations WHERE user_id = :uid AND status = 'ACTIVE' LIMIT 1"
        ), {"uid": user_id}).first()
        if already_nominated:
            continue  # migration deja jouee pour cet utilisateur

        conn.execute(sa.text(
            """
            INSERT INTO nominations (id, user_id, poste, status, nominated_by, notes, nominated_at)
            VALUES (gen_random_uuid(), :uid, :poste, 'ACTIVE', :admin, :notes, NOW())
            """
        ), {
            "uid": user_id,
            "poste": target_poste,
            "admin": system_admin,
            "notes": "Migration automatique depuis User.position (legacy) - migration 042",
        })


def downgrade() -> None:
    # Supprime uniquement les nominations creees par cette migration
    # (tracables via la note), sans toucher aux nominations manuelles.
    conn = op.get_bind()
    conn.execute(sa.text(
        "DELETE FROM nominations WHERE notes = "
        "'Migration automatique depuis User.position (legacy) - migration 042'"
    ))
