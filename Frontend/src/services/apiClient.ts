/**
 * EduManagePro (EMP) — Client API Centralisé & Hybride
 * Gère la communication HTTP avec le backend FastAPI :
 * - Injection automatique du Bearer Token JWT
 * - Erreurs explicites et persistance des authentifications via le backend
 * - Adaptateurs typés pour tous les modules métier
 */

import type {
  AcademicContext,
  AcademicSession,
  ApiRecord,
  AuthUser,
  Campus,
  Candidature,
  CandidaturePage,
  AdmissionView,
  AdmissionViewFilters,
  BulkAdmissionAction,
  CandidatureCreatePayload,
  CandidatureUpdatePayload,
  AdmissionDocument,
  CandidatureStatus,
  AdmissionDocumentStatus,
  AdmissionDecisionType,
  Department,
  Filiere,
  Matiere,
  TeachingUnit,
  Absence,
  Course,
  BalanceResponse,
  FeeGrid,
  Invoice,
  LoginResponse,
  Note,
  Payment,
  Receipt,
  SetupStatus,
  Student,
  StudentPortalData,
  TeacherPortalData,
  User,
} from "./apiTypes";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

const AUTH_TOKEN_KEY = "emp_auth_token";
const USER_KEY = "emp_auth_user";
const AUTH_UNAUTHORIZED_EVENT = "emp_auth_unauthorized";

export interface ApiResult<T> {
  data?: T;
  error?: string;
  status: number;
}

// ---------------------------------------------------------------------------
// Helpers HTTP de base
// ---------------------------------------------------------------------------
function getHeaders(): Record<string, string> {
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

export function extractErrorMessage(
  detail: unknown,
  fallback = "Une erreur inattendue est survenue."
): string {
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (typeof item === "object" && item !== null) {
          const loc = Array.isArray(item.loc)
            ? item.loc.filter((p: unknown) => p !== "body").join(".")
            : "";
          const msg = item.msg || item.message || "Champ invalide";
          return loc ? `${loc}: ${msg}` : msg;
        }
        return String(item);
      })
      .join(" — ");
  }
  if (typeof detail === "object" && detail !== null) {
    const objectDetail = detail as Record<string, unknown>;
    return String(objectDetail.message || objectDetail.msg || objectDetail.detail || fallback);
  }
  return String(detail);
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResult<T>> {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const headers: Record<string, string> = { ...getHeaders() };
    if (options.headers instanceof Headers) {
      options.headers.forEach((value, key) => {
        headers[key] = value;
      });
    } else if (Array.isArray(options.headers)) {
      for (const [key, value] of options.headers) {
        headers[key] = value;
      }
    } else if (options.headers) {
      Object.assign(headers, options.headers);
    }
    if (options.body instanceof FormData) {
      // Le navigateur doit définir lui-même la_boundary multipart.
      delete headers["Content-Type"];
    }
    const response = await fetch(url, {
      ...options,
      headers,
    });

    const status = response.status;
    if (status === 401) {
      localStorage.removeItem(AUTH_TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      window.dispatchEvent(new Event(AUTH_UNAUTHORIZED_EVENT));
    }
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
  } catch (err: unknown) {
    // Mode dégradé / serveur backend inaccessible
    return {
      error: err instanceof Error ? err.message : "Impossible de contacter le serveur backend EMP.",
      status: 0,
    };
  }
}

async function requestBlob(endpoint: string): Promise<ApiResult<Blob>> {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: getHeaders(),
    });
    const status = response.status;
    if (status === 401) {
      localStorage.removeItem(AUTH_TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      window.dispatchEvent(new Event(AUTH_UNAUTHORIZED_EVENT));
    }
    if (!response.ok) {
      const json = await response.json().catch(() => null);
      const fallback = `Erreur serveur (${status})`;
      const rawError = json?.detail ?? json?.message ?? fallback;
      return {
        error: extractErrorMessage(rawError, fallback),
        status,
      };
    }
    return { data: await response.blob(), status };
  } catch (err: unknown) {
    return {
      error: err instanceof Error ? err.message : "Impossible de télécharger le fichier.",
      status: 0,
    };
  }
}

