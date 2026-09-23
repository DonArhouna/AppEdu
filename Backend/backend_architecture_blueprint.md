# Cadrage Architecture Backend (FastAPI) & Stratégie Multi-Tenant

Ce document scelle les arbitrages architecturaux et la feuille de route technique pour le démarrage du backend **EduManagePro (EMP)**.

---

## 1. Synthèse des Arbitrages Techniques

### 1.1 Mode de Livraison chez le Client
- **Décision arbitrée** : **Package Docker Compose « tout-en-un » par défaut, avec bascule transparente vers SGBD externe**.
- **Justification** : 
  - 90 % des établissements scolaires n'ont ni DBA ni environnement PostgreSQL préconfiguré : le conteneur prêt à l'emploi (`FastAPI` + `PostgreSQL 16` + volume persistant) élimine 100 % des problèmes de versions et de dépendances OS.
  - Pour les 10 % de grandes universités dotées d'une DSI imposant leur propre serveur SGBD (cluster interne ou RDS), il suffit de renseigner `DATABASE_URL` dans le fichier `.env` pour désactiver le conteneur local et pointer directement sur leur infrastructure existante.

### 1.2 Initialisation Initiale : Setup Wizard Web (`/setup`)
- **Décision arbitrée** : **Assistant Web pas-à-pas activé tant que le système n'est pas initialisé (`is_configured == False`)**.
- **Champs collectés lors du wizard** :
  1. **Étape 1 — Connexion Base de Données** :
     - En mode Docker par défaut : détection automatique du PostgreSQL interne (zéro saisie requise).
     - En mode SGBD externe : Hôte, Port, Nom de la base, Utilisateur, Mot de passe (avec bouton « Tester la connexion »).
  2. **Étape 2 — Profil Établissement** :
     - Raison sociale / Nom de l'établissement, Sigle (ex: *EMP*), Email officiel, Téléphone, Pays, Devise financière principale (*FCFA, EUR, USD*).
  3. **Étape 3 — Compte Super-Administrateur** :
     - Nom, Prénom, Identifiant/Email de connexion, Mot de passe fort (vérification de complexité), Confirmation.
  4. **Étape 4 — Licence & Clé d'Activation** :
     - Numéro de série / Clé de licence (signature cryptographique offline garantissant le fonctionnement sans accès Internet obligatoire).
- **Finalisation** :
  - Exécution automatique de la migration Alembic (`alembic upgrade head`).
  - Insertion des tables socles et création du compte SuperAdmin initial (rôle `ADMIN`).
  - Scellement du système (`setup_completed = True`) et génération immédiate des tokens JWT avec redirection vers le Tableau de Bord.

### 1.3 Stack Technique Retenue
- **Décision arbitrée** : **FastAPI + SQLAlchemy 2.0 (Async) + Alembic + Asyncpg + Pydantic V2**.
- **Justification** :
  - **FastAPI + Pydantic V2** : Vitesse d'exécution maximale grâce au parseur Rust de Pydantic, typage statique strict et documentation interactive Swagger/ReDoc générée nativement.
  - **SQLAlchemy 2.0 (Async) + asyncpg** : L'écosystème le plus robuste en Python pour le requêtage non-bloquant sous forte charge (concurrence élevée lors des périodes de rentrée et de saisie des notes).
  - **Alembic** : Suivi rigoureux et versionné des évolutions de schémas, exécuté automatiquement au boot applicatif.
  - **Sécurité** : `passlib` avec `bcrypt` pour le hachage des mots de passe et `pyjwt` pour les tokens d'accès et de rafraîchissement.

---

## 2. Arborescence Finale et Définitive du Dossier `Backend/`

