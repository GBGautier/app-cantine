"""Module de gestion de la base de données.

Ce module centralise toutes les opérations liées à la base de données SQLite,
y compris l'initialisation du schéma, les migrations et les requêtes.
"""

import sqlite3
from pathlib import Path
from typing import Any

from src.backend.config import get_database_path

# Chemin vers la base de données
DB_PATH = get_database_path()


# Schéma de la base de données
SCHEMA = """
CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    contact TEXT, email TEXT, phone TEXT, address TEXT, siret TEXT,
    delivery_days TEXT,            -- JSON : ["lun", "jeu"]
    franco REAL,                   -- montant minimum de commande pour une livraison (€ HT)
    order_method TEXT,             -- internet | telephone | email | autre
    order_url TEXT,                -- lien du site de commande (si internet)
    categories TEXT,               -- JSON : catégories de produits vendues
    local_default TEXT,            -- provenance par défaut des produits de ce fournisseur
    direct_producteur INTEGER DEFAULT 0,
    parser_regex TEXT,             -- regex optionnelle de lecture des lignes de PDF
    keywords TEXT,                 -- mots-clés de reconnaissance dans les PDF, séparés par « ; »
    notes TEXT
);
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ref TEXT,                      -- référence du produit chez le fournisseur
    name TEXT NOT NULL,
    supplier_id INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
    category TEXT,
    gamme TEXT,                    -- 1 à 6
    label_egalim TEXT DEFAULT 'bio',   -- bio | autre | sans
    label_detail TEXT,             -- AOP, Label Rouge, MSC...
    provenance TEXT,               -- cc_nozay | loire_atlantique | pays_loire | france | ue | international
    direct_producteur INTEGER DEFAULT 0,
    commerce_equitable INTEGER DEFAULT 0,
    avoid INTEGER DEFAULT 0,       -- « à éviter » : produit signalé (affiché en orange dans la liste)
    favorite INTEGER DEFAULT 0,    -- produit favori (étoile)
    unit TEXT DEFAULT 'kg',
    unit_price REAL,               -- prix courant (dernier prix connu)
    datasheet TEXT,                -- fichier de la fiche technique
    notes TEXT
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
    ref TEXT,
    kind TEXT DEFAULT 'livraison', -- livraison (provisoire) | facture (définitive)
    date TEXT,                     -- AAAA-MM-JJ
    delivery_date TEXT,            -- facture qui remplace des bons de livraison : date de livraison (date des relevés de prix)
    total_ht REAL,
    source_file TEXT,
    notes TEXT
);
CREATE TABLE IF NOT EXISTS order_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
    ref TEXT,
    label TEXT,
    qty REAL, unit TEXT, unit_price REAL, total_ht REAL
);
CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    date TEXT,
    price REAL NOT NULL,
    unit TEXT,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    source TEXT                    -- reception | manuel
);
CREATE INDEX IF NOT EXISTS ix_price_history ON price_history(product_id, date);
CREATE TABLE IF NOT EXISTS meals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    nb_maternelles INTEGER DEFAULT 0,
    nb_elementaires INTEGER DEFAULT 0,
    nb_adultes INTEGER DEFAULT 0,
    guests INTEGER NOT NULL DEFAULT 0,   -- total des trois
    name TEXT,                     -- inutilisé (ancien « intitulé du repas »)
    entree TEXT,
    plat TEXT,
    accompagnement TEXT,
    laitage TEXT,
    dessert TEXT,
    notes TEXT,
    commentaire_post TEXT,         -- commentaire après le repas (gaspillage, etc.)
    modif_prevu INTEGER DEFAULT 0, -- 1 = le repas prévu a été modifié
    recipe_entree TEXT,               -- recette liée à l'entrée (id)
    recipe_plat TEXT,                 -- recette liée au plat (id)
    recipe_accompagnement TEXT,       -- recette liée à l'accompagnement (id)
    recipe_laitage TEXT,              -- recette liée au laitage (id)
    recipe_dessert TEXT,              -- recette liée au dessert (id)
    estimation TEXT,                  -- JSON : lignes de l'onglet « Estimation des coûts » (produits rattachés, qtés, prix)
    statut TEXT DEFAULT 'prevu'    -- prevu | passe
);
CREATE TABLE IF NOT EXISTS meal_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meal_id INTEGER NOT NULL REFERENCES meals(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    qty REAL NOT NULL,
    unit TEXT,
    prix_reel REAL                 -- prix réellement payé (ajustement post-repas)
);
CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    categorie TEXT,                -- entree | plat | accompagnement | laitage | dessert
    description TEXT,
    created TEXT
);
CREATE TABLE IF NOT EXISTS recipe_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
    label TEXT,                    -- nom libre si pas de product_id
    qty_maternelle REAL,           -- grammage par convive maternelle (g)
    qty_elementaire REAL,          -- grammage par convive élémentaire (g)
    qty_adulte REAL                -- grammage par convive adulte (g)
);
CREATE TABLE IF NOT EXISTS stock_adjustments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    date TEXT,
    qty REAL NOT NULL,             -- positif ou négatif
    unit TEXT,
    reason TEXT,
    username TEXT
);
CREATE TABLE IF NOT EXISTS grammages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_key TEXT,               -- entrees | plats | accompagnements | produits_laitiers | desserts
    section_label TEXT,             -- libellé affiché de la section
    section_title TEXT,             -- sous-titre de la section (peut être NULL)
    label TEXT NOT NULL,            -- intitulé GEMRCN / CGRS
    gemrcn TEXT,                    -- JSON : [mat, elem, adu] recommandé par le GEMRCN
    cgrs TEXT,                      -- JSON : [mat, elem, adu] appliqué par le CGRS
    coeff REAL DEFAULT 1,           -- coefficient cru/cuit (qté à acheter = qté à servir × coeff)
    unit TEXT                       -- 'unité' pour les grammages en nombre de pièces
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS commitments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    metric TEXT NOT NULL,          -- bio | egalim | local | direct | provenance:<clé> | gamme:<n> | label:<clé> | price_per_meal (conservé pour compat.)
    metrics TEXT,                  -- JSON : liste d'indicateurs (remplace metric)
    category TEXT,                 -- optionnel : calcul limité à une catégorie (conservé pour compat.)
    categories TEXT,               -- JSON : liste de catégories (remplace category)
    gammes TEXT,                   -- JSON : liste de gammes filtrées (optionnel)
    level TEXT DEFAULT 'marche',   -- marche (engagements du marché) | par (engagements PAR)
    target REAL NOT NULL,          -- % (ou € pour price_per_meal)
    mode TEXT DEFAULT 'min',       -- min = au moins | max = au plus
    notes TEXT
);
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,            -- admin | reader | stats
    created TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS action_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,              -- horodatage ISO (UTC)
    username TEXT NOT NULL,        -- identifiant de l'utilisateur
    action TEXT NOT NULL,          -- create | update | delete
    entity TEXT NOT NULL,          -- supplier | product | order | meal | commitment | user | stock | settings
    entity_id INTEGER,             -- id de l'objet concerné (NULL si supprimé ou non applicable)
    description TEXT               -- résumé lisible
);
CREATE INDEX IF NOT EXISTS ix_action_log_ts ON action_log(ts DESC);
"""

