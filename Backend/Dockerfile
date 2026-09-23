# ==============================================================================
# EduManagePro (EMP) — Dockerfile Backend (Python 3.12 / 3.13 Slim)
# ==============================================================================

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Installation des dépendances système de compilation légères
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copie et installation des dépendances Python
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copie du code applicatif et des fichiers de migration
COPY app /app/app
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini
COPY docker/entrypoint.sh /app/entrypoint.sh

# Rendre l'entrypoint exécutable
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]