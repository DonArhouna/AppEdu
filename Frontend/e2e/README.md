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
| `test_deliberation.py` | Règlement, séance, décisions motivées, clôture bloquée tant qu'il reste un inscrit |
| `test_tableau_de_bord_deliberation.py` | La carte dit si le règlement est confirmé, et ne l'invente pas |
| `test_instance_neuve.py` | L'ecran d'une instance sans session : etat, pas panne |
| `test_setup_wizard.py` | Le wizard envoie le pays, et l'adresse n'a plus de trou |
| `test_relances.py` | Créance échue réelle, recherche honnête, parcours complet de relance, accès refusé |
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
| **« J'ai enregistré, ça n'a pas changé »** — signalé en usage réel | Le formulaire n'était pas un vrai `<form>` : **Entrée n'enregistrait rien**, sans aucun message. Le clic et la touche suivaient deux chemins, dont un muet. Et « aucun changement » n'était qu'un toast éphémère, facile à rater. Corrigé : formulaire réel, retour **persistant dans le formulaire**, indicateur de saisie en attente. |
| L'historique se remplit de faux changements de `pays` | Le formulaire renvoie `""` pour un champ vide, alors que la colonne vaut `NULL` : chaque enregistrement créait une version pour ce faux changement. `NULL` et chaîne vide sont désormais la même valeur, et la colonne ne stocke plus que `NULL`. |
| Une panne de l'historique se lit comme « aucune modification enregistrée » | `setVersions(versionsResult.data ?? [])` traitait un **échec** de `GET /institution/versions` comme une liste vide. L'agent lisait une affirmation — « personne n'a jamais modifié la configuration » — alors que l'écran n'avait rien chargé. Un état vide affirme une absence de données ; une panne en est une autre. L'échec a désormais son propre message, et `test_un_historique_qui_echoue_ne_paie_pas_vide` le verrouille en interceptant l'appel. |
| Un test échoue sur une ligne qui n'a rien à voir | `page.locator("table tbody tr").first` visait **toutes** les tables de l'écran, dont celle des sessions. L'échec ne disait donc pas la cause. La lecture est désormais scopée à la carte d'historique. |
| Le détail d'une facture et la balance âgée répondaient **500** | `Facture.reste_a_payer` est une `@property`, et ces deux endpoints l'appelaient comme une méthode. Le recouvrement était donc inutilisable depuis que la propriété existe. Trouvé par `test_relances_e2e.py` (backend), pas par cette suite : les deux moitiés du produit se vérifient l'une l'autre. |
| Une installation neuve demarre sans pays, et son adresse finit par `", , "` | `EtablissementSetupInput` ne portait pas `pays` : le pays n'etait ni recu ni stocke. Pire, le payload assemblait l'adresse par `` `${adresse}, ${ville}, ${pays}` `` alors que **`ville` et `pays` n'avaient aucun champ de formulaire** — tout le monde obtenait une adresse malformee, imprimee sur chaque document officiel. Corrige : champ `pays` au schema et au wizard, champs Ville et Pays, adresse assemblee en ne joignant que les parties saisies. `test_setup_wizard.py` verrouille les deux, en interceptant `GET /setup/status` puisque le wizard n'est accessible que sur une instance vierge. |
| Un test dependait d'un etat fortuit du jeu de donnees | `test_un_champ_vide_ne_cree_pas_de_faux_changement` affirmait que le champ Pays etait vide. Renseigner le pays dans le seed — correction legitime par ailleurs — a rendu sa premisse fausse sans que le defaut couvert change. Le test etablit maintenant sa condition par l'API, comme le fait deja `test_modifier_un_champ_deja_rempli`. |
| `initialize(payload: unknown)` laissait passer n'importe quel champ manquant | Le payload du Setup Wizard n'etait type par rien : un `pays` ajoute au formulaire aurait compile, et l'API l'aurait ignore en silence. Type `SetupInitPayload` ajoute, cote client. |
| Le tableau de bord affiche une erreur sur une instance neuve | `GET /sessions/active` repond 404 faute de session — l'etat normal d'un institut juste apres le Setup Wizard. Le tableau de bord traitait cela comme une erreur **fatale** et affichait « Erreur de synchronisation backend » alors que les etudiants, filieres et paiements etaient charges. Le repli « Non definie » prevu dix lignes plus bas etait donc mort : il ne pouvait pas s'executer. Corrige en distinguant le 404 de l'echec reel. |
| `GET /context/academique` repond 409, et l'ecran l'avalait | Le schema portait `configuree: bool`, mais le code levait 409 **avant** de pouvoir renvoyer `configuree: false` : le champ etait mort. Le 409 etait aussi faux — rien n'est en conflit, l'annee n'est pas encore configuree. Pire, l'ecran de Parametrage absorbait l'echec et affichait « non configure », **indistinguable** d'un etat normal. Corrige : 200 avec `configuree: false`, et l'echart entre les deux est desormais annonce. |

Ces deux defauts ne pouvaient pas etre vus par la suite : `conftest` seme une session, des filieres et des classes **avant** le premier test. L'instance neuve n'est donc jamais exercee. `test_instance_neuve.py` la reproduit en interceptant les reponses, avec les statuts que le backend renvoie reellement — verifies par `test_institution_e2e.py`.

### Un test qui ne prouve rien

`test_le_tableau_de_bord_survit_a_l_absence_de_session` est passe malgre le bug, trois fois de suite. Trois erreurs distinctes, de plus en plus subtiles :

1. l'assertion visait « Impossible de charger les donnees », une chaine de **repli** que le code n'utilise pas puisque le backend renvoie un message precis ;
2. elle visait ensuite « Erreur de chargement », libelle reels « Erreur de synchronisation backend » ;
3. elle attendait « Non definie » comme fin de chargement — mais le badge l'affiche **aussi** quand rien n'a ete charge.

La garde correcte est « Total Etudiants » : les cartes KPI ne sont rendues que si `setData` a eu lieu, donc si le chargement a reussi. Verifie en reinstalant le bug : le test echoue alors en 36 s.

> Un test vert ne prouve rien s'il n'a jamais ete vu rouge. Tout test qui pretend verrouiller un defaut merite d'etre verifie contre le defaut.

## Le cas qui manquait

La suite partait d'un établissement **sans adresse**. Un champ vide et un champ
déjà rempli ne sont pas le même chemin : celui où l'on corrige une adresse
existante n'était pas exercé — et c'est exactement le cas rencontré en usage
réel.

`test_modifier_un_champ_deja_rempli` le prépare désormais par l'API, puis
**tape par-dessus** la valeur existante au lieu de la remplacer d'un bloc.
Un `fill()` aurait masqué un éventuel re-render qui remit le champ à sa
valeur d'origine.

Conséquence retenue : un jeu de données de test doit ressembler à la
production. Une base « propre » mais irréaliste crée des angles morts.

## Piege de preparation : l'identite d'une classe

`ClasseResponse` ne renvoie **pas** de `code`, et le backend refuse deux
classes de meme filiere et meme niveau. Chercher sa classe par `code`
retrouvait donc toujours rien, et le second appel etait refuse en doublon.
L'identite d'une classe est le couple `filiere_id` / `niveau_id`.

Meme principe pour le libelle de niveau : le backend le compare au **nom**
du niveau de la classe, pas a son code, et refuse le melange en 422.
`test_relances.py` retrouve ses propres donnees au lieu d'en recreer, ce
qui evite qu'un test casse le suivant sur la pile partagee.

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
