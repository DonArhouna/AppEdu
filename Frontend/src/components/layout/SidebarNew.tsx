import { useState, useEffect, useMemo } from "react";
import { Link, useLocation } from "react-router-dom";
import { NavLink } from "@/components/NavLink";
import {
  LayoutDashboard, UserPlus, Users, FileCheck, GraduationCap,
  BookOpen, Building2, MapPin, UserCog, BookMarked,
  CalendarDays, FileText, ClipboardCheck, ChevronDown,
  DollarSign, CreditCard, TrendingUp, BarChart3, School,
  Briefcase, Wallet, UserCircle, Settings, Search, X, Sliders,
  ShieldCheck, Sparkles, Layers, ChevronLeft, ChevronRight,
} from "lucide-react";
import logo from "@/assets/logo.svg";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip, TooltipContent, TooltipProvider, TooltipTrigger
} from "@/components/ui/tooltip";
import {
  HoverCard, HoverCardContent, HoverCardTrigger
} from "@/components/ui/hover-card";

import { useRBAC, type UserRole } from "@/contexts/RBACContext";

/* ─────────────────────────────────────────────────────────────────── */
/* DATA & CATEGORIES HIÉRARCHIQUES                                     */
/* ─────────────────────────────────────────────────────────────────── */

export interface MenuItem {
  title: string;
  icon: React.ElementType;
  href: string;
  badge?: string;
  badgeVariant?: "default" | "secondary" | "destructive" | "outline" | "warning";
  description?: string;
  allowedRoles?: UserRole[];
}

export interface NavigationSection {
  id: string;
  title: string;
  icon: React.ElementType;
  colorClass: string;
  bgLightClass: string;
  allowedRoles?: UserRole[];
  items: MenuItem[];
}

