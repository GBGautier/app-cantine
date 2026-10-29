"""Tests unitaires pour les services."""

import pytest
import tempfile
from pathlib import Path

from src.backend.services.pdf_parser import (
    to_float,
    fnum,
    norm,
    norm_ref,
    unit_norm,
    MONTHS,
    UNIT_MAP,
)
from src.backend.services.menu_parser import (
    norm as menu_norm,
    clean_value,
    classify_cat,
    CANON_CATS,
    CAT_MAP,
    MONTHS_FR,
    DAYS_FR,
    parse_date_header,
    build_date,
    resolve_year,
    infer_year,
)


class TestPdfParserUtils:
    """Tests pour les utilitaires de pdf_parser."""

    def test_to_float(self):
        """Test de la fonction to_float."""
        assert to_float("123") == 123.0
        assert to_float("123.45") == 123.45
        assert to_float("123,45") == 123.45
        assert to_float("1 234.56") == 1234.56
        assert to_float("1.234,56") == 1234.56
        assert to_float(None) is None
        assert to_float("abc") is None
        assert to_float("") is None

    def test_fnum(self):
        """Test de la fonction fnum."""
        assert fnum("abc 123 def") == 123.0
        assert fnum("123.45") == 123.45
        assert fnum("123,45") == 123.45
        assert fnum("-123.45") == -123.45
        assert fnum("abc") is None
        assert fnum("") is None
        assert fnum(None) is None

    def test_norm(self):
        """Test de la fonction norm."""
        assert norm("Test String") == "test string"
        assert norm("Tëst String") == "test string"
        assert norm("Test-String") == "test string"
        assert norm("Test_String") == "test string"
        assert norm("") == ""
        assert norm(None) == ""

    def test_norm_ref(self):
        """Test de la fonction norm_ref."""
        assert norm_ref("Test-String") == "teststring"
        assert norm_ref("Test_String") == "teststring"
        assert norm_ref("Test String") == "teststring"
        assert norm_ref("Tëst") == "test"
        assert norm_ref("") == ""
        assert norm_ref(None) == ""

    def test_unit_norm(self):
        """Test de la fonction unit_norm."""
        assert unit_norm("kg") == "kg"
        assert unit_norm("KG") == "kg"
        assert unit_norm("kilo") == "kg"
        assert unit_norm("pièce") == "pièce"
        assert unit_norm("PIÈCE") == "pièce"
        assert unit_norm("pc") == "pièce"
        assert unit_norm("colis") == "colis"
        assert unit_norm("unknown") == "unknown"
        assert unit_norm(None) is None
        assert unit_norm("") is None

    def test_months(self):
        """Test du dictionnaire MONTHS."""
        assert MONTHS["janvier"] == 1
        assert MONTHS["février"] == 2
        assert MONTHS["décembre"] == 12


class TestMenuParserUtils:
    """Tests pour les utilitaires de menu_parser."""

    def test_menu_norm(self):
        """Test de la fonction menu_norm."""
        assert menu_norm("Test String") == "test string"
        assert menu_norm("Tëst String") == "test string"
        assert menu_norm("") == ""
        assert menu_norm(None) is None

    def test_clean_value(self):
        """Test de la fonction clean_value."""
        assert clean_value("Test*Value") == "Test Value"
        assert clean_value("Test**Value") == "Test Value"
        assert clean_value("Test Value") == "Test Value"
        assert clean_value("") == ""
        assert clean_value(None) == ""
        
        # Test spécial pour accompagnement
        assert clean_value("n Test", cat="accompagnement") == "Test"
        assert clean_value("nt Test", cat="accompagnement") == "Test"

    def test_classify_cat(self):
        """Test de la fonction classify_cat."""
        assert classify_cat("Entrée") == "entree"
        assert classify_cat("entree") == "entree"
        assert classify_cat("Entrée principale") == "entree"
        assert classify_cat("Plat") == "plat"
        assert classify_cat("plat") == "plat"
        assert classify_cat("Plat principal") == "plat"
        assert classify_cat("Accompagnement") == "accompagnement"
        assert classify_cat("Acompagnement") == "accompagnement"
        assert classify_cat("Laitage") == "laitage"
        assert classify_cat("Dessert") == "dessert"
        assert classify_cat("") is None
        assert classify_cat(None) is None

    def test_parse_date_header(self):
        """Test de la fonction parse_date_header."""
        # Avec nom de jour
        result = parse_date_header("lundi 30 novembre 2026")
        assert result == ("lundi", 30, 11, 2026)
        
        # Sans année
        result = parse_date_header("lundi 30 novembre")
        assert result == ("lundi", 30, 11, None)
        
        # Date numérique
        result = parse_date_header("30/11/2026")
        assert result[1:] == (30, 11, 2026)
        
        # Aucun résultat
        result = parse_date_header("Test")
        assert result is None

    def test_build_date(self):
        """Test de la fonction build_date."""
        assert build_date(30, 11, 2026) == "2026-11-30"
        assert build_date(1, 1, 2026) == "2026-01-01"
        
        # Date invalide
        assert build_date(31, 2, 2026) is None

    def test_resolve_year(self):
        """Test de la fonction resolve_year."""
        # Avec année valide
        year = resolve_year("lundi", 30, 11, 2026, None)
        assert year == 2026
        
        # Sans année, avec doc_year
        year = resolve_year("lundi", 30, 11, None, 2026)
        assert year == 2026

    def test_infer_year(self):
        """Test de la fonction infer_year."""
        # Avec contexte
        year = infer_year(30, 11, 2026)
        assert year == 2026
        
        # Sans contexte (utilise l'année courante)
        year = infer_year(30, 11)
        assert year is not None
