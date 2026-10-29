# Architecture de l'application CGRS - Réceptions & stocks

## Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Structure du projet](#structure-du-projet)
3. [Backend](#backend)
4. [Frontend](#frontend)
5. [Base de données](#base-de-données)
6. [Sécurité](#sécurité)
7. [Déploiement](#déploiement)
8. [Bonnes pratiques](#bonnes-pratiques)

---

## Vue d'ensemble

L'application CGRS (Centre de Gestion des Réceptions et Stocks) est une solution complète pour la gestion des cantines scolaires. Elle permet de :

- Gérer les fournisseurs et leurs produits
- Enregistrer les commandes et réceptions
- Planifier les repas et recettes
- Suivre les stocks
- Générer des statistiques et rapports
- Exporter les données vers Dolibarr

L'application est construite avec une architecture moderne et modulaire, utilisant :

- **Python 3.10+** comme langage principal
- **FastAPI** pour le backend REST
- **SQLite** pour la persistance des données
- **HTML/CSS/JavaScript** pour le frontend
- **Docker** pour le déploiement

---

## Structure du projet

```
cgrs-app/
├── src/
│   ├── __init__.py
│   ├── backend/
│   │   ├── __init__.py
│   │   ├── app.py              # Application FastAPI principale
│   │   ├── main.py             # Point d'entrée pour l'application desktop
│   │   ├── config/
│   │   │   ├── __init__.py     # Configuration centrale
│   │   │   └── paths.py        # Gestion des chemins
│   │   ├── models/
│   │   │   ├── __init__.py     # Export des modèles
│   │   │   ├── base.py         # Modèles de base
│   │   │   ├── auth.py         # Modèles d'authentification
│   │   │   ├── suppliers.py    # Modèles des fournisseurs
│   │   │   ├── products.py     # Modèles des produits
│   │   │   ├── orders.py       # Modèles des commandes
│   │   │   ├── meals.py        # Modèles des repas
│   │   │   ├── recipes.py      # Modèles des recettes
│   │   │   ├── stocks.py       # Modèles des stocks
│   │   │   └── commitments.py  # Modèles des engagements
│   │   ├── routes/
│   │   │   ├── __init__.py     # Export des routes
│   │   │   ├── auth.py         # Routes d'authentification
│   │   │   ├── users.py        # Routes des utilisateurs
│   │   │   ├── suppliers.py    # Routes des fournisseurs
│   │   │   ├── products.py     # Routes des produits
│   │   │   ├── orders.py       # Routes des commandes
│   │   │   ├── meals.py        # Routes des repas
│   │   │   ├── recipes.py      # Routes des recettes
│   │   │   ├── stocks.py       # Routes des stocks
│   │   │   ├── commitments.py  # Routes des engagements
│   │   │   ├── settings.py     # Routes des paramètres
│   │   │   ├── grammages.py    # Routes des grammages
│   │   │   ├── export.py       # Routes d'export
│   │   │   ├── files.py        # Routes des fichiers
│   │   │   └── backup.py       # Routes des sauvegardes
│   │   ├── db/
│   │   │   └── __init__.py     # Gestion de la base de données
│   │   ├── services/
│   │   │   ├── __init__.py     # Export des services
│   │   │   ├── dolibarr.py     # Export Dolibarr
│   │   │   ├── pdf_parser.py   # Parsing des PDF
│   │   │   └── menu_parser.py  # Parsing des menus
│   │   └── utils/
│   │       └── __init__.py     # Fonctions utilitaires
│   └── frontend/
│       └── static/
│           └── index.html      # Frontend HTML/CSS/JS
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_utils.py
│   │   ├── test_models.py
│   │   ├── test_db.py
│   │   └── test_services.py
│   └── integration/
│       ├── __init__.py
│       └── test_api.py
├── config/
│   ├── nginx/
│   │   ├── nginx.conf
│   │   └── ssl/
│   └── .env.example
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── backup.yml
├── Dockerfile
├── docker-compose.yml
├── docker-compose.prod.yml
├── pyproject.toml
├── requirements.txt
├── README.md
└── .gitignore
```

---

## Backend

### Application FastAPI

Le cœur de l'application est construit avec **FastAPI**, un framework moderne pour créer des APIs REST en Python. Les principaux avantages sont :

- **Typage fort** avec Pydantic
- **Validation automatique** des données
- **Documentation automatique** (Swagger/OpenAPI)
- **Performances élevées** (basé sur Starlette)

### Structure des routes

Les routes sont organisées par domaine fonctionnel et suivent le pattern REST :

| Domaine | Préfixe | Description |
|---------|---------|-------------|
| Authentification | `/api/auth` | Connexion, déconnexion, gestion des sessions |
| Utilisateurs | `/api/users` | Gestion des utilisateurs (CRUD) |
| Fournisseurs | `/api/suppliers` | Gestion des fournisseurs (CRUD) |
| Produits | `/api/products` | Gestion des produits (CRUD) |
| Commandes | `/api/orders` | Gestion des commandes et réceptions |
| Repas | `/api/meals` | Gestion des repas et planning |
| Recettes | `/api/recipes` | Gestion des recettes |
| Stocks | `/api/stocks` | Suivi des stocks |
| Engagements | `/api/commitments` | Gestion des engagements (EGalim, etc.) |
| Paramètres | `/api/settings` | Gestion des paramètres de l'application |
| Grammages | `/api/grammages` | Gestion des grammages GEMRCN |
| Export | `/api/export` | Export des données (Dolibarr, etc.) |
| Fichiers | `/api/files` | Gestion des fichiers uploadés |
| Sauvegardes | `/api/backup` | Gestion des sauvegardes |

### Modèles de données

Les modèles sont définis avec **Pydantic** pour :

1. **Valider** les données entrantes
2. **Sérialiser** les données sortantes
3. **Documenter** l'API automatiquement

Chaque domaine a ses propres modèles :

- `models/auth.py` : Utilisateurs, rôles, authentification
- `models/suppliers.py` : Fournisseurs
- `models/products.py` : Produits, catégories, provenances
- `models/orders.py` : Commandes, lignes de commande
- `models/meals.py` : Repas, éléments de repas
- `models/recipes.py` : Recettes, ingrédients
- `models/stocks.py` : Ajustements de stock
- `models/commitments.py` : Engagements

### Services

Les services contiennent la logique métier :

- `services/dolibarr.py` : Export des données vers Dolibarr
- `services/pdf_parser.py` : Parsing des PDF de commandes/réceptions
- `services/menu_parser.py` : Parsing des PDF de menus

### Utilitaires

Les fonctions utilitaires communes sont dans `utils/__init__.py` :

- Gestion des mots de passe (hachage, vérification)
- Gestion des sessions
- Conversion d'unités
- Journalisation des actions
- Vérification des permissions

---

## Frontend

Le frontend est actuellement un fichier HTML statique (`static/index.html`) qui :

1. Utilise **Vanilla JavaScript** (pas de framework pour l'instant)
2. Communique avec le backend via **Fetch API**
3. Gère l'état localement
4. Utilise **Bootstrap** pour le style (à confirmer)

### Architecture frontend recommandée

Pour une meilleure maintenabilité, il est recommandé de migrer vers :

1. **Un framework moderne** : React, Vue.js ou Svelte
2. **Une architecture par composants** :
   - `components/` : Composants réutilisables
   - `pages/` : Pages principales
   - `stores/` : Gestion d'état (Redux, Pinia, etc.)
   - `services/` : Appels API
   - `utils/` : Fonctions utilitaires frontend
3. **TypeScript** pour le typage fort

---

## Base de données

### Schéma SQLite

La base de données SQLite contient les tables suivantes :

| Table | Description |
|-------|-------------|
| `suppliers` | Fournisseurs |
| `products` | Produits |
| `orders` | Commandes et réceptions |
| `order_lines` | Lignes de commande |
| `price_history` | Historique des prix |
| `meals` | Repas |
| `meal_items` | Éléments des repas |
| `recipes` | Recettes |
| `recipe_items` | Ingrédients des recettes |
| `stock_adjustments` | Ajustements de stock |
| `grammages` | Grammages GEMRCN/CGRS |
| `settings` | Paramètres de l'application |
| `commitments` | Engagements |
| `users` | Utilisateurs |
| `sessions` | Sessions utilisateurs |
| `action_log` | Journal des actions |

### Migrations

Les migrations sont gérées directement dans le code via la fonction `init()` dans `db/__init__.py` :

1. Création des tables si elles n'existent pas
2. Ajout des colonnes manquantes
3. Exécution des migrations de données

### Accès aux données

Les fonctions d'accès à la base sont :

- `conn()` : Crée une nouvelle connexion
- `init()` : Initialise la base de données
- `rows(sql, args)` : Exécute une requête et retourne tous les résultats
- `one(sql, args)` : Exécute une requête et retourne le premier résultat
- `execute(sql, args)` : Exécute une requête et retourne l'ID de la dernière ligne
- `execute_many(sql, args_list)` : Exécute une requête avec plusieurs jeux de paramètres
- `execute_script(sql)` : Exécute un script SQL

---

## Sécurité

### Authentification

- **PBKDF2-SHA256** pour le hachage des mots de passe
- **240 000 itérations** pour ralentir les attaques par force brute
- **Sessions** avec tokens aléatoires (32 caractères)
- **Duration des sessions** : 30 jours (configurable)

### Protection des endpoints

- **Protection CSRF** : En-tête `x-requested-with: cgrs` requis pour les requêtes POST/PUT/DELETE
- **Protection CORS** : Origines autorisées configurables
- **En-têtes de sécurité** :
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY` (sauf pour `/api/files/`)
  - `Referrer-Policy: same-origin`
  - `Cache-Control: no-store` pour les endpoints API

### Protection contre les attaques

- **Limite des tentatives de connexion** : 5 tentatives maximum, puis blocage de 60 secondes
- **Taille maximale des uploads** : 25 Mo
- **Validation des fichiers** : Extensions autorisées seulement
- **Sanitization** : Nettoyage des entrées utilisateur

### Bonnes pratiques

1. **Ne jamais stocker de mots de passe en clair**
2. **Utiliser des tokens aléatoires** pour les sessions
3. **Valider toutes les entrées** utilisateur
4. **Limiter les permissions** selon les rôles
5. **Journaliser les actions** sensibles
6. **Ne pas exposer d'informations** sensibles dans les erreurs

---

## Déploiement

### Développement local

1. Cloner le dépôt :
   ```bash
   git clone https://github.com/GBGautier/app-cantine.git
   cd app-cantine
   ```

2. Créer un virtual environment :
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   .\.venv\Scripts\activate  # Windows
   ```

3. Installer les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

4. Lancer l'application :
   ```bash
   uvicorn src.backend.app:app --reload --port 8000
   ```

5. Ouvrir dans le navigateur :
   ```
   http://localhost:8000
   ```

### Déploiement avec Docker

1. Construire l'image :
   ```bash
   docker build -t cgrs-app .
   ```

2. Lancer avec Docker Compose :
   ```bash
   docker-compose up -d
   ```

3. Pour la production :
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

### Configuration

Copier `.env.example` en `.env` et adapter les valeurs :

```bash
cp .env.example .env
```

Les principales variables sont :

- `ENVIRONMENT` : `development` ou `production`
- `DEBUG` : `true` ou `false`
- `SECRET_KEY` : Clé secrète pour les sessions
- `DATABASE_PATH` : Chemin vers la base de données
- `UPLOADS_DIR` : Répertoire des uploads
- `CORS_ORIGINS` : Origines CORS autorisées

### Reverse Proxy (Nginx)

Un exemple de configuration Nginx est fourni dans `config/nginx/nginx.conf` :

- **SSL/TLS** : Configuration sécurisée
- **Reverse Proxy** : Vers l'application FastAPI
- **En-têtes de sécurité** : Protection supplémentaire
- **Cache** : Optimisation des performances

---

## Bonnes pratiques

### Développement

1. **Suivre les conventions de nommage** :
   - `snake_case` pour les variables et fonctions
   - `PascalCase` pour les classes
   - `SCREAMING_SNAKE_CASE` pour les constantes

2. **Documenter le code** :
   - Docstrings pour toutes les fonctions et classes
   - Commentaires pour les parties complexes

3. **Écrire des tests** :
   - Tests unitaires pour les fonctions
   - Tests d'intégration pour les endpoints
   - Tests E2E pour les workflows complets

4. **Utiliser le typage** :
   - Annotations de type pour toutes les fonctions
   - Modèles Pydantic pour la validation

5. **Gérer les erreurs** :
   - Ne pas laisser les exceptions non gérées
   - Retourner des messages d'erreur clairs
   - Journaliser les erreurs

### Performance

1. **Optimiser les requêtes** :
   - Éviter les N+1 queries
   - Utiliser les jointures
   - Limiter les résultats

2. **Cache** :
   - Cache des données statiques
   - Cache des résultats de calculs coûteux

3. **Asynchrone** :
   - Utiliser `async/await` pour les opérations I/O
   - Éviter de bloquer l'event loop

### Sécurité

1. **Mettre à jour les dépendances** :
   ```bash
   pip list --outdated
   pip install --upgrade <package>
   ```

2. **Scanner les vulnérabilités** :
   ```bash
   pip install safety bandit
   safety check
   bandit -r src/
   ```

3. **Revoir les permissions** :
   - Vérifier les rôles et permissions
   - Limiter les accès sensibles

4. **Auditer le code** :
   - Vérifier les points d'entrée
   - Vérifier la validation des données
   - Vérifier la gestion des erreurs

---

## Annexes

### Technologies utilisées

| Catégorie | Technologie | Version |
|----------|-------------|---------|
| Langage | Python | 3.10+ |
| Backend | FastAPI | 0.109+ |
| ASGI Server | Uvicorn | 0.27+ |
| Base de données | SQLite | 3 |
| OCR | Tesseract | 5 |
| PDF Parsing | pdfplumber | 0.10+ |
| Desktop | pywebview | 5 |
| Validation | Pydantic | 2.5+ |
| Tests | pytest | 7.4+ |
| Linting | ruff, black, mypy | Latest |
| Conteneurisation | Docker | 20+ |
| Orchestration | Docker Compose | 2+ |

### Dépendances principales

```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.6
pdfplumber>=0.10.3
pytesseract>=0.3.10
Pillow>=10.1.0
pywebview>=5.0
pydantic>=2.5.0
python-dotenv>=1.0.0
```

### Outils de développement

```
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-asyncio>=0.23.0
httpx>=0.26.0
black>=24.0.0
ruff>=0.1.0
mypy>=1.8.0
```
