# Guide de Démarrage & Documentation Complète — EduManagePro (EMP)

Ce guide détaille les étapes simples pour lancer le **Backend (FastAPI)**, le **Frontend (React/Vite)** et exécuter les **suites de tests automatisées**.

---

## 📋 Table des Matières
1. [Prérequis Système](#1-prérequis-système)
2. [Démarrage Rapide du Backend (FastAPI)](#2-démarrage-rapide-du-backend-fastapi)
3. [Démarrage du Frontend (React / Vite)](#3-démarrage-du-frontend-react--vite)
4. [Exécution des Suites de Tests Automatisées](#4-exécution-des-suites-de-tests-automatisées)
5. [Parcours de Test Manuel de Bout en Bout](#5-parcours-de-test-manuel-de-bout-en-bout)
6. [Alternative : Déploiement Conteneurisé (Docker Compose)](#6-alternative--déploiement-conteneurisé-docker-compose)
7. [Référence des URLs et Identifiants par Défaut](#7-référence-des-urls-et-identifiants-par-défaut)

---

## 1. Prérequis Système

- **Python** : Version 3.11, 3.12 ou 3.13 installée sur votre machine.
- **Node.js** : Version 18+ ou 20+ avec `npm`.
- **Système d'exploitation** : Windows (PowerShell), macOS ou Linux.

---

## 2. Démarrage Rapide du Backend (FastAPI)

Le backend dispose d'un environnement virtuel Python dédié (`venv`) situé dans le dossier `Backend/`.

### Étape 2.1 — Ouvrir un terminal dans le dossier Backend
```powershell
cd Backend
```

### Étape 2.2 — Activer l'environnement virtuel Python
- **Sous Windows (PowerShell)** :
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
  *(Si vous rencontrez une restriction d'exécution de script PowerShell, exécutez d'abord : `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

- **Sous Windows (Invite de commandes CMD classique)** :
  ```cmd
  .\venv\Scripts\activate.bat
  ```

- **Sous macOS / Linux** :
  ```bash
  source venv/bin/activate
  ```

### Étape 2.3 — Lancer le serveur Backend (Uvicorn)
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
> Le backend démarre immédiatement sur : **[http://localhost:8000](http://localhost:8000)**  
> La documentation interactive Swagger est accessible sur : **[http://localhost:8000/docs](http://localhost:8000/docs)**  
> La documentation ReDoc est accessible sur : **[http://localhost:8000/redoc](http://localhost:8000/redoc)**

---

## 3. Démarrage du Frontend (React / Vite)

Dans un **second terminal** :

### Étape 3.1 — Aller dans le dossier Frontend
```powershell
cd Frontend
```

### Étape 3.2 — Lancer le serveur de développement Vite
```powershell
npm run dev
```
> Le frontend s'ouvre sur : **[http://localhost:5173](http://localhost:5173)** (ou le port indiqué dans le terminal).

---

## 4. Exécution des Suites de Tests Automatisées

Le projet intègre deux suites de tests automatisées complètes. Vous pouvez les exécuter depuis le dossier `Backend` avec l'environnement virtuel activé.

### Test 1 — Cœur Métier (Sprint 2)
Valide la Structure Académique, les Étudiants, le Moteur de Délibération ECTS/LMD et les Finances (Facturation, Encaissement, Reçu) :
```powershell
cd Backend
.\venv\Scripts\python.exe test_sprint2.py
```
**Résultat attendu :**
```
================================================================
  TOUS LES TESTS DU SPRINT 2 ONT RÉUSSI AVEC SUCCÈS (4/4) !    
================================================================
```

### Test 2 — Parcours de Premier Lancement E2E (Sprint 3)
Valide l'état sur base vierge, l'initialisation du Setup Wizard, le rejet de réinitialisation (409 Conflict), le login SuperAdmin, la récupération du profil `/auth/me` et les périodes de session :
```powershell
cd Backend
.\venv\Scripts\python.exe test_sprint3_e2e.py
```
**Résultat attendu :**
```
==================================================================
   PARCOURS COMPLET SETUP -> LOGIN -> DASHBOARD VALIDÉ (7/7) !   
==================================================================
```

### Suites E2E par module (toutes exécutables de la même manière)

Chaque module a sa suite autonome (base SQLite isolée, créée puis détruite) :
`test_academic_e2e.py`, `test_auth_lot2_e2e.py` (durcissement auth : verrouillage,
rotation des sessions, écran « mes sessions »), `test_bulletins_lot_e2e.py`
(bulletins groupés par classe), `test_deliberation_e2e.py`, `test_documents_e2e.py`,
`test_etudiant_import_e2e.py`, `test_export_e2e.py`, `test_import_notes_e2e.py`,
`test_institution_e2e.py`, `test_matricule_e2e.py`, `test_relances_e2e.py`,
`test_rbac_e2e.py`, `test_salles_conflits_e2e.py` (salles + conflits d'emploi du
temps), `test_semestre_e2e.py`. Exemple :

```powershell
.\venv\Scripts\python.exe test_salles_conflits_e2e.py
```

Les tests **ne touchent jamais votre base PostgreSQL** : chaque suite migre son
propre SQLite temporaire via Alembic jusqu'à la révision `head`.

---

## 5. Parcours de Test Manuel de Bout en Bout

Pour tester manuellement l'application comme un nouvel utilisateur client :

### Étape A — Premier Démarrage (Setup Wizard)
1. Ouvrez votre navigateur sur **[http://localhost:5173](http://localhost:5173)**.
2. Si l'application détecte un système non initialisé, elle vous redirige automatiquement vers **`/setup`**.
3. Complétez les 4 étapes du Wizard :
   - **Étape 1 (Infrastructure)** : Vérifiez la connexion PostgreSQL configurée par `.env` ou Docker Compose.
   - **Étape 2 (Établissement)** : Entrez le nom de l'université/école (ex : *Institut Supérieur des Technologies & Management*), le code/sigle et la devise de l'établissement.
   - **Étape 3 (SuperAdmin)** : Définissez votre nom, prénom, adresse email et un mot de passe fort. Observez la jauge de sécurité du mot de passe.
   - **Étape 4 (Licence & Finalisation)** : Saisissez éventuellement une clé de licence puis cliquez sur **Initialiser EduManagePro**. Les sessions et échéances seront créées ensuite depuis le module Sessions.
4. L'écran de confirmation s'affiche avec le récapitulatif. Cliquez sur **Se Connecter au Portail**.

### Étape B — Connexion au Portail (Login)
1. Vous arrivez sur **[http://localhost:5173/login](http://localhost:5173/login)**.
2. Saisissez les identifiants que vous avez définis lors du Setup.
3. Cliquez sur **Se Connecter**.
4. Le système valide le JWT Bearer et vous connecte directement au **Tableau de bord (Dashboard)** avec le rôle **ADMIN**.

### Étape C — Vérification de la Sécurité Anti-Réinitialisation
1. Dans la barre d'adresse de votre navigateur, essayez d'accéder manuellement à **[http://localhost:5173/setup](http://localhost:5173/setup)**.
2. Le système détecte que l'établissement est déjà configuré (`is_configured === true`), affiche une notification et vous renvoie automatiquement vers `/login`.

---

## 6. Alternative : Déploiement Conteneurisé (Docker Compose)

Si vous préférez exécuter l'ensemble de la pile (FastAPI + PostgreSQL 16 Alpine) avec Docker :

```powershell
cd Backend
docker compose up -d --build
```

- Le conteneur backend applique automatiquement les migrations Alembic avant d'ouvrir le port 8000.
- La migration `0006_remove_implicit_defaults` retire les valeurs métier injectées par la base.
- La migration `0007_portal_identity` ajoute le lien optionnel entre un compte et son dossier étudiant, sans supprimer de données.
- La base PostgreSQL est persistée dans le volume `emp_postgres_data`.
- En développement, `SECRET_KEY` peut rester vide pour générer une clé éphémère ; en production, injectez une valeur aléatoire via `EMP_SECRET_KEY` ou le gestionnaire de secrets.
- Pour arrêter les conteneurs : `docker compose down`.

---

## 6 bis. Migrations Alembic (à connaître en exploitation)

Le schéma évolue par migrations **additives** (aucune donnée réinterprétée).
Après une mise à jour du code, appliquez-les sur PostgreSQL depuis `Backend/` :

```powershell
.\venv\Scripts\python.exe -m alembic current   # où en est la base
.\venv\Scripts\python.exe -m alembic upgrade head
```

Migrations récentes :

| Révision | Contenu |
| :--- | :--- |
| `0023_financial_integrity` | Montants en `Numeric(14,2)`, unicité des notes, clés comptables RESTRICT |
| `0024_auth_hardening` | Anti-brute-force (`login_attempts`, verrouillage) + sessions révocables (`refresh_tokens`) |
| `0025_salles` | Table des salles physiques, support de la détection de conflits d'emploi du temps |
| `0026_relances_email` | Trace d'envoi des relances par email (`email_statut`, `email_envoye_le`) |
| `0027_paiement_intents` | Paiements en ligne : intention de paiement et confirmation (jeton public) |
| `0028_tenant_registry` | Registre des écoles (`tenants`) sur la base de contrôle — socle multi-tenant, **additif pur** |

### Multi-tenant (lot 6) : héberger plusieurs écoles

Le défaut reste **standalone** : chez un client on-premise, rien ne change.
Pour héberger plusieurs écoles sur un même serveur PostgreSQL, chaque école
reçoit sa propre base (`emp_tenant_{slug}`) et une ligne dans le registre
(table `tenants`, base de contrôle) — méthode Sage X3 : même code, isolation
physique des données, sauvegarde et restauration par école.

```powershell
# Depuis Backend/ — provisionner une école (base + migrations + registre) :
.\venv\Scripts\python.exe -m app.provisioning creer mon-ecole "Mon École" --email contact@mon-ecole.fr
.\venv\Scripts\python.exe -m app.provisioning lister
.\venv\Scripts\python.exe -m app.provisioning migrer-tous      # à chaque mise à jour
.\venv\Scripts\python.exe -m app.provisioning suspendre mon-ecole   # impayé
.\venv\Scripts\python.exe -m app.provisioning reactiver mon-ecole
```

Le serveur bascule avec `TENANT_MODE=multi_tenant` dans le `.env` : chaque
requête doit alors porter l'en-tête `X-Tenant-ID: {slug}` (le sous-domaine
`{slug}.edumanagepro.fr` viendra plus tard). Sans en-tête, la requête touche
la base de contrôle ; un slug inconnu ou suspendu reçoit 403. Le directeur de
chaque école crée son compte admin par le Setup Wizard habituel, dans sa
propre base.

---

## 7. Référence des URLs et de l'accès

| Composant | URL | Description |
| :--- | :--- | :--- |
| **Frontend Application** | [http://localhost:5173](http://localhost:5173) | Interface utilisateur React / Vite |
| **Setup Wizard** | [http://localhost:5173/setup](http://localhost:5173/setup) | Assistant d'initialisation premier lancement |
| **Page de Connexion** | [http://localhost:5173/login](http://localhost:5173/login) | Authentification par email / mot de passe |
| **Backend API Root** | [http://localhost:8000](http://localhost:8000) | Accueil de l'API FastAPI |
| **Swagger OpenAPI** | [http://localhost:8000/docs](http://localhost:8000/docs) | Documentation et tests interactifs des 62 opérations HTTP |
| **ReDoc Documentation**| [http://localhost:8000/redoc](http://localhost:8000/redoc) | Documentation technique alternative |
| **Healthcheck** | [http://localhost:8000/health](http://localhost:8000/health) | État de santé et statut de connexion DB |

### Identifiants administrateur

Aucun mot de passe administrateur n'est prérempli. Utilisez exclusivement les identifiants créés lors du premier lancement.

### Changer le mot de passe d'un administrateur existant

Si l'instance a déjà été initialisée avec un ancien mot de passe, ne relancez pas le Setup Wizard. Depuis `Backend/`, utilisez l'outil interactif (le mot de passe est saisi de manière masquée) :

```powershell
.\venv\Scripts\python.exe manage_admin_password.py --email votre-email@votre-etablissement.org
```

Le compte n'est jamais réinitialisé avec une valeur codée en dur.

---

## 8. Sécurité de l'authentification (lot 2) et salles (lot 3)

### Ce qui a changé pour les utilisateurs

- **Une session se révoque.** Le login émet un `refresh_token` : la session
  peut être fermée (déconnexion, changement de mot de passe, écran
  **Paramètres du compte ▸ Mes sessions**), et l'accès tombe **immédiatement**,
  même si le jeton d'accès n'a pas expiré.
- **Le jeton d'accès vaut 1 heure** (au lieu de 8). Le frontend le renouvelle
  en silence par rotation du refresh token (7 jours) : l'utilisateur ne voit
  rien, sauf une déconnexion après 7 jours d'inactivité.
- **Le login se défend.** Après 5 échecs consécutifs, le compte se verrouille
  15 minutes (HTTP 423). Après 10 échecs rapprochés depuis une même adresse,
  le serveur répond 429 avec `Retry-After`. Derrière un reverse-proxy,
  ajoutez `TRUST_PROXY_HEADERS=true` au `.env` pour que le débit voie les
  vraies IP clients.

### Salles et conflits d'emploi du temps

Les salles se gèrent dans **Structure académique ▸ Salles**. Une salle a un
nom unique (la casse est ignorée) : c'est par ce nom que les cours s'y
rattachent. Depuis l'activation, le serveur **refuse** (409) de créer ou de
déplacer un cours sur un créneau déjà pris dans la même salle ou par le même
enseignant — deux cours consécutifs restent légaux. Les conflits posés avant
l'activation restent listés par `GET /api/v1/pedagogie/cours/conflits` et
affichés en bandeau sur la page **Emplois du temps**.

Une salle « indisponible » (travaux…) refuse toute nouvelle séance sans que
les cours déjà posés disparaissent ; une salle citée par des cours ne se
supprime pas.