# =====================================================================================
# Dockerfile pour l'application CGRS - Réceptions & stocks
# =====================================================================================
# Multi-stage build pour réduire la taille de l'image finale

# -----------------------------------------------------------------------------
# Stage 1: Build de l'application
# -----------------------------------------------------------------------------
FROM python:3.11-slim as builder

# Définir les variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Installer les dépendances de build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Créer et activer un virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Installer les dépendances Python
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: Image finale
# -----------------------------------------------------------------------------
FROM python:3.11-slim

# Définir les variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Dépendances pour Tesseract OCR
    tesseract-ocr \
    tesseract-ocr-fra \
    tesseract-ocr-eng \
    libtesseract-dev \
    # Autres dépendances
    poppler-utils \
    # Nettoyage
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copier le virtual environment depuis le stage builder
COPY --from=builder /opt/venv /opt/venv

# Créer les répertoires nécessaires
RUN mkdir -p /app/data/uploads /app/data/sauvegardes-auto

# Copier l'application
WORKDIR /app
COPY src/ ./src/
COPY static/ ./static/
COPY .env.example .

# Créer un utilisateur non-root pour la sécurité
RUN useradd -m -u 1000 cgrs && \
    chown -R cgrs:cgrs /app/data /app/static

# Exposer le port par défaut
EXPOSE 8000

# Configurer l'entrée point
USER cgrs
CMD ["uvicorn", "src.backend.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
