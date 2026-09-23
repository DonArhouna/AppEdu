/**
 * Service de gestion des Sessions Académiques et de leurs Périodes de Paiement
 * Gère la persistance, le rattachement étudiant <-> session et les règles de calcul dynamiques.
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

export interface StudentSessionProfile {
  id?: string;
  matricule: string;
  nom: string;
  prenom: string;
  email?: string;
  filiere: string;
  niveau: string;
  sessionId: string; // Rattachement direct à la session
  statut?: string;
  historiquePaiements?: Array<{
    numRecu: string;
    datePaiement: string;
    sessionId: string;
    periodes: string[];
    montant: number;
  }>;
}

const STORAGE_KEY_SESSIONS = "emp_academic_sessions_v1";
const STORAGE_KEY_STUDENTS = "emp_students_registry_v1";

export const DEFAULT_SESSIONS: AcademicSession[] = [
  {
    id: "SES-2025-MAIN",
    nom: "Session Principale 2025-2026",
    code: "SES-25-26-MAIN",
    anneeAcademique: "2025-2026",
    dateDebut: "2025-09-01",
    dateFin: "2026-06-30",
    statut: "active",
    description: "Session annuelle standard (Rentrée Septembre) avec calendrier financier en 3 tranches.",
    periodes: [
      {
        id: "per-main-1",
        nom: "Tranche 1 (Octobre)",
        mois: "Octobre",
        dateEcheance: "2025-10-15",
        montantEstime: 60000,
        pourcentage: 40,
        ordre: 1,
      },
      {
        id: "per-main-2",
        nom: "Tranche 2 (Janvier)",
        mois: "Janvier",
        dateEcheance: "2026-01-15",
        montantEstime: 60000,
        pourcentage: 30,
        ordre: 2,
      },
      {
        id: "per-main-3",
        nom: "Tranche 3 (Avril)",
        mois: "Avril",
        dateEcheance: "2026-04-15",
        montantEstime: 60000,
        pourcentage: 30,
        ordre: 3,
      },
    ],
  },
  {
    id: "SES-2026-DECALEE",
    nom: "Session Décalée Janvier 2026",
    code: "SES-26-DEC",
    anneeAcademique: "2025-2026",
    dateDebut: "2026-01-15",
    dateFin: "2026-10-31",
    statut: "active",
    description: "Session semestrielle décalée (Rentrée Janvier) avec calendrier en 4 tranches bimestrielles.",
    periodes: [
      {
        id: "per-dec-1",
        nom: "Tranche 1 (Février)",
        mois: "Février",
        dateEcheance: "2026-02-15",
        montantEstime: 65000,
        pourcentage: 30,
        ordre: 1,
      },
      {
        id: "per-dec-2",
        nom: "Tranche 2 (Avril)",
        mois: "Avril",
        dateEcheance: "2026-04-15",
        montantEstime: 65000,
        pourcentage: 25,
        ordre: 2,
      },
      {
        id: "per-dec-3",
        nom: "Tranche 3 (Juin)",
        mois: "Juin",
        dateEcheance: "2026-06-15",
        montantEstime: 65000,
        pourcentage: 25,
        ordre: 3,
      },
      {
        id: "per-dec-4",
        nom: "Tranche 4 (Août)",
        mois: "Août",
        dateEcheance: "2026-08-15",
        montantEstime: 65000,
        pourcentage: 20,
        ordre: 4,
      },
    ],
  },
  {
    id: "SES-2026-PRINTEMPS",
    nom: "Session Executive & Continue Mars 2026",
    code: "SES-26-EXEC",
    anneeAcademique: "2025-2026",
    dateDebut: "2026-03-01",
    dateFin: "2026-11-30",
    statut: "planifiee",
    description: "Programme de formation continue professionnelle articulé en 2 semestres.",
    periodes: [
      {
        id: "per-exec-1",
        nom: "Semestre 1 (Mars)",
        mois: "Mars",
        dateEcheance: "2026-03-20",
        montantEstime: 120000,
        pourcentage: 50,
        ordre: 1,
      },
      {
        id: "per-exec-2",
        nom: "Semestre 2 (Juillet)",
        mois: "Juillet",
        dateEcheance: "2026-07-20",
        montantEstime: 120000,
        pourcentage: 50,
        ordre: 2,
      },
    ],
  },
];

export const DEFAULT_STUDENTS: StudentSessionProfile[] = [
  {
    id: "ETU001",
    matricule: "2025-INF-0042",
    nom: "Dupont",
    prenom: "Marie",
    email: "marie.dupont@email.com",
    filiere: "Génie Informatique",
    niveau: "Licence 3",
    sessionId: "SES-2025-MAIN",
    statut: "actif",
    historiquePaiements: [
      {
        numRecu: "REC-849201",
        datePaiement: "2026-01-20",
        sessionId: "SES-2025-MAIN",
        periodes: ["Tranche 1 (Octobre)"],
        montant: 280000,
      },
    ],
  },
  {
    id: "ETU002",
    matricule: "2025-GES-0108",
    nom: "Konan",
    prenom: "Kouassi Jean",
    email: "k.konan@email.com",
    filiere: "Gestion & Finance",
    niveau: "Master 1",
    sessionId: "SES-2026-DECALEE",
    statut: "actif",
    historiquePaiements: [
      {
        numRecu: "REC-910234",
        datePaiement: "2026-01-22",
        sessionId: "SES-2026-DECALEE",
        periodes: ["Droits d'Inscription"],
        montant: 200000,
      },
    ],
  },
  {
    id: "ETU003",
    matricule: "2025-COM-0019",
    nom: "Sarr",
    prenom: "Awa",
    email: "awa.sarr@email.com",
    filiere: "Commerce & Marketing",
    niveau: "Licence 2",
    sessionId: "SES-2025-MAIN",
    statut: "suspendu",
  },
  {
    id: "ETU004",
    matricule: "2025-INF-0201",
    nom: "Dubois",
    prenom: "Pierre",
    email: "pierre.dubois@email.com",
    filiere: "Génie Informatique",
    niveau: "Master 2",
    sessionId: "", // Cas limite : Étudiant sans session rattachée
    statut: "actif",
  },
];

// Helper to notify listeners of changes across tabs/components
function emitChange() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event("emp_sessions_changed"));
  }
}

/* ─────────────────────────────────────────────────────────────────── */
/* SESSIONS CRUD                                                       */
/* ─────────────────────────────────────────────────────────────────── */

