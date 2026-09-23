import { NavLink } from "@/components/NavLink";
import {
  LayoutDashboard,
  UserPlus,
  Users,
  FileCheck,
  GraduationCap,
  BookOpen,
  Building2,
  MapPin,
  Building,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

const menuItems = [
  {
    title: "Tableau de Bord",
    icon: LayoutDashboard,
    href: "/",
  },
  {
    title: "Pré-inscription",
    icon: UserPlus,
    href: "/pre-inscription",
  },
  {
    title: "Liste des Étudiants",
    icon: Users,
    href: "/etudiants",
  },
  {
    title: "Validation Dossiers",
    icon: FileCheck,
    href: "/validation",
  },
  {
    title: "Promotions",
    icon: GraduationCap,
    href: "/promotions",
  },
  {
    title: "Départements",
    icon: Building2,
    href: "/departements",
  },
  {
    title: "Filières",
    icon: BookOpen,
    href: "/filieres",
  },
  {
    title: "Campus",
    icon: MapPin,
    href: "/campus",
  },
  {
    title: "Sites",
    icon: Building,
    href: "/sites",
  },
];

export const Sidebar = ({ isOpen, onClose }: SidebarProps) => {
  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm md:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed left-0 top-0 z-50 h-full w-64 border-r border-border bg-card transition-transform duration-300 md:sticky md:top-16 md:h-[calc(100vh-4rem)] md:translate-x-0",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-16 items-center justify-between px-4 md:hidden border-b border-border">
          <span className="font-bold text-lg text-primary">Menu</span>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-5 w-5" />
          </Button>
        </div>

        <nav className="space-y-1 p-4">
          {menuItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.href}
                to={item.href}
                className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
                activeClassName="bg-accent text-accent-foreground"
                onClick={() => {
                  if (window.innerWidth < 768) onClose();
                }}
              >
                <Icon className="h-5 w-5" />
                {item.title}
              </NavLink>
            );
          })}
        </nav>
      </aside>
    </>
  );
};