export const navigationSections: NavigationSection[] = [
  {
    id: "structure",
    title: "Structure Académique",
    icon: Building2,
    colorClass: "text-blue-500",
    bgLightClass: "bg-blue-500/10",
    allowedRoles: ["ADMIN", "DIRECTEUR_ETUDES"],
    items: [
      { title: "Campus", icon: MapPin, href: "/campus", description: "Gestion multi-campus et implantations" },
      { title: "Départements", icon: Building2, href: "/departements", description: "Unités académiques et facultés" },
      { title: "Filières & Cursus", icon: BookOpen, href: "/filieres", description: "Programmes de formation et diplômes" },
      { title: "Promotions & Cohortes", icon: GraduationCap, href: "/promotions", description: "Sessions et années d'études" },
      { title: "Sessions Académiques", icon: CalendarDays, href: "/sessions", description: "Sessions et périodes de paiement" },
      { title: "Unités d'Ens. (UE)", icon: Layers, href: "/ue", description: "Unités d'enseignement et crédits ECTS" },
      { title: "Matières (ECUE)", icon: BookMarked, href: "/matieres", description: "Modules, coefficients et volumes horaires" },
    ],
  },
  {
    id: "admissions",
    title: "Admissions & Scolarité",
    icon: School,
    colorClass: "text-sky-500",
    bgLightClass: "bg-sky-500/10",
    allowedRoles: ["ADMIN", "SECRETARIAT", "DIRECTEUR_ETUDES"],
    items: [
      { title: "Pré-inscriptions", icon: UserPlus, href: "/pre-inscription", description: "Candidatures persistées et suivi des dossiers" },
      { title: "Validation dossiers", icon: FileCheck, href: "/validation", description: "Pièces, décisions et conversion étudiants" },
      { title: "Registre Étudiants", icon: Users, href: "/etudiants", description: "Dossiers scolaires et fiches individuelles" },
    ],
  },
  {
    id: "pedagogie",
    title: "Pédagogie & Évaluations",
    icon: BookOpen,
    colorClass: "text-emerald-500",
    bgLightClass: "bg-emerald-500/10",
    allowedRoles: ["ADMIN", "DIRECTEUR_ETUDES", "ENSEIGNANT"],
    items: [
      { title: "Emplois du Temps", icon: CalendarDays, href: "/emplois-du-temps", description: "Plannings hebdomadaires et réservations" },
      { title: "Carnet de Notes", icon: FileText, href: "/notes", description: "Saisie des notes, CC et examens" },
      { title: "Suivi des Absences", icon: ClipboardCheck, href: "/absences", description: "Appels de classe et assiduité" },
    ],
  },
  {
    id: "personnel",
    title: "Corps Enseignant & RH",
    icon: Briefcase,
    colorClass: "text-violet-500",
    bgLightClass: "bg-violet-500/10",
    allowedRoles: ["ADMIN", "SECRETARIAT", "ENSEIGNANT"],
    items: [
      { title: "Enseignants", icon: GraduationCap, href: "/enseignants", description: "Corps professoral, vacataires et titulaires", allowedRoles: ["ADMIN", "SECRETARIAT"] },
      { title: "Personnel & RH", icon: UserCog, href: "/personnel", description: "Personnel administratif et technique", allowedRoles: ["ADMIN", "SECRETARIAT"] },
      { title: "Portail Enseignant", icon: GraduationCap, href: "/portail-enseignant", description: "Espace réservé aux professeurs", allowedRoles: ["ENSEIGNANT"] },
    ],
  },
  {
    id: "finances",
    title: "Facturation & Finances",
    icon: Wallet,
    colorClass: "text-amber-500",
    bgLightClass: "bg-amber-500/10",
    allowedRoles: ["ADMIN", "COMPTABILITE"],
    items: [
      { title: "Frais de Scolarité", icon: DollarSign, href: "/frais-scolarite", description: "Grilles tarifaires, bourses et remises" },
      { title: "Factures", icon: FileText, href: "/factures", description: "Échéanciers et factures émises" },
      { title: "Paiements", icon: CreditCard, href: "/paiements", description: "Encaissements, virements et mobile money" },
      { title: "Reporting Financier", icon: TrendingUp, href: "/reporting-financier", description: "Balance âgée, trésorerie et bilans" },
    ],
  },
  {
    id: "portails",
    title: "Vie Scolaire & Portails",
    icon: UserCircle,
    colorClass: "text-teal-500",
    bgLightClass: "bg-teal-500/10",
    allowedRoles: ["ADMIN", "ETUDIANT", "ENSEIGNANT", "SECRETARIAT"],
    items: [
      { title: "Espace Étudiant", icon: UserCircle, href: "/espace-etudiant", description: "Portail self-service étudiant", allowedRoles: ["ETUDIANT"] },
    ],
  },
  {
    id: "pilotage",
    title: "Pilotage & Analytics",
    icon: BarChart3,
    colorClass: "text-indigo-500",
    bgLightClass: "bg-indigo-500/10",
    allowedRoles: ["ADMIN", "DIRECTEUR_ETUDES", "COMPTABILITE"],
    items: [
      { title: "Analytics & BI", icon: BarChart3, href: "/analytics", badge: "KPI", badgeVariant: "secondary", description: "Statistiques d'établissement et indicateurs" },
    ],
  },
  {
    id: "administration",
    title: "Administration & Sécurité",
    icon: Settings,
    colorClass: "text-rose-500",
    bgLightClass: "bg-rose-500/10",
    allowedRoles: ["ADMIN"],
    items: [
      { title: "Comptes Utilisateurs", icon: Users, href: "/utilisateurs", description: "Accès au système et annuaire" },
      { title: "Rôles & Permissions", icon: ShieldCheck, href: "/roles-permissions", description: "Matrice de sécurité RBAC" },
      { title: "Paramétrage Général", icon: Sliders, href: "/parametrage", description: "Configuration de l'établissement" },
    ],
  },
];