// ---------------------------------------------------------------------------
// 1. Authentification & Setup Wizard
// ---------------------------------------------------------------------------
export const authApi = {
  login: async (email: string, password: string) => {
    const res = await request<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    if (res.data?.access_token) {
      localStorage.setItem(AUTH_TOKEN_KEY, res.data.access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(res.data.user));
    }
    return res;
  },

  getMe: () => request<AuthUser>("/auth/me"),
  updateMe: (data: { nom?: string; prenom?: string; telephone?: string | null }) =>
    request<AuthUser>("/auth/me", {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  changePassword: (data: { current_password: string; new_password: string }) =>
    request<void>("/auth/me/password", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  logout: () => {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },

  getToken: () => localStorage.getItem(AUTH_TOKEN_KEY),
  getCurrentUser: () => {
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      localStorage.removeItem(USER_KEY);
      return null;
    }
  },
};

export const setupApi = {
  getStatus: () => request<SetupStatus>("/setup/status"),
  initialize: (payload: unknown) =>
    request<ApiRecord>("/setup/initialize", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

// ---------------------------------------------------------------------------
// 2. Contexte global & sessions académiques
// ---------------------------------------------------------------------------
export const academicContextApi = {
  get: () => request<AcademicContext>("/context/academique"),
  update: (data: { annee_academique: string; session_id?: string | null }) =>
    request<AcademicContext>("/context/academique", {
      method: "PUT",
      body: JSON.stringify(data),
    }),
};

export const sessionsApi = {
  getAll: () => request<AcademicSession[]>("/sessions/"),
  getActive: () => request<AcademicSession>("/sessions/active"),
  getById: (id: string) => request<AcademicSession>(`/sessions/${id}`),
  getPeriods: (sessionId: string) =>
    request<AcademicSession["periodes"]>(`/sessions/${sessionId}/periodes`),
  create: (session: unknown) =>
    request<AcademicSession>("/sessions/", {
      method: "POST",
      body: JSON.stringify(session),
    }),
  update: (id: string, session: unknown) =>
    request<AcademicSession>(`/sessions/${id}`, {
      method: "PUT",
      body: JSON.stringify(session),
    }),
  delete: (id: string) =>
    request<void>(`/sessions/${id}`, {
      method: "DELETE",
    }),
};

// ---------------------------------------------------------------------------
// 3. Structure Académique (Campus, Dép., Filières, UEs, Matières)
// ---------------------------------------------------------------------------
export const structureApi = {
  // Campus
  getCampuses: () => request<Campus[]>("/structure/campuses"),
  createCampus: (data: unknown) =>
    request<Campus>("/structure/campuses", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateCampus: (id: string, data: unknown) =>
    request<Campus>(`/structure/campuses/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteCampus: (id: string) =>
    request<void>(`/structure/campuses/${id}`, { method: "DELETE" }),

  // Départements
  getDepartements: (campusId?: string) =>
    request<Department[]>(
      `/structure/departements${campusId ? `?campus_id=${campusId}` : ""}`
    ),
  createDepartement: (data: unknown) =>
    request<Department>("/structure/departements", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateDepartement: (id: string, data: unknown) =>
    request<Department>(`/structure/departements/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteDepartement: (id: string) =>
    request<void>(`/structure/departements/${id}`, { method: "DELETE" }),

  // Filières
  getFilieres: (deptId?: string) =>
    request<Filiere[]>(
      `/structure/filieres${deptId ? `?departement_id=${deptId}` : ""}`
    ),
  createFiliere: (data: unknown) =>
    request<Filiere>("/structure/filieres", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateFiliere: (id: string, data: unknown) =>
    request<Filiere>(`/structure/filieres/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteFiliere: (id: string) =>
    request<void>(`/structure/filieres/${id}`, { method: "DELETE" }),

  // UEs
  getUEs: (filiereId?: string, semestre?: string) => {
    const params = new URLSearchParams();
    if (filiereId) params.append("filiere_id", filiereId);
    if (semestre) params.append("semestre", semestre);
    return request<TeachingUnit[]>(`/structure/ues?${params.toString()}`);
  },
  getUEById: (id: string) => request<TeachingUnit>(`/structure/ues/${id}`),
  createUE: (data: unknown) =>
    request<TeachingUnit>("/structure/ues", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateUE: (id: string, data: unknown) =>
    request<TeachingUnit>(`/structure/ues/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteUE: (id: string) =>
    request<void>(`/structure/ues/${id}`, { method: "DELETE" }),

  // Matières (ECUE)
  getMatieres: (ueId?: string) =>
    request<Matiere[]>(`/structure/matieres${ueId ? `?ue_id=${ueId}` : ""}`),
  getMatiereById: (id: string) => request<Matiere>(`/structure/matieres/${id}`),
  createMatiere: (data: unknown) =>
    request<Matiere>("/structure/matieres", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateMatiere: (id: string, data: unknown) =>
    request<Matiere>(`/structure/matieres/${id}`, {
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
    return request<Student[]>(`/etudiants/?${params.toString()}`);
  },
  getById: (id: string) => request<Student>(`/etudiants/${id}`),
  create: (data: unknown) =>
    request<Student>("/etudiants/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: string, data: unknown) =>
    request<Student>(`/etudiants/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    request<void>(`/etudiants/${id}`, { method: "DELETE" }),
  inscrire: (id: string, payload: { session_id: string; filiere?: string; niveau?: string }) =>
    request<ApiRecord>(`/etudiants/${id}/inscrire`, {
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
    return request<Course[]>(`/pedagogie/cours?${params.toString()}`);
  },
  createCours: (data: unknown) =>
    request<Course>("/pedagogie/cours", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateCours: (id: string, data: unknown) =>
    request<Course>(`/pedagogie/cours/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteCours: (id: string) =>
    request<void>(`/pedagogie/cours/${id}`, { method: "DELETE" }),

  // Examens
  getExamens: (sessionId?: string, matiereId?: string) => {
    const params = new URLSearchParams();
    if (sessionId) params.append("session_id", sessionId);
    if (matiereId) params.append("matiere_id", matiereId);
    return request<ApiRecord[]>(`/pedagogie/examens?${params.toString()}`);
  },
  createExamen: (data: unknown) =>
    request<ApiRecord>("/pedagogie/examens", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Notes
  getNotes: (filters?: { etudiant_id?: string; matiere_id?: string; session_id?: string }) => {
    const params = new URLSearchParams();
    if (filters?.etudiant_id) params.append("etudiant_id", filters.etudiant_id);
    if (filters?.matiere_id) params.append("matiere_id", filters.matiere_id);
    if (filters?.session_id) params.append("session_id", filters.session_id);
    return request<Note[]>(`/pedagogie/notes?${params.toString()}`);
  },
  saveNote: (data: unknown) =>
    request<Note>("/pedagogie/notes", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateNote: (id: string, data: unknown) =>
    request<Note>(`/pedagogie/notes/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  bulkSaveNotes: (data: { matiere_id: string; examen_id?: string; session_id?: string; notes: unknown[] }) =>
    request<Note[]>("/pedagogie/notes/bulk", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Absences
  getAbsences: (etudiantId?: string) =>
    request<Absence[]>(`/pedagogie/absences${etudiantId ? `?etudiant_id=${etudiantId}` : ""}`),
  declareAbsence: (data: unknown) =>
    request<Absence>("/pedagogie/absences", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Moteur de Délibération ECTS
  calculerEtudiant: (etudiantData: unknown, config?: unknown) =>
    request<ApiRecord>("/pedagogie/deliberation/calculer-etudiant", {
      method: "POST",
      body: JSON.stringify({ etudiant: etudiantData, config }),
    }),
  calculerPromotion: (etudiants: unknown[], config?: unknown) =>
    request<ApiRecord>("/pedagogie/deliberation/calculer-promotion", {
      method: "POST",
      body: JSON.stringify({ etudiants, config }),
    }),
};

// ---------------------------------------------------------------------------
// 6. Finances & Encaissements
// ---------------------------------------------------------------------------
export const financesApi = {
  // Grilles tarifaires
  getGrillesTarifaires: (filters?: { filiere_id?: string; actif?: boolean }) => {
    const params = new URLSearchParams();
    if (filters?.filiere_id) params.append("filiere_id", filters.filiere_id);
    if (filters?.actif !== undefined) params.append("actif", String(filters.actif));
    return request<FeeGrid[]>(`/finances/grilles-tarifaires?${params.toString()}`);
  },
  createGrilleTarifaire: (data: unknown) =>
    request<FeeGrid>("/finances/grilles-tarifaires", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateGrilleTarifaire: (id: string, data: unknown) =>
    request<FeeGrid>(`/finances/grilles-tarifaires/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteGrilleTarifaire: (id: string) =>
    request<void>(`/finances/grilles-tarifaires/${id}`, { method: "DELETE" }),

  // Factures
  getFactures: (filters?: { etudiant_id?: string; session_id?: string; statut?: string }) => {
    const params = new URLSearchParams();
    if (filters?.etudiant_id) params.append("etudiant_id", filters.etudiant_id);
    if (filters?.session_id) params.append("session_id", filters.session_id);
    if (filters?.statut) params.append("statut", filters.statut);
    return request<Invoice[]>(`/finances/factures?${params.toString()}`);
  },
  createFacture: (data: unknown) =>
    request<Invoice>("/finances/factures", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getFactureById: (id: string) => request<Invoice>(`/finances/factures/${id}`),

  // Paiements & Encaissements
  getPaiements: (filters?: { etudiant_id?: string; session_id?: string }) => {
    const params = new URLSearchParams();
    if (filters?.etudiant_id) params.append("etudiant_id", filters.etudiant_id);
    if (filters?.session_id) params.append("session_id", filters.session_id);
    return request<Payment[]>(`/finances/paiements?${params.toString()}`);
  },
  getPaiementById: (id: string) => request<Payment>(`/finances/paiements/${id}`),
  enregistrerPaiement: (data: unknown) =>
    request<Payment>("/finances/paiements", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Reçus
  getRecuById: (id: string) => request<Receipt>(`/finances/recus/${id}`),
  getRecuByPaiement: (paiementId: string) =>
    request<Receipt>(`/finances/paiements/${paiementId}/recu`),

  // Balance Âgée
  getBalanceAgee: () => request<BalanceResponse>("/finances/balance-agee"),
};

export const usersApi = {
  getAll: (filters?: { role?: string; active?: boolean }) => {
    const params = new URLSearchParams();
    if (filters?.role) params.append("role", filters.role);
    if (filters?.active !== undefined) params.append("active", String(filters.active));
    return request<User[]>(`/users/?${params.toString()}`);
  },
  create: (data: unknown) =>
    request<User>("/users/", { method: "POST", body: JSON.stringify(data) }),
  update: (id: number, data: unknown) =>
    request<User>(`/users/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: number) => request<void>(`/users/${id}`, { method: "DELETE" }),
};

export const admissionsApi = {
  getAll: (filters?: {
    search?: string;
    statut?: CandidatureStatus;
    filiere_id?: string;
    session_id?: string;
    page?: number;
    page_size?: number;
  }) => {
    const params = new URLSearchParams();
    if (filters?.search) params.append("search", filters.search);
    if (filters?.statut) params.append("statut", filters.statut);
    if (filters?.filiere_id) params.append("filiere_id", filters.filiere_id);
    if (filters?.session_id) params.append("session_id", filters.session_id);
    if (filters?.page !== undefined) params.append("page", String(filters.page));
    if (filters?.page_size !== undefined) params.append("page_size", String(filters.page_size));
    const query = params.toString();
    return request<CandidaturePage>(`/admissions/candidatures${query ? `?${query}` : ""}`);
  },
  getById: (id: string) => request<Candidature>(`/admissions/candidatures/${id}`),
  listViews: () => request<AdmissionView[]>("/admissions/vues"),
  createView: (data: { nom: string; filtres: AdmissionViewFilters }) =>
    request<AdmissionView>("/admissions/vues", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateView: (id: string, data: { nom?: string; filtres?: AdmissionViewFilters }) =>
    request<AdmissionView>(`/admissions/vues/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteView: (id: string) =>
    request<void>(`/admissions/vues/${id}`, { method: "DELETE" }),
  bulkAction: (data: { ids: string[]; action: BulkAdmissionAction; commentaire?: string }) =>
    request<{ updated_ids: string[]; errors: { candidature_id: string; message: string }[] }>(
      "/admissions/candidatures/actions",
      { method: "POST", body: JSON.stringify(data) }
    ),
  create: (data: CandidatureCreatePayload) =>
    request<Candidature>("/admissions/candidatures", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: string, data: CandidatureUpdatePayload) =>
    request<Candidature>(`/admissions/candidatures/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  updateStatus: (id: string, statut: CandidatureStatus, commentaire?: string) =>
    request<Candidature>(`/admissions/candidatures/${id}/statut`, {
      method: "PATCH",
      body: JSON.stringify({ statut, commentaire }),
    }),
  addDocument: (id: string, data: { type: string; nom_fichier?: string; commentaire?: string }) =>
    request<AdmissionDocument>(`/admissions/candidatures/${id}/pieces`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  uploadDocument: (pieceId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file, file.name);
    return request<AdmissionDocument>(`/admissions/pieces/${pieceId}/fichier`, {
      method: "POST",
      body: formData,
    });
  },
  downloadDocument: (pieceId: string) =>
    requestBlob(`/admissions/pieces/${pieceId}/fichier`),
  updateDocument: (
    pieceId: string,
    data: { nom_fichier?: string; statut?: AdmissionDocumentStatus; commentaire?: string }
  ) =>
    request<AdmissionDocument>(`/admissions/pieces/${pieceId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  decide: (id: string, data: { decision: AdmissionDecisionType; motif?: string }) =>
    request<Candidature>(`/admissions/candidatures/${id}/decisions`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  convert: (id: string) =>
    request<{ candidature: Candidature; etudiant: Student }>(`/admissions/candidatures/${id}/convertir`, {
      method: "POST",
    }),
};

export const portalsApi = {
  getStudentPortal: () => request<StudentPortalData>("/portail/etudiant"),
  getTeacherPortal: () => request<TeacherPortalData>("/portail/enseignant"),
};

export default {
  auth: authApi,
  setup: setupApi,
  academicContext: academicContextApi,
  sessions: sessionsApi,
  structure: structureApi,
  etudiants: etudiantsApi,
  pedagogie: pedagogieApi,
  finances: financesApi,
  users: usersApi,
  portals: portalsApi,
  admissions: admissionsApi,
};
