# Migration des données EduManagePro vers le backend

## Règle appliquée

Les écrans ne doivent plus afficher de données de démonstration. Une page dont le
backend n'est pas encore disponible affiche un état vide explicite et ne simule
aucun enregistrement.

La migration `0006_remove_implicit_defaults` retire également les anciennes
valeurs server default (année, devise, filière, niveau, etc.) : les API et
formulaires doivent fournir les valeurs explicitement.

## Modules connectés

- Setup et authentification : établissement, devise et compte administrateur créés
  par l'API ; aucun credential prérempli.
- Sessions académiques et périodes de paiement : CRUD API.
- Contexte académique global : année et session courantes persistées sur
  l'établissement, avec reprise additive depuis une session active existante.
- Pagination serveur : registre des candidatures paginé et filtré côté API.
- Vues enregistrées et actions groupées sur les candidatures, privées par
  utilisateur et contrôlées côté API avec erreurs explicites par dossier.
- Structure : campus, départements, filières, UE et matières.
- Étudiants : CRUD API, rattachement aux sessions et recherche backend.
- Frais : grilles tarifaires par filière/niveau, sans devise ou montant implicite.
- Factures, paiements et reçus : enregistrement et consultation API ; la
  passerelle bancaire externe n'est pas simulée.
- Notes et absences : saisie et consultation API.
- Emploi du temps : CRUD des cours via l'API ; salles et enseignants sont des
  saisies/référentiels à enrichir.
- Comptes utilisateurs : CRUD API avec rôles et statuts.
- Portails auto-service : agrégats filtrés côté serveur pour le dossier étudiant
  et les cours/notes affectés à l'enseignant.
- Admissions : candidatures, checklist de pièces, décisions historisées et
  conversion transactionnelle en dossier étudiant via des endpoints RBAC ; aucun
  compte utilisateur n'est créé automatiquement.
- Tableaux de bord, analytics et reporting : agrégats calculés à partir des
  données API disponibles.

## Modules explicitement en attente

- Ressources et fichiers pédagogiques.
- Sites, bâtiments et salles.
- Messagerie interne.
- Journal d'audit persisté.
- Attributs RH détaillés (poste, département, contrat, Vacation).
- Vérification de documents et génération de bulletins/PV.
- Paramètres avancés (semestres, seuils, nomenclature).
- Prestataires de paiement en ligne.
- Stockage des pièces d'admission : les octets sont écrits dans
  `Backend/storage/admissions` via un endpoint RBAC ; PostgreSQL ne conserve que
  le chemin relatif. Les sauvegardes, l'antivirus et un stockage objet restent à
  brancher pour la production.

## Ordre de migration recommandé

1. Ajouter le modèle et la migration Alembic.
2. Ajouter les schémas Pydantic et les endpoints protégés.
3. Ajouter le client API typé.
4. Remplacer l'écran par le chargement API et les états vide/erreur.
5. Ajouter un test E2E sur données réelles.
6. Réactiver l'entrée de menu et le workflow.

## P0 appliqué

- Migration `0007_portal_identity` : lien nullable `Utilisateur.etudiant_id`,
  avec reprise additive uniquement pour un compte étudiant et un email réel
  déjà présent.
- Endpoints `/api/v1/portail/etudiant` et `/api/v1/portail/enseignant` :
  filtrage serveur par identité et tests de non-divulgation.
- Notes, absences et cours teacher's endpoints limités aux affectations de
  l'enseignant.
- Les contrôles hors-ligne, notifications, année académique et préférences non
  persistées ont été rendus explicites ou retirés.
- Les entrées de menu des modules sans backend persistant sont masquées ;
  leurs routes restent accessibles pour le travail de migration contrôlée.

## Admissions — lot P1 appliqué

- Migration additive `0008_admissions_workflow` : tables `candidatures`,
  `pieces_candidature` et `decisions_admission`, avec contraintes et index.
- Schémas Pydantic et endpoints `/api/v1/admissions/*` protégés par
  `require_admissions` (administrateur, direction des études, secrétariat).
- Le client TypeScript et les écrans `PreInscription` / `Validation` chargent
  exclusively les données API et exposent les états vide, erreur et succès.
- Le test `test_sprint3_e2e.py` couvre création, checklist, décision, conversion,
  accès enseignant refusé et l'absence de création automatique de compte.
- La conversion crée uniquement un dossier étudiant ; la création du compte et
  du mot de passe reste une action explicite d'administration.
- Les fichiers d'admission sont déposés via multipart dans
  `Backend/storage/admissions`, téléchargés par un endpoint RBAC et jamais
  stockés dans PostgreSQL ; les noms de fichiers sont régénérés côté serveur.
- La migration `0009_global_academic_context` persiste l'année et la session
  de référence ; l'API `/context/academique` alimente la navigation et le
  paramétrage. La liste des candidatures renvoie une enveloppe paginée.
- La migration `0010_admission_views` ajoute les vues de filtres privées et les
  actions groupées (mise en vérification, dossier complet, annulation).
