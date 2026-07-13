"""Unit tests for PDFService — verifies PDF generation returns bytes."""

from datetime import datetime
from io import BytesIO

import pytest

from src.infrastructure.services.pdf_service import (
    PDFService,
    _base_doc,
    _footer_text,
    _header_elements,
    _styles,
)

# ─── helpers ─────────────────────────────────────────────────────────────────


def test_base_doc_creates_document():
    buf = BytesIO()
    doc = _base_doc(buf, "Test Document")
    assert doc is not None


def test_styles_returns_all_keys():
    st = _styles()
    assert "title" in st
    assert "subtitle" in st
    assert "section" in st
    assert "body" in st
    assert "small" in st
    assert "center" in st


def test_header_elements_no_subtitle():
    st = _styles()
    elems = _header_elements(st, "Mon Titre")
    assert len(elems) >= 2


def test_header_elements_with_subtitle():
    st = _styles()
    elems = _header_elements(st, "Mon Titre", "Sous-titre")
    assert len(elems) >= 3


def test_footer_text_returns_elements():
    st = _styles()
    footer = _footer_text(st)
    assert len(footer) >= 2


# ─── PDFService ───────────────────────────────────────────────────────────────


def test_generate_certificate_returns_bytes():
    svc = PDFService()
    result = svc.generate_certificate(
        participant_first_name="Jean",
        participant_last_name="Dupont",
        training_title="Formation Liturgique",
        training_date=datetime(2026, 6, 1),
        trainer_name="Père Joseph",
    )
    assert isinstance(result, bytes)
    assert len(result) > 100
    # PDF starts with %PDF
    assert result[:4] == b"%PDF"


def test_generate_certificate_with_score():
    svc = PDFService()
    result = svc.generate_certificate(
        participant_first_name="Marie",
        participant_last_name="Kone",
        training_title="Formation Acolyte",
        training_date=datetime(2026, 5, 15),
        score=92.5,
    )
    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"


def test_generate_attendance_report_for_servant():
    svc = PDFService()
    sessions = [
        {"date": "2026-06-01", "type": "MESSE", "status": "PRESENT"},
        {"date": "2026-06-08", "type": "REUNION", "status": "ABSENT"},
    ]
    result = svc.generate_attendance_report(
        servant_name="Jean Dupont",
        sessions=sessions,
        period_label="Juin 2026",
        total_present=1,
        total_absent=1,
    )
    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"


def test_generate_attendance_report_empty_sessions():
    svc = PDFService()
    result = svc.generate_attendance_report(
        servant_name="Marie Kone",
        sessions=[],
        period_label="Mai 2026",
    )
    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"


def test_generate_financial_statement_empty():
    svc = PDFService()
    result = svc.generate_financial_statement(
        entries=[],
        period_label="Juin 2026",
        generated_by="Économe Test",
        total_income=0.0,
        total_expense=0.0,
    )
    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"


def test_generate_financial_statement_with_entries():
    svc = PDFService()
    entries = [
        {"date": "2026-06-01", "description": "Collecte", "type": "Recette", "amount": 50000},
        {"date": "2026-06-02", "description": "Fournitures", "type": "Dépense", "amount": -10000},
    ]
    result = svc.generate_financial_statement(
        entries=entries,
        period_label="Juin 2026",
        generated_by="Économe",
        total_income=50000.0,
        total_expense=10000.0,
    )
    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"


def test_generate_report_minutes():
    svc = PDFService()
    result = svc.generate_report(
        title="PV Conseil du 01/06/2026",
        report_type="Procès-verbal",
        report_date=datetime(2026, 6, 1, 14, 0),
        location="Basilique BMRA",
        content="Réunion ordinaire du conseil. Discussion sur les activités du mois.",
        author_name="Secrétaire Général",
        participants=["Jean Dupont", "Marie Kone", "Pierre Tamba"],
        decisions="Validation du budget. Organisation de la retraite annuelle.",
        action_items="Préparer le planning de juillet. Contacter les formateurs.",
    )
    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"


def test_generate_report_minimal():
    svc = PDFService()
    result = svc.generate_report(
        title="Rapport Simple",
        report_type="Note de service",
        report_date=datetime(2026, 5, 15),
        location="Sacristie",
        content="Contenu du rapport.",
        author_name="Admin",
    )
    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"
