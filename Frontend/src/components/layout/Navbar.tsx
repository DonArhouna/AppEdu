import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Bell, User, Settings, LogOut, Calendar, Check,
  Sun, Moon, Menu, CheckCheck, Trash2, UserPlus, CreditCard, AlertCircle,
  Search, ShieldCheck
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { useRBAC, AVAILABLE_ROLES } from "@/contexts/RBACContext";
import { GlobalCommandPalette } from "./GlobalCommandPalette";

interface NavbarProps {
  onMenuClick: () => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

interface NotificationItem {
  id: string;
  title: string;
  description: string;
  time: string;
  read: boolean;
  type: "user" | "payment" | "alert";
}

export const Navbar = ({ onMenuClick }: NavbarProps) => {
  const navigate = useNavigate();
  const [academicYear, setAcademicYear] = useState("2025-2026");
  const [commandOpen, setCommandOpen] = useState(false);
  const { currentRole, setCurrentRole, currentRoleInfo } = useRBAC();

  const [isDark, setIsDark] = useState(() => {
    if (typeof window === "undefined") return false;
    const stored = localStorage.getItem("theme");
    if (stored) return stored === "dark";
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  });

  useEffect(() => {
    const root = document.documentElement;
    if (isDark) {
      root.classList.add("dark");
      localStorage.setItem("theme", "dark");
    } else {
      root.classList.remove("dark");
      localStorage.setItem("theme", "light");
    }
  }, [isDark]);

  const toggleTheme = () => {
    setIsDark((prev) => !prev);
    toast.success(!isDark ? "Mode Sombre activé 🌙" : "Mode Clair activé ☀️", {
      duration: 1500,
    });
  };

  const [notifications, setNotifications] = useState<NotificationItem[]>([
    {
      id: "1",
      title: "Nouvelle pré-inscription",
      description: "Marie Dupont a soumis son dossier en Master 1 Génie Logiciel.",
      time: "10 min",
      read: false,
      type: "user",
    },
    {
      id: "2",
      title: "Paiement Wave Reçu",
      description: "Règlement de 375 000 FCFA effectué par Kouassi Konan.",
      time: "45 min",
      read: false,
      type: "payment",
    },
    {
      id: "3",
      title: "Modification d'emploi du temps",
      description: "Le cours de Réseaux du Mercredi a été déplacé en salle A204.",
      time: "2h",
      read: true,
      type: "alert",
    },
  ]);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const markAllRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    toast.success("Toutes les notifications marquées comme lues.");
  };

  const clearAll = () => {
    setNotifications([]);
    toast.info("Notifications effacées.");
  };

  const NotifIcon = ({ type }: { type: NotificationItem["type"] }) => {
    const map = {
      user: { icon: UserPlus, color: "text-blue-500 bg-blue-50 dark:bg-blue-950" },
      payment: { icon: CreditCard, color: "text-emerald-500 bg-emerald-50 dark:bg-emerald-950" },
      alert: { icon: AlertCircle, color: "text-amber-500 bg-amber-50 dark:bg-amber-950" },
    };
    const { icon: Icon, color } = map[type];
    return (
      <div className={cn("p-2 rounded-xl shrink-0", color)}>
        <Icon className="h-3.5 w-3.5" />
      </div>
    );
  };

