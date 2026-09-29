/**
 * EduManagePro (EMP) — Client API Centralisé & Hybride
 * Gère la communication HTTP avec le backend FastAPI :
 * - Injection automatique du Bearer Token JWT
 * - Erreurs explicites et persistance des authentifications via le backend
 * - Adaptateurs typés pour tous les modules métier
 */

import type {
  AcademicClass,
  AcademicClassInput,
  AcademicContext,
  AcademicCycle,
  AcademicCycleInput,
  AcademicLevel,
  AcademicLevelInput,
  AcademicSession,
  AcademicTemplateResult,
  ApiRecord,
  AuditEvent,
  AuthUser,
  AuthSessionList,
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
  Enrollment,
  Filiere,
  Matiere,
  TeachingUnit,
  Absence,
  Course,
  ConflitEdt,
  Salle,
  BalanceResponse,
  FeeGrid,
  Invoice,
  PaiementIntention,
  PaiementIntentionCreee,
  ResumeFamille,
  ConfirmationPaiement,
  LoginResponse,
  Note,
  Payment,
  Receipt,
  DocumentOfficiel,
  ImportAnalyse,
  ImportBatch,
  LotDocuments,
  TypeDocument,
  ImportModele,
  ImportMode,
  ImportValidation,
  ConfigurationVersion,
  DecisionDeliberation,
  Deliberation,
  DeliberationDetail,
  EtudiantARelancer,
  InstitutionConfig,
  InstitutionConfigModifiee,
  InstitutionConfigPayload,
  RbacPermission,
  RbacRole,
  RbacUserAccess,
  PropositionEtudiant,
  RbacUserPermissions,
  ReglesDeliberation,
  Relance,
  Semestre,
  SemestreRepartition,
  SetupStatus,
  Bulletin,
  RattrapageEtudiant,
  SetupInitPayload,
  BilanImportNotes,
  ModeleImportNotes,
  RapportImportNotes,
  JetonMatricule,
  MatriculeParametres,
  MatriculeParametresMaj,
  SyntheseRelances,
  Student,
  StudentSummary,
  StudentPortalData,
  TeacherPortalData,
  User,
} from "./apiTypes";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

const AUTH_TOKEN_KEY = "emp_auth_token";
const USER_KEY = "emp_auth_user";
/** Session révocable (lot 2) : le jeton de rafraîchissement, jamais exposé. */
const REFRESH_TOKEN_KEY = "emp_auth_refresh";
const AUTH_UNAUTHORIZED_EVENT = "emp_auth_unauthorized";

export interface ApiResult<T> {
  data?: T;
  error?: string;
  status: number;
  /** Total global d'une liste paginée (en-tête ``X-Total-Count``). */
  total?: number;
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

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setRefreshToken(jeton: string | null | undefined): void {
  if (jeton) {
    localStorage.setItem(REFRESH_TOKEN_KEY, jeton);
  } else {
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  }
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

/**
 * Une seule rotation a la fois : les requêtes qui tombent en 401 pendant un
 * rafraîchissement en cours s'y abonnent, au lieu d'en relancer chacune un.
 * Sans verrou, N requêtes parallèles produiraient N rotations — et la
 * rotation N+1 revoquerait le jeton que N requêtes viennent de recevoir.
 */
let rotationEnCours: Promise<boolean> | null = null;

async function tournerJeton(): Promise<boolean> {
  const jetonActuel = getRefreshToken();
  if (!jetonActuel) {
    return false;
  }
  try {
    const reponse = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ refresh_token: jetonActuel }),
    });
    if (!reponse.ok) {
      return false;
    }
    const corps = (await reponse.json()) as {
      access_token?: string;
      refresh_token?: string;
    };
    if (!corps.access_token || !corps.refresh_token) {
      return false;
    }
    // La rotation rend un NOUVEAU jeton de rafraîchissement : l'ancien est
    // déjà révoqué côté serveur, le garder reviendrait à le rejouer — et le
    // rejeu ferme toutes les sessions du compte.
    localStorage.setItem(AUTH_TOKEN_KEY, corps.access_token);
    setRefreshToken(corps.refresh_token);
    return true;
  } catch {
    return false;
  }
}

/**
 * Tente un rafraîchissement silencieux. Résout `true` si un NOUVEAU jeton
 * d'accès est disponible : l'appelant peut alors rejouer SA requête une fois.
 */
async function rafraichirSilencieusement(): Promise<boolean> {
  if (!rotationEnCours) {
    rotationEnCours = tournerJeton().finally(() => {
      rotationEnCours = null;
    });
  }
  return rotationEnCours;
}

function abandonnerSession(): void {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  window.dispatchEvent(new Event(AUTH_UNAUTHORIZED_EVENT));
}

interface RequestOptionsEtendues extends RequestInit {
  /**
   * Endpoint public (lien de paiement de la famille) : n'envoie pas le
   * jeton d'authentification et ne déclenche pas de rafraîchissement — la
   * porte de la famille ne doit jamais réveiller la session du secrétaire
   * qui, par hasard, utiliserait le même navigateur.
   */
  skipAuth?: boolean;
}

