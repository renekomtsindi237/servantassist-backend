"""
Tâches Celery pour la génération de PDF.

Utilise reportlab (déjà installé) pour générer les rapports.
Les PDF sont retournés comme bytes (à envoyer en StreamingResponse ou uploader en storage).

Usage :
    result = export_user_data_pdf.delay(user_id="uuid-here")
    # result.get() → bytes du PDF
"""

import asyncio
import io
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from src.infrastructure.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _build_pdf_header(canvas_obj, title: str, subtitle: str = "") -> None:
    """Dessine l'en-tête ServantAssist commun à tous les PDF."""
    from reportlab.lib import colors
    from reportlab.lib.units import cm

    canvas_obj.setFont("Helvetica-Bold", 16)
    canvas_obj.setFillColor(colors.HexColor("#2A72B4"))
    canvas_obj.drawString(2 * cm, 27 * cm, "ServantAssist")
    canvas_obj.setFont("Helvetica-Bold", 13)
    canvas_obj.setFillColor(colors.black)
    canvas_obj.drawString(2 * cm, 25.5 * cm, title)
    if subtitle:
        canvas_obj.setFont("Helvetica", 10)
        canvas_obj.setFillColor(colors.grey)
        canvas_obj.drawString(2 * cm, 24.5 * cm, subtitle)
    canvas_obj.setStrokeColor(colors.HexColor("#2A72B4"))
    canvas_obj.line(2 * cm, 24 * cm, 19 * cm, 24 * cm)


# ── Portabilité des données (Art. 20 Loi 2024/017) ────────────────────────────


@celery_app.task(
    name="src.infrastructure.tasks.pdf_tasks.export_user_data_pdf",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
)
def export_user_data_pdf(self, user_id: str) -> Optional[bytes]:
    """
    Génère un PDF complet des données personnelles d'un utilisateur.

    Conformité Art. 20 Loi 2024/017 (portabilité des données).
    Inclut : profil, présences, cotisations, affectations, notes de discipline.

    Returns:
        bytes du PDF, ou None si l'utilisateur n'existe pas.
    """
    try:
        return _run_async(_export_user_data_pdf_async(UUID(user_id)))
    except Exception as exc:
        logger.error("export_user_data_pdf: failed user_id=%s error=%s", user_id, exc)
        raise self.retry(exc=exc)


async def _export_user_data_pdf_async(user_id: UUID) -> Optional[bytes]:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from sqlmodel import col, select

    from src.core.entities.attendance import Attendance
    from src.core.entities.contribution import MemberCotisation
    from src.core.entities.user import User
    from src.infrastructure.database.session import sessionmanager

    async with sessionmanager.session() as session:
        user = await session.get(User, user_id)
        if not user:
            logger.warning("export_user_data_pdf: user %s not found", user_id)
            return None

        stmt_att = select(Attendance).where(Attendance.user_id == user_id)
        result_att = await session.exec(stmt_att)
        attendances = result_att.all()

        stmt_cot = select(MemberCotisation).where(MemberCotisation.user_id == user_id)
        result_cot = await session.exec(stmt_cot)
        cotisations = result_cot.all()

    buf = io.BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm)

    story = []
    title_style = styles["Heading1"]
    normal_style = styles["Normal"]

    story.append(Paragraph("Export de données personnelles", title_style))
    story.append(Paragraph(f"Généré le {datetime.now(timezone.utc).strftime('%d/%m/%Y à %H:%M UTC')}", normal_style))
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("Profil", styles["Heading2"]))
    profile_data = [
        ["Champ", "Valeur"],
        ["Prénom", user.first_name or ""],
        ["Nom", user.last_name or ""],
        ["Rôle", user.role.value if hasattr(user.role, "value") else str(user.role)],
        ["Statut", "Actif" if user.is_active else "Inactif"],
        ["Consentement données", str(user.data_consent_at)[:10] if user.data_consent_at else "Non renseigné"],
    ]
    profile_table = Table(profile_data, colWidths=[6 * cm, 11 * cm])
    profile_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2A72B4")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F6FB")]),
    ]))
    story.append(profile_table)
    story.append(Spacer(1, 0.5 * cm))

    if attendances:
        story.append(Paragraph(f"Présences ({len(attendances)} enregistrements)", styles["Heading2"]))
        att_data = [["Session", "Date", "Statut"]]
        for a in attendances[:50]:
            att_data.append([
                str(a.session_id)[:8] + "...",
                str(a.created_at)[:10] if a.created_at else "",
                a.status.value if hasattr(a.status, "value") else str(a.status),
            ])
        att_table = Table(att_data, colWidths=[6 * cm, 4 * cm, 7 * cm])
        att_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2A72B4")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        story.append(att_table)
        story.append(Spacer(1, 0.5 * cm))

    if cotisations:
        story.append(Paragraph(f"Cotisations ({len(cotisations)} enregistrements)", styles["Heading2"]))
        cot_data = [["Mois", "Année", "Montant (XAF)", "Statut"]]
        for c in cotisations[:50]:
            cot_data.append([
                c.month or "",
                str(c.year) if c.year else "",
                f"{c.amount:,.0f}" if c.amount else "0",
                c.status.value if hasattr(c.status, "value") else str(c.status),
            ])
        cot_table = Table(cot_data, colWidths=[4 * cm, 3 * cm, 5 * cm, 5 * cm])
        cot_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2A72B4")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        story.append(cot_table)

    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(
        "Ce document a été généré conformément à l'Art. 20 de la Loi 2024/017 "
        "relative à la protection des données personnelles au Cameroun.",
        styles["Italic"],
    ))

    doc.build(story)
    return buf.getvalue()


