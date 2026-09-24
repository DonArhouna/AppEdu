import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Calendar,
  LogOut,
  Menu,
  Moon,
  Search,
  Settings,
  ShieldCheck,
  Sun,
  User,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { useRBAC } from "@/contexts/RBACContext";
import { useAuth } from "@/contexts/AuthContext";
import { GlobalCommandPalette } from "./GlobalCommandPalette";
import { academicContextApi } from "@/services/apiClient";

interface NavbarProps {
  onMenuClick: () => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

type ThemePreference = "light" | "dark" | "system";

const getInitialTheme = (): ThemePreference => {
  if (typeof window === "undefined") return "light";
  const stored = window.localStorage.getItem("theme");
  if (stored === "light" || stored === "dark") return stored;
  return "system";
};

export const Navbar = ({ onMenuClick }: NavbarProps) => {
  const navigate = useNavigate();
  const [academicYear, setAcademicYear] = useState("");
  const [commandOpen, setCommandOpen] = useState(false);
  const [themePreference, setThemePreference] = useState<ThemePreference>(getInitialTheme);
  const [systemPrefersDark, setSystemPrefersDark] = useState(() =>
    typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches
  );
  const { currentRoleInfo } = useRBAC();
  const { user } = useAuth();
  const isDark = themePreference === "dark" || (themePreference === "system" && systemPrefersDark);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = (event: MediaQueryListEvent) => setSystemPrefersDark(event.matches);
    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", isDark);
    window.localStorage.setItem("theme", themePreference);
  }, [isDark, themePreference]);

  useEffect(() => {
    let active = true;
    const loadAcademicContext = async () => {
      const result = await academicContextApi.get();
      if (!active || result.error || !result.data) return;
      setAcademicYear(result.data.annee_academique);
    };
    void loadAcademicContext();
    return () => {
      active = false;
    };
  }, []);

  const toggleTheme = () => {
    setThemePreference(isDark ? "light" : "dark");
    toast.success(isDark ? "Mode clair activé." : "Mode sombre activé.", { duration: 1500 });
  };

  return (
    <header className="sticky top-0 z-30 w-full bg-background/80 px-3 pb-2 pt-3 backdrop-blur-md transition-all sm:px-5 md:px-6">
      <div
        className={cn(
          "flex h-14 items-center gap-3 rounded-2xl border border-border/70 px-4",
          "bg-[hsl(var(--navbar-background))] shadow-[var(--shadow-sm)]",
          "backdrop-blur-md supports-[backdrop-filter]:bg-[hsl(var(--navbar-background)/0.95)]"
        )}
      >
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={onMenuClick}
          aria-label="Ouvrir le menu de navigation"
          className="h-8 w-8 rounded-xl hover:bg-muted md:hidden"
        >
          <Menu className="h-4 w-4" />
        </Button>

        <div className="mx-2 min-w-0 flex-1 sm:max-w-md">
          <Button
            type="button"
            variant="outline"
            onClick={() => setCommandOpen(true)}
            aria-label="Ouvrir la recherche globale"
            className="group h-8.5 w-full justify-between rounded-xl border-border/70 bg-muted/40 px-3 text-xs text-muted-foreground transition-all hover:bg-muted/70 hover:text-foreground"
          >
            <span className="flex min-w-0 items-center gap-2">
              <Search className="h-3.5 w-3.5 shrink-0 text-primary transition-transform group-hover:scale-110" />
              <span className="hidden truncate sm:inline">Rechercher étudiant, cours, salle...</span>
              <span className="sm:hidden">Recherche...</span>
            </span>
            <kbd className="pointer-events-none hidden h-5 select-none items-center gap-1 rounded-md border border-border bg-background px-1.5 font-mono text-[10px] font-semibold text-muted-foreground shadow-2xs md:inline-flex">
              <span className="text-xs">⌘</span>K
            </kbd>
          </Button>
        </div>

        <div className="flex items-center gap-1.5">
          <div
            className={cn("hidden h-8 items-center gap-1.5 rounded-xl border px-2.5 text-xs font-semibold lg:flex", currentRoleInfo.colorClass)}
            title={`Rôle serveur : ${currentRoleInfo.label}`}
          >
            <ShieldCheck className="h-3.5 w-3.5" />
            <span className="hidden xl:inline">{currentRoleInfo.label}</span>
            <Badge className="border-none bg-background/60 px-1.5 py-0 text-[9px] font-bold text-inherit">
              {currentRoleInfo.badge}
            </Badge>
          </div>

          <div
            className="flex h-8 max-w-[170px] items-center gap-1.5 rounded-xl border border-border/60 bg-muted/25 px-2.5 text-xs"
            aria-label={academicYear ? `Année académique active : ${academicYear}` : "Aucune année académique active"}
            title="Année académique active"
          >
            <Calendar className="h-3.5 w-3.5 shrink-0 text-amber-500" />
            <span className="hidden font-normal text-muted-foreground sm:inline">Année :</span>
            <span className="truncate font-semibold text-foreground">{academicYear || "Non définie"}</span>
          </div>

          <div className="mx-0.5 h-5 w-px bg-border" />

          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            title={isDark ? "Passer en mode clair" : "Passer en mode sombre"}
            aria-label={isDark ? "Activer le mode clair" : "Activer le mode sombre"}
            className="h-8 w-8 rounded-xl text-foreground hover:bg-muted"
          >
            {isDark ? <Sun className="h-4 w-4 text-amber-400" /> : <Moon className="h-4 w-4 text-slate-500" />}
          </Button>

          <div className="mx-0.5 h-5 w-px bg-border" />

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                aria-label="Ouvrir le menu du profil"
                className="flex h-8 items-center gap-2 rounded-xl px-2 hover:bg-muted"
              >
                <Avatar className="h-7 w-7 rounded-xl">
                  <AvatarFallback className="rounded-xl bg-primary/10 text-[10px] font-bold text-primary">
                    {`${user?.prenom?.[0] || ""}${user?.nom?.[0] || ""}`.toUpperCase() || "EMP"}
                  </AvatarFallback>
                </Avatar>
                <span className="hidden flex-col items-start sm:flex">
                  <span className="text-[11px] font-semibold leading-none text-foreground">
                    {user ? `${user.prenom} ${user.nom}` : "Utilisateur"}
                  </span>
                  <span className="mt-0.5 text-[9px] leading-none text-muted-foreground">
                    {currentRoleInfo.label}
                  </span>
                </span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-52 rounded-2xl border-border/60 p-1.5 shadow-xl">
              <div className="mb-1 px-2 py-2">
                <p className="text-sm font-bold">{user ? `${user.prenom} ${user.nom}` : "Utilisateur"}</p>
                <p className="text-xs text-muted-foreground">{user?.email || ""}</p>
              </div>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => navigate("/profil")} className="cursor-pointer gap-2 rounded-xl text-xs">
                <User className="h-3.5 w-3.5 text-primary" /> Mon profil
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => navigate("/parametres-compte")} className="cursor-pointer gap-2 rounded-xl text-xs">
                <Settings className="h-3.5 w-3.5 text-primary" /> Paramètres
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => navigate("/deconnexion")}
                className="cursor-pointer gap-2 rounded-xl text-xs text-destructive focus:text-destructive"
              >
                <LogOut className="h-3.5 w-3.5" /> Déconnexion
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <GlobalCommandPalette open={commandOpen} onOpenChange={setCommandOpen} />
    </header>
  );
};
