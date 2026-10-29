"""Tests d'intégration pour l'API."""

import pytest
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

from src.backend.app import app
from src.backend.db import init as db_init, execute as db_execute


@pytest.fixture(scope="module")
def test_client():
    """Crée un client de test pour l'API."""
    return TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    """Configure une base de données de test."""
    # Créer une base de données temporaire
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_db = f.name
    
    # Remplacer DB_PATH
    import src.backend.db as db_module
    original_db_path = db_module.DB_PATH
    db_module.DB_PATH = Path(temp_db)
    
    # Initialiser la base
    db_init()
    
    yield
    
    # Nettoyer
    db_module.DB_PATH = original_db_path
    Path(temp_db).unlink(missing_ok=True)


class TestAuthAPI:
    """Tests pour les endpoints d'authentification."""

    def test_auth_status_no_users(self, test_client):
        """Test du statut d'authentification sans utilisateurs."""
        response = test_client.get("/api/auth/status")
        assert response.status_code == 200
        data = response.json()
        assert "setup_needed" in data
        assert data["setup_needed"] is True
        assert data["user"] is None

    def test_auth_setup(self, test_client):
        """Test de la création du premier compte."""
        response = test_client.post(
            "/api/auth/setup",
            json={"username": "admin", "password": "admin123"},
            headers={"x-requested-with": "cgrs"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert data["user"]["username"] == "admin"
        assert data["user"]["role"] == "admin"

    def test_auth_setup_already_exists(self, test_client):
        """Test de la création du premier compte quand un utilisateur existe déjà."""
        # Créer un utilisateur
        test_client.post(
            "/api/auth/setup",
            json={"username": "admin", "password": "admin123"},
            headers={"x-requested-with": "cgrs"}
        )
        
        # Essayer de créer un autre compte
        response = test_client.post(
            "/api/auth/setup",
            json={"username": "admin2", "password": "admin123"},
            headers={"x-requested-with": "cgrs"}
        )
        assert response.status_code == 403

    def test_auth_login(self, test_client):
        """Test de la connexion."""
        # Créer un utilisateur
        test_client.post(
            "/api/auth/setup",
            json={"username": "testuser", "password": "testpass123"},
            headers={"x-requested-with": "cgrs"}
        )
        
        # Se connecter
        response = test_client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "testpass123"},
            headers={"x-requested-with": "cgrs"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert data["user"]["username"] == "testuser"

    def test_auth_login_wrong_password(self, test_client):
        """Test de la connexion avec un mauvais mot de passe."""
        # Créer un utilisateur
        test_client.post(
            "/api/auth/setup",
            json={"username": "testuser", "password": "testpass123"},
            headers={"x-requested-with": "cgrs"}
        )
        
        # Se connecter avec un mauvais mot de passe
        response = test_client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "wrongpass"},
            headers={"x-requested-with": "cgrs"}
        )
        assert response.status_code == 401

    def test_auth_logout(self, test_client):
        """Test de la déconnexion."""
        # Créer et connecter un utilisateur
        test_client.post(
            "/api/auth/setup",
            json={"username": "testuser", "password": "testpass123"},
            headers={"x-requested-with": "cgrs"}
        )
        test_client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "testpass123"},
            headers={"x-requested-with": "cgrs"}
        )
        
        # Se déconnecter
        response = test_client.post("/api/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True


class TestSuppliersAPI:
    """Tests pour les endpoints des fournisseurs."""

    def test_list_suppliers_empty(self, test_client):
        """Test de la liste des fournisseurs vide."""
        response = test_client.get("/api/suppliers/")
        assert response.status_code == 401  # Non autorisé sans authentification

    def test_create_supplier(self, test_client):
        """Test de la création d'un fournisseur."""
        # Créer et connecter un utilisateur admin
        test_client.post(
            "/api/auth/setup",
            json={"username": "admin", "password": "admin123"},
            headers={"x-requested-with": "cgrs"}
        )
        login_response = test_client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
            headers={"x-requested-with": "cgrs"}
        )
        
        # Créer un fournisseur
        response = test_client.post(
            "/api/suppliers/",
            json={"name": "Test Supplier"},
            headers={"x-requested-with": "cgrs"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data


class TestHealthCheck:
    """Tests pour le health check."""

    def test_root_endpoint(self, test_client):
        """Test de l'endpoint racine."""
        response = test_client.get("/")
        assert response.status_code == 200