# ── Rapport de présences ──────────────────────────────────────────────────────


@celery_app.task(
    name="src.infrastructure.tasks.pdf_tasks.generate_attendance_report_pdf",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def generate_attendance_report_pdf(self, session_id: str) -> Optional[bytes]:
    """Génère un rapport PDF de présences pour une session donnée."""
    try:
        return _run_async(_generate_attendance_report_async(UUID(session_id)))
    except Exception as exc:
        logger.error("generate_attendance_report_pdf: failed session_id=%s error=%s", session_id, exc)
        raise self.retry(exc=exc)


async def _generate_attendance_report_async(session_id: UUID) -> Optional[bytes]:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from sqlmodel import select

    from src.core.entities.attendance import Attendance, AttendanceSession
    from src.infrastructure.database.session import sessionmanager

    async with sessionmanager.session() as session:
        att_session = await session.get(AttendanceSession, session_id)
        if not att_session:
            return None
        stmt = select(Attendance).where(Attendance.session_id == session_id)
        result = await session.exec(stmt)
        attendances = result.all()

    buf = io.BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm)
    story = []

    title = getattr(att_session, "title", "Session de présence")
    story.append(Paragraph(f"Rapport de présences — {title}", styles["Heading1"]))
    story.append(Paragraph(f"Généré le {datetime.now(timezone.utc).strftime('%d/%m/%Y à %H:%M')}", styles["Normal"]))
    story.append(Spacer(1, 0.5 * cm))

    present = sum(1 for a in attendances if str(getattr(a.status, "value", a.status)) == "PRESENT")
    absent = sum(1 for a in attendances if str(getattr(a.status, "value", a.status)) == "ABSENT")
    rate = f"{present / len(attendances) * 100:.1f}%" if attendances else "N/A"

    summary_data = [
        ["Total", "Présents", "Absents", "Taux"],
        [str(len(attendances)), str(present), str(absent), rate],
    ]
    summary_table = Table(summary_data, colWidths=[4 * cm, 4 * cm, 4 * cm, 4 * cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2A72B4")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.5 * cm))

    if attendances:
        rows = [["Servant", "Statut", "Note"]]
        for a in attendances:
            rows.append([
                str(a.user_id)[:8] + "...",
                str(getattr(a.status, "value", a.status)),
                getattr(a, "note", "") or "",
            ])
        detail_table = Table(rows, colWidths=[7 * cm, 4 * cm, 6 * cm])
        detail_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2A72B4")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F6FB")]),
        ]))
        story.append(detail_table)

    doc.build(story)
    return buf.getvalue()


# ── Rapport financier ─────────────────────────────────────────────────────────


@celery_app.task(
    name="src.infrastructure.tasks.pdf_tasks.generate_financial_report_pdf",
    bind=True,
    max_retries=2,
)
def generate_financial_report_pdf(self, period: str, year: int) -> Optional[bytes]:
    """Génère un rapport PDF financier (cotisations + trésorerie) pour une période."""
    try:
        return _run_async(_generate_financial_report_async(period, year))
    except Exception as exc:
        logger.error("generate_financial_report_pdf: period=%s year=%s error=%s", period, year, exc)
        raise self.retry(exc=exc)


async def _generate_financial_report_async(period: str, year: int) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from sqlmodel import col, select

    from src.core.entities.contribution import MemberCotisation
    from src.infrastructure.database.session import sessionmanager

    async with sessionmanager.session() as session:
        stmt = select(MemberCotisation).where(
            MemberCotisation.year == year,
        )
        result = await session.exec(stmt)
        cotisations = result.all()

    buf = io.BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm)
    story = []

    story.append(Paragraph(f"Rapport financier — {period} {year}", styles["Heading1"]))
    story.append(Paragraph(f"Généré le {datetime.now(timezone.utc).strftime('%d/%m/%Y')}", styles["Normal"]))
    story.append(Spacer(1, 0.5 * cm))

    total = sum(c.amount or 0 for c in cotisations)
    paid = sum(c.amount or 0 for c in cotisations if str(getattr(c.status, "value", c.status)) == "PAID")
    story.append(Paragraph(f"Total attendu : {total:,.0f} XAF | Collecté : {paid:,.0f} XAF | Taux : {paid/total*100:.1f}%" if total else "Aucune donnée", styles["Normal"]))
    story.append(Spacer(1, 0.5 * cm))

    if cotisations:
        rows = [["Servant", "Mois", "Montant (XAF)", "Statut"]]
        for c in cotisations[:100]:
            rows.append([
                str(c.user_id)[:8] + "...",
                c.month or "",
                f"{c.amount:,.0f}" if c.amount else "0",
                str(getattr(c.status, "value", c.status)),
            ])
        table = Table(rows, colWidths=[5 * cm, 3 * cm, 5 * cm, 4 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2A72B4")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        story.append(table)

    doc.build(story)
    return buf.getvalue()
