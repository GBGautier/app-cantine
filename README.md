# CGRS – Réceptions & stocks

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-005571.svg)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3-07405E.svg)](https://www.sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linting: Ruff](https://img.shields.io/badge/linting-ruff-1E1E1E.svg)](https://github.com/astral-sh/ruff)

**Application professionnelle de gestion des réceptions et stocks pour les cantines scolaires**

CGRS (Centre de Gestion des Réceptions et Stocks) est une solution complète open-source conçue pour répondre aux besoins spécifiques des cantines scolaires. Elle permet une gestion centralisée des fournisseurs, commandes, réceptions, stocks, repas, recettes et engagements (EGalim, bio, local, etc.).

---

## 📋 Table des matières

- [✨ Fonctionnalités](#-fonctionnalités)
- [🚀 Installation rapide](#-installation-rapide)
- [⚙️ Configuration](#️-configuration)
- [📖 Documentation complète](#-documentation-complète)
- [🔒 Sécurité](#-sécurité)
- [🏗️ Architecture](#️-architecture)
- [🛠️ Développement](#-développement)
- [🚢 Déploiement](#-déploiement)
- [🤝 Contribution](#-contribution)
- [📜 Licence](#-licence)

---

## ✨ Fonctionnalités

### 📦 Gestion des fournisseurs
- Fiches détaillées des fournisseurs avec contacts, SIRET, adresses
- Configuration des méthodes de commande (internet, téléphone, email)
- Gestion des jours de livraison et seuils de franco
- Classification par provenance (local, régional, national, UE, international)
- Parsing automatique des PDF de commandes avec regex personnalisées

### 📋 Commandes et réceptions
- Saisie des commandes et bons de livraison
- Import automatique depuis PDF (avec OCR via Tesseract)
- Historique complet des prix avec suivi des évolutions
- Calcul automatique des écarts entre commandes et réceptions
- Validation des totaux HT pour détecter les erreurs de saisie

### 🥬 Produits et stocks
- Base de données produits avec références fournisseurs
- Classification par catégorie, gamme, label (bio, Label Rouge, AOP, MSC, etc.)
- Suivi des provenances et circuits courts
- Gestion des stocks avec ajustements manuels
- Alertes sur les produits à éviter ou favoris

### 🍽️ Planification des repas
- Calendrier des repas par jour
- Gestion des effectifs (maternelle, élémentaire, adultes)
- Association des recettes aux éléments du menu
- Estimation automatique des coûts
- Suivi des gaspillages et commentaires post-repas

### 📝 Recettes
- Base de recettes avec ingrédients détaillés
- Grammages différenciés par type de convive (maternelle, élémentaire, adulte)
- Classification par catégorie (entrée, plat, accompagnement, laitage, dessert)
- Calcul automatique des quantités nécessaires
- Génération de listes de courses

### 📊 Engagements et statistiques
- Suivi des engagements EGalim (bio, local, qualité, etc.)
- Indicateurs personnalisables par catégorie de produits
- Calcul automatique des pourcentages
- Tableaux de bord et rapports exportables
- Historique des performances

### 📈 Export et intégration
- Export des données vers Dolibarr (ERP)
- Génération de rapports PDF
- Export Excel des données
- API REST complète pour l'intégration avec d'autres systèmes

### 🔐 Sécurité et administration
- Authentification sécurisée avec PBKDF2-SHA256
- Gestion des utilisateurs avec rôles (admin, éditeur, lecteur, statistiques)
- Protection CSRF et CORS configurables
- Journalisation complète des actions
- Sauvegardes automatiques de la base de données

---

## 🚀 Installation rapide

### Méthode 1: Avec Docker (recommandé)

```bash
# Cloner le dépôt
git clone https://github.com/GBGautier/app-cantine.git
cd app-cantine

# Copier le fichier de configuration
echo "SECRET_KEY=$(openssl rand -hex 32)" > .env
cp .env.example .env

# Lancer l'application en mode développement
docker-compose up

# Pour la production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

L'application sera accessible à [http://localhost:8000](http://localhost:8000)

### Méthode 2: Installation directe (Python)

```bash
# Cloner le dépôt
git clone https://github.com/GBGautier/app-cantine.git
cd app-cantine

# Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .\.venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Copier et configurer l'environnement
cp .env.example .env
# Éditer .env pour configurer SECRET_KEY et autres paramètres

# Initialiser la base de données
python -c "from src.backend.db import init; init()"

# Lancer l'application
uvicorn src.backend.app:app --reload --port 8000
```

### Méthode 3: Avec pip (installation globale)

```bash
pip install git+https://github.com/GBGautier/app-cantine.git
cgrs-app
```

---

## ⚙️ Configuration

### Variables d'environnement essentielles

Copiez le fichier `.env.example` en `.env` et configurez au minimum :

```bash
cp .env.example .env
```

**Variables obligatoires pour la production :**

```ini
# Environnement
ENVIRONMENT=production
DEBUG=false

# Sécurité
SECRET_KEY=votre-clé-secrète-aléatoire-de-32-caractères-minimum
CSRF_PROTECTION=true
HTTPS_MODE=true
CORS_ORIGINS=https://votre-domaine.com

# Base de données
DATABASE_PATH=/chemin/vers/cantine.db
UPLOADS_DIR=/chemin/vers/uploads
BACKUPS_DIR=/chemin/vers/sauvegardes
```

**Génération d'une clé secrète :**

```python
import secrets
print(secrets.token_urlsafe(32))
```

### Dépendances système (pour l'OCR)

Pour le parsing des PDF avec reconnaissance optique de caractères :

**Linux (Debian/Ubuntu):**
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng libtesseract-dev poppler-utils
```

**macOS:**
```bash
brew install tesseract tesseract-lang poppler
```

**Windows:**
- Télécharger Tesseract depuis [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
- Ajouter le chemin de Tesseract à la variable `TESSERACT_PATH` dans `.env`

---

## 📖 Documentation complète

Pour une documentation détaillée, consultez :

- **[📚 Architecture de l'application](docs/ARCHITECTURE.md)** – Structure du code, schémas de base de données, API
- **[🛠️ Guide de développement](docs/DEVELOPMENT.md)** – Installation, tests, linting, contribution
- **[🔒 Guide de sécurité](docs/SECURITY.md)** – Bonnes pratiques, configuration, audit

---

## 🔒 Sécurité

### 🛡️ Fonctionnalités de sécurité intégrées

| Fonctionnalité | Description |
|----------------|-------------|
| **Hachage des mots de passe** | PBKDF2-SHA256 avec 240 000 itérations et sel aléatoire |
| **Protection CSRF** | En-tête `x-requested-with: cgrs` requis pour les requêtes POST/PUT/DELETE |
| **Protection CORS** | Origines configurables via `CORS_ORIGINS` |
| **Limite des tentatives** | 5 tentatives max, blocage de 60 secondes |
| **En-têtes de sécurité** | X-Content-Type-Options, X-Frame-Options, Referrer-Policy |
| **Validation des uploads** | Extensions autorisées, taille maximale (25 Mo par défaut) |
| **Injections SQL** | Requêtes paramétrées uniquement |

### 🔐 Bonnes pratiques

1. **Ne jamais committer de secrets** dans le code ou le dépôt Git
2. **Utiliser HTTPS** en production
3. **Limiter les permissions** selon les rôles des utilisateurs
4. **Sauvegarder régulièrement** la base de données
5. **Mettre à jour** les dépendances régulièrement
6. **Vérifier les vulnérabilités** avec `safety check` et `bandit -r src/`

### 🚨 Signalement des vulnérabilités

Si vous découvrez une faille de sécurité, merci de la signaler de manière responsable à :
**security@cgrs.fr**

Ne divulguez pas publiquement la vulnérabilité avant qu'elle ne soit corrigée.

---

## 🏗️ Architecture

### Structure du projet

```
app-cantine/
├── src/
│   └── backend/
│       ├── app.py              # Application FastAPI principale
│       ├── main.py             # Point d'entrée pour l'application desktop
│       ├── config/
│       │   └── __init__.py     # Configuration centrale
│       ├── models/
│       │   ├── __init__.py     # Export des modèles Pydantic
│       │   ├── base.py         # Modèles de base
│       │   ├── auth.py         # Authentification
│       │   ├── suppliers.py    # Fournisseurs
│       │   ├── products.py     # Produits
│       │   ├── orders.py       # Commandes
│       │   ├── meals.py        # Repas
│       │   ├── recipes.py      # Recettes
│       │   ├── stocks.py       # Stocks
│       │   └── commitments.py  # Engagements
│       ├── routes/
│       │   ├── __init__.py     # Export des routes
│       │   ├── auth.py         # Routes d'authentification
│       │   ├── users.py        # Routes des utilisateurs
│       │   ├── suppliers.py    # Routes des fournisseurs
│       │   ├── products.py     # Routes des produits
│       │   ├── orders.py       # Routes des commandes
│       │   ├── meals.py        # Routes des repas
│       │   ├── recipes.py      # Routes des recettes
│       │   ├── stocks.py       # Routes des stocks
│       │   ├── commitments.py  # Routes des engagements
│       │   ├── settings.py     # Routes des paramètres
│       │   ├── grammages.py    # Routes des grammages
│       │   ├── export.py       # Routes d'export
│       │   ├── files.py        # Routes des fichiers
│       │   └── backup.py       # Routes des sauvegardes
│       ├── db/
│       │   └── __init__.py     # Gestion de la base de données SQLite
│       ├── services/
│       │   ├── __init__.py     # Export des services
│       │   ├── dolibarr.py     # Export vers Dolibarr
│       │   ├── pdf_parser.py   # Parsing des PDF
│       │   └── menu_parser.py  # Parsing des menus
│       └── utils/
│           └── __init__.py     # Fonctions utilitaires
├── tests/
│   ├── unit/
│   │   ├── test_models.py      # Tests des modèles
│   │   └── test_utils.py       # Tests des utilitaires
│   └── integration/
│       └── test_api.py         # Tests de l'API
├── docs/
│   ├── ARCHITECTURE.md         # Documentation de l'architecture
│   ├── DEVELOPMENT.md          # Guide de développement
│   └── SECURITY.md             # Guide de sécurité
├── config/
│   └── nginx/
│       ├── nginx.conf          # Configuration Nginx
│       └── ssl/                # Certificats SSL
├── docker-compose.yml          # Configuration Docker (développement)
├── docker-compose.prod.yml     # Configuration Docker (production)
├── Dockerfile                  # Image Docker
├── requirements.txt            # Dépendances Python
├── pyproject.toml              # Configuration du projet
└── README.md                   # Ce fichier
```

### Technologies utilisées

| Catégorie | Technologie | Version |
|-----------|-------------|---------|
| **Langage** | Python | 3.10+ |
| **Backend** | FastAPI | 0.109+ |
| **ASGI Server** | Uvicorn | 0.27+ |
| **Base de données** | SQLite | 3 |
| **OCR** | Tesseract | 5 |
| **PDF Parsing** | pdfplumber | 0.10+ |
| **Validation** | Pydantic | 2.5+ |
| **Desktop** | pywebview | 5 |
| **Tests** | pytest | 7.4+ |
| **Linting** | ruff, black, mypy | Latest |
| **Conteneurisation** | Docker | 20+ |

---

## 🛠️ Développement

### Prérequis

- Python 3.10 ou supérieur
- Git
- Docker (optionnel mais recommandé)
- Tesseract OCR (pour le parsing des PDF)

### Installation pour le développement

```bash
# Cloner le dépôt
git clone https://github.com/GBGautier/app-cantine.git
cd app-cantine

# Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate

# Installer les dépendances de développement
pip install -e ".[dev]"

# Copier la configuration
cp .env.example .env

# Lancer l'application avec reload automatique
uvicorn src.backend.app:app --reload --port 8000
```

### Commandes utiles

```bash
# Lancer les tests
pytest -v --cov=src --cov-report=term-missing

# Linting et formatage
ruff check --fix src/ tests/
black src/ tests/
mypy src/ --ignore-missing-imports

# Vérification des vulnérabilités
safety check
bandit -r src/

# Build de l'image Docker
docker build -t cgrs-app .

# Lancer avec Docker Compose
docker-compose up
```

### Structure des commits

Nous suivons les [Conventional Commits](https://www.conventionalcommits.org/) :

- `feat:` – Nouvelle fonctionnalité
- `fix:` – Correction de bug
- `docs:` – Documentation
- `style:` – Changements de style
- `refactor:` – Refactorisation
- `perf:` – Amélioration des performances
- `test:` – Ajout ou correction de tests
- `chore:` – Changements divers

---

## 🚢 Déploiement

### Déploiement avec Docker (recommandé)

```bash
# Construire et lancer en production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Vérifier les logs
docker-compose logs -f app
```

### Déploiement avec Nginx (reverse proxy)

Un exemple de configuration Nginx est fourni dans `config/nginx/nginx.conf`.

```bash
# Lancer Nginx avec Docker
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d nginx
```

### Déploiement manuel

```bash
# Installer les dépendances
pip install -r requirements.txt

# Lancer avec Gunicorn + Uvicorn (production)
gunicorn -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000 src.backend.app:app
```

### Configuration recommandée pour la production

- **Serveur** : Linux (Ubuntu 22.04 LTS recommandé)
- **Base de données** : SQLite (pour les petites installations) ou PostgreSQL (pour les grosses installations)
- **Reverse Proxy** : Nginx ou Apache avec SSL/TLS
- **Certificats SSL** : Let's Encrypt (Certbot)
- **Surveillance** : Prometheus + Grafana (optionnel)
- **Sauvegardes** : Script cron pour sauvegarder `cantine.db` et `uploads/`

---

## 🤝 Contribution

Les contributions sont les bienvenues ! Voici comment contribuer :

### Étapes pour contribuer

1. **Forker** le dépôt sur GitHub
2. **Créer une branche** pour votre fonctionnalité :
   ```bash
   git checkout -b feat/ma-fonctionnalité
   ```
3. **Faire des commits** avec des messages clairs
4. **Pousser** vers votre fork :
   ```bash
   git push origin feat/ma-fonctionnalité
   ```
5. **Créer une Pull Request** vers la branche `main`

### Checklist avant Pull Request

- [ ] Le code suit les conventions de style (black, ruff)
- [ ] Tous les tests passent (`pytest -v`)
- [ ] Le code est typé correctement (mypy)
- [ ] La documentation est mise à jour
- [ ] Les dépendances sont à jour
- [ ] Aucune vulnérabilité de sécurité n'est introduite

### Code de conduite

Nous nous engageons à maintenir un environnement ouvert et accueillant. Veuillez respecter le [Code de conduite](https://github.com/GBGautier/app-cantine/blob/main/CODE_OF_CONDUCT.md) (à créer si nécessaire).

---

## 📜 Licence

Ce projet est sous licence **MIT**. Consultez le fichier [LICENSE](LICENSE) pour plus de détails.

Vous êtes libre d'utiliser, copier, modifier et distribuer ce logiciel à condition de conserver la notice de copyright et cette notice de licence.

---

## 📞 Contact

- **Email** : [contact@cgrs.fr](mailto:contact@cgrs.fr)
- **GitHub** : [GBGautier/app-cantine](https://github.com/GBGautier/app-cantine)
- **Site web** : [https://cgrs.fr](https://cgrs.fr) (à venir)

---

## 🙏 Remerciements

Un grand merci à tous les contributeurs qui ont aidé à améliorer ce projet !

---

*© 2026 CGRS – Centre de Gestion des Réceptions et Stocks*
*Dernière mise à jour : Octobre 2026*
