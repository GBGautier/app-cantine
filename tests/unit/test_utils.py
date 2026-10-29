"""Tests unitaires pour les utilitaires."""

import pytest
from datetime import datetime, timezone

from src.backend.utils import (
    now_iso,
    sha,
    hash_password,
    verify_password,
    clean_username,
    check_password_rule,
    unit_info,
    convert,
    USERNAME_RE,
)


class TestHashFunctions:
    """Tests pour les fonctions de hachage."""

    def test_sha(self):
        """Test de la fonction sha."""
        assert sha("test") == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
        assert sha("") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def test_hash_password(self):
        """Test de la fonction hash_password."""
        pw = "test-password-123"
        hashed = hash_password(pw)
        assert hashed.startswith("pbkdf2_sha256$")
        assert "$" in hashed
        assert len(hashed.split("$")) == 4

    def test_verify_password(self):
        """Test de la fonction verify_password."""
        pw = "test-password-123"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed) is True
        assert verify_password("wrong-password", hashed) is False
        assert verify_password("", "invalid-hash") is False


class TestUsernameValidation:
    """Tests pour la validation des noms d'utilisateur."""

    def test_valid_usernames(self):
        """Test des noms d'utilisateur valides."""
        valid_usernames = [
            "test",
            "user123",
            "user.name",
            "user_name",
            "user-name",
            "user@domain",
            "a" * 40,  # 40 caractères
        ]
        for username in valid_usernames:
            assert USERNAME_RE.match(username) is not None

    def test_invalid_usernames(self):
        """Test des noms d'utilisateur invalides."""
        invalid_usernames = [
            "ab",  # Trop court
            "a" * 41,  # Trop long
            "User",  # Majuscule
            "user name",  # Espace
            "user@domain.com",  # Trop de caractères spéciaux
            "",  # Vide
        ]
        for username in invalid_usernames:
            assert USERNAME_RE.match(username) is None

    def test_clean_username(self):
        """Test de la fonction clean_username."""
        # Valide
        assert clean_username("test") == "test"
        assert clean_username("  test  ") == "test"
        assert clean_username("Test") == "test"
        
        # Invalide
        with pytest.raises(Exception):
            clean_username("ab")
        with pytest.raises(Exception):
            clean_username("User")


class TestPasswordValidation:
    """Tests pour la validation des mots de passe."""

    def test_valid_password(self):
        """Test des mots de passe valides."""
        valid_passwords = [
            "password123",
            "a" * 8,
            "A1b2C3d4",
        ]
        for pw in valid_passwords:
            check_password_rule(pw)  # Ne doit pas lever d'exception

    def test_invalid_password(self):
        """Test des mots de passe invalides."""
        invalid_passwords = [
            "",
            "a" * 7,
            "short",
        ]
        for pw in invalid_passwords:
            with pytest.raises(Exception):
                check_password_rule(pw)


class TestDateFunctions:
    """Tests pour les fonctions de date."""

    def test_now_iso(self):
        """Test de la fonction now_iso."""
        result = now_iso()
        # Doit être une chaîne ISO 8601 sans timezone
        assert isinstance(result, str)
        # Doit être parsable comme une date
        datetime.fromisoformat(result)


class TestUnitConversion:
    """Tests pour la conversion d'unités."""

    def test_unit_info(self):
        """Test de la fonction unit_info."""
        assert unit_info("kg") == ("mass", 1)
        assert unit_info("g") == ("mass", 0.001)
        assert unit_info("l") == ("vol", 1)
        assert unit_info("ml") == ("vol", 0.001)
        assert unit_info("pièce") == ("count", 1)
        assert unit_info("unité") == ("count", 1)
        assert unit_info("unknown") == ("x:unknown", 1)
        assert unit_info(None) is None
        assert unit_info("") is None

    def test_convert(self):
        """Test de la fonction convert."""
        # Conversion de masse
        assert convert(1.0, "kg", "g") == 1000.0
        assert convert(1000.0, "g", "kg") == 1.0
        assert convert(1.0, "kg", "kg") == 1.0
        
        # Conversion de volume
        assert convert(1.0, "l", "ml") == 1000.0
        assert convert(1000.0, "ml", "l") == 1.0
        
        # None
        assert convert(None, "kg", "g") is None
        
        # Incompatible
        assert convert(1.0, "kg", "l") is None
