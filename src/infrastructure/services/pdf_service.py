"""
Service de génération de documents PDF avec filigrane logo.

Utilise reportlab pour générer :
- Certificats de formation
- Rapports (comptes rendus, PV)
- Bilans financiers
- Rapports de présence
"""
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Chemin du logo (optionnel — PDF sans filigrane si absent)
_LOGO_PATH = Path(__file__).parent.parent.parent.parent / "assets" / "logo_servant.jpeg"

# Couleurs institutionnelles
_COLOR_PRIMARY = colors.HexColor("#1a3a5c")   # Bleu marine
_COLOR_ACCENT = colors.HexColor("#c9a84c")    # Or
_COLOR_LIGHT = colors.HexColor("#f5f5f5")     # Gris clair


def _base_doc(buffer: BytesIO, title: str) -> SimpleDocTemplate:
    """Crée un document A4 avec marges standard."""
    return SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2 * cm,
        title=title,
        author="ServantAssist",
    )


def _styles() -> dict:
    """Retourne un dictionnaire de styles réutilisables."""
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontSize=18,
            textColor=_COLOR_PRIMARY,
            spaceAfter=6,
            alignment=TA_CENTER,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontSize=12,
            textColor=_COLOR_ACCENT,
            spaceAfter=4,
            alignment=TA_CENTER,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=base["Heading2"],
            fontSize=11,
            textColor=_COLOR_PRIMARY,
            spaceBefore=12,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontSize=10,
            textColor=colors.black,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["Normal"],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_RIGHT,
        ),
        "center": ParagraphStyle(
            "Center",
            parent=base["Normal"],
            fontSize=10,
            alignment=TA_CENTER,
        ),
    }


def _header_elements(st: dict, title: str, subtitle: str = "") -> list:
    """Retourne les éléments d'en-tête communs."""
    elems = [
        Paragraph("ServantAssist", st["subtitle"]),
        Paragraph(title, st["title"]),
    ]
    if subtitle:
        elems.append(Paragraph(subtitle, st["subtitle"]))
    elems.append(HRFlowable(width="100%", thickness=1, color=_COLOR_ACCENT, spaceAfter=10))
    return elems


def _footer_text(st: dict) -> list:
    """Retourne le pied de page commun."""
    now = datetime.now().strftime("%d/%m/%Y à %H:%M")
    return [
        Spacer(1, 1 * cm),
        HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey),
        Paragraph(f"Document généré le {now} par ServantAssist", st["small"]),
    ]


