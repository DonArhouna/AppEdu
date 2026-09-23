import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import {
  Users,
  Building2,
  BookOpen,
  Calendar,
  FileText,
  CreditCard,
  Settings,
  PlusCircle,
  GraduationCap,
  Layers,
  MapPin,
  TrendingUp,
  Mail,
  ShieldCheck,
  Search,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface GlobalCommandPaletteProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export const GlobalCommandPalette = ({
  open: externalOpen,
  onOpenChange: externalOnOpenChange,
}: GlobalCommandPaletteProps) => {
  const [internalOpen, setInternalOpen] = useState(false);
  const navigate = useNavigate();

  const isControlled = externalOpen !== undefined;
  const isOpen = isControlled ? externalOpen : internalOpen;
  const setIsOpen = useCallback(
    (open: boolean) => {
      if (isControlled && externalOnOpenChange) {
        externalOnOpenChange(open);
      } else {
        setInternalOpen(open);
      }
    },
    [isControlled, externalOnOpenChange]
  );

  // Global keyboard shortcut Ctrl+K / Cmd+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setIsOpen(!isOpen);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, setIsOpen]);

  const handleSelect = (callback: () => void) => {
    setIsOpen(false);
    callback();
  };

  // Mock search indexes for instant lookup
  const students = [
    { id: "ETU001", name: "Marie Dupont", matricule: "2025-INF-0042", filiere: "Génie Informatique L3" },
    { id: "ETU002", name: "Kouassi Jean Konan", matricule: "2025-INF-0089", filiere: "Génie Informatique L3" },
    { id: "ETU003", name: "Aminata Diallo", matricule: "2025-GES-0104", filiere: "Gestion & Finance M1" },
    { id: "ETU004", name: "Mohamed Traoré", matricule: "2025-RES-0056", filiere: "Réseaux & Télécoms L2" },
  ];

  const rooms = [
    { name: "Salle A101 (Informatique)", capacity: "40 places", campus: "Campus Principal" },
    { name: "Salle A204 (Cours Magistraux)", capacity: "60 places", campus: "Campus Principal" },
    { name: "Labo Réseau 1 (CISCO)", capacity: "30 postes", campus: "Campus Principal" },
    { name: "Amphithéâtre A", capacity: "250 places", campus: "Site Central" },
  ];

  const subjects = [
    { code: "INF301", name: "Programmation Web React", prof: "M. Mamadou Diallo" },
    { code: "INF302", name: "Base de données relationnelles SQL", prof: "Mme Sophie Ndiaye" },
    { code: "INF303", name: "Algorithmique Avancée & Complexité", prof: "M. Jean-Philippe Sow" },
    { code: "MGT201", name: "Gestion de projet Agile & Scrum", prof: "M. Mamadou Diallo" },
  ];

  return (
    <CommandDialog open={isOpen} onOpenChange={setIsOpen}>
      <CommandInput placeholder="Rechercher un étudiant, matricule, salle, matière ou action... (ex: 2025-INF)" />
      <CommandList className="max-h-[380px] scrollbar-thin">
        <CommandEmpty>Aucun résultat trouvé dans la base académique.</CommandEmpty>

        {/* Actions Rapides */}
        <CommandGroup heading="Actions Rapides">
          <CommandItem
            onSelect={() => handleSelect(() => navigate("/emplois-du-temps"))}
            className="flex items-center gap-2.5 cursor-pointer py-2"
          >
            <PlusCircle className="h-4 w-4 text-primary" />
            <span className="font-medium">Planifier un nouveau cours</span>
            <Badge variant="outline" className="ml-auto text-[10px]">Pédagogie</Badge>
          </CommandItem>
          <CommandItem
            onSelect={() => handleSelect(() => navigate("/pre-inscription"))}
            className="flex items-center gap-2.5 cursor-pointer py-2"
          >
            <PlusCircle className="h-4 w-4 text-emerald-500" />
            <span className="font-medium">Enregistrer une pré-inscription</span>
            <Badge variant="outline" className="ml-auto text-[10px]">Admissions</Badge>
          </CommandItem>
          <CommandItem
            onSelect={() => handleSelect(() => navigate("/paiements"))}
            className="flex items-center gap-2.5 cursor-pointer py-2"
          >
            <CreditCard className="h-4 w-4 text-amber-500" />
            <span className="font-medium">Encaisser un paiement guichet / Mobile Money</span>
            <Badge variant="outline" className="ml-auto text-[10px]">Finances</Badge>
          </CommandItem>
        </CommandGroup>

        <CommandSeparator />

        {/* Étudiants par Matricule ou Nom */}
        <CommandGroup heading="Étudiants & Dossiers">
          {students.map((st) => (
            <CommandItem
              key={st.matricule}
              value={`${st.name} ${st.matricule} ${st.filiere}`}
              onSelect={() => handleSelect(() => navigate("/etudiants"))}
              className="flex items-center justify-between cursor-pointer py-2"
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <Users className="h-4 w-4 text-blue-500 shrink-0" />
                <div className="flex flex-col min-w-0">
                  <span className="font-semibold text-xs text-foreground truncate">{st.name}</span>
                  <span className="text-[10px] text-muted-foreground truncate">{st.filiere}</span>
                </div>
              </div>
              <Badge className="font-mono text-[10px] bg-primary/10 text-primary border-none shrink-0 ml-2">
                {st.matricule}
              </Badge>
            </CommandItem>
          ))}
        </CommandGroup>

        <CommandSeparator />

        {/* Matières & Cours */}
        <CommandGroup heading="Matières & Cours (ECUE)">
          {subjects.map((sub) => (
            <CommandItem
              key={sub.code}
              value={`${sub.code} ${sub.name} ${sub.prof}`}
              onSelect={() => handleSelect(() => navigate("/matieres"))}
              className="flex items-center justify-between cursor-pointer py-2"
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <BookOpen className="h-4 w-4 text-emerald-500 shrink-0" />
                <div className="flex flex-col min-w-0">
                  <span className="font-medium text-xs text-foreground truncate">{sub.name}</span>
                  <span className="text-[10px] text-muted-foreground truncate">{sub.prof}</span>
                </div>
              </div>
              <Badge variant="outline" className="font-mono text-[10px] shrink-0 ml-2">
                {sub.code}
              </Badge>
            </CommandItem>
          ))}
        </CommandGroup>

        <CommandSeparator />

        {/* Salles & Infrastructures */}
        <CommandGroup heading="Salles de Cours & Labos">
          {rooms.map((room) => (
            <CommandItem
              key={room.name}
              value={`${room.name} ${room.capacity} ${room.campus}`}
              onSelect={() => handleSelect(() => navigate("/salles"))}
              className="flex items-center justify-between cursor-pointer py-2"
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <Building2 className="h-4 w-4 text-indigo-500 shrink-0" />
                <div className="flex flex-col min-w-0">
                  <span className="font-medium text-xs text-foreground truncate">{room.name}</span>
                  <span className="text-[10px] text-muted-foreground truncate">{room.campus}</span>
                </div>
              </div>
              <Badge variant="secondary" className="text-[10px] shrink-0 ml-2">
                {room.capacity}
              </Badge>
            </CommandItem>
          ))}
        </CommandGroup>

        <CommandSeparator />

        {/* Navigation Rapide vers Pages Clés */}
        <CommandGroup heading="Navigation Directe">
          <CommandItem onSelect={() => handleSelect(() => navigate("/"))} className="cursor-pointer">
            <TrendingUp className="h-4 w-4 mr-2 text-primary" /> Tableau de Bord Global
          </CommandItem>
          <CommandItem onSelect={() => handleSelect(() => navigate("/emplois-du-temps"))} className="cursor-pointer">
            <Calendar className="h-4 w-4 mr-2 text-emerald-500" /> Emplois du Temps & Plannings
          </CommandItem>
          <CommandItem onSelect={() => handleSelect(() => navigate("/notes"))} className="cursor-pointer">
            <FileText className="h-4 w-4 mr-2 text-emerald-600" /> Carnet de Notes & Évaluations
          </CommandItem>
          <CommandItem onSelect={() => handleSelect(() => navigate("/factures"))} className="cursor-pointer">
            <CreditCard className="h-4 w-4 mr-2 text-amber-500" /> Factures & Échéanciers
          </CommandItem>
          <CommandItem onSelect={() => handleSelect(() => navigate("/analytics"))} className="cursor-pointer">
            <TrendingUp className="h-4 w-4 mr-2 text-indigo-500" /> Analytics & BI
          </CommandItem>
          <CommandItem onSelect={() => handleSelect(() => navigate("/parametrage"))} className="cursor-pointer">
            <Settings className="h-4 w-4 mr-2 text-rose-500" /> Paramétrage Général
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
};