# Colonnes ajoutées après la première version
NEW_COLUMNS = {
    "suppliers": {"keywords": "TEXT", "delivery_days": "TEXT", "franco": "REAL", "order_method": "TEXT",
                  "order_url": "TEXT", "categories": "TEXT"},
    "products": {"ref": "TEXT", "datasheet": "TEXT", "avoid": "INTEGER DEFAULT 0", "favorite": "INTEGER DEFAULT 0"},
    "order_lines": {"ref": "TEXT"},
    "orders": {"delivery_date": "TEXT"},
    "commitments": {"level": "TEXT DEFAULT 'marche'", "metrics": "TEXT", "categories": "TEXT", "gammes": "TEXT"},
    "meals": {"nb_maternelles": "INTEGER DEFAULT 0", "nb_elementaires": "INTEGER DEFAULT 0",
              "nb_adultes": "INTEGER DEFAULT 0", "entree": "TEXT", "plat": "TEXT",
              "accompagnement": "TEXT", "laitage": "TEXT", "dessert": "TEXT",
              "commentaire_post": "TEXT", "statut": "TEXT DEFAULT 'prevu'",
              "recipe_entree": "TEXT", "recipe_plat": "TEXT", "recipe_accompagnement": "TEXT", "recipe_laitage": "TEXT", "recipe_dessert": "TEXT",
              "estimation": "TEXT",
              "modif_prevu": "INTEGER DEFAULT 0"},
    "meal_items": {"prix_reel": "REAL"},
    "recipes": {"nb_maternelles": "INTEGER DEFAULT 0", "nb_elementaires": "INTEGER DEFAULT 0",
                "nb_adultes": "INTEGER DEFAULT 0"},
    "recipe_items": {"qty_servi": "REAL", "qty_commander": "REAL", "principal": "INTEGER DEFAULT 0", "intitule_gemrcn": "TEXT", "unit": "TEXT"},
}