class PDFService:
    """Service de génération de documents PDF."""

    # ── Certificat de formation ────────────────────────────────────────────

    def generate_certificate(
        self,
        participant_first_name: str,
        participant_last_name: str,
        training_title: str,
        training_date: datetime,
        trainer_name: str = "Le Responsable de Formation",
        score: Optional[float] = None,
    ) -> bytes:
        """
        Génère un certificat de formation PDF.

        Args:
            participant_first_name: Prénom du participant
            participant_last_name: Nom du participant
            training_title: Titre de la formation
            training_date: Date de la formation
            trainer_name: Nom du formateur (signataire)
            score: Score d'évaluation (optionnel)

        Returns:
            Contenu du PDF en bytes
        """
        buffer = BytesIO()
        doc = _base_doc(buffer, f"Certificat — {training_title}")
        st = _styles()
        story = []

        # En-tête
        story.extend(_header_elements(st, "CERTIFICAT DE FORMATION"))
        story.append(Spacer(1, 1.5 * cm))

        # Corps du certificat
        story.append(
            Paragraph("Nous certifions que", st["center"])
        )
        story.append(Spacer(1, 0.5 * cm))
        story.append(
            Paragraph(
                f"<b>{participant_first_name.upper()} {participant_last_name.upper()}</b>",
                ParagraphStyle(
                    "Name",
                    parent=st["title"],
                    fontSize=20,
                    textColor=_COLOR_PRIMARY,
                ),
            )
        )
        story.append(Spacer(1, 0.5 * cm))
        story.append(
            Paragraph(
                f"a suivi et validé avec succès la formation",
                st["center"],
            )
        )
        story.append(Spacer(1, 0.3 * cm))
        story.append(
            Paragraph(
                f"<b>« {training_title} »</b>",
                ParagraphStyle(
                    "TrainingTitle",
                    parent=st["subtitle"],
                    fontSize=14,
                    textColor=_COLOR_ACCENT,
                ),
            )
        )
        story.append(Spacer(1, 0.3 * cm))
        story.append(
            Paragraph(
                f"le {training_date.strftime('%d %B %Y')}",
                st["center"],
            )
        )

        if score is not None:
            story.append(Spacer(1, 0.5 * cm))
            story.append(
                Paragraph(f"Note obtenue : <b>{score:.1f} / 20</b>", st["center"])
            )

        story.append(Spacer(1, 2 * cm))

        # Signature
        sig_data = [
            ["", ""],
            [trainer_name, ""],
            [
                datetime.now().strftime("%d/%m/%Y"),
                "",
            ],
        ]
        sig_table = Table(sig_data, colWidths=[8 * cm, 8 * cm])
        sig_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTSIZE", (0, 1), (-1, 1), 10),
                    ("TEXTCOLOR", (0, 1), (-1, 1), _COLOR_PRIMARY),
                    ("TOPPADDING", (0, 0), (-1, 0), 30),
                    ("LINEABOVE", (0, 0), (0, 0), 0.5, colors.grey),
                ]
            )
        )
        story.append(sig_table)
        story.extend(_footer_text(st))

        doc.build(story)
        return buffer.getvalue()

    # ── Rapport ───────────────────────────────────────────────────────────

    def generate_report(
        self,
        title: str,
        report_type: str,
        report_date: datetime,
        location: str,
        content: str,
        author_name: str,
        participants: Optional[List[str]] = None,
        decisions: Optional[str] = None,
        action_items: Optional[str] = None,
    ) -> bytes:
        """
        Génère un rapport PDF (compte rendu, PV, etc.).
        """
        buffer = BytesIO()
        doc = _base_doc(buffer, title)
        st = _styles()
        story = []

        # En-tête
        story.extend(_header_elements(st, title, report_type.upper()))

        # Métadonnées
        meta_data = [
            ["Date :", report_date.strftime("%d/%m/%Y")],
            ["Lieu :", location],
            ["Rédigé par :", author_name],
        ]
        meta_table = Table(meta_data, colWidths=[4 * cm, 12 * cm])
        meta_table.setStyle(
            TableStyle(
                [
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("TEXTCOLOR", (0, 0), (0, -1), _COLOR_PRIMARY),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(meta_table)
        story.append(Spacer(1, 0.5 * cm))

        # Participants
        if participants:
            story.append(Paragraph("Participants", st["section"]))
            for p in participants:
                story.append(Paragraph(f"• {p}", st["body"]))
            story.append(Spacer(1, 0.3 * cm))

        # Contenu principal
        story.append(Paragraph("Compte rendu", st["section"]))
        for line in content.split("\n"):
            if line.strip():
                story.append(Paragraph(line, st["body"]))

        # Décisions
        if decisions:
            story.append(Paragraph("Décisions prises", st["section"]))
            for line in decisions.split("\n"):
                if line.strip():
                    story.append(Paragraph(f"→ {line}", st["body"]))

        # Points d'action
        if action_items:
            story.append(Paragraph("Points d'action", st["section"]))
            for line in action_items.split("\n"):
                if line.strip():
                    story.append(Paragraph(f"☐ {line}", st["body"]))

        story.extend(_footer_text(st))
        doc.build(story)
        return buffer.getvalue()

    # ── Bilan financier ───────────────────────────────────────────────────

    def generate_financial_statement(
        self,
        entries: list,
        period_label: str,
        generated_by: str,
        total_income: float = 0.0,
        total_expense: float = 0.0,
    ) -> bytes:
        """
        Génère un bilan financier PDF.

        Args:
            entries: Liste de dicts {date, description, type, amount, category}
            period_label: Ex. "Janvier 2026" ou "2026-01-01 au 2026-03-31"
            generated_by: Nom du commissaire
            total_income: Total des entrées
            total_expense: Total des sorties
        """
        buffer = BytesIO()
        doc = _base_doc(buffer, f"Bilan Financier — {period_label}")
        st = _styles()
        story = []

        story.extend(
            _header_elements(st, "BILAN FINANCIER", f"Période : {period_label}")
        )
        story.append(
            Paragraph(f"Établi par : {generated_by}", st["small"])
        )
        story.append(Spacer(1, 0.5 * cm))

        # Résumé
        balance = total_income - total_expense
        bal_color = "#2e7d32" if balance >= 0 else "#c62828"
        summary_data = [
            ["Total Entrées", "Total Sorties", "Solde"],
            [
                f"{total_income:,.0f} FCFA",
                f"{total_expense:,.0f} FCFA",
                f"{balance:+,.0f} FCFA",
            ],
        ]
        summary_table = Table(summary_data, colWidths=[5.5 * cm, 5.5 * cm, 5.5 * cm])
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), _COLOR_PRIMARY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BACKGROUND", (0, 1), (-1, 1), _COLOR_LIGHT),
                    ("TEXTCOLOR", (2, 1), (2, 1), colors.HexColor(bal_color)),
                    ("FONTNAME", (2, 1), (2, 1), "Helvetica-Bold"),
                    ("BOX", (0, 0), (-1, -1), 0.5, _COLOR_PRIMARY),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_COLOR_LIGHT]),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(summary_table)
        story.append(Spacer(1, 0.8 * cm))

        # Détail des opérations
        if entries:
            story.append(Paragraph("Détail des opérations", st["section"]))
            table_data = [["Date", "Description", "Catégorie", "Type", "Montant (FCFA)"]]
            for e in entries:
                date_str = (
                    e["date"].strftime("%d/%m/%Y")
                    if hasattr(e.get("date"), "strftime")
                    else str(e.get("date", ""))
                )
                table_data.append(
                    [
                        date_str,
                        str(e.get("description", ""))[:40],
                        str(e.get("category", "")),
                        str(e.get("type", "")),
                        f"{float(e.get('amount', 0)):,.0f}",
                    ]
                )
            entry_table = Table(
                table_data,
                colWidths=[2.5 * cm, 6 * cm, 3 * cm, 2 * cm, 3 * cm],
            )
            entry_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), _COLOR_PRIMARY),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("ALIGN", (4, 0), (4, -1), "RIGHT"),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _COLOR_LIGHT]),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(entry_table)

        story.extend(_footer_text(st))
        doc.build(story)
        return buffer.getvalue()

    # ── Rapport de présence ───────────────────────────────────────────────

    def generate_attendance_report(
        self,
        servant_name: str,
        sessions: list,
        period_label: str,
        total_present: int = 0,
        total_absent: int = 0,
    ) -> bytes:
        """
        Génère un rapport de présence individuel PDF.

        Args:
            servant_name: Nom complet du servant
            sessions: Liste de dicts {date, event_title, status, role}
            period_label: Période couverte
            total_present: Nombre de présences
            total_absent: Nombre d'absences
        """
        buffer = BytesIO()
        doc = _base_doc(buffer, f"Rapport de Présence — {servant_name}")
        st = _styles()
        story = []

        story.extend(
            _header_elements(
                st,
                "RAPPORT DE PRÉSENCE",
                f"Période : {period_label}",
            )
        )
        story.append(Paragraph(f"Servant : <b>{servant_name}</b>", st["body"]))
        story.append(Spacer(1, 0.5 * cm))

        # Résumé
        total = total_present + total_absent
        rate = (total_present / total * 100) if total else 0
        summary_data = [
            ["Présences", "Absences", "Taux de présence"],
            [str(total_present), str(total_absent), f"{rate:.1f} %"],
        ]
        summary_table = Table(summary_data, colWidths=[5.5 * cm, 5.5 * cm, 5.5 * cm])
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), _COLOR_PRIMARY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BACKGROUND", (0, 1), (-1, 1), _COLOR_LIGHT),
                    ("BOX", (0, 0), (-1, -1), 0.5, _COLOR_PRIMARY),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(summary_table)
        story.append(Spacer(1, 0.8 * cm))

        # Détail des sessions
        if sessions:
            story.append(Paragraph("Détail des participations", st["section"]))
            table_data = [["Date", "Événement", "Rôle liturgique", "Statut"]]
            for s in sessions:
                date_str = (
                    s["date"].strftime("%d/%m/%Y")
                    if hasattr(s.get("date"), "strftime")
                    else str(s.get("date", ""))
                )
                status = str(s.get("status", ""))
                status_display = "✓ Présent" if "PRESENT" in status.upper() else "✗ Absent"
                table_data.append(
                    [
                        date_str,
                        str(s.get("event_title", ""))[:35],
                        str(s.get("role", "")),
                        status_display,
                    ]
                )
            detail_table = Table(
                table_data,
                colWidths=[3 * cm, 7 * cm, 4 * cm, 2.5 * cm],
            )
            detail_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), _COLOR_PRIMARY),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _COLOR_LIGHT]),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(detail_table)

        story.extend(_footer_text(st))
        doc.build(story)
        return buffer.getvalue()