async function request<T>(
  endpoint: string,
  options: RequestOptionsEtendues = {},
  dejaRafraichi = false
): Promise<ApiResult<T>> {
  const url = `${API_BASE_URL}${endpoint}`;
  const { skipAuth, ...optionsFetch } = options;
  try {
    const headers: Record<string, string> = skipAuth ? {} : { ...getHeaders() };
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
      ...optionsFetch,
      headers,
    });

    const status = response.status;
    if (status === 401 && !skipAuth) {
      // L'endpoint de rafraîchissement lui-même ne se rafraîchit pas : la
      // rotation qui échoue est une fin de session, pas un nouvel essai.
      const jetonRefus = endpoint.startsWith("/auth/refresh");
      const rafraichi = !jetonRefus && !dejaRafraichi && (await rafraichirSilencieusement());
      if (rafraichi) {
        // Une seule seconde tentative : la session vient d'être prolongée,
        // un nouvel échec 401 signale autre chose qu'une expiration.
        return request<T>(endpoint, options, true);
      }
      abandonnerSession();
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

    return { data: json as T, status, total: parseTotal(response) };
  } catch (err: unknown) {
    // Mode dégradé / serveur backend inaccessible
    return {
      error: err instanceof Error ? err.message : "Impossible de contacter le serveur backend EMP.",
      status: 0,
    };
  }
}

function parseTotal(response: Response): number | undefined {
  const brut = response.headers.get("X-Total-Count");
  if (brut === null) return undefined;
  const nombre = Number(brut);
  return Number.isFinite(nombre) ? nombre : undefined;
}

