/**
 * EduManagePro (EMP) — Client API Centralisé & Hybride
 * Gère la communication HTTP avec le backend FastAPI :
 * - Injection automatique du Bearer Token JWT
 * - Gestion gracieuse du mode hors-ligne / fallback local
 * - Adaptateurs typés pour tous les modules métier
 */

const API_BASE_URL =
  (import.meta as any).env?.VITE_API_URL || "http://localhost:8000/api/v1";

const AUTH_TOKEN_KEY = "emp_auth_token";
const USER_KEY = "emp_auth_user";

// ---------------------------------------------------------------------------
// Helpers HTTP de base
// ---------------------------------------------------------------------------
function getHeaders(): HeadersInit {
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

function extractErrorMessage(detail: any, fallback: string): string {
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (typeof item === "object" && item !== null) {
          const loc = Array.isArray(item.loc)
            ? item.loc.filter((p: any) => p !== "body").join(".")
            : "";
          const msg = item.msg || item.message || "Champ invalide";
          return loc ? `${loc}: ${msg}` : msg;
        }
        return String(item);
      })
      .join(" — ");
  }
  if (typeof detail === "object" && detail !== null) {
    return detail.message || detail.msg || detail.detail || fallback;
  }
  return String(detail);
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<{ data?: T; error?: string; status: number }> {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...getHeaders(),
        ...(options.headers || {}),
      },
    });

    const status = response.status;
    if (status === 204) {
      return { status };
    }

    const json = await response.json().catch(() => null);
    if (!response.ok) {
      const fallback = `Erreur serveur (${status})`;
      const rawError = json?.detail ?? json?.message ?? fallback;
      const errMsg = extractErrorMessage(rawError, fallback);
      return { error: errMsg, status };
    }

    return { data: json as T, status };
  } catch (err: any) {
    // Mode dégradé / serveur backend inaccessible
    return {
      error: String(err?.message || "Impossible de contacter le serveur backend EMP."),
      status: 0,
    };
  }
}

// ---------------------------------------------------------------------------
// 1. Authentification & Setup Wizard
// ---------------------------------------------------------------------------
export const authApi = {
  login: async (email: string, password: string) => {
    const res = await request<any>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    if (res.data?.access_token) {
      localStorage.setItem(AUTH_TOKEN_KEY, res.data.access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(res.data.user));
    }
    return res;
  },

  getMe: () => request<any>("/auth/me"),

  logout: () => {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },

  getToken: () => localStorage.getItem(AUTH_TOKEN_KEY),
  getCurrentUser: () => {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  },
};