def conn():
    """Crée une nouvelle connexion à la base de données."""
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def init():
    """Initialise la base de données avec le schéma et les migrations."""
    with conn() as c:
        c.executescript(SCHEMA)
        for table, cols in NEW_COLUMNS.items():
            existing = {r[1] for r in c.execute(f"PRAGMA table_info({table})")}
            for col, typ in cols.items():
                if col not in existing:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
        
        # Migrations de données
        c.execute("UPDATE orders SET kind='livraison' WHERE kind IS NULL OR kind NOT IN ('livraison','facture')")
        c.execute("UPDATE products SET category='Fruit: autres' WHERE category='fruits'")
        c.execute("UPDATE commitments SET category='Fruit: autres' WHERE category='fruits'")
        c.execute("UPDATE suppliers SET categories=REPLACE(categories, '\"fruits\"', '\"Fruit: autres\"') "
                  "WHERE categories LIKE '%\"fruits\"%'")
        
        # Renommage des catégories
        renames = [
            ("Fruit: pommes, poires, kiwis", "Fruits: pommes, poires, kiwis"), ("Fruit: autres", "Fruits: autres"),
            ("légume", "Légumes"), ("viande porc", "Viande de porc"), ("viande volaille", "Viande de volaille"),
            ("viande boeuf", "Viande de boeuf"), ("pêche", "Produits de la pêche"), ("laitier", "Produits laitiers"),
            ("ovoproduit", "Ovoproduits"), ("épicerie légumineuse", "Épicerie: légumineuses"),
            ("épicerie céréale", "Épicerie: céréales"), ("épicerie autre", "Épicerie: autre"),
            ("pain", "Pain"), ("autre", "Autre"),
            ("Viande porc", "Viande de porc"), ("Viande volaille", "Viande de volaille"), ("Ovoproduit", "Ovoproduits"),
            ("Épicerie légumineuse", "Épicerie: légumineuses"), ("Épicerie céréale", "Épicerie: céréales"),
            ("Épicerie autre", "Épicerie: autre"), ("Viande boeuf", "Viande de boeuf"),
        ]
        for old, new in renames:
            c.execute("UPDATE products SET category=? WHERE category=?", (new, old))
            c.execute("UPDATE commitments SET category=? WHERE category=?", (new, old))
            c.execute("UPDATE commitments SET categories=REPLACE(categories, ?, ?) WHERE categories LIKE ?",
                      ('"' + old + '"', '"' + new + '"', '%"' + old + '"%'))
            c.execute("UPDATE suppliers SET categories=REPLACE(categories, ?, ?) WHERE categories LIKE ?",
                      ('"' + old + '"', '"' + new + '"', '%"' + old + '"%'))


def rows(sql: str, args: tuple = ()) -> list[dict]:
    """Exécute une requête et retourne tous les résultats sous forme de dictionnaires."""
    with conn() as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]


def one(sql: str, args: tuple = ()) -> dict | None:
    """Exécute une requête et retourne le premier résultat sous forme de dictionnaire."""
    r = rows(sql, args)
    return r[0] if r else None


def execute(sql: str, args: tuple = ()) -> int:
    """Exécute une requête et retourne l'ID de la dernière ligne insérée."""
    with conn() as c:
        cur = c.execute(sql, args)
        return cur.lastrowid


def execute_many(sql: str, args_list: list[tuple]) -> None:
    """Exécute une requête avec plusieurs jeux de paramètres."""
    with conn() as c:
        c.executemany(sql, args_list)


def execute_script(sql: str) -> None:
    """Exécute un script SQL."""
    with conn() as c:
        c.executescript(sql)
