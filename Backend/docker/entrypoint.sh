#!/bin/sh
set -e

echo "🚀 [EduManagePro] Initialisation du conteneur Backend..."

# Attente de disponibilité de PostgreSQL si DB_HOST est configuré
if [ -n "$DB_HOST" ]; then
  echo "⏳ Vérification de la disponibilité du serveur PostgreSQL ($DB_HOST:$DB_PORT)..."
  until python -c "
import socket, sys
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.connect(('$DB_HOST', int('$DB_PORT' or 5432)))
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
"; do
    echo "   ... En attente de PostgreSQL sur $DB_HOST:$DB_PORT"
    sleep 2
  done
  echo "✅ Serveur PostgreSQL disponible !"
fi

echo "📦 Application des migrations de schéma avec Alembic..."
alembic upgrade head || echo "⚠️ Avertissement : Les migrations n'ont pu être appliquées (premier démarrage ou DB vide)."

echo "🌟 Démarrage du serveur Uvicorn sur 0.0.0.0:8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000