# RBAC dynamique — Backend

Implémentation d'un RBAC dynamique **réel** côté backend, coexistant avec le
rôle legacy `utilisateurs.role`.

- Alembic est la **seule** source de schéma.
- Aucune suppression de colonne legacy, aucun seed de compte, aucun mock.
- Le catalogue de permissions n'accorde **rien** tout seul : il n'existe
  volontairement **aucune matrice rôle/permission** dans le code ni dans la
  migration.

---

## 1. Fichiers

### Nouveaux

| Fichier | Rôle |
|---|---|
| `app/core/permissions.py` | Source de vérité unique du catalogue (14 permissions d'origine) et des 6 rôles système. Deux permissions complémentaires sont ajoutées par les migrations 0015 et 0016 : voir § 1.1. Aucune dépendance ORM/DB, importable par Alembic. |
| `app/models/rbac.py` | `Permission`, `Role`, `RolePermission`, `UserRoleAssignment` (+ `Base`, `TimestampMixin`). |
| `app/schemas/rbac.py` | Schémas Pydantic V2 (CRUD, affectations, permissions effectives, contrat étendu de `/auth/me`). |
| `app/services/rbac_service.py` | Résolution d'autorité transaction-safe : `effective_permissions`, `list_effective_role_codes`, `list_effective_permission_codes`, `resolve_authz_version`, `role_permission_codes`. |
| `app/api/v1/endpoints/rbac.py` | 18 opérations sous `/api/v1/rbac`. |
| `alembic/versions/0013_rbac_dynamic.py` | Migration additive `0012_academic_structure` → `0013_rbac_dynamic`. |
| `test_rbac_e2e.py` | E2E isolé (SQLite temporaire) : cycle Alembic, seed, CRUD, guards, `/auth/me`. |

### Modifiés

| Fichier | Modification |
|---|---|
| `app/api/deps.py` | Ajout de `PermissionChecker`, `require_permission()`, `require_rbac_admin`, `require_users_manage`, `require_audit_read`. Les `RoleChecker` statiques sont **inchangés**. |
| `app/api/v1/api.py` | Enregistrement du routeur `rbac` sous le préfixe `/rbac`. |
| `app/api/v1/endpoints/auth.py` | `GET /auth/me` renvoie `CurrentUserResponse` (contrat legacy + 3 champs additifs). `POST /login`, `PATCH /me`, `POST /me/password` **inchangés**. |
| `app/api/v1/endpoints/rbac.py` | *(nouveau)* |
| `app/api/v1/endpoints/audit.py` | `require_admin` → `require_audit_read`. Comportement observable identique, gain dynamique. |
| `app/api/v1/endpoints/users.py` | `require_admin` / `require_academic_staff` → `require_users_manage` / `require_users_read` + garde-fou anti-escalade. |
| `app/models/__init__.py` | Export des 4 modèles RBAC. |
| `app/schemas/__init__.py` | Export des schémas RBAC. |

---

## 2. Schéma

Quatre tables, préfixées `rbac_` pour ne jamais entrer en collision avec le
nomenclature métier existant.

### `rbac_permissions`

| Colonne | Type | Note |
|---|---|---|
| `id` | `SERIAL` PK | |
| `code` | `VARCHAR(100)` | `domaine.action`, **immuable**, index unique `uq_rbac_permissions_code` |
| `domaine` | `VARCHAR(50)` | partie avant le `.`, pour le regroupement UI |
| `action` | `VARCHAR(50)` | partie après le `.` |
| `libelle` | `VARCHAR(150)` | métadonnée UI |
| `description` | `TEXT` | métadonnée UI |
| `systeme` | `BOOLEAN NOT NULL DEFAULT false` | `true` = livrée par la migration, protégée |
| `actif` | `BOOLEAN NOT NULL DEFAULT true` | |
| `created_at` / `updated_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | |

Index : `uq_rbac_permissions_code` (unique), `ix_rbac_permissions_domaine`, `ix_rbac_permissions_actif`.

### `rbac_roles`

| Colonne | Type | Note |
|---|---|---|
| `id` | `SERIAL` PK | |
| `code` | `VARCHAR(50)` | **immuable**, index unique `uq_rbac_roles_code` |
| `libelle` | `VARCHAR(150)` | |
| `description` | `TEXT` | |
| `ordre` | `INTEGER NOT NULL DEFAULT 0` | ordre d'affichage, tri déterministe du JSON |
| `systeme` | `BOOLEAN NOT NULL DEFAULT false` | `true` = livré par la migration |
| `actif` | `BOOLEAN NOT NULL DEFAULT true` | |

Index : `uq_rbac_roles_code` (unique), `ix_rbac_roles_systeme`, `ix_rbac_roles_actif`.

### `rbac_role_permissions` (grants allow-only)

| Colonne | Type | Note |
|---|---|---|
| `id` | `SERIAL` PK | |
| `role_id` | `INTEGER NOT NULL` | FK → `rbac_roles.id` **ON DELETE CASCADE** |
| `permission_id` | `INTEGER NOT NULL` | FK → `rbac_permissions.id` **ON DELETE CASCADE** |
| `attribue_par` | `INTEGER NULL` | FK → `utilisateurs.id` **ON DELETE SET NULL** |
| `motif` | `TEXT NULL` | justification métier |
| `created_at` / `updated_at` | `TIMESTAMPTZ` | |

Contrainte : `UNIQUE (role_id, permission_id)` → `uq_rbac_role_permissions`.
Index : `ix_rbac_role_permissions_role_id`, `..._permission_id`, `..._attribue_par`.

### `rbac_user_roles` (affectations)

| Colonne | Type | Note |
|---|---|---|
| `id` | `SERIAL` PK | |
| `user_id` | `INTEGER NOT NULL` | FK → `utilisateurs.id` **ON DELETE CASCADE** |
| `role_id` | `INTEGER NOT NULL` | FK → `rbac_roles.id` **ON DELETE CASCADE** |
| `actif` | `BOOLEAN NOT NULL DEFAULT true` | un retrait désactive, ne supprime pas |
| `attribue_par` | `INTEGER NULL` | FK → `utilisateurs.id` **ON DELETE SET NULL** |
| `motif` | `TEXT NULL` | |
| `created_at` / `updated_at` | `TIMESTAMPTZ` | |

Contrainte : `UNIQUE (user_id, role_id)` → `uq_rbac_user_roles`.
Index : `ix_rbac_user_roles_user_id`, `..._role_id`, `..._attribue_par`.

> **Aucune relation ORM** n'est déclarée entre `UserRoleAssignment` et
> `Utilisateur` : `user_id` et `attribue_par` pointent la même table, ce qui
> créerait une ambiguïté de clé étrangère. La lecture se fait par requête
> explicite dans `rbac_service`. Le module ne dépend donc pas de l'ordre
> d'import des modèles.

Portable PostgreSQL / SQLite : `SERIAL` (PG) / `INTEGER` auto-incrémenté
(SQLite), `BOOLEAN` avec `true`/`false`, `TIMESTAMP WITH TIME ZONE`,
`server_default=now()`. `alembic check` ne signale **aucun** écart entre les
modèles ORM et la migration.

---

## 3. Migration `0013_rbac_dynamic`

`down_revision = "0012_academic_structure"`.

### Ce qu'elle crée

1. Les **4 tables vides** décrites ci-dessus, avec index et contraintes.
2. Un seed **idempotent** (`SELECT` avant chaque `INSERT`) :

| Type | Nombre | Détail |
|---|---|---|
| Permissions techniques | **14** | `dashboard.read`, `students.read`, `students.write`, `admissions.read`, `admissions.write`, `academic.read`, `academic.write`, `pedagogy.read`, `pedagogy.write`, `finance.read`, `finance.write`, `users.manage`, `roles.manage`, `audit.read` — toutes `systeme = true`, `actif = true` |
| Permissions ajoutées après | **2** | `documents.issue` (migration 0015), `institution.settings` (migration 0016) — voir § 1.1. `systeme = true`, `actif = true`, aucun grant |
| Rôles système | **6** | `ROLE_ADMIN`, `ROLE_DIRECTEUR_ETUDES`, `ROLE_SECRETARIAT`, `ROLE_COMPTABILITE`, `ROLE_ENSEIGNANT`, `ROLE_ETUDIANT` — tous `systeme = true`, `actif = true`, `ordre` 10/20/30/40/50/60 |
| Grants rôle→permission | **0** | aucun |
| Affectations utilisateur→rôle | **0** | aucune |
| Comptes utilisateurs | **0** | aucun (`SELECT COUNT(*) FROM utilisateurs` = 0 après migration) |

### 1.1. Permissions ajoutees apres la bascule

La migration `0013_rbac_dynamic` livre 14 permissions. Deux sont venues
s'aplater ensuite, chacune avec sa migration, **sans toucher aux 14 autres**
ni a la fenetre d'aucun role existant.

| Permission | Migration | Guard | Fenetre legacy | Justification |
|---|---|---|---|---|
| `documents.issue` | `0015_documents_officiels` | `require_documents_issue` | SECRETARIAT | Deleguer l'emission d'un certificat au secretariat sans ouvrir l'ecriture sur les dossiers etudiants. `students.write` ne convient pas : il ouvrirait aussi la suppression. |
| `institution.settings` | `0016_configuration_institutionnelle` | `require_institution_settings` | — (ADMIN) | Faire preparer le branding (logo, coordonnees) par une direction sans lui accorder `users.manage` ni `roles.manage`. Fenetre vide : personne n'y accedait avant, donc la creer n'ouvre aucune route preexistante. |

Deux proprietes meritent d'etre soulignees :

- `documents.issue` **ne retire rien** a `students.write` : une ecriture de
  dossier et une emission de certificat sont deux actes distincts, delegables
  a deux personnes differentes.
- `institution.settings` entre automatiquement dans
  `PERMISSIONS_ADMIN_SEULE`, dont la liste est **derivee** de `_GUARD_SPECS` :
  ajouter un guard n'a pas a etre reporte ailleurs.

La lecture de la configuration institutionnelle, elle, reutilise le guard
`require_academic_read` existant plutot qu'un checker neuf. Un checker cree
avec une fenetre legacy vide aurait refuse aux roles historiques qui ont
acces partout ailleurs — une regression silencieuse.

### Ce qu'elle ne fait pas

- elle **n'accorde aucune permission** : une matrice rôle/permission serait une
  invention métier. Les droits sont arbitrés par un administrateur ;
- elle **ne crée aucun compte** et ne rattache personne ;
- elle **ne modifie aucune ligne** de `utilisateurs` ;
- elle **ne supprime rien** et ne touche à aucune colonne legacy.

### Downgrade

`downgrade()` **refuse** (RuntimeError) dès qu'un rôle hors catalogue existe :

```
La downgrade 0013 est refusee : N role(s) dynamique(s) hors catalogue existent.
Supprimez-les explicitement via DELETE /api/v1/rbac/roles/{code} avant de
retrograder le schema.
```

Si seuls le catalogue et les six rôles système sont présents, le downgrade
supprime les quatre tables et leurs index. Effet de bord assumé et documenté :
des affectations faites sur des rôles système seraient perdues (elles ne sont
pas « données métier » mais des décisions de transition).

---

## 4. Modèle d'autorisation

- **Aucun héritage de rôle.** `Role` n'a pas de parent. Une permission n'existe
  que par une ligne `rbac_role_permissions`.
- **Allow-only strict.** Pas de négation, pas de « tout sauf ». `PUT
  /roles/{code}/permissions` remplace l'ensemble : une permission absente est
  réellement retirée.
- **Résolution transaction-safe.** `rbac_service` n'ouvre ni ne commit de
  transaction ; tout est résolu dans la transaction de l'appelant, donc la
  réponse JSON et l'état de la base sont atomiques.
- **`is_superuser` n'est jamais une autorité.** Seul `utilisateurs.role` est lu
  comme rôle legacy, et uniquement par les guards statiques.
- Requêtes de résolution (3 allers-retours max par `/auth/me`) :

```sql
-- rôles
SELECT r.code, r.libelle FROM rbac_roles r
JOIN rbac_user_roles ur ON ur.role_id = r.id
WHERE ur.user_id = :uid AND ur.actif AND r.actif
ORDER BY r.ordre, r.code;

-- permissions (DISTINCT, sans parcours hiérarchique)
SELECT DISTINCT p.code FROM rbac_permissions p
JOIN rbac_role_permissions rp ON rp.permission_id = p.id
JOIN rbac_roles r ON r.id = rp.role_id
JOIN rbac_user_roles ur ON ur.role_id = r.id
WHERE ur.user_id = :uid AND ur.actif AND r.actif AND p.actif
ORDER BY p.code;

-- authz_version = max(updated_at) sur 4 sous-requêtes scalaires
```

---

## 5. `require_permission(permission_code)`

```python
from app.api.deps import require_permission

_actor = Depends(require_permission("roles.manage"))
# ou, en conservant des rôles legacy :
_actor = Depends(require_permission("users.manage", legacy_roles=[UserRole.SECRETARIAT]))
```

Autorise, **dans cet ordre** :

1. le rôle legacy `ADMIN` (raccourci de transition, pour qu'aucun compte
   existant ne perde l'accès) ;
2. les rôles legacy listés explicitement dans `legacy_roles` ;
3. un rôle dynamique actif portant la permission.

`is_superuser` n'est jamais consulté. Le refus est un `403` avec le code
manquant dans le détail :

```json
{"detail": "Permission requise absente : roles.manage. Aucun role dynamique ne l'accorde."}
```

Guardes exposés :

| Garde | Permission |
|---|---|
| `require_rbac_admin` | `roles.manage` |
| `require_users_manage` | `users.manage` |
| `require_audit_read` | `audit.read` |

### Endpoints migrés vers la couche dynamique

| Endpoint | Avant | Après | Régression |
|---|---|---|---|
| `/api/v1/rbac/**` (18 opérations) | inexistant | `require_rbac_admin` | aucune (nouveau) |
| `GET /api/v1/audit/events` | `require_admin` | `require_audit_read` | aucune : ADMIN legacy passe, les autres étaient et restent `403` |
| `POST /api/v1/users/` | `require_admin` | `require_users_manage` | aucune |
| `PUT /api/v1/users/{id}` | `require_admin` | `require_users_manage` | aucune |
| `DELETE /api/v1/users/{id}` | `require_admin` | `require_users_manage` | aucune |
| `GET /api/v1/users/` | `require_academic_staff` | `require_users_read` (`legacy_roles` = les 5 rôles staff) | aucune |

### Migration des guards métier : terminée

**Les 104 routes métier ont basculé vers la couche dynamique.** Aucun
`RoleChecker` n'est plus utilisé par un endpoint : la colonne
`utilisateurs.role` n'est plus l'autorité d'aucune route, elle n'est plus
lue que comme projection de compatibilité.

L'arbitrage est porté par une **table déclarative unique**,
`_GUARD_SPECS` dans `app/api/deps.py`, qui déclare pour chaque guard la
permission exigée **et** la fenêtre legacy. Cette table produit :

1. les guards effective utilisées par les endpoints ;
2. `LEGACY_PERMISSION_MATRIX`, exposée par `/auth/me`.

Il n'existe donc qu'une seule matrice, côté serveur.

| Guard | Permission | Fenêtre legacy (inchangée) | Routes |
|---|---|---|---|
| `require_academic_read` | `academic.read` | 5 rôles staff | `structure/*` lectures (10), `sessions/*` lectures (4) |
| `require_academic_structure_write` | `academic.write` | ADMIN | `structure/*` écritures (15), `sessions/*` écritures (3) |
| `require_academic_registry_read` | `academic.read` | ADMIN, DIRC, SECR | `academic/*` lectures cycles/niveaux/classes/inscriptions (8) |
| `require_academic_write` | `academic.write` | ADMIN, DIRC | `academic/*` écritures (11), `context` PUT |
| `require_students_read` | `students.read` | ADMIN, DIRC, SECR | `etudiants` recherche + détail |
| `require_students_directory_read` | `students.read` | + COMPTABILITE | `etudiants` répertoire minimal |
| `require_students_write` | `students.write` | ADMIN, DIRC, SECR | `etudiants` création/modification/inscription, `academic` inscriptions POST |
| `require_students_delete` | `students.write` | ADMIN | `etudiants` DELETE |
| `require_admissions_read` | `admissions.read` | ADMIN, DIRC, SECR | `admissions/*` lectures, `admission_views` GET |
| `require_admissions_write` | `admissions.write` | ADMIN, DIRC, SECR | `admissions/*` écritures, `admission_views` POST/PUT/DELETE |
| `require_pedagogy_read` | `pedagogy.read` | 5 rôles staff | `pedagogie` cours/examens/absences GET |
| `require_pedagogy_grades_read` | `pedagogy.read` | ADMIN, DIRC, ENSE | `pedagogie` notes GET |
| `require_pedagogy_write` | `pedagogy.write` | ADMIN, DIRC, ENSE | saisie notes/absences/cours/examens, délibérations |
| `require_pedagogy_delete` | `pedagogy.write` | ADMIN | `pedagogie` cours DELETE |
| `require_finance_read` | `finance.read` | ADMIN, COMPT | `finances/*` lectures (9) |
| `require_finance_write` | `finance.write` | ADMIN, COMPT | `finances/*` écritures (5) |
| `require_users_read` | `users.manage` | 5 rôles staff | `GET /users/` |
| `require_users_manage` | `users.manage` | — (ADMIN) | `POST/PUT/DELETE /users/` |
| `require_audit_read` | `audit.read` | — (ADMIN) | `GET /audit/events` |
| `require_rbac_admin` | `roles.manage` | — (ADMIN) | `/rbac/**` (18 opérations) |
| `require_documents_issue` | `documents.issue` | ADMIN, DIRC, SECR | `/documents` émission unitaire, aperçu, lot, duplicata (4) |
| `require_institution_settings` | `institution.settings` | — (ADMIN) | `/institution` écriture identité + logo (PUT config, POST/DELETE logo) |

#### Pourquoi plusieurs guards partagent une permission

`academic.write` est par exemple requis sur le socle académique (fenêtre
ADMIN + DIRC, ancien `require_pedagogie`) **et** sur le référentiel
structurel (fenêtre ADMIN seul, ancien `require_admin`). Consolider sur un
seul guard aurait laissé un Directeur des études modifier filières et UE,
ce qui n'était jamais possible. Deux guards, une permission, deux fenêtres
legacy : l'accès nouveau est le même, le périmètre historique est intact.

#### Preuve de non-régression

`test_rbac_e2e.py` §19-20 vérifie, sur comptes réels :

- un `ETUDIANT` sans rôle dynamique est refusé (`403`) sur `GET /etudiants` ;
- après affectation d'un rôle portant `students.read` + `pedagogy.read`, le
  même compte obtient `200` sur ces lectures ;
- `POST /etudiants` et `POST /structure/filieres` restent en `403` ;
- l'enseignant lit `/pedagogie/notes` (`200`) mais le secrétariat non
  (`403`) : fenêtre `require_pedagogy_grades_read` préservée ;
- le secrétariat lit `/etudiants` (`200`) mais ne peut ni écrire
  `/structure/filieres` ni supprimer un dossier (`403`) ;
- `permissions_effectives` reproduit exactement la fenêtre legacy.

---

## 6. Contrat JSON

### `GET /api/v1/auth/me`

Le contrat historique est **intégralement préservé** : tous les champs de
l'ancien `UserResponse` sont toujours là, avec les mêmes noms et les mêmes
contraintes. Trois champs sont **ajoutés**, tous optionnels.

```json
{
  "id": 1,
  "email": "admin@ecole-ci.org",
  "nom": "Test",
  "prenom": "Admin",
  "telephone": null,
  "role": "ADMIN",
  "is_active": true,
  "is_superuser": true,
  "etudiant_id": null,
  "avatar_url": null,
  "last_login": "2026-09-25T10:11:12.345678+00:00",
  "created_at": "2026-09-25T10:00:00+00:00",
  "updated_at": "2026-09-25T10:00:00+00:00",

  "roles": ["ROLE_CONTROLE_AUDIT"],
  "permissions": ["audit.read", "students.read"],
  "permissions_effectives": [
    "academic.read", "admissions.read", "admissions.write",
    "audit.read", "pedagogy.read", "students.read", "students.write",
    "users.manage"
  ],
  "authz_version": "2026-09-25T10:12:00.123456+00:00"
}
```

| Champ | Type | Sémantique |
|---|---|---|
| `role` | `string` | rôle **legacy**, inchangé. Projection de compatibilité, plus l'autorité d'aucune route. |
| `is_superuser` | `bool` | projection historique de `role`, **jamais** une autorité. |
| `roles` | `string[]` | codes des rôles dynamiques **actifs** portés par le compte, triés par `Role.ordre` puis `code`. `[]` si aucun. |
| `permissions` | `string[]` | **autorité dynamique pure** : uniquement ce que les rôles dynamiques affectés accordent, allow-only, sans héritage. `[]` si aucun rôle dynamique. C'est la source de vérité de l'écran d'administration des rôles. |
| `permissions_effectives` | `string[]` | **droits réellement exerçables** : union de `permissions` et de la fenêtre legacy du rôle, triée. C'est exactement ce que les guards accordent sur les endpoints ; le frontend s'en sert pour la navigation et n'héberge aucune matrice. |
| `authz_version` | `string \| null` | ISO-8601 du `max(updated_at)` sur (affectations, rôles, grants, permissions) du compte. `null` tant qu'aucune affectation dynamique n'existe. Sert à invalider un cache client sans recharger la liste. |

> **Pourquoi deux listes ?** `permissions` décrit ce que l'administrateur a
> *attribué* ; `permissions_effectives` décrit ce que le serveur *autorise*.
> Les confondre rendrait l'écran des rôles trompeur, ou ferait disparaître
> des menus à des comptes qui ont pourtant toujours eu accès.

> `authz_version` est un `string` ISO et non un entier : il est stable, lisible
> et se compare lexicographiquement après normalisation UTC. Il est monotonic
> dans le temps, pas nécessairement +1.

### `GET /api/v1/rbac/permissions`

```json
[{
  "id": 1, "code": "academic.read", "domaine": "academic", "action": "read",
  "libelle": "Consulter le socle academique",
  "description": "Acces en lecture aux cycles, niveaux, filieres, ...",
  "systeme": true, "actif": true,
  "created_at": "...", "updated_at": "..."
}]
```

Filtres : `?domaine=`, `?actif=`, `?systeme=`. Trié par `code`.

### `GET /api/v1/rbac/roles`

```json
[{
  "id": 1, "code": "ROLE_ADMIN", "libelle": "Administrateur",
  "description": "Role systeme aligne sur le role legacy ADMIN.",
  "ordre": 10, "systeme": true, "actif": true,
  "permissions": [], "utilisateurs": 0,
  "created_at": "...", "updated_at": "..."
}]
```

`permissions` = codes accordés **et actifs**. `utilisateurs` = nombre
d'affectations **actives**. Trié par `ordre`, puis `code`.

### `GET|PUT /api/v1/rbac/roles/{code}/permissions`

`GET` renvoie la liste des objets `Permission` liés (inactives incluses, pour
pouvoir diagnostiquer).

`PUT` — **remplacement total**, idempotent :

```json
{ "permissions": ["audit.read", "students.read"], "motif": "Perimetre 2026" }
```

Réponse : le `RoleResponse` complet. Codes inconnus ou permissions inactives →
`422` avec la liste fautive. Le `motif` est optionnel.

`POST` (ajout incrémental, idempotent) : `{"permission": "rapports.read", "motif": "..."}` → `201`.
`DELETE /roles/{code}/permissions/{permission_code}` → `200` + `RoleResponse`, `404` si absent.

### `POST /api/v1/rbac/roles/{code}/users`

```json
{
  "user_ids": [2, 3],
  "motif": "Controle de fin d'annee",
  "aligner_role_legacy": false
}
```

Réponse :

```json
{
  "role_code": "ROLE_CONTROLE_AUDIT",
  "affectes": [2, 3],
  "deja_affectes": [],
  "legacy_role_aligne": null,
  "reponses": [{
    "user_id": 2, "role_id": 7, "role_code": "ROLE_CONTROLE_AUDIT",
    "role_libelle": "Controle audit", "role_systeme": false,
    "actif": true, "motif": "Controle de fin d'annee", "attribue_par": 1,
    "created_at": "...", "updated_at": "..."
  }]
}
```

- `deja_affectes` : comptes déjà porteurs du rôle (l'opération reste un `200`,
  elle n'échoue pas).
- `aligner_role_legacy` : écrit `utilisateurs.role`. Refusé `422` si le rôle
  n'a pas d'équivalent legacy, refusé `409` si le compte porte déjà un rôle
  legacy **plus hiérarchique** (une affectation ne retire jamais un droit).
- Compte inexistant → `422` avec la liste des ids introuvables.
- Rôle désactivé → `409`.

### `DELETE /api/v1/rbac/roles/{code}/users/{user_id}?aligner_role_legacy=false`

La ligne est **conservée** et passée `actif = false` (historique). Une seconde
suppression renvoie `404` (l'affectation n'existe plus en droit).
Sans `aligner_role_legacy`, `utilisateurs.role` n'est pas touché.

### `GET /api/v1/rbac/users/roles[?role_code=]`

```json
[{
  "id": 2, "email": "secretariat@ecole-ci.org",
  "nom": "Secretariat", "prenom": "Rbac",
  "role": "SECRETARIAT", "is_active": true,
  "roles": ["ROLE_CONTROLE_AUDIT"],
  "role_labels": ["Controle audit"],
  "permissions": ["audit.read", "students.read"],
  "authz_version": "2026-09-25T10:12:00.123456+00:00"
}]
```

Cette vue est **résolue en jointure depuis la base** à chaque appel — ce n'est
pas une matrice mise en cache ni simulée. Aucun secret n'est exposé.

### `GET /api/v1/rbac/users/{user_id}/permissions`

```json
{
  "user_id": 2,
  "role": "SECRETARIAT",
  "legacy_role_is_admin": false,
  "roles": ["ROLE_CONTROLE_AUDIT"],
  "role_labels": ["Controle audit"],
  "permissions": ["audit.read", "students.read"],
  "permission_domains": ["audit", "students"],
  "authz_version": "2026-09-25T10:12:00.123456+00:00"
}
```

Purement consultatif : n'accorde rien. Seul un guard décide d'un accès.

---

## 7. Codes HTTP notables

| Situation | Code |
|---|---|
| Permission dynamique absente et rôle legacy non listé | `403` |
| Rôle / permission inconnu | `404` |
| Code déjà utilisé (permission, rôle) | `409` |
| Permission système supprimée ou désactivée | `409` |
| Rôle système supprimé | `409` |
| Rôle affecté / permission accordée : suppression refusée | `409` |
| Affectation d'un rôle désactivé | `409` |
| Alignement legacy qui rétrograderait le compte | `409` |
| Permission/rôle à créer avant d'être accordé | `422` |
| `aligner_role_legacy` sur un rôle sans équivalent legacy | `422` |
| Utilisateur introuvable dans une affectation | `422` |
| Création de compte ADMIN ou changement de `role`/`is_active` par un non-ADMIN legacy | `403` |

---

## 8. Garde-fou anti-escalade

Tant que les `RoleChecker` lisent `utilisateurs.role`, un rôle dynamique
`users.manage` ne doit pas pouvoir s'auto-attribuer des pouvoirs. Règle
appliquée **côté écriture** dans `app/api/v1/endpoints/users.py`
(`_assert_can_manage_legacy_projection`) :

- seul ADMIN legacy peut **créer** un compte (donc choisir son `role`) ;
- seul ADMIN legacy peut **modifier** `role` ou `is_active` d'un compte.

Un rôle dynamique `users.manage` peut donc gérer l'annuaire et les profils, mais
pas construire sa propre élévation. Les protections existantes sont conservées :
auto-rétrogradation et dernier administrateur actif
(`app/services/user_security.py`).

---

## 9. Journalisation

Toutes les mutations RBAC écrivent dans `audit_events` (convention
`app/services/audit_service.py`), dans la **même** transaction que l'écriture :

`security.rbac.permission.created|updated|deleted`,
`security.rbac.role.created|updated|deleted`,
`security.rbac.role.permissions_set|permission_added|permission_removed`,
`security.rbac.role.assigned|unassigned`.

Aucun mot de passe, hash ou jeton n'est placé dans `details` (vérifié par
`test_rbac_e2e.py`).

---

## 10. Limites restantes

1. **Raccourci ADMIN legacy.** `require_permission` laisse passer
   `role == "ADMIN"`. À retirer quand les premiers rôles dynamiques
   porteront `roles.manage` : c'est le dernier reliquat de la projection
   legacy comme autorité.
2. **`/auth/me` est le seul endpoint annoté.** `POST /auth/login` renvoie
   toujours l'ancien `UserResponse` (contrat inchangé). Le frontend appelle
   `/auth/me` après connexion pour obtenir `permissions_effectives`.
3. **`authz_version` n'est pas dans le JWT.** Le token reste valide après un
   changement de droits ; c'est volontaire (pas de blacklist). Le client
   compare `authz_version` au rechargement du profil.
4. **Deux permissions ne sont pas encore portées par un endpoint** :
   `dashboard.read` (le tableau de bord est un agrégat côté client, sans
   endpoint dédié) et `roles.manage` / `users.manage` / `audit.read` qui ne
   s'appliquent qu'à l'administration. Elles restent utiles pour masquer des
   menus, pas pour autoriser une route métier.
5. **Le frontend cumule encore `allowedRoles` et `requiredPermission`**
   (sémantique AND) sur les modules dont la liste de rôles historique est
   plus étroite que la fenêtre de la permission : structure, pédagogie,
   sessions, utilisateurs, enquiry personnel. Ce n'est pas un défaut, c'est
   une prudence : retirer `allowedRoles` élargirait l'interface. Le jour où
   l'on décide que la permission seule fait foi, il suffit de supprimer
   `allowedRoles` sur ces routes — le backend est déjà prêt.
6. **`/rbac/**` exige `roles.manage`.** Aucun bootstrap n'est fourni : le
   premier compte à l'obtenir est l'ADMIN legacy du setup wizard, qui passe par
   le raccourci.
7. **Downgrade destructive pour les affectations système.** Documenté §3.
8. **Aucune interface d'attribution en lot.** L'écran Rôles affecte les
   comptes rôle par rôle ; un écran dédié dans « Comptes utilisateurs »
   serait plus confortable pour une école de taille moyenne.

---

## 11. Tests

```powershell
.\venv\Scripts\python.exe test_rbac_e2e.py       # nouveau
.\venv\Scripts\python.exe test_academic_e2e.py   # non-régression
.\venv\Scripts\python.exe test_sprint3_e2e.py    # non-régression
.\venv\Scripts\python.exe test_sprint2.py        # non-régression
```

`test_rbac_e2e.py` couvre 18 scénarios sur une base SQLite temporaire
(`%TEMP%\appedu-rbac-e2e`, supprimée en fin de run) — **aucune base locale
n'est touchée, aucun reset** :

1. cycle `upgrade → downgrade → upgrade` de 0013 ;
2. refus de downgrade dès qu'un rôle hors catalogue existe ;
3. seed exact : 14 permissions, 6 rôles système, **0** grant, **0** compte ;
   le catalogue total est de 16 permissions après 0015 et 0016, ce que
   `test_rbac_e2e.py` vérifie explicitement ;
4. `/auth/me` : 13 champs legacy intacts + 3 champs dynamiques ;
5. catalogue : liste, filtres, détail, création, doublon `409`, code invalide
   `422`, protection système `409` ;
6. rôles : liste, création, code réservé `409`, `PUT`, suppression système
   refusée `409` ;
7. idempotence des `PUT /permissions`, code inconnu `422` ;
8. ajout/retrait de grants, permission liée non supprimable `409` ;
9. affectation idempotente, utilisateur inconnu `422`, alignement legacy
   impossible hors rôle système `422` ;
10. **effet réel** : après affectation, `/auth/me` expose les permissions,
    `/audit/events` passe de `403` à `200` sans toucher à `users.role` ;
11. garde `roles.manage` toujours `403` pour ce compte ;
12. vue `users/roles` et permissions effectives ;
13. retrait d'une permission → `/auth/me` se rétrécit réellement ;
14. désactivation d'un rôle → permissions perdues puis restaurées ;
15. retrait d'affectation → ligne conservée, `404` à la seconde suppression ;
16. projection legacy : alignement, refus de rétrogradation, independence ;
17. suppression d'un rôle : `409` si affecté, `200` sinon ;
18. anti-escalade `users.manage` et journalisation RBAC.

Vérification supplémentaire : `alembic check` après `upgrade head` →
**« No new upgrade operations detected »** (modèles et migration alignés).
