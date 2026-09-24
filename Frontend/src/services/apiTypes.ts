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

export interface Student {
  id: string;
  matricule: string;
  nom: string;
  prenom: string;
  sexe?: string | null;
  email?: string | null;
  telephone?: string | null;
  filiere: string;
  filiere_id?: string | null;
  niveau: string;
  statut: string;
  session_id?: string | null;
  date_naissance?: string | null;
  adresse?: string | null;
  lieu_naissance?: string | null;
  credits_valides?: number | null;
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

export interface TeachingUnit {
  id: string;
  code: string;
  nom: string;
  filiere_id: string;
  filiere?: Filiere;
  credits: number;
  coefficient: number;
  heures: number;
  semestre: string;
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
  niveau?: string;
  session_id?: string | null;
  notes?: string | null;
  source?: string | null;
}