```text
Backend/
├── alembic/                          # Système de migration de base de données
│   ├── env.py                        # Configuration d'exécution asynchrone Alembic
│   ├── script.py.mako
│   └── versions/                     # Fichiers de migration séquentiels
├── app/
│   ├── api/
│   │   ├── deps.py                   # Injections de dépendances (get_db, get_current_user, require_role)
│   │   └── v1/
│   │       ├── api.py                # Agrégateur des routes v1
│   │       └── endpoints/
│   │           ├── auth.py           # Login, Refresh token, Profil me
│   │           ├── setup.py          # Setup Wizard (initialisation premier lancement)
│   │           ├── etudiants.py      # CRUD étudiants, scolarité, inscriptions
│   │           ├── sessions.py       # Sessions académiques & tranches de paiement
│   │           ├── finances.py       # Paiements physiques, factures, quittances
│   │           ├── pedagogie.py      # Notes, absences, délibérations
│   │           └── structure.py      # Campus, sites, filières, départements
│   ├── core/
│   │   ├── config.py                 # Pydantic Settings (chargement .env, variables système)
│   │   ├── security.py               # Hachage mots de passe, génération & validation JWT
│   │   └── database.py               # Engine Async, SessionMaker et Tenant Database Resolver
│   ├── models/                       # Entités SQLAlchemy ORM
│   │   ├── base.py                   # Base déclarative partagée avec timestamps
│   │   ├── etablissement.py          # Infos structure, licence, paramètres globaux
│   │   ├── utilisateur.py            # Comptes, rôles RBAC, permissions
│   │   ├── session_academique.py     # Sessions & périodes financières rattachées
│   │   ├── etudiant.py               # Fiches scolaires, matricules, sessionId
│   │   ├── finance.py                # Factures, échéances, paiements, reçus
│   │   └── pedagogie.py              # Filières, cours, notes, examens
│   ├── schemas/                      # Schémas de validation Pydantic V2 (DTO)
│   │   ├── setup.py                  # DTO pour le wizard d'installation
│   │   ├── auth.py                   # LoginRequest, TokenResponse, UserProfile
│   │   ├── etudiant.py               # StudentCreate, StudentUpdate, StudentOut
│   │   ├── session_academique.py     # SessionCreate, PeriodePaiementOut
│   │   └── finance.py                # PaiementCreate, RecuPaiementResponse
│   ├── services/                     # Logique métier pure
│   │   ├── auth_service.py           # Authentification & gestion des sessions
│   │   ├── setup_service.py          # Orchestration de l'initialisation système
│   │   ├── tenant_service.py         # Résolution dynamique multi-base
│   │   ├── paiement_service.py       # Règles d'encaissement et tranches
│   │   └── deliberation_engine.py    # Calculs de moyennes et passage LMD
│   └── main.py                       # Point d'entrée FastAPI, middlewares CORS, lifespan
├── docker/
│   ├── Dockerfile
│   ├── entrypoint.sh                 # Script d'amorce : migration auto + uvicorn
│   └── nginx.conf                    # Reverse-proxy sécurisé optionnel
├── docker-compose.yml                # Déploiement On-Premise 1-clic (Backend + Postgres 16)
├── .env.example
├── .gitignore
├── alembic.ini
└── requirements.txt
```

---

## 3. Plan de Démarrage Immédiat (Sprint 1 Backend)

1. **Brique 1 — Fondations Système & Environnement** :
   - Fichiers d'environnement : `requirements.txt`, `.env.example`, `.gitignore`.
   - `app/core/config.py` : Configuration centralisée Pydantic Settings (`TENANT_MODE=standalone|multi_tenant`).
   - `app/core/database.py` : Moteur asynchrone SQLAlchemy 2.0 (`asyncpg`) et session maker.
2. **Brique 2 — Modèles Socles & Sécurité** :
   - `app/core/security.py` : Hachage des mots de passe bcrypt et émission/décodage de JWT.
   - Modèles ORM initiaux : `Etablissement` (état du setup, licence), `Utilisateur` (SuperAdmin, matrice RBAC), `SessionAcademique` et `PeriodePaiement`.
   - Initialisation d'Alembic en mode asynchrone.
3. **Brique 3 — Setup Wizard & Authentification** :
   - Endpoint `GET /api/v1/setup/status` : Indique si le système nécessite le wizard initial.
   - Endpoint `POST /api/v1/setup/initialize` : Exécute le provisionnement initial.
   - Endpoints `POST /api/v1/auth/login` et `GET /api/v1/auth/me`.
4. **Brique 4 — Déploiement Conteneurisé** :
   - `Dockerfile` et `docker-compose.yml` pour valider le lancement d'un seul bloc avec PostgreSQL.
