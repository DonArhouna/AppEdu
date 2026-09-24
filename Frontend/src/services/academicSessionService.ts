/**
 * Types partagés pour les sessions académiques.
 *
 * La persistance et les données appartiennent désormais à l'API backend.
 * Ce fichier ne contient plus de données par défaut ni de stockage local.
 */

export interface PaymentPeriod {
  id: string;
  nom: string;
  mois: string;
  dateEcheance: string;
  montantEstime?: number;
  pourcentage?: number;
  ordre: number;
}

export interface AcademicSession {
  id: string;
  nom: string;
  code: string;
  anneeAcademique: string;
  dateDebut: string;
  dateFin: string;
  statut: "active" | "planifiee" | "cloturee";
  description?: string;
  periodes: PaymentPeriod[];
}