async function requestBlob(
  endpoint: string,
  dejaRafraichi = false
): Promise<ApiResult<Blob>> {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: getHeaders(),
    });
    const status = response.status;
    if (status === 401) {
      const rafraichi = !dejaRafraichi && (await rafraichirSilencieusement());
      if (rafraichi) {
        return requestBlob(endpoint, true);
      }
      abandonnerSession();
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
      // Le serveur émet une session révocable : son jeton permet la rotation
      // silencieuse. Absent (backend antérieur au lot 2) : on fonctionne
      // comme avant, sans dégradation.
      setRefreshToken(res.data.refresh_token ?? null);
    }
    return res;
  },

  getMe: () => request<AuthUser>("/auth/me"),
  getSessions: () => request<AuthSessionList>("/auth/sessions"),
  fermerSession: (sessionId: string) =>
    request<void>(`/auth/sessions/${sessionId}`, { method: "DELETE" }),
  fermerAutresSessions: () =>
    request<void>("/auth/sessions/fermer-autres", { method: "POST" }),
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

  /**
   * Ferme la session CÔTÉ SERVEUR quand un jeton de rafraîchissement
   * existe : révoqué, il ne rafraîchira plus rien, même intercepté. Sans
   * jeton (backend antérieur au lot 2), la déconnexion reste locale.
   */
  logout: async () => {
    const jeton = getRefreshToken();
    if (jeton) {
      try {
        await fetch(`${API_BASE_URL}/auth/logout`, {
          method: "POST",
          headers: { ...getHeaders(), "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: jeton }),
        });
      } catch {
        // Le serveur est injoignable : la session locale se ferme quand
        // même. Un logout qui exigerait le serveur serait un logout qui
        // échoue chaque fois que le serveur tombe.
      }
    }
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
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
  initialize: (payload: SetupInitPayload) =>
    request<ApiRecord>("/setup/initialize", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

// ---------------------------------------------------------------------------
// 1 bis. Configuration institutionnelle (identité, logo, historique)
// ---------------------------------------------------------------------------

/**
 * Permission exigee pour modifier la configuration institutionnelle.
 *
 * Elle vit dans la couche API, avec les autres noms de permissions : l'ecran
 * n'a pas a la redeclarer, et un ecran qui l'invente divergerait de ce que
 * le backend reellement autorise.
 */
export const PERMISSION_INSTITUTION_SETTINGS = "institution.settings";

export const institutionApi = {
  /** Configuration en vigueur, avec son numéro de version. */
  getConfig: () => request<InstitutionConfig>("/institution/configuration"),

  /**
   * Enregistre l'identite. Une reponse dont `modifications` est vide signifie
   * qu'aucun champ n'a reellement change : aucune version n'a ete creee, et
   * ce n'est pas une erreur.
   */
  updateConfig: (payload: InstitutionConfigPayload) =>
    request<InstitutionConfigModifiee>("/institution/configuration", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  /**
   * Televerse le logo. Le format est verifie par le serveur **sur les
   * octets** : un fichier qui n'est pas une image est refuse, quel que soit
   * son nom. La validation cote navigateur ne dispense pas de cette verite.
   */
  uploadLogo: (fichier: File) => {
    const donnees = new FormData();
    donnees.append("fichier", fichier);
    return request<InstitutionConfigModifiee>("/institution/logo", {
      method: "POST",
      body: donnees,
    });
  },

  removeLogo: () =>
    request<InstitutionConfigModifiee>("/institution/logo", { method: "DELETE" }),

  /** Historique des versions, de la plus recente a la plus ancienne. */
  getVersions: () => request<ConfigurationVersion[]>("/institution/versions"),

  /**
   * Octets du logo, pour l'apercu. Un 404 signifie « pas de logo » : c'est
   * un etat normal, pas une erreur, d'ou le retour du statut a l'appelant.
   */
  getLogo: () => requestBlob("/institution/logo"),
};

/*
 * Le logo ne se charge pas par une `<img src>` : cet endpoint est protege par
 * `academic.read` et une balise `<img>` ne peut pas envoyer le jeton Bearer.
 * L'ecran recupere les octets par `getLogo()` et attache une URL d'objet.
 */

// ---------------------------------------------------------------------------
// 1 ter. Deliberation et jury
// ---------------------------------------------------------------------------
export const deliberationApi = {
  /** Regles en vigueur, avec leur etat de confirmation. */
  getRegles: () => request<ReglesDeliberation>("/deliberation/regles"),

  /**
   * Enregistre le reglement. `confirme` declare que l'institut valide ses
   * propres seuils : sans cette case, les valeurs restent « a confirmer » et
   * l'ecran le signale. Les deliberations deja tenues gardent les regles
   * qu'elles avaient figees.
   */
  updateRegles: (regles: Omit<ReglesDeliberation, "confirmee" | "confirme_par" | "confirme_le"> & { confirme: boolean }) =>
    request<ReglesDeliberation>("/deliberation/regles", {
      method: "PUT",
      body: JSON.stringify(regles),
    }),

  /**
   * Enregistre, pour un etudiant, ce que le jury decide sur chaque UE.
   *
   * Les trois etats possibles sont fermes cote serveur : `validation` hors de
   * cette liste est refusee, parce qu'une valeur qui n'est pas une decision
   * ne doit pas pouvoir etre enregistree. Un ecart avec la proposition du
   * moteur exige `motif` ; le serveur le refuse aussi, et le formulaire
   * l'exige donc avant d'activer le bouton.
   *
   * L'enregistrement est **partiel et repetable** : envoyer trois UE sur cinq
   * n'annule pas les deux autres.
   */
  recordDecisionsUnites: (
    deliberationId: string,
    etudiantId: string,
    decisions: Array<{
      ue_id: string;
      validation: "Validée" | "Validée en SR" | "À reprendre";
      credits_obtenus?: number | null;
      mention?: string | null;
      motif?: string | null;
    }>
  ) =>
    request<DecisionDeliberation>(
      `/deliberation/${deliberationId}/decisions/${etudiantId}/unites`,
      { method: "PUT", body: JSON.stringify({ decisions }) }
    ),

  list: () => request<Deliberation[]>("/deliberation/"),

  get: (id: string) => request<DeliberationDetail>(`/deliberation/${id}`),

  /** Ouvre une seance. Le president et les membres sont saisis, jamais devines. */
  create: (payload: {
    classe_id: string;
    session_id: string;
    date_deliberation: string;
    president: string;
    membres: { nom: string; qualite?: string | null }[];
    lieu?: string | null;
  }) =>
    request<Deliberation>("/deliberation/", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  /**
   * Consigne la decision du jury. Le serveur refuse un ecart avec la
   * proposition du moteur sans `motif_ecart` : l'ecart reste donc explicite
   * dans le corps de la requete, pas seulement dans l'interface.
   */
  recordDecision: (id: string, etudiantId: string, decision: {
    statut: string;
    mention?: string | null;
    motif_ecart?: string | null;
  }) =>
    request<DecisionDeliberation>(
      `/deliberation/${id}/decisions?etudiant_id=${encodeURIComponent(etudiantId)}`,
      { method: "POST", body: JSON.stringify(decision) },
    ),

  /**
   * Arrete le verdict. `confirmation: "arreter"` est exigee par le serveur :
   * la cloture est irreversible et ne doit pas dependre d'un simple clic.
   */
  cloturer: (id: string) =>
    request<Deliberation>(`/deliberation/${id}/cloturer`, {
      method: "POST",
      body: JSON.stringify({ confirmation: "arreter" }),
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
const normalizeCycle = (item: AcademicCycle): AcademicCycle => ({
  ...item,
  nom: item.nom || item.libelle,
  libelle: item.libelle || item.nom,
  ordre: item.ordre ?? item.rang,
  rang: item.rang ?? item.ordre,
});

const normalizeLevel = (item: AcademicLevel): AcademicLevel => ({
  ...item,
  nom: item.nom || item.libelle,
  libelle: item.libelle || item.nom,
  ordre: item.ordre ?? item.rang,
  rang: item.rang ?? item.ordre,
  cycle: item.cycle ? normalizeCycle(item.cycle) : item.cycle,
});

const academicClassCode = (item: AcademicClass) =>
  item.code || [item.filiere?.code, item.niveau?.code].filter(Boolean).join("-").toUpperCase();

const normalizeClass = (item: AcademicClass): AcademicClass => {
  const code = academicClassCode(item);
  const derivedLabel = [item.filiere?.nom, item.niveau?.nom || item.niveau?.libelle]
    .filter(Boolean)
    .join(" — ");
  return {
    ...item,
    code,
    libelle: item.libelle || item.nom || derivedLabel || code,
    filiere: item.filiere || null,
    niveau: item.niveau ? normalizeLevel(item.niveau) : item.niveau,
    cycle: item.cycle ? normalizeCycle(item.cycle) : item.cycle,
  };
};

const withNormalizedData = <T>(
  result: ApiResult<T[]>,
  normalize: (item: T) => T
): ApiResult<T[]> => ({
  ...result,
  data: result.data?.map(normalize),
});

export const academicApi = {
  getCycles: async () =>
    withNormalizedData(await request<AcademicCycle[]>("/academic/cycles"), normalizeCycle),
  createCycle: async (data: AcademicCycleInput) => {
    const result = await request<AcademicCycle>("/academic/cycles", {
      method: "POST",
      body: JSON.stringify(data),
    });
    return result.data ? { ...result, data: normalizeCycle(result.data) } : result;
  },
  updateCycle: async (id: string, data: Partial<AcademicCycleInput>) => {
    const result = await request<AcademicCycle>(`/academic/cycles/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
    return result.data ? { ...result, data: normalizeCycle(result.data) } : result;
  },
  deleteCycle: (id: string) =>
    request<void>(`/academic/cycles/${id}`, { method: "DELETE" }),

  getLevels: async (cycleId?: string) => {
    const params = new URLSearchParams();
    if (cycleId) params.append("cycle_id", cycleId);
    return withNormalizedData(
      await request<AcademicLevel[]>(`/academic/niveaux?${params.toString()}`),
      normalizeLevel
    );
  },
  createLevel: async (data: AcademicLevelInput) => {
    const result = await request<AcademicLevel>("/academic/niveaux", {
      method: "POST",
      body: JSON.stringify(data),
    });
    return result.data ? { ...result, data: normalizeLevel(result.data) } : result;
  },
  updateLevel: async (id: string, data: Partial<AcademicLevelInput>) => {
    const result = await request<AcademicLevel>(`/academic/niveaux/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
    return result.data ? { ...result, data: normalizeLevel(result.data) } : result;
  },
  deleteLevel: (id: string) =>
    request<void>(`/academic/niveaux/${id}`, { method: "DELETE" }),

  getClasses: async (filters?: { filiereId?: string; niveauId?: string; cycleId?: string }) => {
    const params = new URLSearchParams();
    if (filters?.filiereId) params.append("filiere_id", filters.filiereId);
    if (filters?.niveauId) params.append("niveau_id", filters.niveauId);
    if (filters?.cycleId) params.append("cycle_id", filters.cycleId);
    return withNormalizedData(
      await request<AcademicClass[]>(`/academic/classes?${params.toString()}`),
      normalizeClass
    );
  },
  createClass: async (data: AcademicClassInput) => {
    const result = await request<AcademicClass>("/academic/classes", {
      method: "POST",
      body: JSON.stringify(data),
    });
    return result.data ? { ...result, data: normalizeClass(result.data) } : result;
  },
  updateClass: async (id: string, data: Partial<AcademicClassInput>) => {
    const result = await request<AcademicClass>(`/academic/classes/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
    return result.data ? { ...result, data: normalizeClass(result.data) } : result;
  },
  deleteClass: (id: string) =>
    request<void>(`/academic/classes/${id}`, { method: "DELETE" }),

  loadLmdTemplate: () =>
    request<AcademicTemplateResult>("/academic/modele-lmd/charger", { method: "POST" }),
  listEnrollments: (etudiantId?: string, activeOnly = false) => {
    const params = new URLSearchParams();
    if (etudiantId) params.append("etudiant_id", etudiantId);
    if (activeOnly) params.append("active_only", "true");
    return request<Enrollment[]>(`/academic/inscriptions?${params.toString()}`);
  },
};

// 3. Semestres
//
// Un semestre est une donnee de l'institut : un numero, un libelle, des dates.
// La repartition d'une session indique aussi combien d'UE restent **sans**
// rattachement — le compte qui dit a l'agent qu'une matiere sortira du bulletin.
export const semestresApi = {
  getRepartition: (sessionId: string) =>
    request<SemestreRepartition>(
      `/academic/semestres/repartition?session_id=${encodeURIComponent(sessionId)}`
    ),
  getById: (id: string) => request<Semestre>(`/academic/semestres/${id}`),
  create: (sessionId: string, data: unknown) =>
    request<Semestre>(
      `/academic/semestres?session_id=${encodeURIComponent(sessionId)}`,
      { method: "POST", body: JSON.stringify(data) }
    ),
  update: (id: string, data: unknown) =>
    request<Semestre>(`/academic/semestres/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    request<void>(`/academic/semestres/${id}`, { method: "DELETE" }),
};

// 4. Bulletins et rattrapage
//
// Le bulletin est produit en **deux** appels qui sortent du meme calcul : l'un
// rend le contenu en JSON, l'autre le PDF. Les relire, c'est verifier le
// document avant de l'imprimer — c'est ce qui evite de distribuer un bulletin
// faux, et c'est aussi la seule facon de voir ce que le PDF dira.
export const bulletinsApi = {
  /** Le contenu, avant impression. */
  lire: (etudiantId: string, semestreId: string) =>
    request<Bulletin>(
      `/pedagogie/bulletins/${encodeURIComponent(etudiantId)}/${encodeURIComponent(semestreId)}`
    ),

  /** Le PDF. Ni signature ni cachet : le document se signe a la main. */
  pdf: (etudiantId: string, semestreId: string) =>
    requestBlob(
      `/pedagogie/bulletins/${encodeURIComponent(etudiantId)}/${encodeURIComponent(semestreId)}/pdf`
    ),

  /**
   * Le lot d'une classe entiere : un ZIP, un bulletin par etudiant.
   *
   * Le serveur reutilise le meme rendu que le PDF individuel — le lot ne
   * peut pas diverger du document signe un par un. Un etudiant dont le
   * bulletin echoue n'interrompt pas l'archive : un rapport
   * `_bulletins-non-produits.txt` la signale.
   */
  telechargerLot: (classeId: string, semestreId: string) =>
    requestBlob(
      `/pedagogie/bulletins/classe/${encodeURIComponent(classeId)}/${encodeURIComponent(semestreId)}/archive`
    ),

  /**
   * Les matieres sur lesquelles l'etudiant peut repasser une epreuve.
   *
   * `etat` distingue trois situations qui ne se remedient pas de la meme
   * facon : `aucune_seance` (le jury ne s'est pas prononce), `rien_a_reprendre`
   * (c'est une reponse) et `a_reprendre` (la liste). Une liste vide sans
   * explication se lirait comme « rien a reprendre ».
   */
  rattrapage: (etudiantId: string, sessionId: string) =>
    request<RattrapageEtudiant>(
      `/pedagogie/rattrapage/${encodeURIComponent(etudiantId)}?session_id=${encodeURIComponent(sessionId)}`
    ),
};

export const structureApi = {
  // Salles (lot 3)
  getSalles: () => request<Salle[]>("/structure/salles"),
  createSalle: (data: unknown) =>
    request<Salle>("/structure/salles", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateSalle: (id: string, data: unknown) =>
    request<Salle>(`/structure/salles/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteSalle: (id: string) =>
    request<void>(`/structure/salles/${id}`, { method: "DELETE" }),

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
  /**
   * `semestreId` filtre sur l'identifiant, `semestre` sur le libelle
   * d'affichage. Le libelle n'est pas unique — deux semestres peuvent porter la
   * meme etiquette — donc seul l'identifiant donne un resultat non ambigu.
   */
  getUEs: (filiereId?: string, semestre?: string, semestreId?: string) => {
    const params = new URLSearchParams();
    if (filiereId) params.append("filiere_id", filiereId);
    if (semestre) params.append("semestre", semestre);
    if (semestreId) params.append("semestre_id", semestreId);
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
    /** Pagination additive : absent, la réponse reste complète. */
    limit?: number;
    offset?: number;
  }) => {
    const params = new URLSearchParams();
    if (filters?.search) params.append("search", filters.search);
    if (filters?.filiere) params.append("filiere", filters.filiere);
    if (filters?.sessionId) params.append("session_id", filters.sessionId);
    if (filters?.statut) params.append("statut", filters.statut);
    if (filters?.limit != null) params.append("limit", String(filters.limit));
    if (filters?.offset) params.append("offset", String(filters.offset));
    return request<Student[]>(`/etudiants/?${params.toString()}`);
  },
  getSummary: (filters?: {
    search?: string;
    filiere?: string;
    sessionId?: string;
    statut?: string;
    niveau?: string;
  }) => {
    const params = new URLSearchParams();
    if (filters?.search) params.append("search", filters.search);
    if (filters?.filiere) params.append("filiere", filters.filiere);
    if (filters?.sessionId) params.append("session_id", filters.sessionId);
    if (filters?.statut) params.append("statut", filters.statut);
    if (filters?.niveau) params.append("niveau", filters.niveau);
    return request<StudentSummary[]>(`/etudiants/summary?${params.toString()}`);
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
  inscrire: (
    id: string,
    payload: {
      session_id: string;
      classe_id: string;
    }
  ) =>
    request<ApiRecord>(`/etudiants/${id}/inscrire`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

// ---------------------------------------------------------------------------
// 5. Pédagogie & Moteur de Délibération
// ---------------------------------------------------------------------------
export const pedagogieApi = {
  getAssignedStudents: (matiereId: string, sessionId: string) => {
    const params = new URLSearchParams({ matiere_id: matiereId, session_id: sessionId });
    return request<StudentSummary[]>(`/pedagogie/etudiants-assignes?${params.toString()}`);
  },

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

  // Audit des conflits d'emploi du temps (lot 3)
  getCoursConflits: () => request<ConflitEdt[]>("/pedagogie/cours/conflits"),

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

  /*
   * Les methodes de calcul de deliberation ont ete retirees avec le moteur
   * qu'elles appelaient. Un verdict calcule a partir d'un dossier fourni par
   * l'appelant, sans jury, n'a aucune valeur : la seule voie est
   * `deliberationApi`, qui travaille sur les notes reellement enregistrees.
   */
};

// ---------------------------------------------------------------------------
// 1 quater. Relances de facturation
// ---------------------------------------------------------------------------
export const relancesApi = {
  /**
   * Creances en retard a suivre. `retardMinimum` vaut 1 par defaut : une
   * facture echue aujourd'hui n'a pas de retard, et relancer le jour de
   * l'echeance serait injustifiable.
   */
  getARelancer: (params?: { sessionId?: string; retardMinimum?: number }) => {
    const requete = new URLSearchParams();
    if (params?.sessionId) requete.set("session_id", params.sessionId);
    if (params?.retardMinimum !== undefined)
      requete.set("retard_minimum", String(params.retardMinimum));
    const suffixe = requete.toString() ? `?${requete}` : "";
    return request<SyntheseRelances>(`/finances/relances${suffixe}`);
  },

  /** Constate une relance faite par le secretariat. */
  enregistrer: (payload: {
    etudiant_id: string;
    moyen: string;
    date_relance?: string;
    session_id?: string | null;
    message?: string | null;
  }) =>
    request<{ relance: Relance; resume: Record<string, unknown> }>("/finances/relances", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  historique: (etudiantId?: string, limite = 100) => {
    const requete = new URLSearchParams({ limite: String(limite) });
    if (etudiantId) requete.set("etudiant_id", etudiantId);
    return request<Relance[]>(`/finances/relances/historique?${requete}`);
  },

  /**
   * Constate le solde apres une relance. Appel distinct, volontaire : le
   * solde decrit la situation **apres** la relance, pas aujourd'hui. Un
   * paiement posterieur ne doit pas retroagir sur le passe.
   */
  constaterSolde: (etudiantId: string, niveau: number) =>
    request<{ etudiant_id: string; niveau: number; solde_apres: number; nb_relances_concernees: number }>(
      `/finances/relances/solde?etudiant_id=${encodeURIComponent(etudiantId)}&niveau=${niveau}`,
      { method: "POST" },
    ),

  /**
   * Lettre de relance imprimable.
   *
   * Le PDF rend l'instantane fige a la relance : il dit ce qui a ete reclame
   * ce jour-la, pas le solde du moment ou l'on imprime. Un encaissement
   * survenu entre-temps ne doit pas faire dire a la lettre autre chose que ce
   * qui a ete remis.
   */
  getLettre: (relanceId: string) =>
    requestBlob(`/finances/relances/${encodeURIComponent(relanceId)}/lettre`),

  /**
   * Envoie la lettre de relance (PDF) par email. Acte explicite : le
   * résultat revient sur la relance — ``envoye``, ``simule`` (SMTP non
   * configuré, l'application le dit) ou ``echec`` (à retenter).
   */
  envoyerLettreEmail: (relanceId: string) =>
    request<Relance>(
      `/finances/relances/${encodeURIComponent(relanceId)}/envoyer-email`,
      { method: "POST" }
    ),

  /**
   * Moyens declares par le serveur. L'ecran n'invente pas de liste : une
   * saisie libre diverge des le premier synonymes et rend l'historique
   * illisible.
   */
  getMoyens: () => request<string[]>("/finances/relances/moyens"),
};

// ---------------------------------------------------------------------------
// 6. Finances & Encaissements
// ---------------------------------------------------------------------------
export const financesApi = {
  // Paiements en ligne (lot 4b)
  creerLienPaiement: (data: { facture_id: string; montant?: number; validite_jours?: number }) =>
    request<PaiementIntentionCreee>("/finances/paiements-en-ligne", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getIntentionsPaiement: (statut?: string) =>
    request<PaiementIntention[]>(
      `/finances/paiements-en-ligne${statut ? `?statut=${statut}` : ""}`
    ),
  annulerLienPaiement: (intentionId: string) =>
    request<void>(`/finances/paiements-en-ligne/${intentionId}/annuler`, {
      method: "POST",
    }),
  /** Porte publique de la famille : sans authentification, gardée par le jeton. */
  lireLienPaiement: (token: string) =>
    request<ResumeFamille>(
      `/finances/public/paiement/${encodeURIComponent(token)}`,
      { skipAuth: true }
    ),
  confirmerLienPaiement: (token: string, data: { reference?: string }) =>
    request<ConfirmationPaiement>(
      `/finances/public/paiement/${encodeURIComponent(token)}/confirmer`,
      { method: "POST", body: JSON.stringify(data), skipAuth: true }
    ),

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

export const etudiantImportApi = {
  /** Contrat du fichier attendu : en-tetes documentes, sans donnee fictive. */
  getModele: () => request<ImportModele>("/etudiants/import/modele"),
  /**
   * Analyse un fichier (dry-run). Aucune ecriture metier : le backend
   * retourne un rapport ligne a ligne que l'administrateur valide ensuite.
   */
  analyser: (file: File, mode: ImportMode) => {
    const formData = new FormData();
    formData.append("fichier", file, file.name);
    formData.append("mode", mode);
    return request<ImportAnalyse>("/etudiants/import/analyse", {
      method: "POST",
      body: formData,
    });
  },
  /** Ecrit les lignes valides du lot. Idempotent. */
  valider: (batchId: string) =>
    request<ImportValidation>(`/etudiants/import/${encodeURIComponent(batchId)}/valider`, {
      method: "POST",
    }),
  annuler: (batchId: string) =>
    request<ImportBatch>(`/etudiants/import/${encodeURIComponent(batchId)}/annuler`, {
      method: "POST",
    }),
  lister: (limite = 20) => request<ImportBatch[]>(`/etudiants/import/?limite=${limite}`),
  getLot: (batchId: string) =>
    request<ImportBatch>(`/etudiants/import/${encodeURIComponent(batchId)}`),
  /** URL du modele CSV : le navigateur telecharge le fichier directement. */
  urlModeleCsv: () => `${API_BASE_URL}/etudiants/import/modele.csv`,
};

/** Telecharge le proces-verbal d'une seance de jury. */
export async function telechargerProcesVerbal(
  deliberationId: string
): Promise<ApiResult<Blob>> {
  return requestBlob(`/deliberation/${deliberationId}/proces-verbal`);
}

export const documentsApi = {
  /** Catalogue des types emissibles et conditions a satisfaire. */
  getTypes: () => request<TypeDocument[]>("/documents/types"),
  /**
   * Emet un document pour un etudiant.
   * `apercu: true` reserve un numero sans produire de PDF.
   */
  emettre: (
    etudiantId: string,
    data: { type_document: string; session_id?: string | null; apercu?: boolean }
  ) =>
    request<DocumentOfficiel>(
      `/documents/etudiants/${encodeURIComponent(etudiantId)}`,
      { method: "POST", body: JSON.stringify(data) }
    ),
  /** Verifie l'eligibilite et affiche la future reference, sans ecrire. */
  apercu: (etudiantId: string, data: { type_document: string; session_id?: string | null }) =>
    request<DocumentOfficiel>(
      `/documents/etudiants/${encodeURIComponent(etudiantId)}/apercu`,
      { method: "POST", body: JSON.stringify(data) }
    ),
  /** Emission en serie pour une classe ou une session. */
  emettreLot: (data: {
    type_document: string;
    classe_id?: string | null;
    session_id?: string | null;
    ignorer_les_non_eligibles?: boolean;
  }) =>
    request<LotDocuments>("/documents/lot", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  lister: (params: { etudiant_id?: string; type_document?: string; limite?: number } = {}) => {
    const query = new URLSearchParams();
    if (params.etudiant_id) query.set("etudiant_id", params.etudiant_id);
    if (params.type_document) query.set("type_document", params.type_document);
    if (params.limite) query.set("limite", String(params.limite));
    const suffix = query.toString();
    return request<DocumentOfficiel[]>(`/documents/${suffix ? `?${suffix}` : ""}`);
  },
  duplicata: (documentId: string, motif: string) =>
    request<DocumentOfficiel>(
      `/documents/${encodeURIComponent(documentId)}/duplicata`,
      { method: "POST", body: JSON.stringify({ motif }) }
    ),
  marquerDelivrance: (documentId: string) =>
    request<DocumentOfficiel>(
      `/documents/${encodeURIComponent(documentId)}/delivrance`,
      { method: "POST" }
    ),
  /** URL de telechargement : le navigateur recupere le PDF directement. */
  urlTelecharger: (documentId: string) =>
    `${API_BASE_URL}/documents/${encodeURIComponent(documentId)}/telecharger`,
};

/**
 * Nomenclature de matricule : la regle qui numerote les prochains dossiers.
 *
 * La regle s'applique aux **prochains** dossiers seulement. Les matricules deja
 * attribues ne sont jamais renommes : un certificat delivre doit rester
 * rattache a l'identifiant de l'epoque.
 */
export const matriculeApi = {
  get: () => request<MatriculeParametres>("/institution/matricule"),

  /** Jetons acceptes dans le modele, servis par le backend. */
  getJetons: () =>
    request<{ jetons: JetonMatricule[] }>("/institution/matricule/jetons"),

  update: (payload: MatriculeParametresMaj) =>
    request<MatriculeParametres>("/institution/matricule", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
};

/**
 * Export de la liste des etudiants.
 *
 * Le fichier est produit par le serveur, jamais par l'ecran : un export
 * construit dans le navigateur partirait de la liste affichee, donc de la
 * page courante, et l'institut croirait avoir exporte toute la promotion
 * alors qu'il n'en aurait sorti qu'une page.
 *
 * `classeId` restreint a une promotion. Sans lui, l'export porte sur tous les
 * etudiants — un usage legitime, pas une degradation.
 */
export const etudiantsExportApi = {
  /** Retourne l'URL de telechargement et le nombre de lignes exportees. */
  async telecharger(
    options: { classeId?: string; format?: "xlsx" | "csv" } = {}
  ): Promise<{ url: string; nombre: number; nomFichier: string }> {
    const params = new URLSearchParams();
    if (options.classeId) params.set("classe_id", options.classeId);
    params.set("format", options.format ?? "xlsx");
    const url = `${API_BASE_URL}/etudiants/export?${params.toString()}`;

    const reponse = await fetch(url, { headers: getHeaders() });
    if (!reponse.ok) {
      // L'echec doit dire pourquoi : un 404 sur une classe supprimee ne se
      // deduit pas d'un fichier qui ne s'ouvre pas.
      const detail = await reponse.json().catch(() => null);
      throw new Error(
        extractErrorMessage(
          detail?.detail ?? detail?.message,
          `Erreur serveur (${reponse.status})`
        )
      );
    }
    const nombre = Number(reponse.headers.get("X-Export-Etudiants") ?? "0");
    const entete = reponse.headers.get("Content-Disposition") ?? "";
    const trouve = /filename="([^"]+)"/.exec(entete);
    return {
      url: URL.createObjectURL(await reponse.blob()),
      nombre,
      nomFichier: trouve?.[1] ?? "etudiants.xlsx",
    };
  },
};

/**
 * Import de notes depuis un tableur.
 *
 * L'ecran ne construit **jamais** le fichier a envoyer, et n'invente **jamais**
 * une colonne : le serveur lit le fichier, decide ce qu'est une evaluation, et
 * renvoie le rapport. L'ecran se contente de le montrer.
 *
 * Le meme decouplage que l'import d'etudiants : `analyser` n'ecrit rien,
 * `valider` ecrit ce que le rapport annoncait. L'agent lit donc avant
 * d'ecrire, et l'ecran ne peut pas promettre autre chose que ce qu'il
 * enregistre.
 */
export const notesImportApi = {
  /** Le format attendu, sans aucune donnee d'etudiant. */
  modele: () => request<ModeleImportNotes>("/pedagogie/import/modele"),

  /**
   * Lecture seule : renvoie le rapport ligne a ligne.
   *
   * `semestreId` et `rattrapage` sont renvayes **dans** le rapport, et la
   * validation s'en sert. L'agent voit donc exactement ce qui va etre ecrit
   * avant de confirmer — le meme contrat que pour les notes.
   *
   * `rattrapage` sans `semestreId` est refuse par le serveur : les notes
   * remplaceraient une premiere tentative qu'on ne saurait pas laquelle.
   */
  analyser: (params: {
    fichier: File;
    classeId: string;
    matiereId: string;
    sessionId: string;
    semestreId?: string | null;
    rattrapage?: boolean;
  }) => {
    const corps = new FormData();
    corps.append("fichier", params.fichier);
    corps.append("classe_id", params.classeId);
    corps.append("matiere_id", params.matiereId);
    corps.append("session_id", params.sessionId);
    if (params.semestreId) corps.append("semestre_id", params.semestreId);
    corps.append("rattrapage", String(params.rattrapage ?? false));
    return request<RapportImportNotes>("/pedagogie/import/analyse", {
      method: "POST",
      body: corps,
    });
  },

  /** Ecrit exactement ce que le rapport a annonce. */
  valider: (rapport: unknown) =>
    request<BilanImportNotes>("/pedagogie/import/valider", {
      method: "POST",
      body: JSON.stringify(rapport),
    }),
};

export const rbacApi = {
  getPermissions: (filters?: { domaine?: string; actif?: boolean; systeme?: boolean }) => {
    const params = new URLSearchParams();
    if (filters?.domaine) params.append("domaine", filters.domaine);
    if (filters?.actif !== undefined) params.append("actif", String(filters.actif));
    if (filters?.systeme !== undefined) params.append("systeme", String(filters.systeme));
    const query = params.toString();
    return request<RbacPermission[]>(`/rbac/permissions${query ? `?${query}` : ""}`);
  },
  getRoles: () => request<RbacRole[]>("/rbac/roles"),
  createRole: (data: { code: string; libelle: string; description?: string | null; ordre?: number; actif?: boolean }) =>
    request<RbacRole>("/rbac/roles", { method: "POST", body: JSON.stringify(data) }),
  updateRole: (code: string, data: { libelle?: string; description?: string | null; ordre?: number; actif?: boolean }) =>
    request<RbacRole>(`/rbac/roles/${encodeURIComponent(code)}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteRole: (code: string) =>
    request<void>(`/rbac/roles/${encodeURIComponent(code)}`, { method: "DELETE" }),
  getRolePermissions: (code: string) =>
    request<RbacPermission[]>(`/rbac/roles/${encodeURIComponent(code)}/permissions`),
  replaceRolePermissions: (code: string, data: { permissions: string[]; motif?: string | null }) =>
    request<RbacRole>(`/rbac/roles/${encodeURIComponent(code)}/permissions`, { method: "PUT", body: JSON.stringify(data) }),
  addRolePermission: (code: string, data: { permission: string; motif?: string | null }) =>
    request<RbacPermission>(`/rbac/roles/${encodeURIComponent(code)}/permissions`, { method: "POST", body: JSON.stringify(data) }),
  removeRolePermission: (code: string, permissionCode: string) =>
    request<RbacRole>(`/rbac/roles/${encodeURIComponent(code)}/permissions/${encodeURIComponent(permissionCode)}`, { method: "DELETE" }),
  getUsers: (roleCode?: string) => {
    const params = new URLSearchParams();
    if (roleCode) params.set("role_code", roleCode);
    const query = params.toString();
    return request<RbacUserAccess[]>(`/rbac/users/roles${query ? `?${query}` : ""}`);
  },
  assignRole: (code: string, data: { user_ids: number[]; motif?: string | null; aligner_role_legacy?: boolean }) =>
    request<{ role_code: string; affectes: number[]; deja_affectes: number[] }>(`/rbac/roles/${encodeURIComponent(code)}/users`, { method: "POST", body: JSON.stringify(data) }),
  unassignRole: (code: string, userId: number) =>
    request<void>(`/rbac/roles/${encodeURIComponent(code)}/users/${userId}`, { method: "DELETE" }),
  getUserPermissions: (userId: number) =>
    request<RbacUserPermissions>(`/rbac/users/${userId}/permissions`),
};

export const auditApi = {
  getEvents: (filters?: {
    action?: string;
    resourceType?: string;
    resourceId?: string;
    actorId?: number;
    limit?: number;
  }) => {
    const params = new URLSearchParams();
    if (filters?.action) params.append("action", filters.action);
    if (filters?.resourceType) params.append("resource_type", filters.resourceType);
    if (filters?.resourceId) params.append("resource_id", filters.resourceId);
    if (filters?.actorId !== undefined) params.append("actor_id", String(filters.actorId));
    if (filters?.limit !== undefined) params.append("limit", String(filters.limit));
    return request<AuditEvent[]>(`/audit/events?${params.toString()}`);
  },
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
  etudiantImport: etudiantImportApi,
  documents: documentsApi,
  rbac: rbacApi,
  portals: portalsApi,
  admissions: admissionsApi,
};
