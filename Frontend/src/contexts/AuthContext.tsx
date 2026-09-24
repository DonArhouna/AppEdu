import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { authApi, type ApiResult } from "@/services/apiClient";
import type { UserRole } from "@/contexts/RBACContext";

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
}

interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<ApiResult<LoginResponse>>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AUTH_UNAUTHORIZED_EVENT = "emp_auth_unauthorized";

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const clearSession = useCallback(() => {
    authApi.logout();
    setUser(null);
    setIsLoading(false);
  }, []);

  const refreshUser = useCallback(async () => {
    if (!authApi.getToken()) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    const result = await authApi.getMe();
    if (result.error || !result.data) {
      clearSession();
      return;
    }
    setUser(result.data as AuthUser);
    setIsLoading(false);
  }, [clearSession]);

  useEffect(() => {
    void refreshUser();
    const handleUnauthorized = () => clearSession();
    window.addEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized);
    return () => window.removeEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized);
  }, [clearSession, refreshUser]);

  const login = useCallback(async (email: string, password: string) => {
    const result = await authApi.login(email, password);
    if (result.error || !result.data?.user) {
      return result;
    }
    setUser(result.data.user as AuthUser);
    setIsLoading(false);
    return result;
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isLoading,
      login,
      logout: clearSession,
      refreshUser,
    }),
    [clearSession, isLoading, login, refreshUser, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextValue => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth doit être utilisé dans AuthProvider.");
  }
  return context;
};
