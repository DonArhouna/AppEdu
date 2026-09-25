# Suite E2E frontend (Playwright)

Ces tests pilotent un vrai navigateur (Chromium) contre la vraie application.
Ils visent les défauts qu'une relecture de code ne voit pas : un crash de
rendu, une boucle `Maximum update depth exceeded`, un `<button>` imbriqué dans
un `<button>`, un titre invisible en mode clair.

## Lancement

```powershell
cd Frontend
npm run test:e2e
```

Ou, pour un sous-ensemble :

```powershell
..\Backend\venv\Scripts\python.exe -m pytest e2e/test_paiements.py -q
..\Backend\venv\Scripts\python.exe -m pytest e2e/test_navigation.py -k filieres -q
```

Prérequis (déjà installés dans le venv du backend) :
`playwright`, `pytest`, `pytest-timeout`, `requests`, et le navigateur
`python -m playwright install chromium`.

## Isolation

La suite est **hermétique**. Elle ne touche jamais la base ni le stockage de
l'institut :

| Ressource      | Emplacement                                        |
| -------------- | -------------------------------------------------- |
| Base           | `%TEMP%\appedu-e2e-frontend\e2e.db` (SQLite neuve) |
| Stockage       | `%TEMP%\appedu-e2e-frontend\{admissions,documents}` |
| Backend        | port 8111-8114, lancé par la fixture               |
| Frontend       | port 5173-5176, Vite dédié                         |

Les migrations Alembic sont appliquées dans un **sous-processus**
(`alembic upgrade head`), comme en exploitation : `alembic/env.py` appelle
`asyncio.run()`, qui refuse de s'exécuter si une boucle est déjà active dans
le processus de test.

Les ports 8000 et 8080 (vos serveurs de développement) ne sont jamais
utilisés. Avant de démarrer, la fixture élimine les processus E2E des runs
précédents et **échoue bruyamment** si un verrou empêche le nettoyage : un
`rmtree(ignore_errors=True)` silencieux laissait une base déjà amorcée, ce
qui produisait un « système déjà configuré » trompeur au run suivant.

## Le signal qui compte : la console

Chaque page collecte les erreurs, avertissements et exceptions de la console
du navigateur. Une page peut s'afficher correctement **et** produire une
erreur ; la seule présence d'un élément ne le détecte pas. C'est ce signal
qui a attrapé les plantages de rendu.

Les messages connus et sans rapport avec l'application (avertissements de
React Router v6, invitation à React DevTools) sont filtrés dans
`BRUITS_CONSOLE`.

## Données de test

Le jeu de données est créé **par l'API**, jamais en SQL, et il est
délibérément réaliste : la session comporte des périodes de paiement, parce
qu'une page vide ne traverse pas le code qui plante — la tuile de période du
modal de paiement n'est rendue que si la session en contient.

Comptes créés par le Setup Wizard de l'instance de test :

| Profil      | Rôle         | Email                        |
| ----------- | ------------ | ---------------------------- |
| Administrateur | `ADMIN`     | `admin.e2e@ecole-ci.org`     |
| Secrétariat | `SECRETARIAT`| `secretariat.e2e@ecole-ci.org`|
| Enseignant  | `ENSEIGNANT` | `enseignant.e2e@ecole-ci.org`|
| Étudiant    | `ETUDIANT`   | `etudiant.e2e@ecole-ci.org`  |

## Fichiers

| Fichier                | Couverture                                              |
| ---------------------- | ------------------------------------------------------- |
| `conftest.py`          | Pile isolée, amorçage, collecte console, fixtures de connexion |
| `test_navigation.py`   | Les 29 pages se chargent, aucune erreur console, aucune entrée de menu cassée |
| `test_login.py`        | Contenu visible sans défilement, bascule de thème, connexion refusée |
| `test_paiements.py`    | Ouverture du modal de guichet, sélection de périodes, fermeture |
| `test_portails.py`     | Le menu ne vend que les portails que la route accorde |
| `test_parametrage_institution.py` | Versionnement, validation, téléversement et retrait du logo |
| `test_identite_documents.py` | L'identité que le secrétariat imprime est visible là où il travaille |

## Ordre d'exécution

La pile est partagée par toute la session : un test qui écrit laisse donc son
état aux suivants. Les tests du paramétrage **lisent la version affichée** et
vérifient l'écart, au lieu de supposer qu'elle vaut 0.

Une exception assumée : `test_etat_neuf_sans_logo_ni_historique` suppose un
état intact et **le vérifie**. Si un test modifiant la configuration
s'exécutait avant lui, l'échec le dirait explicitement plutôt que de
produire un résultat faux. Aucun autre module de la suite ne touche la
configuration institutionnelle.

## Ce que les tests ont trouvé

| Défaut | Cause |
|---|---|
| Le menu propose le Portail Enseignant et l'Espace Étudiant à un administrateur | `hasAccess` accorde tout à ADMIN, alors que ces deux routes sont `allowSuperuser={false}`. Corrigé en portant le même opting-out que `ProtectedRoute` dans le menu. |
| Le logo ne s'affiche jamais après un téléversement réussi | Une `<img src>` ne peut pas envoyer l'en-tête `Authorization` ; l'endpoint est protégé par `academic.read`. Corrigé en chargeant les octets par le client authentifié et en attachant une URL d'objet, révoquée au changement. |
| Une version est créée pour un enregistrement sans changement | Le formulaire renvoyait la configuration entière. Corrigé en ne transmettant que les champs modifiés, le serveur comparant champ par champ. |
| Le secretariat ne voit pas l'identité qu'il imprime | L'écran Documents est protégé par `documents.issue` : c'est voulu. L'identité a donc été affichée sur cet écran, en lecture seule, sans lien d'édition trompeur. |

## Défaut trouvé par cette suite

`hasAccess` accorde tout à `ADMIN`, alors que `/portail-enseignant` et
`/espace-etudiant` sont déclarés `allowSuperuser={false}`. Le menu
proposait donc à l'administrateur deux entrées qui ne menaient qu'à un écran
« Accès réservé ».

Corrigé en portant le même opting-out que `ProtectedRoute` dans
`SidebarNew` (`MenuItem.allowSuperuser`). Le menu annonce désormais
exactement ce que la route autorise, et `test_portails.py` verrouille les
deux moités : l'administrateur ne voit pas les portails d'autrui, chaque
profil voit le sien avec de vraies données.
