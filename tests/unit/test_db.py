"""Tests unitaires pour la base de données."""

import pytest
import sqlite3
import tempfile
from pathlib import Path

from src.backend.db import (
    conn,
    init,
    rows,
    one,
    execute,
    execute_many,
    execute_script,
)


class TestDatabaseConnection:
    """Tests pour la connexion à la base de données."""

    def test_conn(self):
        """Test de la fonction conn."""
        c = conn()
        assert isinstance(c, sqlite3.Connection)
        c.close()


class TestDatabaseInitialization:
    """Tests pour l'initialisation de la base de données."""

    def test_init_creates_tables(self):
        """Test que init crée les tables nécessaires."""
        # Utiliser une base de données temporaire
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_db = f.name
        
        try:
            # Remplacer temporairement DB_PATH
            import src.backend.db as db_module
            original_db_path = db_module.DB_PATH
            db_module.DB_PATH = Path(temp_db)
            
            # Initialiser
            init()
            
            # Vérifier que les tables existent
            c = conn()
            tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            table_names = [t[0] for t in tables]
            
            expected_tables = [
                "suppliers", "products", "orders", "order_lines", "price_history",
                "meals", "meal_items", "recipes", "recipe_items", "stock_adjustments",
                "grammages", "settings", "commitments", "users", "sessions", "action_log"
            ]
            
            for table in expected_tables:
                assert table in table_names, f"Table {table} non trouvée"
            
            c.close()
        finally:
            # Restaurer DB_PATH
            db_module.DB_PATH = original_db_path
            # Supprimer la base temporaire
            Path(temp_db).unlink(missing_ok=True)


class TestDatabaseQueries:
    """Tests pour les requêtes de base de données."""

    def test_execute(self):
        """Test de la fonction execute."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_db = f.name
        
        try:
            import src.backend.db as db_module
            original_db_path = db_module.DB_PATH
            db_module.DB_PATH = Path(temp_db)
            
            init()
            
            # Insérer un fournisseur
            sid = execute(
                "INSERT INTO suppliers (name) VALUES (?)",
                ("Test Supplier",)
            )
            assert sid == 1
            
            # Vérifier l'insertion
            supplier = one("SELECT * FROM suppliers WHERE id=?", (sid,))
            assert supplier is not None
            assert supplier["name"] == "Test Supplier"
        finally:
            db_module.DB_PATH = original_db_path
            Path(temp_db).unlink(missing_ok=True)

    def test_rows(self):
        """Test de la fonction rows."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_db = f.name
        
        try:
            import src.backend.db as db_module
            original_db_path = db_module.DB_PATH
            db_module.DB_PATH = Path(temp_db)
            
            init()
            
            # Insérer plusieurs fournisseurs
            execute("INSERT INTO suppliers (name) VALUES (?)", ("Supplier 1",))
            execute("INSERT INTO suppliers (name) VALUES (?)", ("Supplier 2",))
            execute("INSERT INTO suppliers (name) VALUES (?)", ("Supplier 3",))
            
            # Récupérer tous les fournisseurs
            suppliers = rows("SELECT * FROM suppliers ORDER BY id")
            assert len(suppliers) == 3
            assert suppliers[0]["name"] == "Supplier 1"
            assert suppliers[1]["name"] == "Supplier 2"
            assert suppliers[2]["name"] == "Supplier 3"
        finally:
            db_module.DB_PATH = original_db_path
            Path(temp_db).unlink(missing_ok=True)

    def test_one(self):
        """Test de la fonction one."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_db = f.name
        
        try:
            import src.backend.db as db_module
            original_db_path = db_module.DB_PATH
            db_module.DB_PATH = Path(temp_db)
            
            init()
            
            # Insérer un fournisseur
            execute("INSERT INTO suppliers (name) VALUES (?)", ("Unique Supplier",))
            
            # Récupérer un fournisseur
            supplier = one("SELECT * FROM suppliers WHERE name=?", ("Unique Supplier",))
            assert supplier is not None
            assert supplier["name"] == "Unique Supplier"
            
            # Aucun résultat
            result = one("SELECT * FROM suppliers WHERE name=?", ("Non Existent",))
            assert result is None
        finally:
            db_module.DB_PATH = original_db_path
            Path(temp_db).unlink(missing_ok=True)

    def test_execute_many(self):
        """Test de la fonction execute_many."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_db = f.name
        
        try:
            import src.backend.db as db_module
            original_db_path = db_module.DB_PATH
            db_module.DB_PATH = Path(temp_db)
            
            init()
            
            # Insérer plusieurs fournisseurs
            suppliers = [
                ("Batch Supplier 1",),
                ("Batch Supplier 2",),
                ("Batch Supplier 3",),
            ]
            execute_many(
                "INSERT INTO suppliers (name) VALUES (?)",
                suppliers
            )
            
            # Vérifier l'insertion
            result = rows("SELECT * FROM suppliers ORDER BY id")
            assert len(result) == 3
        finally:
            db_module.DB_PATH = original_db_path
            Path(temp_db).unlink(missing_ok=True)

    def test_execute_script(self):
        """Test de la fonction execute_script."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_db = f.name
        
        try:
            import src.backend.db as db_module
            original_db_path = db_module.DB_PATH
            db_module.DB_PATH = Path(temp_db)
            
            init()
            
            # Exécuter un script
            script = """
            INSERT INTO suppliers (name) VALUES ('Script Supplier 1');
            INSERT INTO suppliers (name) VALUES ('Script Supplier 2');
            """
            execute_script(script)
            
            # Vérifier l'exécution
            result = rows("SELECT * FROM suppliers ORDER BY id")
            assert len(result) >= 2
        finally:
            db_module.DB_PATH = original_db_path
            Path(temp_db).unlink(missing_ok=True)
