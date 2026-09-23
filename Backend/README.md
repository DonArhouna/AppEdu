# EduManagePro (EMP) — Backend API (FastAPI)

API Backend haute performance pour la plateforme SaaS de gestion scolaire et universitaire **EduManagePro (EMP)**.

---

## 1. Environnement Virtuel Dédié (venv)

Le projet utilise un environnement virtuel Python isolé situé dans `Backend/venv`.

### Activation de l'environnement virtuel

- **Sous Windows (PowerShell)** :
  ```powershell
  cd Backend
  .\venv\Scripts\Activate.ps1
  # ou sous CMD classique :
  .\venv\Scripts\activate.bat
  ```

- **Sous Linux / macOS** :
  ```bash
  cd Backend
  source venv/bin/activate
  ```

---

## 2. Installation des Dépendances

Une fois le venv activé :
```bash
pip install -r requirements.txt
```

---

## 3. Lancement du Serveur de Développement

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **Documentation Swagger interactive** : [http://localhost:8000/docs](http://localhost:8000/docs)
- **Documentation ReDoc** : [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Vérification de santé (Healthcheck)** : [http://localhost:8000/health](http://localhost:8000/health)

---

## 4. Migrations de Base de Données (Alembic)

```bash
# Appliquer les migrations
alembic upgrade head

# Créer une nouvelle migration automatique
alembic revision --autogenerate -m "description_du_changement"
```

---

## 5. Déploiement Conteneurisé (Docker Compose)

```bash
docker compose up -d --build
```
L'image effectue automatiquement les migrations Alembic au démarrage avant d'ouvrir le port applicatif.
