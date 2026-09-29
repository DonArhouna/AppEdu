import type { UserRole } from "@/contexts/RBACContext";

export type JsonPrimitive = string | number | boolean | null | undefined;
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };

export interface ApiRecord {
  [key: string]: unknown;
  id?: string;
  nom?: string;
  code?: string;
  email?: string;
  telephone?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface SetupStatus {
  is_configured: boolean;
  etablissement_nom?: string | null;
  etablissement_code?: string | null;
  devise?: string | null;
  version: string;
  tenant_mode: string;
  database_connected: boolean;
  details?: string | null;
}

/**
 * Identité et compte créés par le Setup Wizard.
 *
 * Le type existe pour que l'API et le wizard ne puissent plus diverger en
 * silence : un payload typé `unknown` avait laissé passer un `pays` jamais
 * transmis, et l'adresse se retrouvait assemblée avec des champs vides.
 */
export interface SetupInitPayload {
  etablissement: {
    nom: string;
    code: string;
    adresse?: string | null;
    telephone?: string | null;
    email: string;
    /** Figuré sur les documents officiels. */
    pays?: string | null;
    devise: string;
    license_key?: string | null;
  };
  admin: {
    nom: string;
    prenom: string;
    email: string;
    password: string;
    telephone?: string | null;
  };
  database?: {
    host?: string;
    port?: number;
    user?: string;
    password?: string;
    database?: string;
  } | null;
}

export interface AuthSession {
  id: string;
  created_at: string;
  expires_at: string;
  last_used_at?: string | null;
  actuelle: boolean;
}

export interface AuthSessionList {
  sessions: AuthSession[];
  total: number;
}

export interface AuthUser {
  id: number;
  email: string;
  nom: string;
  prenom: string;
  telephone?: string | null;
  role: UserRole;
  is_active: boolean;
  is_superuser: boolean;
  etudiant_id?: string | null;
  avatar_url?: string | null;
  last_login?: string | null;
  created_at: string;
  updated_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
  /**
   * Jeton de rafraîchissement d'une session révocable (lot 2). Le serveur
   * l'émet à chaque login ; le conserver ouvre la rotation silencieuse et
   * la révocation. Un client qui l'ignore se comporte comme avant.
   */
  refresh_token?: string | null;
}

export interface SessionPeriod {
  id: string;
  session_id: string;
  nom: string;
  mois: string;
  date_echeance?: string | null;
  montant_estime?: number | null;
  pourcentage?: number | null;
  ordre: number;
}

export interface AcademicSession {
  id: string;
  nom: string;
  code: string;
  annee_academique: string;
  date_debut: string;
  date_fin: string;
  statut: string;
  description?: string | null;
  periodes: SessionPeriod[];
  created_at?: string;
  updated_at?: string;
}

export interface AcademicContext {
  annee_academique: string;
  session_id?: string | null;
  session?: AcademicSession | null;
  configuree: boolean;
  updated_at: string;
}

export interface StudentSummary {
  id: string;
  matricule: string;
  nom: string;
  prenom: string;
  filiere: string;
  filiere_id?: string | null;
  classe_id?: string | null;
  niveau: string;
  statut: string;
  session_id?: string | null;
}

export interface Student extends StudentSummary {
  sexe?: string | null;
  email?: string | null;
  telephone?: string | null;
  date_naissance?: string | null;
  adresse?: string | null;
  lieu_naissance?: string | null;
  credits_valides?: number | null;
}

export interface RbacPermission {
  id: number;
  code: string;
  domaine: string;
  action: string;
  libelle: string;
  description?: string | null;
  systeme: boolean;
  actif: boolean;
  created_at: string;
  updated_at: string;
}

export interface RbacRole {
  id: number;
  code: string;
  libelle: string;
  description?: string | null;
  ordre: number;
  systeme: boolean;
  actif: boolean;
  permissions: string[];
  utilisateurs: number;
  created_at: string;
  updated_at: string;
}

export interface RbacUserAccess {
  id: number;
  email: string;
  nom: string;
  prenom: string;
  role: string;
  is_active: boolean;
  roles: string[];
  role_labels: string[];
  permissions: string[];
  authz_version?: string | null;
}

export interface RbacUserPermissions {
  user_id: number;
  role: string;
  legacy_role_is_admin: boolean;
  roles: string[];
  role_labels: string[];
  permissions: string[];
  permission_domains: string[];
  authz_version?: string | null;
}

export type ImportMode = "creation" | "mise_a_jour";
export type ImportLigneStatut = "valide" | "erreur" | "ignore";
export type ImportAction = "creer" | "mettre_a_jour" | "aucune";

export interface ImportColonne {
  source: string;
  cible: string;
}

export interface ImportAnalyseLigne {
  ligne: number;
  statut: ImportLigneStatut;
  action: ImportAction;
  matricule?: string | null;
  nom?: string | null;
  prenom?: string | null;
  filiere?: string | null;
  niveau?: string | null;
  email?: string | null;
  erreurs: string[];
  avertissements: string[];
}

export interface ImportAnalyse {
  batch_id: string;
  nom_fichier: string;
  format_source: string;
  statut: string;
  mode: ImportMode;
  nb_lignes: number;
  nb_creer: number;
  nb_mettre_a_jour: number;
  nb_erreurs: number;
  nb_avertissements: number;
  nb_ignorees: number;
  colonnes_reconnues: ImportColonne[];
  colonnes_ignorees: string[];
  champs_obligatoires_manquants: string[];
  lignes: ImportAnalyseLigne[];
  message?: string | null;
}

export interface ImportLigneResultat {
  ligne: number;
  statut: string;
  action: string;
  matricule?: string | null;
  etudiant_id?: string | null;
  erreurs: string[];
}

export interface ImportValidation {
  batch_id: string;
  statut: string;
  nb_importes: number;
  nb_mises_a_jour: number;
  nb_erreurs: number;
  nb_ignorees: number;
  lignes: ImportLigneResultat[];
  message?: string | null;
}

export interface ImportBatch {
  id: string;
  nom_fichier: string;
  format_source: string;
  statut: string;
  mode: string;
  nb_lignes: number;
  nb_creer: number;
  nb_mettre_a_jour: number;
  nb_erreurs: number;
  nb_avertissements: number;
  nb_importes: number;
  nb_ignorees: number;
  colonnes: Record<string, unknown>;
  message?: string | null;
  cree_par_id?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
  rows?: ImportRow[];
}

export interface ImportRow {
  id: number;
  ligne: number;
  statut: string;
  action: string;
  matricule?: string | null;
  etudiant_id?: string | null;
  erreurs: string[];
  avertissements: string[];
  donnees: Record<string, unknown>;
}

export interface ImportColonneModele {
  colonne: string;
  champ: string;
  obligatoire: boolean;
  description: string;
  exemples: string[];
}

export interface ImportModele {
  nom_fichier_suggere: string;
  formats_acceptes: string[];
  encodage: string;
  separateurs_csv: string[];
  colonnes: ImportColonneModele[];
  notes: string[];
}

export type DocumentTypeCode = "certificat_scolarite" | "releve_notes" | "quitus_financier";

export interface TypeDocument {
  code: DocumentTypeCode;
  prefixe: string;
  libelle: string;
  description: string;
  permission: string;
  avec_tableau: boolean;
  /** Conditions a satisfaire pour pouvoir emettre le document. */
  conditions: string[];
}

export interface DocumentOfficiel {
  id: string;
  type_document: DocumentTypeCode;
  numero: string;
  etudiant_id: string;
  session_id?: string | null;
  annee: number;
  fichier?: string;
  sha256: string;
  taille_octets: number;
  donnees: Record<string, unknown>;
  reserves: string[];
  remplace_document_id?: string | null;
  motif_duplicata?: string | null;
  emis_par_id?: number | null;
  emis_le: string;
  delivre_le?: string | null;
  created_at?: string | null;
  etudiant_nom?: string | null;
  etudiant_prenom?: string | null;
  etudiant_matricule?: string | null;
  libelle?: string | null;
}

export interface ResultatLigneDocument {
  etudiant_id: string;
  matricule?: string | null;
  nom?: string | null;
  emis: boolean;
  numero?: string | null;
  document_id?: string | null;
  motif?: string | null;
}

export interface LotDocuments {
  type_document: DocumentTypeCode;
  emis: number;
  echoues: number;
  lignes: ResultatLigneDocument[];
}

export interface AuditEvent {
  id: string;
  occurred_at: string;
  actor_id?: number | null;
  actor_email?: string | null;
  action: string;
  resource_type: string;
  resource_id?: string | null;
  outcome: string;
  reason?: string | null;
  details: Record<string, unknown>;
}

export interface User {
  id: number;
  email: string;
  nom: string;
  prenom: string;
  telephone?: string | null;
  role: UserRole;
  is_active: boolean;
  is_superuser: boolean;
  etudiant_id?: string | null;
  avatar_url?: string | null;
  last_login?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Campus {
  id: string;
  code: string;
  nom: string;
  description: string;
  ville: string;
  adresse: string;
  responsable: string;
  departements?: Department[];
  telephone?: string | null;
  email?: string | null;
}

export interface Department {
  id: string;
  code: string;
  nom: string;
  description: string;
  responsable?: string | null;
  campus_id?: string | null;
  filieres?: Filiere[];
}

export interface Filiere {
  id: string;
  code: string;
  nom: string;
  description: string;
  diplome: string;
  duree: number;
  departement_id?: string | null;
  departement?: Department;
  unites_enseignement?: TeachingUnit[];
}

export interface AcademicCycle {
  id: string;
  code: string;
  nom: string;
  libelle: string;
  description?: string | null;
  ordre: number;
  rang: number;
  actif: boolean;
  created_at: string;
  updated_at: string;
}

export interface AcademicLevel {
  id: string;
  code: string;
  nom: string;
  libelle: string;
  cycle_id: string;
  description?: string | null;
  ordre: number;
  rang: number;
  actif: boolean;
  created_at: string;
  updated_at: string;
  cycle?: AcademicCycle | null;
}

export interface AcademicClass {
  id: string;
  code: string;
  nom?: string | null;
  libelle: string;
  filiere_id: string;
  niveau_id: string;
  cycle_id?: string | null;
  actif: boolean;
  created_at: string;
  updated_at: string;
  filiere?: Filiere | null;
  niveau?: AcademicLevel | null;
  cycle?: AcademicCycle | null;
}

export interface AcademicCycleInput {
  code: string;
  nom: string;
  description?: string | null;
  ordre: number;
  actif: boolean;
}

export interface AcademicLevelInput {
  code: string;
  nom: string;
  cycle_id: string;
  description?: string | null;
  ordre: number;
  actif: boolean;
}

export interface AcademicClassInput {
  nom: string;
  filiere_id: string;
  niveau_id: string;
  actif: boolean;
}

export interface AcademicTemplateResult {
  cycles: AcademicCycle[];
  niveaux: AcademicLevel[];
  cycles_crees: number;
  niveaux_crees: number;
  total_cycles: number;
  total_niveaux: number;
  created: boolean;
  idempotent: boolean;
}

export interface Enrollment {
  id: string;
  etudiant_id: string;
  classe_id: string;
  session_id: string;
  statut: string;
  actif: boolean;
  date_inscription: string;
  created_at: string;
  updated_at: string;
  classe?: AcademicClass | null;
}

/**
 * Les trois etats d'une unite d'enseignement.
 *
 * La liste est **fermee** et le serveur la refuse hors de ces trois valeurs :
 * une quatrième reponse n'existerait pas, elle signifierait que le jury n'a pas
 * tranche. Ecrire autre chose laisserait un bulletin affichant un verdict que
 * personne n'a prononce.
 */
export type ValidationUE = "Validée" | "Validée en SR" | "À reprendre";

export const VALIDATIONS_UE: ValidationUE[] = [
  "Validée",
  "Validée en SR",
  "À reprendre",
];

/** Ce que le moteur a calcule, avant que le jury tranche. */
export interface MoyenneUEProposee {
  ue: string;
  code: string;
  ects: number;
  nb_notes: number;
  moyenne: number;
  validee?: boolean;
  validee_sur_merite?: boolean;
  validee_par_compensation?: boolean;
  eliminatoire?: boolean;
  proposition_validation?: ValidationUE;
  proposition_credits?: number;
  proposition_mention?: string | null;
  /** Ce que le jury a reellement decide. Absent tant qu'il n'a pas tranche. */
  validation?: ValidationUE;
  credits_obtenus?: number;
  mention?: string | null;
  motif_ecart?: string | null;
}

export interface BulletinMatiere {
  code: string;
  nom: string;
  /** Moyenne controlee, ou `null` si aucune note de type CC. */
  mcc: number | null;
  /** Moyenne d'examen, ou `null` si aucune. */
  exam: number | null;
  cec: number;
  mec: number | null;
}

export interface BulletinUnite {
  code: string;
  nom: string;
  cue: number;
  /** L'enseignement est annuel : il figure sur chaque semestre. */
  annuelle: boolean;
  mue: number | null;
  mention: string | null;
  /** Ce que le jury a decide. `null` tant qu'il n'a pas tranche. */
  validation: ValidationUE | null;
  /** Ce que le moteur avait propose. Ce n'est **pas** une decision. */
  proposition_validation?: ValidationUE | null;
  credits_obtenus: number | null;
  matieres: BulletinMatiere[];
}

export interface Bulletin {
  etudiant: {
    nom: string;
    prenom: string;
    matricule: string | null;
    filiere: string | null;
    niveau: string | null;
    classe: string | null;
  };
  etablissement: {
    nom: string;
    sigle: string | null;
    adresse: string | null;
    pays: string | null;
  };
  session: {
    nom: string | null;
    annee_academique: string | null;
    semestre_numero: number;
    semestre_libelle: string;
  };
  unites: BulletinUnite[];
  totaux: {
    credits_prevus: number;
    credits_obtenus: number;
    moyenne: number | null;
    mention: string | null;
  };
  recapitulatif: {
    lignes: Array<{ libelle: string; credits: number | null; moyenne: number | null }>;
    moyenne_annuelle: number | null;
    mention_annuelle: string | null;
  };
  observations: {
    incompletudes: Array<{
      unite: string;
      matiere: string;
      code: string;
      manque: string;
    }>;
    annuelles_absentes: Array<{
      ue_id: string;
      unite: string;
      code: string;
      raison: string;
    }>;
    hors_bulletin: Array<{ matiere?: string; code?: string; raison?: string }>;
    /** Aucune seance de jury : le bulletin ne porte aucune decision. */
    deliberation_absente: boolean;
  };
}

export type RattrapageEtat = "aucune_seance" | "rien_a_reprendre" | "a_reprendre";

export interface RattrapageEtudiant {
  etudiant_id: string;
  matricule: string;
  nom: string;
  prenom: string;
  etat: RattrapageEtat;
  /** Pourquoi l'etat est ce qu'il est. `null` quand il y a une liste. */
  message: string | null;
  unites: Array<{
    ue_id: string;
    ue_code: string;
    ue_nom: string;
    credits_ue: number;
    matieres: Array<{
      matiere_id: string;
      matiere_code: string;
      matiere_nom: string;
      coefficient: number;
    }>;
  }>;
  total_matieres: number;
}

export interface Semestre {
  id: string;
  session_id: string;
  numero: number;
  libelle: string;
  date_debut: string | null;
  date_fin: string | null;
  actif: boolean;
  /** UE rattachees a ce semestre. */
  nb_unites: number;
  /** Etudiants inscrits sur la session entiere, pas sur ce seul semestre. */
  nb_etudiants: number;
}

export interface SemestreRepartition {
  session_id: string;
  session_nom: string;
  semestres: Semestre[];
  /**
   * UE sans rattachement. C'est ce compte qui dit a l'agent qu'une matiere
   * sortira du bulletin : il est annonce, pas laisse disparaitre.
   */
  unites_sans_semestre: number;
}

export interface TeachingUnit {
  id: string;
  code: string;
  nom: string;
  filiere_id: string;
  filiere?: Filiere;
  credits: number;
  coefficient: number;
  heures: number;
  /** Libelle d'affichage, choisi par l'institut. */
  semestre: string;
  /** Rattachement structurel. Nullable : une UE creee avant la gestion des
   *  semestre, ou un enseignement annuel, n'en a pas. */
  semestre_id?: string | null;
  /**
   * `semestrielle` (defaut) ou `annuelle`.
   *
   * Un enseignement annuel se retrouve sur **tous** les semestres de la session
   * et se donne sur chacun : il n'a donc pas de semestre unique, et il n'en
   * porte pas d'etiquette.
   */
  regime?: "semestrielle" | "annuelle";
  niveau: string;
  responsable?: string | null;
  matieres?: Matiere[];
}

export interface Matiere {
  id: string;
  code: string;
  nom: string;
  credits: number;
  coefficient: number;
  heures_cm: number;
  heures_td: number;
  heures_tp: number;
  ue_id?: string | null;
  ue?: TeachingUnit | null;
  enseignant_nom?: string | null;
  description?: string | null;
}

export interface FeeGrid {
  id: string;
  filiere_id: string | null;
  filiere: string;
  niveau: string;
  droits_inscription: number;
  scolarite_mensuelle: number;
  nombre_mois: number;
  total_annuel: number;
  actif: boolean;
}

export interface BalanceItem {
  etudiant_id: string;
  matricule: string;
  nom_complet: string;
  filiere: string;
  montant_total_du: number;
  non_echu: number;
  retard_1_30_jours: number;
  retard_31_60_jours: number;
  retard_plus_60_jours: number;
}

export interface BalanceResponse {
  date_calcul: string;
  total_creances: number;
  items: BalanceItem[];
}

export interface Receipt {
  id: string;
  numero_recu: string;
  paiement_id: string;
  date_emission: string;
  donnees_json: Record<string, unknown>;
  created_at: string;
}

export interface Payment {
  id: string;
  etudiant_id: string;
  session_id: string;
  facture_id?: string | null;
  periode_id?: string | null;
  montant: number;
  date_paiement: string;
  mode_paiement: string;
  reference: string;
  statut: string;
  etudiant?: Student;
  session?: AcademicSession;
  facture?: Invoice;
  encaisse_par_id?: number | null;
}

export interface Invoice {
  id: string;
  numero_facture: string;
  etudiant_id: string;
  session_id: string;
  montant_total: number;
  montant_paye: number;
  reste_a_payer: number;
  date_emission: string;
  date_echeance: string;
  statut: string;
  description?: string | null;
  etudiant?: Student;
  session?: AcademicSession;
  paiements?: Payment[];
}

export interface PaiementIntention {
  id: string;
  facture_id?: string | null;
  etudiant_id: string;
  etudiant_nom?: string | null;
  montant: number;
  provider: string;
  statut: string;
  expires_le: string;
  paiement_id?: string | null;
  created_at: string;
}

export interface PaiementIntentionCreee extends PaiementIntention {
  facture_id: string | null;
  session_id: string;
  /** L'URL relative du lien — le jeton ne repassera jamais par l'API. */
  lien: string;
  token: string;
}

export interface ResumeFamille {
  etablissement: string | null;
  devise: string;
  etudiant: string | null;
  matricule: string | null;
  facture: {
    numero: string | null;
    montant_total: number | null;
    montant_paye: number | null;
    reste_a_payer: number | null;
  } | null;
  montant_demande: number;
  provider: string;
  expire_le: string;
}

export interface ConfirmationPaiement {
  paiement_id: string;
  numero_recu: string;
  montant: number;
  mode_paiement: string;
}

export interface Note {
  id: string;
  etudiant_id: string;
  matiere_id: string;
  examen_id?: string | null;
  session_id?: string | null;
  valeur: number;
  coefficient: number;
  appreciation?: string | null;
  statut: string;
  matiere_nom?: string | null;
}

export interface Absence {
  id: string;
  etudiant_id: string;
  cours_id?: string | null;
  matiere_id?: string | null;
  date_absence: string;
  duree_heures: number;
  justifiee: boolean;
  motif?: string | null;
}

export interface Course {
  id: string;
  matiere_id: string;
  enseignant_id?: number | null;
  enseignant_nom?: string | null;
  salle: string;
  jour_semaine: string;
  heure_debut: string;
  heure_fin: string;
  type_cours: string;
}

export interface Salle {
  id: string;
  nom: string;
  code: string;
  campus_id?: string | null;
  batiment?: string | null;
  etage?: string | null;
  capacite?: number | null;
  type_salle: string;
  equipements?: string | null;
  disponible: boolean;
  created_at: string;
  updated_at: string;
}

export interface ConflitEdt {
  type: string;
  cours_id: string;
  matiere?: string | null;
  enseignant_nom?: string | null;
  salle?: string | null;
  jour: string;
  heure_debut: string;
  heure_fin: string;
}

export interface StudentPortalData {
  etudiant: Student;
  notes: Note[];
  absences: Absence[];
  factures: Invoice[];
  cours: Course[];
  matieres: Matiere[];
  sessions: AcademicSession[];
  devise?: string | null;
}

export interface TeacherPortalData {
  cours: Course[];
  matieres: Matiere[];
  notes: Note[];
  etudiants: Student[];
}

export type CandidatureStatus =
  | "nouvelle"
  | "en_verification"
  | "complete"
  | "acceptee"
  | "refusee"
  | "liste_attente"
  | "converti"
  | "annulee";

export type AdmissionDocumentStatus = "requise" | "recue" | "validee" | "rejetee";
export type AdmissionDecisionType = "acceptee" | "refusee" | "liste_attente";

export interface AdmissionDocument {
  id: string;
  candidature_id: string;
  type: string;
  nom_fichier?: string | null;
  fichier_disponible?: boolean;
  statut: AdmissionDocumentStatus;
  date_depot?: string | null;
  commentaire?: string | null;
  valide_par_id?: number | null;
  date_validation?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdmissionDecision {
  id: string;
  candidature_id: string;
  decision: AdmissionDecisionType;
  motif?: string | null;
  decisionnaire_id: number;
  date_decision: string;
  created_at: string;
  updated_at: string;
}

export interface CandidaturePage {
  items: Candidature[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  counts: Partial<Record<CandidatureStatus, number>>;
}

export interface AdmissionViewFilters {
  search?: string;
  statut?: CandidatureStatus;
  filiere_id?: string;
  session_id?: string;
}

export interface AdmissionView {
  id: string;
  nom: string;
  filtres: AdmissionViewFilters;
  created_at: string;
  updated_at: string;
}

export type BulkAdmissionAction = "mettre_en_verification" | "marquer_complete" | "annuler";

export interface Candidature {
  id: string;
  reference: string;
  nom: string;
  prenom: string;
  sexe?: string | null;
  date_naissance?: string | null;
  email: string;
  telephone?: string | null;
  adresse?: string | null;
  filiere_id: string;
  niveau_id?: string | null;
  classe_id?: string | null;
  niveau: string;
  session_id?: string | null;
  statut: CandidatureStatus;
  date_demande: string;
  notes?: string | null;
  source?: string | null;
  created_by_id?: number | null;
  etudiant_id?: string | null;
  created_at: string;
  updated_at: string;
  filiere?: Filiere | null;
  session?: AcademicSession | null;
  pieces: AdmissionDocument[];
  decisions: AdmissionDecision[];
}

export interface CandidatureCreatePayload {
  nom: string;
  prenom: string;
  sexe?: string;
  date_naissance?: string;
  email: string;
  telephone?: string;
  adresse?: string;
  filiere_id: string;
  niveau_id?: string;
  classe_id?: string;
  niveau: string;
  session_id?: string;
  notes?: string;
  source?: string;
}

export interface CandidatureUpdatePayload {
  nom?: string;
  prenom?: string;
  sexe?: string | null;
  date_naissance?: string | null;
  email?: string;
  telephone?: string | null;
  adresse?: string | null;
  filiere_id?: string;
  niveau_id?: string | null;
  classe_id?: string | null;
  niveau?: string;
  session_id?: string | null;
  notes?: string | null;
  source?: string | null;
}

/* -------------------------------------------------------------------------- */
/* Configuration institutionnelle                                             */
/* -------------------------------------------------------------------------- */

/**
 * Identite imprimable de l'etablissement, dans sa version en vigueur.
 *
 * `logo_present` distingue la configuration du disque : un logo enregistre
 * dont le fichier a disparu est signale `false`, pour ne pas laisser croire
 * a un branding actif.
 */
export interface InstitutionConfig {
  version: number;
  nom: string;
  sigle: string;
  adresse: string | null;
  telephone: string | null;
  email: string;
  pays: string | null;
  devise: string;
  annee_academique_active: string | null;
  logo_present: boolean;
}

/** Champs modifiables. Tous facultatifs : seuls ceux envoyes sont touches. */
export interface InstitutionConfigPayload {
  nom?: string;
  sigle?: string;
  adresse?: string | null;
  telephone?: string | null;
  email?: string;
  pays?: string | null;
  devise?: string;
}

/** Valeur d'un champ avant/apres une modification. */
export interface ChampModifie {
  avant: string | null;
  apres: string | null;
}

/**
 * Reponse a une ecriture.
 *
 * `modifications` vide signifie « rien n'a change » : aucune version n'a ete
 * creee. C'est un resultat normal, pas un echec.
 */
export interface InstitutionConfigModifiee {
  configuration: InstitutionConfig;
  version: number;
  modifications: Record<string, ChampModifie>;
}

/** Entree de l'historique des versions de la configuration. */
export interface ConfigurationVersion {
  version: number;
  nature: "etablissement" | "branding" | string;
  modifications: Record<string, ChampModifie>;
  logo_present: boolean;
  modifie_par_email: string | null;
  created_at: string;
  instantane: Record<string, unknown>;
}

/* -------------------------------------------------------------------------- */
/* Deliberation et jury                                                       */
/* -------------------------------------------------------------------------- */

/**
 * Regles de deliberation en vigueur.
 *
 * `confirmee` distingue le reglement de l'institut d'une valeur de depart
 * reprise du moteur : une seance de jury ne devrait pas s'appuyer sur des
 * regles que personne n'a validees.
 */
export interface ReglesDeliberation {
  seuil_validation_moyenne: number;
  seuil_eliminatoire: number;
  seuil_rattrapage_minimale: number;
  seuil_passage_conditionnel_ects: number;
  compensation_autorisee: boolean;
  bareme_mentions: { libelle: string; seuil_min: number }[];
  confirmee: boolean;
  confirme_par: string | null;
  confirme_le: string | null;
}

export interface MembreJury {
  nom: string;
  qualite?: string | null;
}

/** Une seance de jury, et son etat. */
export interface Deliberation {
  id: string;
  classe_id: string;
  classe_nom: string | null;
  session_id: string;
  session_nom: string | null;
  date_deliberation: string;
  lieu: string | null;
  president: string;
  membres: MembreJury[];
  statut: "brouillon" | "close";
  regles: Record<string, unknown>;
  close_le: string | null;
  created_at: string | null;
  nb_inscrits: number;
  nb_decisions: number;
}

/**
 * Ce que le moteur propose pour un etudiant.
 *
 * Ce n'est **pas** une decision : `decision_statut` reste null tant que le
 * jury n'a rien consigne. L'ecart entre les deux est ce que le jury doit
 * motiver.
 */
export interface PropositionEtudiant {
  etudiant_id: string;
  matricule: string;
  nom: string;
  prenom: string;
  filiere: string | null;
  moyenne_generale: number;
  ects_acquis: number;
  ects_total: number;
  proposition_statut: string;
  proposition_mention: string | null;
  moyennes_ue: Record<string, { ue: string; code: string; ects: number; moyenne: number }>;
  notes_eliminatoires: { matiere: string; note: number }[];
  avertissements: string[];
  decision_statut: string | null;
  decision_mention: string | null;
  motif_ecart: string | null;
  ecart: boolean;
}

export interface DecisionDeliberation {
  etudiant_id: string;
  matricule: string | null;
  nom: string | null;
  prenom: string | null;
  proposition_statut: string;
  proposition_mention: string | null;
  statut: string;
  mention: string | null;
  motif_ecart: string | null;
  ecart: boolean;
  moyenne_generale: number;
  ects_acquis: number;
  ects_total: number;
  decide_le: string | null;
}

export interface DeliberationDetail extends Deliberation {
  propositions: PropositionEtudiant[];
  decisions: DecisionDeliberation[];
  avertissements: string[];
}

/* -------------------------------------------------------------------------- */
/* Relances de facturation                                                    */
/* -------------------------------------------------------------------------- */

/** Une facture echue non soldee, au moment de la lecture. */
export interface CreanceEtudiant {
  facture_id: string;
  numero: string;
  date_echeance: string;
  description: string | null;
  montant_total: number;
  montant_regle: number;
  reste: number;
  retard_jours: number;
}

/** La derniere relance connue, pour eviter de relancer deux fois de suite. */
export interface RelanceAnterieure {
  niveau: number;
  date_relance: string;
  moyen: string;
  montant_reclame: number;
}

/** Un etudiant dont la dette merite un suivi. */
export interface EtudiantARelancer {
  etudiant_id: string;
  matricule: string;
  nom: string;
  prenom: string;
  filiere: string | null;
  telephone: string | null;
  email: string | null;
  creances: CreanceEtudiant[];
  nb_creances: number;
  total_du: number;
  retard_jours: number;
  anciennete_jours: number;
  /** Numero de la prochaine relance si elle est faite aujourd'hui. */
  niveau_suivant: number;
  nb_relances: number;
  derniere_relance: RelanceAnterieure | null;
  jours_depuis_derniere: number | null;
}

/**
 * Vue d'ensemble des creances a suivre.
 *
 * Les paliers reprennent ceux de la balance agee : les deux vues doivent
 * concorder, et le backend le verifie.
 */
export interface SyntheseRelances {
  date_calcul: string;
  devise: string;
  nb_etudiants: number;
  nb_creances: number;
  total_du: number;
  retard_1_30: number;
  retard_31_60: number;
  retard_plus_60: number;
  items: EtudiantARelancer[];
}

/**
 * Une relance consignee, avec l'instantane de ce qui etait reclame.
 *
 * `solde_apres` reste `null` tant qu'aucun encaissement n'a suivi : une
 * relance efficace n'est pas un solde sur du papier. C'est ce qui distingue
 * « on a relance » de « la relance a marche ».
 */
export interface Relance {
  id: string;
  etudiant_id: string;
  matricule: string | null;
  nom: string | null;
  prenom: string | null;
  session_id: string | null;
  niveau: number;
  date_relance: string;
  moyen: string;
  montant_reclame: number;
  retard_jours: number;
  message: string | null;
  solde_apres: number | null;
  relance_par_email: string | null;
  created_at: string | null;
  nb_factures: number;
  factures_concernees: Record<string, unknown>[];
  email_statut?: string | null;
  email_envoye_le?: string | null;
  resolue: boolean;
}

/* -------------------------------------------------------------------------- */
/* Nomenclature de matricule                                                    */
/* -------------------------------------------------------------------------- */

/** Regle de fabrication des matricules, propre a l'etablissement. */
export interface MatriculeParametres {
  modele: string;
  largeur_numero: number;
  demarrage: number;
  /** Format historique, pour signaler ce qui a change. */
  modele_depart: string;
  /** Exemple produit par le serveur : c'est lui qui fait foi. */
  exemple: string;
  personnalisee: boolean;
  configuree: boolean;
  maj_par_email: string | null;
  maj_le: string | null;
}

/** Un jeton accepte dans le modele. */
export interface JetonMatricule {
  jeton: string;
  libelle: string;
  exemple: string;
}

export interface MatriculeParametresMaj {
  modele: string;
  largeur_numero: number;
  demarrage: number;
}

/* -------------------------------------------------------------------------- */
/* Import de notes                                                             */
/* -------------------------------------------------------------------------- */

/** Une colonne du tableur, interpretee comme evaluation. */
export interface ColonneEvaluation {
  nom: string;
  /** Position dans le fichier, telle que l'agent la voit. */
  colonne: number;
  coefficient: number;
  /** `CC` ou `Examen Final` : ce que le serveur en fera. */
  type: string;
  /** false si l'evaluation existe deja pour cette matiere et cette session. */
  nouvelle: boolean;
}

export interface LigneRapportNotes {
  numero: number;
  matricule: string | null;
  nom_complet: string;
  etudiant_id: string | null;
  /**
   * Notes lues, indexees par evaluation normalisee. Une valeur absente
   * signifie « non evalue » — ce qui n'est pas un zero.
   */
  notes: Record<string, number | null>;
  a_creer: number;
  a_modifier: number;
  erreurs: string[];
  /** Ligne vide du tableur, ou entierement sans note. */
  ignoree: boolean;
}

export interface RapportImportNotes {
  evaluations: ColonneEvaluation[];
  lignes: LigneRapportNotes[];
  classe: { id: string; nom: string; code: string | null } | null;
  matiere: { id: string; nom: string; code: string } | null;
  session: { id: string; nom: string } | null;
  resume: Record<string, number>;
  /** false si aucune note ne peut etre enregistree. */
  importable: boolean;
}

export interface BilanImportNotes {
  evaluations: number;
  lignes: number;
  total_notes: number;
  notes_creees: number;
  notes_modifiees: number;
  lignes_en_erreur: number;
  total_erreurs: number;
  creees: number;
  modifiees: number;
  lignes_ignorees: number;
}

/** Description du format attendu, servie par le backend. */
export interface ModeleImportNotes {
  colonnes_identite: Record<string, string>;
  colonnes_evaluation: string;
  exemple_entetes: string[];
  regles: string[];
  fichiers_acceptes: string;
}