  return (
    <header className="sticky top-0 z-30 w-full px-3 sm:px-5 md:px-6 pt-3 pb-2 bg-background/80 backdrop-blur-md transition-all">
      <div
        className={cn(
          "flex h-14 items-center px-4 gap-3 rounded-2xl border border-border/70",
          "bg-[hsl(var(--navbar-background))] shadow-[var(--shadow-sm)]",
          "backdrop-blur-md supports-[backdrop-filter]:bg-[hsl(var(--navbar-background)/0.95)]"
        )}
      >
        {/* ── Left: Mobile hamburger + Brand ── */}
        <div className="flex items-center gap-3">
          {/* Mobile hamburger */}
          <Button
            variant="ghost"
            size="icon"
            onClick={onMenuClick}
            className="md:hidden h-8 w-8 rounded-xl hover:bg-muted"
          >
            <Menu className="h-4 w-4" />
          </Button>
        </div>

        {/* ── Centre: Command Palette Trigger (Ctrl + K) ── */}
        <div className="flex-1 max-w-md mx-2">
          <Button
            variant="outline"
            onClick={() => setCommandOpen(true)}
            className="w-full justify-between h-8.5 px-3 rounded-xl bg-muted/40 hover:bg-muted/70 text-xs text-muted-foreground border-border/70 hover:text-foreground transition-all group"
          >
            <div className="flex items-center gap-2">
              <Search className="h-3.5 w-3.5 text-primary group-hover:scale-110 transition-transform" />
              <span className="hidden sm:inline">Rechercher étudiant, cours, salle...</span>
              <span className="sm:hidden">Recherche...</span>
            </div>
            <kbd className="pointer-events-none hidden md:inline-flex h-5 select-none items-center gap-1 rounded-md border border-border bg-background px-1.5 font-mono text-[10px] font-semibold text-muted-foreground shadow-2xs">
              <span className="text-xs">⌘</span>K
            </kbd>
          </Button>
        </div>

        {/* ── Right: RBAC Role Switcher, Academic Year, Theme, Notifications, Profile ── */}
        <div className="flex items-center gap-1.5">

          {/* Role Switcher (Simulateur de rôle RBAC) */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className={cn("h-8 px-2.5 rounded-xl text-xs font-semibold gap-1.5 border transition-all", currentRoleInfo.colorClass)}
                title="Changer de rôle pour tester les permissions du menu"
              >
                <ShieldCheck className="h-3.5 w-3.5" />
                <span className="hidden xl:inline">{currentRoleInfo.label}</span>
                <Badge className="ml-0.5 px-1.5 py-0 text-[9px] font-bold border-none bg-background/60 text-inherit">
                  {currentRoleInfo.badge}
                </Badge>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-64 rounded-2xl shadow-xl border-border/60 p-1.5">
              <DropdownMenuLabel className="text-[10px] uppercase font-bold text-muted-foreground px-2 pb-1 flex items-center justify-between">
                <span>Simulateur de Rôle (RBAC)</span>
                <span className="text-[9px] font-normal lowercase text-muted-foreground">test dynamique</span>
              </DropdownMenuLabel>
              {AVAILABLE_ROLES.map((role) => (
                <DropdownMenuItem
                  key={role.id}
                  onClick={() => {
                    setCurrentRole(role.id);
                    toast.success(`Rôle actif basculé sur : ${role.label}`);
                  }}
                  className="flex flex-col items-start gap-0.5 rounded-xl p-2 cursor-pointer"
                >
                  <div className="flex items-center justify-between w-full">
                    <span className="font-semibold text-xs text-foreground">{role.label}</span>
                    {role.id === currentRole && <Check className="h-3.5 w-3.5 text-primary" />}
                  </div>
                  <span className="text-[10px] text-muted-foreground line-clamp-1">{role.description}</span>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Academic Year Switcher */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 px-2.5 rounded-xl text-xs font-semibold gap-1.5 hover:bg-muted text-[hsl(var(--navbar-foreground))]"
              >
                <Calendar className="h-3.5 w-3.5 text-amber-500" />
                <span className="hidden sm:inline opacity-60 font-normal">Année :</span>
                <span>{academicYear}</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-52 rounded-2xl shadow-xl border-border/60 p-1.5">
              <DropdownMenuLabel className="text-[10px] uppercase font-bold text-muted-foreground px-2 pb-1">
                Année Académique
              </DropdownMenuLabel>
              {["2025-2026", "2024-2025", "2023-2024"].map((year) => (
                <DropdownMenuItem
                  key={year}
                  onClick={() => {
                    setAcademicYear(year);
                    toast.info(`Basculé sur ${year}`);
                  }}
                  className="flex items-center justify-between rounded-xl text-xs cursor-pointer"
                >
                  <span className="font-semibold">{year}</span>
                  {year === academicYear && (
                    <Check className="h-3.5 w-3.5 text-primary" />
                  )}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Divider */}
          <div className="h-5 w-px bg-border mx-0.5" />

          {/* Dark / Light Mode Toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            title={isDark ? "Passer en mode clair" : "Passer en mode sombre"}
            className="h-8 w-8 rounded-xl hover:bg-muted text-[hsl(var(--navbar-foreground))]"
          >
            {isDark ? (
              <Sun className="h-4 w-4 text-amber-400 transition-transform duration-300 rotate-0 hover:rotate-45" />
            ) : (
              <Moon className="h-4 w-4 text-slate-500 transition-transform duration-300" />
            )}
          </Button>

          {/* Notifications */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="relative h-8 w-8 rounded-xl hover:bg-muted text-[hsl(var(--navbar-foreground))]"
              >
                <Bell className="h-4 w-4" />
                {unreadCount > 0 && (
                  <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-destructive badge-pulse" />
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="end"
              className="w-80 sm:w-96 rounded-2xl shadow-xl border-border/60 p-0 overflow-hidden"
            >
              {/* Header */}
              <div className="flex items-center justify-between px-4 py-3 border-b border-border/60 bg-muted/30">
                <div className="flex items-center gap-2">
                  <Bell className="h-4 w-4 text-primary" />
                  <span className="font-bold text-sm">Notifications</span>
                  {unreadCount > 0 && (
                    <Badge className="h-5 px-1.5 text-[10px] bg-destructive text-white rounded-full">
                      {unreadCount}
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="icon" onClick={markAllRead} className="h-6 w-6 rounded-lg" title="Tout lire">
                    <CheckCheck className="h-3.5 w-3.5" />
                  </Button>
                  <Button variant="ghost" size="icon" onClick={clearAll} className="h-6 w-6 rounded-lg text-destructive hover:text-destructive" title="Effacer">
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>

              {/* List */}
              <div className="max-h-80 overflow-y-auto scrollbar-thin divide-y divide-border/40">
                {notifications.length === 0 ? (
                  <div className="p-8 text-center">
                    <Bell className="h-8 w-8 text-muted-foreground/30 mx-auto mb-2" />
                    <p className="text-xs text-muted-foreground">Aucune notification</p>
                  </div>
                ) : (
                  notifications.map((n) => (
                    <div
                      key={n.id}
                      className={cn(
                        "flex items-start gap-3 px-4 py-3 transition-colors cursor-pointer",
                        !n.read ? "bg-primary/4 hover:bg-primary/8" : "hover:bg-muted/40 opacity-70"
                      )}
                      onClick={() => setNotifications((prev) =>
                        prev.map((item) => item.id === n.id ? { ...item, read: true } : item)
                      )}
                    >
                      <NotifIcon type={n.type} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <p className={cn("text-xs truncate", !n.read ? "font-semibold" : "font-medium text-muted-foreground")}>
                            {n.title}
                          </p>
                          <span className="text-[10px] text-muted-foreground shrink-0">il y a {n.time}</span>
                        </div>
                        <p className="text-[11px] text-muted-foreground mt-0.5 leading-snug line-clamp-2">
                          {n.description}
                        </p>
                      </div>
                      {!n.read && (
                        <div className="h-2 w-2 rounded-full bg-primary shrink-0 mt-1" />
                      )}
                    </div>
                  ))
                )}
              </div>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Divider */}
          <div className="h-5 w-px bg-border mx-0.5" />

          {/* User Profile */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                className="flex items-center gap-2 h-8 px-2 rounded-xl hover:bg-muted"
              >
                <Avatar className="h-7 w-7 rounded-xl">
                  <AvatarFallback className="rounded-xl text-[10px] font-bold bg-primary/10 text-primary">
                    MD
                  </AvatarFallback>
                </Avatar>
                <div className="hidden sm:flex flex-col items-start">
                  <span className="text-[11px] font-semibold text-[hsl(var(--navbar-foreground))] leading-none">
                    Marie Dupont
                  </span>
                  <span className="text-[9px] text-muted-foreground leading-none mt-0.5">Admin Principal</span>
                </div>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-52 rounded-2xl shadow-xl border-border/60 p-1.5">
              <div className="px-2 py-2 mb-1">
                <p className="text-sm font-bold">Marie Dupont</p>
                <p className="text-xs text-muted-foreground">admin@edumanagepro.com</p>
              </div>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => navigate("/profil")} className="rounded-xl cursor-pointer text-xs gap-2">
                <User className="h-3.5 w-3.5 text-primary" /> Mon Profil
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => navigate("/parametres-compte")} className="rounded-xl cursor-pointer text-xs gap-2">
                <Settings className="h-3.5 w-3.5 text-primary" /> Paramètres
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => navigate("/deconnexion")}
                className="rounded-xl cursor-pointer text-xs gap-2 text-destructive focus:text-destructive"
              >
                <LogOut className="h-3.5 w-3.5" /> Déconnexion
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Global Command Palette (Ctrl + K / Cmd + K) */}
      <GlobalCommandPalette open={commandOpen} onOpenChange={setCommandOpen} />
    </header>
  );
};