export const setupApi = {
  getStatus: () => request<any>("/setup/status"),
  initialize: (payload: any) =>
    request<any>("/setup/initialize", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

// ---------------------------------------------------------------------------
// 2. Sessions Académiques & Périodes de Paiement
// ---------------------------------------------------------------------------
export const sessionsApi = {
  getAll: () => request<any[]>("/sessions/"),
  getActive: () => request<any>("/sessions/active"),
  getById: (id: string) => request<any>(`/sessions/${id}`),
  getPeriods: (sessionId: string) =>
    request<any[]>(`/sessions/${sessionId}/periodes`),
  create: (session: any) =>
    request<any>("/sessions/", {
      method: "POST",
      body: JSON.stringify(session),
    }),
};

// ---------------------------------------------------------------------------
// 3. Structure Académique (Campus, Dép., Filières, UEs, Matières)
// ---------------------------------------------------------------------------
export const structureApi = {
  // Campus
  getCampuses: () => request<any[]>("/structure/campuses"),
  createCampus: (data: any) =>
    request<any>("/structure/campuses", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateCampus: (id: string, data: any) =>
    request<any>(`/structure/campuses/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteCampus: (id: string) =>
    request<void>(`/structure/campuses/${id}`, { method: "DELETE" }),

  // Départements
  getDepartements: (campusId?: string) =>
    request<any[]>(
      `/structure/departements${campusId ? `?campus_id=${campusId}` : ""}`
    ),
  createDepartement: (data: any) =>
    request<any>("/structure/departements", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Filières
  getFilieres: (deptId?: string) =>
    request<any[]>(
      `/structure/filieres${deptId ? `?departement_id=${deptId}` : ""}`
    ),
  createFiliere: (data: any) =>
    request<any>("/structure/filieres", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // UEs
  getUEs: (filiereId?: string, semestre?: string) => {
    const params = new URLSearchParams();
    if (filiereId) params.append("filiere_id", filiereId);
    if (semestre) params.append("semestre", semestre);
    return request<any[]>(`/structure/ues?${params.toString()}`);
  },
  getUEById: (id: string) => request<any>(`/structure/ues/${id}`),
  createUE: (data: any) =>
    request<any>("/structure/ues", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateUE: (id: string, data: any) =>
    request<any>(`/structure/ues/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteUE: (id: string) =>
    request<void>(`/structure/ues/${id}`, { method: "DELETE" }),

  // Matières (ECUE)
  getMatieres: (ueId?: string) =>
    request<any[]>(`/structure/matieres${ueId ? `?ue_id=${ueId}` : ""}`),
  getMatiereById: (id: string) => request<any>(`/structure/matieres/${id}`),
  createMatiere: (data: any) =>
    request<any>("/structure/matieres", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateMatiere: (id: string, data: any) =>
    request<any>(`/structure/matieres/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteMatiere: (id: string) =>
    request<void>(`/structure/matieres/${id}`, { method: "DELETE" }),
};

// ---------------------------------------------------------------------------
// 4. Étudiants & Inscriptions
// ---------------------------------------------------------------------------
export const etudiantsApi = {
  getAll: (filters?: {
    search?: string;
    filiere?: string;
    sessionId?: string;
    statut?: string;
  }) => {
    const params = new URLSearchParams();
    if (filters?.search) params.append("search", filters.search);
    if (filters?.filiere) params.append("filiere", filters.filiere);
    if (filters?.sessionId) params.append("session_id", filters.sessionId);
    if (filters?.statut) params.append("statut", filters.statut);
    return request<any[]>(`/etudiants/?${params.toString()}`);
  },
  getById: (id: string) => request<any>(`/etudiants/${id}`),
  create: (data: any) =>
    request<any>("/etudiants/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: string, data: any) =>
    request<any>(`/etudiants/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    request<void>(`/etudiants/${id}`, { method: "DELETE" }),
  inscrire: (id: string, payload: { session_id: string; filiere?: string; niveau?: string }) =>
    request<any>(`/etudiants/${id}/inscrire`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

// ---------------------------------------------------------------------------
// 5. Pédagogie & Moteur de Délibération
// ---------------------------------------------------------------------------
export const pedagogieApi = {
  // Cours & Emplois du temps
  getCours: (matiereId?: string, jour?: string) => {
    const params = new URLSearchParams();
    if (matiereId) params.append("matiere_id", matiereId);
    if (jour) params.append("jour", jour);
    return request<any[]>(`/pedagogie/cours?${params.toString()}`);
  },
  createCours: (data: any) =>
    request<any>("/pedagogie/cours", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Examens
  getExamens: (sessionId?: string, matiereId?: string) => {
    const params = new URLSearchParams();
    if (sessionId) params.append("session_id", sessionId);
    if (matiereId) params.append("matiere_id", matiereId);
    return request<any[]>(`/pedagogie/examens?${params.toString()}`);
  },
  createExamen: (data: any) =>
    request<any>("/pedagogie/examens", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Notes
  getNotes: (filters?: { etudiant_id?: string; matiere_id?: string; session_id?: string }) => {
    const params = new URLSearchParams();
    if (filters?.etudiant_id) params.append("etudiant_id", filters.etudiant_id);
    if (filters?.matiere_id) params.append("matiere_id", filters.matiere_id);
    if (filters?.session_id) params.append("session_id", filters.session_id);
    return request<any[]>(`/pedagogie/notes?${params.toString()}`);
  },
  saveNote: (data: any) =>
    request<any>("/pedagogie/notes", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  bulkSaveNotes: (data: { matiere_id: string; examen_id?: string; session_id?: string; notes: any[] }) =>
    request<any[]>("/pedagogie/notes/bulk", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Absences
  getAbsences: (etudiantId?: string) =>
    request<any[]>(`/pedagogie/absences${etudiantId ? `?etudiant_id=${etudiantId}` : ""}`),
  declareAbsence: (data: any) =>
    request<any>("/pedagogie/absences", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Moteur de Délibération ECTS
  calculerEtudiant: (etudiantData: any, config?: any) =>
    request<any>("/pedagogie/deliberation/calculer-etudiant", {
      method: "POST",
      body: JSON.stringify({ etudiant: etudiantData, config }),
    }),
  calculerPromotion: (etudiants: any[], config?: any) =>
    request<any>("/pedagogie/deliberation/calculer-promotion", {
      method: "POST",
      body: JSON.stringify({ etudiants, config }),
    }),
};

// ---------------------------------------------------------------------------
// 6. Finances & Encaissements
// ---------------------------------------------------------------------------
export const financesApi = {
  // Factures
  getFactures: (filters?: { etudiant_id?: string; session_id?: string; statut?: string }) => {
    const params = new URLSearchParams();
    if (filters?.etudiant_id) params.append("etudiant_id", filters.etudiant_id);
    if (filters?.session_id) params.append("session_id", filters.session_id);
    if (filters?.statut) params.append("statut", filters.statut);
    return request<any[]>(`/finances/factures?${params.toString()}`);
  },
  createFacture: (data: any) =>
    request<any>("/finances/factures", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getFactureById: (id: string) => request<any>(`/finances/factures/${id}`),

  // Paiements & Encaissements
  getPaiements: (filters?: { etudiant_id?: string; session_id?: string }) => {
    const params = new URLSearchParams();
    if (filters?.etudiant_id) params.append("etudiant_id", filters.etudiant_id);
    if (filters?.session_id) params.append("session_id", filters.session_id);
    return request<any[]>(`/finances/paiements?${params.toString()}`);
  },
  getPaiementById: (id: string) => request<any>(`/finances/paiements/${id}`),
  enregistrerPaiement: (data: any) =>
    request<any>("/finances/paiements", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Reçus
  getRecuById: (id: string) => request<any>(`/finances/recus/${id}`),
  getRecuByPaiement: (paiementId: string) =>
    request<any>(`/finances/paiements/${paiementId}/recu`),

  // Balance Âgée
  getBalanceAgee: () => request<any>("/finances/balance-agee"),
};

export default {
  auth: authApi,
  setup: setupApi,
  sessions: sessionsApi,
  structure: structureApi,
  etudiants: etudiantsApi,
  pedagogie: pedagogieApi,
  finances: financesApi,
};
