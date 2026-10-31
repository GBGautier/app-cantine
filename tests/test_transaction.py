"""Transactions : tout est enregistré, ou rien."""
import sqlite3
import threading

import pytest


def count(db):
    return db.one("SELECT COUNT(*) AS n FROM suppliers")["n"]


def test_validation_en_fin_de_transaction(database):
    with database.transaction():
        database.execute("INSERT INTO suppliers (name) VALUES ('A')")
    assert count(database) == 1


def test_annulation_si_erreur(database):
    with pytest.raises(RuntimeError):
        with database.transaction():
            database.execute("INSERT INTO suppliers (name) VALUES ('A')")
            raise RuntimeError("boum")
    assert count(database) == 0


def test_les_ecritures_sont_visibles_dans_la_transaction_mais_pas_dehors_avant_validation(database):
    with database.transaction():
        database.execute("INSERT INTO suppliers (name) VALUES ('A')")
        assert count(database) == 1                       # lecture dans la transaction : voit l'écriture
        autre = database.conn()                           # autre connexion : ne voit rien tant que ce n'est pas validé
        try:
            assert autre.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0] == 0
        finally:
            autre.close()
    assert count(database) == 1


def test_transaction_imbriquee_rejoint_la_transaction_en_cours(database):
    with pytest.raises(RuntimeError):
        with database.transaction():
            with database.transaction():
                database.execute("INSERT INTO suppliers (name) VALUES ('A')")
            database.execute("INSERT INTO suppliers (name) VALUES ('B')")
            raise RuntimeError
    assert count(database) == 0


def test_sans_transaction_chaque_ecriture_est_validee_aussitot(database):
    """Comportement historique, conservé pour le code qui n'utilise pas de transaction."""
    database.execute("INSERT INTO suppliers (name) VALUES ('A')")
    with pytest.raises(sqlite3.IntegrityError):
        database.execute("INSERT INTO products (name, supplier_id) VALUES ('P', 99999)")   # clé étrangère invalide
    assert count(database) == 1


def test_decorateur_atomic(database):
    @database.atomic
    def saisie():
        database.execute("INSERT INTO suppliers (name) VALUES ('A')")
        database.execute("INSERT INTO products (name, supplier_id) VALUES ('P', 99999)")   # échoue

    with pytest.raises(sqlite3.IntegrityError):
        saisie()
    assert count(database) == 0
    assert saisie.__name__ == "saisie"   # functools.wraps : FastAPI s'appuie sur le nom et la signature


def test_une_transaction_est_propre_a_son_thread(database):
    """Une requête qui s'exécute dans un autre thread ne doit pas se retrouver dans la transaction du premier."""
    vu = {}

    def autre_thread():
        vu["n"] = count(database)

    with database.transaction():
        database.execute("INSERT INTO suppliers (name) VALUES ('A')")
        t = threading.Thread(target=autre_thread)
        t.start()
        t.join()
    assert vu["n"] == 0
