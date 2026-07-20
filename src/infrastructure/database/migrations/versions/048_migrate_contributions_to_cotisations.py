"""048 migrate contributions to cotisation_periods/member_cotisations

Le module `contributions` (paiement au mois/semaine, montant fige en code)
est remplace par le module `cotisations` (periodes + paiements individuels),
seul module actif desormais. Cette migration convertit les donnees
historiques avant que la table `contributions` ne soit supprimee par la
migration 049.

Limite assumee : plusieurs paiements hebdomadaires (semaines 1-4) d'un meme
servant pour un meme mois sont cumules dans un seul MemberCotisation
(amount_paid = somme), car cotisation_periods/member_cotisations ne modelise
pas un identifiant de semaine — seule l'app ServantAssist V0 introduit ce
concept ; les periodes migrees sont marquees inactives (historique).

Revision ID: 048
Revises: 047
Create Date: 2026-07-16
"""
import calendar
from collections import defaultdict
from datetime import datetime

import sqlalchemy as sa

from alembic import op

revision = "048"
down_revision = "047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    system_admin = conn.execute(sa.text(
        "SELECT id FROM users WHERE role IN ('ADMIN', 'AUMÔNIER') ORDER BY created_at LIMIT 1"
    )).scalar()
    if system_admin is None:
        # Base sans admin/aumonier (ex. base de test vide) : rien a migrer.
        return

    contributions = conn.execute(sa.text(
        "SELECT id, servant_id, amount, payment_mode, payment_date, month, year, "
        "week_number, recorded_by, notes FROM contributions ORDER BY year, month, week_number"
    )).fetchall()

    if not contributions:
        return

    # Regrouper par (mode, mois, annee) -> une seule CotisationPeriod pour
    # tous les servants, puis agreger les paiements par (periode, servant).
    period_cache: dict[tuple, str] = {}
    aggregated: dict[tuple, dict] = defaultdict(
        lambda: {"amount": 0.0, "payment_date": None, "notes": [], "recorded_by": None}
    )

    for c in contributions:
        key = (c.payment_mode, c.month, c.year)
        period_id = period_cache.get(key)
        if period_id is None:
            last_day = calendar.monthrange(c.year, c.month)[1]
            # asyncpg exige des objets datetime pour les colonnes timestamp
            # (une chaine ISO brute leve DataError) — cotisation_periods.start_date/
            # end_date sont "timestamp without time zone" (naive), pas timestamptz.
            start = datetime(c.year, c.month, 1)
            end = datetime(c.year, c.month, last_day, 23, 59, 59)
            period_type = "HEBDOMADAIRE" if c.payment_mode == "HEBDOMADAIRE" else "MENSUEL"
            amount_expected = 100.0 if c.payment_mode == "HEBDOMADAIRE" else 500.0
            row = conn.execute(sa.text(
                """
                INSERT INTO cotisation_periods
                    (id, title, cotisation_type, period_type, amount_expected,
                     start_date, end_date, is_active, created_by, created_at, updated_at)
                VALUES
                    (gen_random_uuid(), :title, 'ORDINAIRE', :ptype, :amount,
                     :start, :end, false, :admin, NOW(), NOW())
                RETURNING id
                """
            ), {
                "title": f"Cotisation {period_type.lower()} {c.month:02d}/{c.year} (migree)",
                "ptype": period_type,
                "amount": amount_expected,
                "start": start,
                "end": end,
                "admin": system_admin,
            }).fetchone()
            period_id = str(row[0])
            period_cache[key] = period_id

        # contributions.payment_date est timestamptz (aware) mais
        # member_cotisations.payment_date est "timestamp without time zone" —
        # meme mismatch aware/naive que pour start_date/end_date ci-dessus.
        payment_date_naive = c.payment_date.replace(tzinfo=None) if c.payment_date else None

        agg_key = (period_id, str(c.servant_id))
        agg = aggregated[agg_key]
        agg["amount"] += float(c.amount or 0)
        if agg["payment_date"] is None or (
            payment_date_naive and payment_date_naive > agg["payment_date"]
        ):
            agg["payment_date"] = payment_date_naive
        if c.notes:
            agg["notes"].append(c.notes)
        agg["recorded_by"] = c.recorded_by

    for (period_id, servant_id), agg in aggregated.items():
        expected = conn.execute(sa.text(
            "SELECT amount_expected FROM cotisation_periods WHERE id = :id"
        ), {"id": period_id}).scalar()
        member_status = "PAYE" if agg["amount"] >= (expected or 0) else "PAYE_PARTIELLEMENT"
        notes = "; ".join(agg["notes"]) if agg["notes"] else None
        notes = f"{notes or ''} [migre depuis contributions]".strip()
        conn.execute(sa.text(
            """
            INSERT INTO member_cotisations
                (id, period_id, user_id, amount_paid, status, payment_date,
                 payment_method, notes, recorded_by, created_at, updated_at)
            VALUES
                (gen_random_uuid(), :period_id, :user_id, :amount, :status, :pdate,
                 NULL, :notes, :recorded_by, NOW(), NOW())
            """
        ), {
            "period_id": period_id,
            "user_id": servant_id,
            "amount": agg["amount"],
            "status": member_status,
            "pdate": agg["payment_date"],
            "notes": notes,
            "recorded_by": agg["recorded_by"],
        })


def downgrade() -> None:
    # Suppression best-effort des lignes marquees comme migrees (via le
    # marqueur textuel dans notes). Les cotisation_periods generees restent
    # (elles peuvent avoir ete utilisees depuis) - a nettoyer manuellement
    # si necessaire.
    conn = op.get_bind()
    conn.execute(sa.text(
        "DELETE FROM member_cotisations WHERE notes LIKE '%[migre depuis contributions]%'"
    ))
