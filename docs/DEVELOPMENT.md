# Guide de développement - CGRS - Réceptions & stocks

## Table des matières

1. [Prérequis](#prérequis)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Structure du code](#structure-du-code)
5. [Développement](#développement)
6. [Tests](#tests)
7. [Linting et Formatage](#linting-et-formatage)
8. [Typage](#typage)
9. [Gestion des dépendances](#gestion-des-dépendances)
10. [Dépannage](#dépannage)

---

## Prérequis

### Système

- **Python** : 3.10 ou supérieur
- **Système d'exploitation** : Linux, macOS ou Windows
- **Mémoire** : 4 Go minimum (8 Go recommandé)
- **Espace disque** : 1 Go minimum

### Dépendances système (pour le développement)

#### Linux (Debian/Ubuntu)

```bash
# Dépendances pour Tesseract OCR
sudo apt-get update
sudo apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-fra \
    tesseract-ocr-eng \
    libtesseract-dev \
    poppler-utils

# Dépendances pour le développement
sudo apt-get install -y \
    git \
    curl \
    build-essential
```

#### macOS

```bash
# Installer Homebrew (si non installé)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Dépendances pour Tesseract OCR
brew install tesseract tesseract-lang

# Dépendances pour le développement
brew install git
```

#### Windows

1. Installer **Python** depuis [python.org](https://www.python.org/downloads/)
2. Installer **Tesseract OCR** depuis [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
3. Installer **Git** depuis [git-scm.com](https://git-scm.com/download/win)

---

## Installation

### Cloner le dépôt

```bash
git clone https://github.com/GBGautier/app-cantine.git
cd app-cantine
```

### Créer un virtual environment

#### Linux/macOS

```bash
# Créer le virtual environment
python -m venv .venv

# Activer le virtual environment
source .venv/bin/activate
```

#### Windows

```cmd
:: Créer le virtual environment
python -m venv .venv

:: Activer le virtual environment
.\.venv\Scripts\activate
```

### Installer les dépendances

```bash
# Installer les dépendances de production
pip install -r requirements.txt

# Installer les dépendances de développement
pip install -e ".[dev]"
```

### Initialiser la base de données

La base de données est automatiquement initialisée au premier lancement. Vous pouvez aussi la créer manuellement :

```bash
python -c "from src.backend.db import init; init()"
```

---

## Configuration

### Variables d'environnement

Copier le fichier `.env.example` en `.env` et adapter les valeurs :

```bash
cp .env.example .env
```

Éditer `.env` avec vos paramètres :

```ini
# Environnement
ENVIRONMENT=development
DEBUG=true

# Serveur
HOST=0.0.0.0
PORT=8000
WORKERS=4

# Base de données
DATABASE_PATH=cantine.db

# Répertoires
UPLOADS_DIR=uploads
BACKUPS_DIR=sauvegardes-auto
STATIC_DIR=static

# Authentification
SECRET_KEY=changer-ceci-en-une-cle-secrete-aleatoire
PASSWORD_HASH_ALGORITHM=pbkdf2_sha256
PBKDF2_ITERATIONS=240000
SESSION_EXPIRY_DAYS=30
SESSION_COOKIE_NAME=cgrs_session

# Sécurité
CSRF_PROTECTION=true
CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
HTTPS_MODE=false

# Limites
MAX_UPLOAD_SIZE=25
MAX_LOGIN_ATTEMPTS=5
LOGIN_LOCKOUT_DURATION=60
```

### Générer une clé secrète

Pour générer une clé secrète aléatoire :

```python
import secrets
print(secrets.token_urlsafe(32))
```

---

## Structure du code

Voir [ARCHITECTURE.md](./ARCHITECTURE.md) pour une description détaillée de l'architecture.

### Organisation des fichiers

```
src/
├── backend/
│   ├── app.py              # Application FastAPI principale
│   ├── main.py             # Point d'entrée pour l'application desktop
│   ├── config/
│   │   └── __init__.py     # Configuration centrale
│   ├── models/
│   │   └── __init__.py     # Modèles Pydantic
│   ├── routes/
│   │   └── __init__.py     # Routes API
│   ├── db/
│   │   └── __init__.py     # Base de données
│   ├── services/
│   │   └── __init__.py     # Services métier
│   └── utils/
│       └── __init__.py     # Utilitaires
└── frontend/
    └── static/
        └── index.html      # Frontend
```

---

## Développement

### Lancer l'application

#### Mode développement (avec reload automatique)

```bash
uvicorn src.backend.app:app --reload --port 8000 --log-level debug
```

#### Mode production

```bash
uvicorn src.backend.app:app --host 0.0.0.0 --port 8000 --workers 4
```

#### Avec Gunicorn (pour la production)

```bash
gunicorn -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000 src.backend.app:app
```

### Accéder à l'application

Ouvrir dans votre navigateur :

```
http://localhost:8000
```

### Documentation de l'API

La documentation Swagger est disponible à :

```
http://localhost:8000/api/docs
```

La documentation ReDoc est disponible à :

```
http://localhost:8000/api/redoc
```

---

## Tests

### Exécuter tous les tests

```bash
pytest -v
```

### Exécuter les tests avec couverture

```bash
pytest -v --cov=src --cov-report=term-missing --cov-report=html
```

### Exécuter un fichier de test spécifique

```bash
pytest tests/unit/test_models.py -v
```

### Exécuter un test spécifique

```bash
pytest tests/unit/test_models.py::TestAuthModels::test_credentials -v
```

### Exécuter les tests avec différents niveaux de log

```bash
# Mode silencieux
pytest -v -q

# Mode verbeux
pytest -v -s

# Avec affichage des prints
pytest -v -s --capture=no
```

---

## Linting et Formatage

### Formatage du code avec Black

```bash
# Vérifier le formatage
black --check src/ tests/

# Formater le code
black src/ tests/
```

### Linting avec Ruff

```bash
# Vérifier le code
ruff check src/ tests/

# Corriger automatiquement
ruff check --fix src/ tests/
```

### Vérification des types avec mypy

```bash
# Vérifier les types
mypy src/ --ignore-missing-imports --allow-incomplete-defs
```

### Exécuter tous les checks

```bash
# Formatage
black src/ tests/

# Linting
ruff check --fix src/ tests/

# Typage
mypy src/ --ignore-missing-imports --allow-incomplete-defs

# Tests
pytest -v --cov=src --cov-report=term-missing
```

---

## Typage

### Annotations de type

Toutes les fonctions doivent avoir des annotations de type :

```python
# Bon
def add(a: int, b: int) -> int:
    return a + b

# Mauvais
def add(a, b):
    return a + b
```

### Types courants

| Type | Description | Exemple |
|------|-------------|---------|
| `int` | Entier | `42` |
| `float` | Nombre à virgule | `3.14` |
| `str` | Chaîne de caractères | `"hello"` |
| `bool` | Booléen | `True`, `False` |
| `list[T]` | Liste | `list[int]` |
| `dict[K, V]` | Dictionnaire | `dict[str, int]` |
| `Optional[T]` | Optionnel | `Optional[str]` |
| `Union[T1, T2]` | Union | `Union[int, str]` |
| `Any` | N'importe quel type | `Any` |

### Types personnalisés

Utiliser les types des modèles Pydantic :

```python
from src.backend.models.auth import UserOut, Credentials
from src.backend.models.suppliers import SupplierOut

def get_user(user_id: int) -> UserOut:
    ...

def create_supplier(supplier_data: SupplierOut) -> int:
    ...
```

### Typage des dépendances FastAPI

```python
from fastapi import Depends, Request
from src.backend.utils import READ, EDIT, ADMIN

def list_suppliers(user: dict = Depends(READ)) -> list[SupplierOut]:
    ...

def create_supplier(supplier: SupplierCreate, user: dict = Depends(EDIT)) -> dict:
    ...
```

---

## Gestion des dépendances

### Ajouter une dépendance

1. Ajouter la dépendance dans `requirements.txt` :
   ```
   package-name>=1.0.0
   ```

2. Installer la dépendance :
   ```bash
   pip install package-name
   ```

3. Mettre à jour le lock file (si utilisé) :
   ```bash
   pip freeze > requirements.lock
   ```

### Dépendances de développement

Ajouter les dépendances dans `pyproject.toml` sous `[project.optional-dependencies.dev]` :

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "black>=24.0.0",
    "ruff>=0.1.0",
]
```

### Mettre à jour les dépendances

```bash
# Mettre à jour une dépendance spécifique
pip install --upgrade package-name

# Mettre à jour toutes les dépendances
pip list --outdated
pip install --upgrade -r requirements.txt
```

### Vérifier les vulnérabilités

```bash
pip install safety
safety check

pip install bandit
bandit -r src/
```

---

## Dépannage

### Problèmes courants

#### 1. Erreur de module non trouvé

```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution** : Activer le virtual environment ou installer les dépendances :

```bash
source .venv/bin/activate  # Linux/macOS
.\.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

#### 2. Port déjà utilisé

```
OSError: [Errno 98] Address already in use
```

**Solution** : Changer de port ou tuer le processus existant :

```bash
# Trouver le processus
lsof -i :8000

# Tuer le processus
kill -9 <PID>

# Ou utiliser un autre port
uvicorn src.backend.app:app --port 8001
```

#### 3. Erreur de base de données

```
sqlite3.OperationalError: no such table: users
```

**Solution** : Initialiser la base de données :

```bash
python -c "from src.backend.db import init; init()"
```

#### 4. Erreur de Tesseract OCR

```
TesseractNotFoundError: tesseract is not installed or it's not in your PATH
```

**Solution** : Installer Tesseract :

```bash
# Linux
sudo apt-get install tesseract-ocr tesseract-ocr-fra

# macOS
brew install tesseract tesseract-lang

# Windows
# Télécharger depuis https://github.com/UB-Mannheim/tesseract/wiki
```

#### 5. Erreur de permissions

```
PermissionError: [Errno 13] Permission denied
```

**Solution** : Vérifier les permissions des fichiers et répertoires :

```bash
# Donner les permissions
chmod +x script.py
chmod -R 755 data/

# Ou exécuter en tant qu'administrateur
sudo python script.py
```

---

## Outils recommandés

### Éditeurs de code

- **VS Code** : Léger, extensible, excellent support Python
  - Extensions recommandées :
    - Python (Microsoft)
    - Pylance (Microsoft)
    - Black Formatter
    - Ruff
    - mypy
    - GitLens

- **PyCharm** : IDE complet pour Python
  - Version Community (gratuite) ou Professional

### Outils de développement

- **Git** : Contrôle de version
- **Docker** : Conteneurisation
- **Postman** : Tests d'API
- **pgAdmin** ou **DB Browser for SQLite** : Gestion de base de données
- **Tesseract** : OCR

---

## Contribuer

1. **Forker** le dépôt
2. **Créer une branche** pour votre fonctionnalité :
   ```bash
   git checkout -b feature/ma-fonctionnalité
   ```
3. **Faire des commits** avec des messages clairs :
   ```bash
   git commit -m "Ajout de la fonctionnalité X"
   ```
4. **Pousser** vers votre fork :
   ```bash
   git push origin feature/ma-fonctionnalité
   ```
5. **Créer une Pull Request** vers la branche `main`

### Conventions de commit

Utiliser les conventions [Conventional Commits](https://www.conventionalcommits.org/) :

- `feat:` : Nouvelle fonctionnalité
- `fix:` : Correction de bug
- `docs:` : Documentation
- `style:` : Changements de style (formatage, etc.)
- `refactor:` : Refactorisation du code
- `perf:` : Amélioration des performances
- `test:` : Ajout ou correction de tests
- `chore:` : Changements divers (build, dépendances, etc.)

Exemples :

```
feat: ajout de l'authentification à 2 facteurs
fix: correction de l'erreur de parsing des PDF
docs: mise à jour de la documentation API
style: formatage du code avec Black
refactor: restructuration des modèles
perf: optimisation des requêtes de base de données
test: ajout de tests pour l'authentification
chore: mise à jour des dépendances
```

### Checklist avant Pull Request

- [ ] Le code suit les conventions de style
- [ ] Les tests passent
- [ ] Le code est typé
- [ ] La documentation est mise à jour
- [ ] Les dépendances sont à jour
- [ ] Les vulnérabilités de sécurité sont corrigées