export function getAcademicSessions(): AcademicSession[] {
  if (typeof window === "undefined") return DEFAULT_SESSIONS;
  try {
    const raw = localStorage.getItem(STORAGE_KEY_SESSIONS);
    if (!raw) {
      localStorage.setItem(STORAGE_KEY_SESSIONS, JSON.stringify(DEFAULT_SESSIONS));
      return DEFAULT_SESSIONS;
    }
    return JSON.parse(raw);
  } catch {
    return DEFAULT_SESSIONS;
  }
}

export function getAcademicSessionById(id: string): AcademicSession | undefined {
  const sessions = getAcademicSessions();
  return sessions.find((s) => s.id === id);
}

export function saveAcademicSession(session: AcademicSession): void {
  const sessions = getAcademicSessions();
  const index = sessions.findIndex((s) => s.id === session.id);
  let updated: AcademicSession[];
  if (index >= 0) {
    updated = [...sessions];
    updated[index] = session;
  } else {
    updated = [session, ...sessions];
  }
  localStorage.setItem(STORAGE_KEY_SESSIONS, JSON.stringify(updated));
  emitChange();
}

export function deleteAcademicSession(id: string): boolean {
  const sessions = getAcademicSessions();
  const filtered = sessions.filter((s) => s.id !== id);
  if (filtered.length === sessions.length) return false;
  localStorage.setItem(STORAGE_KEY_SESSIONS, JSON.stringify(filtered));
  emitChange();
  return true;
}

/* ─────────────────────────────────────────────────────────────────── */
/* STUDENTS & SESSIONS MAPPING                                         */
/* ─────────────────────────────────────────────────────────────────── */

export function getStudentsRegistry(): StudentSessionProfile[] {
  if (typeof window === "undefined") return DEFAULT_STUDENTS;
  try {
    const raw = localStorage.getItem(STORAGE_KEY_STUDENTS);
    if (!raw) {
      localStorage.setItem(STORAGE_KEY_STUDENTS, JSON.stringify(DEFAULT_STUDENTS));
      return DEFAULT_STUDENTS;
    }
    return JSON.parse(raw);
  } catch {
    return DEFAULT_STUDENTS;
  }
}

export function getStudentByMatricule(matricule: string): StudentSessionProfile | undefined {
  const students = getStudentsRegistry();
  return students.find((s) => s.matricule === matricule);
}

export function updateStudentSession(matricule: string, newSessionId: string): void {
  const students = getStudentsRegistry();
  const updated = students.map((stu) => {
    if (stu.matricule === matricule) {
      return { ...stu, sessionId: newSessionId };
    }
    return stu;
  });
  localStorage.setItem(STORAGE_KEY_STUDENTS, JSON.stringify(updated));
  emitChange();
}

export function saveStudentProfile(student: StudentSessionProfile): void {
  const students = getStudentsRegistry();
  const index = students.findIndex((s) => s.matricule === student.matricule || (s.id && s.id === student.id));
  let updated: StudentSessionProfile[];
  if (index >= 0) {
    updated = [...students];
    updated[index] = { ...updated[index], ...student };
  } else {
    updated = [student, ...students];
  }
  localStorage.setItem(STORAGE_KEY_STUDENTS, JSON.stringify(updated));
  emitChange();
}

export function recordPaymentForStudent(
  matricule: string,
  receipt: {
    numRecu: string;
    datePaiement: string;
    sessionId: string;
    periodes: string[];
    montant: number;
  }
): void {
  const students = getStudentsRegistry();
  const updated = students.map((stu) => {
    if (stu.matricule === matricule) {
      const existingHistory = stu.historiquePaiements || [];
      return {
        ...stu,
        historiquePaiements: [receipt, ...existingHistory],
      };
    }
    return stu;
  });
  localStorage.setItem(STORAGE_KEY_STUDENTS, JSON.stringify(updated));
  emitChange();
}

/**
 * Calcule dynamiquement la liste des périodes de paiement applicables à une session.
 */
export function getPeriodsForSession(sessionId?: string): PaymentPeriod[] {
  if (!sessionId) return [];
  const session = getAcademicSessionById(sessionId);
  return session ? session.periodes : [];
}

/**
 * Retourne le nombre d'étudiants rattachés à une session donnée.
 */
export function getStudentCountForSession(sessionId: string): number {
  const students = getStudentsRegistry();
  return students.filter((s) => s.sessionId === sessionId).length;
}
