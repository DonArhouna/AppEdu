import React, { createContext, useContext, useState, useEffect } from "react";

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
    colorClass: "bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-500/30",
    description: "Gestion académique, maquettes de cours, filières et plannings",
  },
  {
    id: "SECRETARIAT",
    label: "Secrétariat de Scolarité",
    badge: "Admissions",
    colorClass: "bg-sky-500/15 text-sky-600 dark:text-sky-400 border-sky-500/30",
    description: "Traitement des pré-inscriptions, validation des dossiers et registre étudiants",
  },
  {
    id: "ENSEIGNANT",
    label: "Enseignant / Professeur",
    badge: "Professeur",
    colorClass: "bg-purple-500/15 text-purple-600 dark:text-purple-400 border-purple-500/30",
    description: "Accès portail enseignant, saisie des notes et suivi des absences",
  },
  {
    id: "COMPTABILITE",
    label: "Comptabilité & Trésorerie",
    badge: "Finance",
    colorClass: "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30",
    description: "Encaissements, facturation, grille des frais et bilans de trésorerie",
  },
  {
    id: "ETUDIANT",
    label: "Étudiant (Self-Service)",
    badge: "Étudiant",
    colorClass: "bg-teal-500/15 text-teal-600 dark:text-teal-400 border-teal-500/30",
    description: "Consultation des notes, emploi du temps, reçu de paiement et messagerie",
  },
];

interface RBACContextType {
  currentRole: UserRole;
  setCurrentRole: (role: UserRole) => void;
  currentRoleInfo: RoleInfo;
  hasAccess: (allowedRoles?: UserRole[]) => boolean;
}

const RBACContext = createContext<RBACContextType | undefined>(undefined);

const STORAGE_KEY = "edumanage_active_role";

export const RBACProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentRole, setCurrentRoleState] = useState<UserRole>(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem(STORAGE_KEY) as UserRole | null;
      if (stored && AVAILABLE_ROLES.some((r) => r.id === stored)) {
        return stored;
      }
    }
    return "ADMIN";
  });

  const setCurrentRole = (role: UserRole) => {
    setCurrentRoleState(role);
    localStorage.setItem(STORAGE_KEY, role);
  };

  const currentRoleInfo =
    AVAILABLE_ROLES.find((r) => r.id === currentRole) || AVAILABLE_ROLES[0];

  const hasAccess = (allowedRoles?: UserRole[]): boolean => {
    if (!allowedRoles || allowedRoles.length === 0) return true;
    // ADMIN has universal access
    if (currentRole === "ADMIN") return true;
    return allowedRoles.includes(currentRole);
  };

  return (
    <RBACContext.Provider
      value={{
        currentRole,
        setCurrentRole,
        currentRoleInfo,
        hasAccess,
      }}
    >
      {children}
    </RBACContext.Provider>
  );
};

export const useRBAC = (): RBACContextType => {
  const context = useContext(RBACContext);
  if (!context) {
    throw new Error("useRBAC must be used within an RBACProvider");
  }
  return context;
};