/* ─────────────────────────────────────────────────────────────────── */
/* COMPONENT                                                           */
/* ─────────────────────────────────────────────────────────────────── */

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export const Sidebar = ({
  isOpen,
  onClose,
  isCollapsed = false,
  onToggleCollapse,
}: SidebarProps) => {
  const location = useLocation();
  const [searchQuery, setSearchQuery] = useState("");
  const { hasAccess, currentRoleInfo } = useRBAC();

  // Filter sections by active user role permissions
  const accessibleSections = useMemo(() => {
    return navigationSections
      .filter((section) => hasAccess(section.allowedRoles))
      .map((section) => ({
        ...section,
        items: section.items.filter((item) => hasAccess(item.allowedRoles)),
      }))
      .filter((section) => section.items.length > 0);
  }, [hasAccess]);

  const [openSections, setOpenSections] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {};
    navigationSections.forEach((m) => { init[m.id] = true; });
    return init;
  });

  // Keep active section open when route changes
  useEffect(() => {
    if (!isOpen) return;
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    const previousFocus = document.activeElement as HTMLElement | null;
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("keydown", handleEscape);
      previousFocus?.focus();
    };
  }, [isOpen, onClose]);

  useEffect(() => {
    accessibleSections.forEach((mod) => {
      const active = mod.items.some(
        (item) => location.pathname === item.href || location.pathname.startsWith(item.href + "/")
      );
      if (active) setOpenSections((prev) => ({ ...prev, [mod.id]: true }));
    });
  }, [location.pathname, accessibleSections]);

  const filteredSections = useMemo(() => {
    if (!searchQuery.trim()) return accessibleSections;
    const q = searchQuery.toLowerCase();
    return accessibleSections
      .map((section) => ({
        ...section,
        items: section.items.filter(
          (item) =>
            item.title.toLowerCase().includes(q) ||
            section.title.toLowerCase().includes(q) ||
            item.description?.toLowerCase().includes(q)
        ),
      }))
      .filter((section) => section.items.length > 0);
  }, [searchQuery, accessibleSections]);

  const isActive = (href: string) =>
    location.pathname === href || (href !== "/" && location.pathname.startsWith(href + "/"));

  const isDashboardActive = location.pathname === "/";

  const closeOnMobile = () => {
    if (window.innerWidth < 768) onClose();
  };

  const getBadgeClass = (variant?: MenuItem["badgeVariant"]) => {
    switch (variant) {
      case "destructive":
        return "bg-destructive/15 text-destructive border-destructive/20";
      case "warning":
        return "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/20";
      case "secondary":
        return "bg-secondary text-secondary-foreground border-transparent";
      default:
        return "bg-primary/15 text-primary border-primary/20";
    }
  };

  /* ─── Collapsed Icon Pill with Hover Submenu ─── */
  const CollapsedModuleGroup = ({ section }: { section: NavigationSection }) => {
    const SectionIcon = section.icon;
    const hasActive = section.items.some((i) => isActive(i.href));

    return (
      <HoverCard openDelay={80} closeDelay={120}>
        <HoverCardTrigger asChild>
          <button
            type="button"
            aria-label={section.title}
            className={cn(
              "flex items-center justify-center h-10 w-10 rounded-xl mx-auto cursor-pointer transition-all duration-150 relative group focus:outline-none focus-visible:ring-2 focus-visible:ring-primary",
              hasActive
                ? "bg-primary/15 text-primary font-semibold shadow-xs"
                : "text-[hsl(var(--sidebar-muted))] hover:bg-sidebar-accent hover:text-sidebar-foreground"
            )}
          >
            <SectionIcon className={cn("h-4.5 w-4.5 transition-transform group-hover:scale-110", section.colorClass)} />
            {hasActive && (
              <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-primary rounded-r-full" />
            )}
          </button>
        </HoverCardTrigger>
        <HoverCardContent
          side="right"
          align="start"
          sideOffset={14}
          className={cn(
            "w-60 p-2 rounded-2xl border border-border/80 shadow-[var(--shadow-xl)]",
            "bg-[hsl(var(--sidebar-background))] backdrop-blur-md"
          )}
        >
          {/* Group label */}
          <div className="flex items-center gap-2 px-2.5 py-2 mb-1 border-b border-border/50">
            <div className={cn("p-1.5 rounded-lg", section.bgLightClass)}>
              <SectionIcon className={cn("h-3.5 w-3.5", section.colorClass)} />
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-[11px] font-bold tracking-wide text-foreground truncate">
                {section.title}
              </span>
              <span className="text-[9px] text-muted-foreground">
                {section.items.length} fonctionnalités
              </span>
            </div>
          </div>

          <div className="space-y-0.5 mt-1">
            {section.items.map((item) => {
              const ItemIcon = item.icon;
              const active = isActive(item.href);
              return (
                <NavLink
                  key={item.href}
                  to={item.href}
                  onClick={closeOnMobile}
                  className={cn(
                    "flex items-center gap-2.5 px-2.5 py-2 rounded-xl text-xs font-medium transition-all group",
                    active
                      ? "bg-primary/12 text-primary font-semibold"
                      : "text-sidebar-foreground hover:bg-sidebar-accent"
                  )}
                >
                  <ItemIcon className={cn("h-3.5 w-3.5 shrink-0 transition-transform group-hover:scale-110", active ? "text-primary" : "text-[hsl(var(--sidebar-muted))]")} />
                  <span className="flex-1 truncate">{item.title}</span>
                  {item.badge && (
                    <Badge className={cn("ml-auto h-4 px-1.5 text-[9px] font-bold border", getBadgeClass(item.badgeVariant))}>
                      {item.badge}
                    </Badge>
                  )}
                </NavLink>
              );
            })}
          </div>
        </HoverCardContent>
      </HoverCard>
    );
  };

  return (
    <TooltipProvider delayDuration={200}>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm md:hidden transition-opacity"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* ── Sidebar ── */}
      <aside
        aria-label="Navigation principale"
        className={cn(
          "fixed left-0 top-0 h-screen z-50 flex flex-col",
          "transition-all duration-300 ease-in-out",
          isCollapsed ? "w-[270px] md:w-[76px]" : "w-[270px]",
          isOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        )}
      >
        {/* Inner panel — floating card design */}
        <div className={cn(
          "flex flex-col flex-1 m-3 rounded-2xl overflow-hidden",
          "bg-[hsl(var(--sidebar-background))] border border-[hsl(var(--sidebar-border))]",
          "shadow-[var(--shadow-floating)]"
        )}>

          {/* ── Header ── */}
          <div className="flex h-15 items-center shrink-0 px-3.5 border-b border-[hsl(var(--sidebar-border))] bg-muted/10">
            {!isCollapsed ? (
              <>
                <Link
                  to="/"
                  className="flex items-center gap-3 group flex-1 min-w-0"
                  onClick={closeOnMobile}
                >
                  {/* Distinctive EMP Monogram Squircle Badge */}
                  <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-primary via-blue-600 to-indigo-600 flex items-center justify-center shrink-0 shadow-sm shadow-primary/25 ring-1 ring-primary/20 transition-transform group-hover:scale-105">
                    <span className="font-black text-xs tracking-wider text-white font-mono select-none">
                      EMP
                    </span>
                  </div>
                  <div className="flex flex-col min-w-0">
                    <div className="flex items-baseline gap-1.5">
                      <span className="font-extrabold text-base tracking-tight text-sidebar-foreground group-hover:text-primary transition-colors">
                        EMP
                      </span>
                      <span className="text-[11px] font-semibold text-muted-foreground truncate">
                        EduManage
                      </span>
                    </div>
                    <span className="text-[10px] text-[hsl(var(--sidebar-muted))] flex items-center gap-1 truncate font-medium">
                      <Sparkles className="h-2.5 w-2.5 text-amber-500 shrink-0" />
                      Gestion Scolaire & SIS
                    </span>
                  </div>
                </Link>

                {/* Collapse button — in expanded mode */}
                {onToggleCollapse && (
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={onToggleCollapse}
                    className="hidden md:flex h-7 w-7 rounded-xl hover:bg-sidebar-accent text-[hsl(var(--sidebar-muted))] hover:text-sidebar-foreground shrink-0 ml-1"
                    title="Rétracter le menu"
                    aria-label="Rétracter la barre latérale"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                )}

                {/* Mobile close */}
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={onClose}
                  className="md:hidden h-8 w-8 rounded-xl hover:bg-sidebar-accent ml-1"
                  aria-label="Fermer le menu"
                >
                  <X className="h-4 w-4" />
                </Button>
              </>
            ) : (
              /* Collapsed header: distinctive compact EMP emblem */
              <div className="flex flex-col items-center gap-2 w-full py-1">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Link
                      to="/"
                      className="h-10 w-10 rounded-xl bg-gradient-to-br from-primary via-blue-600 to-indigo-600 flex items-center justify-center shadow-sm shadow-primary/25 ring-1 ring-primary/20 transition-transform hover:scale-105"
                      onClick={closeOnMobile}
                      aria-label="Tableau de Bord EMP"
                    >
                      <span className="font-black text-xs tracking-wider text-white font-mono select-none">
                        EMP
                      </span>
                    </Link>
                  </TooltipTrigger>
                  <TooltipContent side="right" className="font-semibold">EMP — EduManagePro</TooltipContent>
                </Tooltip>
              </div>
            )}
          </div>

          {/* Expand button when collapsed */}
          {isCollapsed && onToggleCollapse && (
            <div className="flex justify-center py-2 border-b border-[hsl(var(--sidebar-border))] bg-muted/5">
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={onToggleCollapse}
                    className="h-7 w-7 rounded-xl hover:bg-sidebar-accent text-[hsl(var(--sidebar-muted))] hover:text-sidebar-foreground"
                    title="Élargir le menu"
                    aria-label="Élargir la barre latérale"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="right">Élargir le menu</TooltipContent>
              </Tooltip>
            </div>
          )}

          {/* ── Search filter (expanded only) ── */}
          {!isCollapsed && (
            <div className="px-3 py-2.5 border-b border-[hsl(var(--sidebar-border))]">
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-[hsl(var(--sidebar-muted))] pointer-events-none" />
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Rechercher une fonction..."
                  aria-label="Filtrer les fonctionnalités du menu"
                  className={cn(
                    "h-8 pl-8 pr-7 text-xs rounded-xl",
                    "bg-sidebar-accent/70 border-transparent",
                    "text-sidebar-foreground placeholder:text-[hsl(var(--sidebar-muted))]",
                    "focus-visible:ring-1 focus-visible:ring-primary focus-visible:border-primary"
                  )}
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery("")}
                    className="absolute right-2.5 top-2.5 text-[hsl(var(--sidebar-muted))] hover:text-sidebar-foreground focus:outline-none"
                    aria-label="Effacer la recherche"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
            </div>
          )}

          {/* ── Navigation List ── */}
          <nav
            aria-label="Menu principal"
            className={cn(
              "flex-1 overflow-y-auto scrollbar-hide py-2.5",
              isCollapsed ? "px-2 space-y-1.5" : "px-3 space-y-1"
            )}
          >

            {/* Dashboard / Accueil */}
            {isCollapsed ? (
              <Tooltip>
                <TooltipTrigger asChild>
                  <NavLink
                    to="/"
                    onClick={closeOnMobile}
                    aria-label="Tableau de Bord"
                    className={cn(
                      "flex items-center justify-center h-10 w-10 rounded-xl mx-auto transition-all relative group",
                      isDashboardActive
                        ? "bg-primary text-primary-foreground shadow-sm font-semibold"
                        : "text-[hsl(var(--sidebar-muted))] hover:bg-sidebar-accent hover:text-sidebar-foreground"
                    )}
                  >
                    <LayoutDashboard className="h-4.5 w-4.5" />
                    {isDashboardActive && (
                      <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-primary-foreground rounded-r-full" />
                    )}
                  </NavLink>
                </TooltipTrigger>
                <TooltipContent side="right">Tableau de Bord</TooltipContent>
              </Tooltip>
            ) : (
              <NavLink
                to="/"
                onClick={closeOnMobile}
                className={cn(
                  "flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium transition-all group relative",
                  isDashboardActive
                    ? "bg-primary text-primary-foreground shadow-sm font-semibold"
                    : "text-[hsl(var(--sidebar-muted))] hover:bg-sidebar-accent hover:text-sidebar-foreground"
                )}
              >
                <LayoutDashboard className={cn("h-4 w-4 shrink-0 transition-transform group-hover:scale-110", isDashboardActive ? "text-primary-foreground" : "text-primary")} />
                <span className="font-semibold">Tableau de Bord</span>
                {isDashboardActive && (
                  <span className="ml-auto w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
                )}
              </NavLink>
            )}

            {/* Separator */}
            <div className="h-px bg-[hsl(var(--sidebar-border))] my-2 mx-1" />

            {/* Sections */}
            {isCollapsed ? (
              /* Collapsed view: icon badges with flyout menus */
              <div className="space-y-1.5">
                {accessibleSections.map((section) => (
                  <CollapsedModuleGroup key={section.id} section={section} />
                ))}
              </div>
            ) : (
              /* Expanded view: Collapsible sections with headers and items */
              filteredSections.map((section) => {
                const SectionIcon = section.icon;
                const isOpenSection = searchQuery.trim() ? true : !!openSections[section.id];
                const hasActive = section.items.some((i) => isActive(i.href));

                return (
                  <Collapsible
                    key={section.id}
                    open={isOpenSection}
                    onOpenChange={() =>
                      setOpenSections((prev) => ({ ...prev, [section.id]: !prev[section.id] }))
                    }
                    className="mb-1"
                  >
                    <CollapsibleTrigger
                      className={cn(
                        "flex items-center gap-2 w-full px-2.5 py-1.5 rounded-xl text-[11px] font-bold uppercase tracking-wider transition-colors group focus:outline-none focus-visible:ring-1 focus-visible:ring-primary",
                        hasActive
                          ? "text-sidebar-foreground bg-sidebar-accent/50"
                          : "text-[hsl(var(--sidebar-muted))] hover:text-sidebar-foreground hover:bg-sidebar-accent/60"
                      )}
                    >
                      <div className={cn("p-1 rounded-md transition-colors", section.bgLightClass)}>
                        <SectionIcon className={cn("h-3 w-3 shrink-0 group-hover:scale-110 transition-transform", section.colorClass)} />
                      </div>
                      <span className="flex-1 truncate text-left">{section.title}</span>
                      <ChevronDown className={cn(
                        "h-3 w-3 shrink-0 text-[hsl(var(--sidebar-muted))] transition-transform duration-200",
                        isOpenSection && "rotate-180"
                      )} />
                    </CollapsibleTrigger>

                    <CollapsibleContent>
                      <div className="ml-3 mt-1 mb-1 pl-2.5 border-l-2 border-[hsl(var(--sidebar-border))] space-y-0.5">
                        {section.items.map((item) => {
                          const ItemIcon = item.icon;
                          const active = isActive(item.href);
                          return (
                            <NavLink
                              key={item.href}
                              to={item.href}
                              onClick={closeOnMobile}
                              title={item.description}
                              className={cn(
                                "flex items-center gap-2 px-2.5 py-1.5 rounded-xl text-xs font-medium transition-all group relative",
                                active
                                  ? "bg-primary/12 text-primary font-semibold shadow-2xs"
                                  : "text-[hsl(var(--sidebar-muted))] hover:bg-sidebar-accent hover:text-sidebar-foreground"
                              )}
                            >
                              <ItemIcon className={cn(
                                "h-3.5 w-3.5 shrink-0 transition-transform group-hover:scale-110",
                                active ? "text-primary" : "text-[hsl(var(--sidebar-muted))]"
                              )} />
                              <span className="flex-1 truncate">{item.title}</span>
                              {item.badge && (
                                <Badge className={cn("h-4 px-1.5 text-[9px] font-semibold border", getBadgeClass(item.badgeVariant))}>
                                  {item.badge}
                                </Badge>
                              )}
                              {active && (
                                <span className="absolute -left-[11px] top-1/2 -translate-y-1/2 w-1.5 h-3.5 bg-primary rounded-r-full" />
                              )}
                            </NavLink>
                          );
                        })}
                      </div>
                    </CollapsibleContent>
                  </Collapsible>
                );
              })
            )}

            {filteredSections.length === 0 && (
              <div className="py-6 px-3 text-center">
                <p className="text-xs text-muted-foreground">Aucune fonctionnalité autorisée pour ce profil</p>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSearchQuery("")}
                  className="mt-2 text-xs text-primary hover:underline h-7"
                >
                  Réinitialiser
                </Button>
              </div>
            )}
          </nav>

          {/* ── Footer / Institution pill with Active Role ── */}
          <div className="px-3 py-2.5 border-t border-[hsl(var(--sidebar-border))] shrink-0 bg-muted/10">
            <div className={cn(
              "flex items-center gap-2.5 rounded-xl p-2 bg-sidebar-accent/50 hover:bg-sidebar-accent transition-colors",
              isCollapsed && "justify-center px-0 py-2"
            )}>
              <div className="h-7 w-7 rounded-lg bg-primary/15 border border-primary/20 flex items-center justify-center text-primary font-bold text-[10px] shrink-0">
                {currentRoleInfo.badge.slice(0, 3).toUpperCase()}
              </div>
              {!isCollapsed && (
                <div className="flex flex-col min-w-0 flex-1">
                  <span className="text-[11px] font-semibold text-sidebar-foreground truncate leading-tight">
                    {currentRoleInfo.label}
                  </span>
                  <span className="text-[9px] text-[hsl(var(--sidebar-muted))] truncate leading-tight mt-0.5">
                    {currentRoleInfo.badge} • EduManagePro
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </aside>
    </TooltipProvider>
  );
};

