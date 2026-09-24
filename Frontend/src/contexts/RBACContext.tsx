import React, {
  createContext,
  useCallback,
  useContext,
  useMemo,
} from "react";
import { useAuth } from "@/contexts/AuthContext";

export type UserRole =
  | "ADMIN"
  | "DIRECTEUR_ETUDES"
  | "ENSEIGNANT"
  | "SECRETARIAT"
  | "COMPTABILITE"
  | "ETUDIANT";

export interface RoleInfo {
  id: UserRole;
  label: string;
  badge: string;
  colorClass: string;
  description: string;
}

export const AVAILABLE_ROLES: RoleInfo[] = [
  {
    id: "ADMIN",
    label: "Administrateur Système",
    badge: "SuperAdmin",
    colorClass: "bg-destructive/15 text-destructive border-destructive/30",
    description: "Accès intégral à l'ensemble des modules, sécurité et paramètres",
  },
  {
    id: "DIRECTEUR_ETUDES",
    label: "Directeur des Études",
    badge: "Pédagogie",
    colorClass: "bg-blue-500/15 text-blue-500 border-blue-500/30",
    description: "Gestion académique, maquettes de cours, filières et plannings",
  },
  {
    id: "SECRETARIAT",
    label: "Secrétariat de Scolarité",
    badge: "Admissions",
    colorClass: "bg-sky-500/15 text-sky-500 border-sky-500/30",
    description: "Traitement des pré-inscriptions, validation des dossiers et registre étudiants",
  },
  {
    id: "ENSEIGNANT",
    label: "Enseignant / Professeur",
    badge: "Professeur",
    colorClass: "bg-purple-500/15 text-purple-500 border-purple-500/30",
    description: "Accès portail enseignant, saisie des notes et suivi des absences",
  },
  {
    id: "COMPTABILITE",
    label: "Comptabilité & Trésorerie",
    badge: "Finance",
    colorClass: "bg-amber-500/15 text-amber-500 border-amber-500/30",
    description: "Encaissements, facturation, grille des frais et bilans de trésorerie",
  },
  {
    id: "ETUDIANT",
    label: "Étudiant (Self-Service)",
    badge: "Étudiant",
    colorClass: "bg-teal-500/15 text-teal-500 border-teal-500/30",
    description: "Consultation des notes, emploi du temps, reçu de paiement et messagerie",
  },
];

interface RBACContextValue {
  currentRole: UserRole;
  currentRoleInfo: RoleInfo;
  hasAccess: (allowedRoles?: UserRole[]) => boolean;
}

const RBACContext = createContext<RBACContextValue | undefined>(undefined);

export const RBACProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const currentRole = user?.role ?? "ETUDIANT";
  const currentRoleInfo =
    AVAILABLE_ROLES.find((role) => role.id === currentRole) || AVAILABLE_ROLES[0];

  const hasAccess = useCallback(
    (allowedRoles?: UserRole[]): boolean => {
      if (!allowedRoles || allowedRoles.length === 0) return true;
      if (currentRole === "ADMIN") return true;
      return allowedRoles.includes(currentRole);
    },
    [currentRole]
  );

  const value = useMemo(
    () => ({ currentRole, currentRoleInfo, hasAccess }),
    [currentRole, currentRoleInfo, hasAccess]
  );

  return <RBACContext.Provider value={value}>{children}</RBACContext.Provider>;
};

export const useRBAC = (): RBACContextValue => {
  const context = useContext(RBACContext);
  if (!context) {
    throw new Error("useRBAC doit être utilisé dans RBACProvider.");
  }
  return context;
};
