import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { BookOpen, Calendar, CreditCard, FileText, PlusCircle, Users } from "lucide-react";
import { CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandSeparator } from "@/components/ui/command";
import { Badge } from "@/components/ui/badge";
import { etudiantsApi, pedagogieApi, structureApi } from "@/services/apiClient";
import type { Course, Student } from "@/services/apiTypes";
import { useRBAC } from "@/contexts/RBACContext";

interface MatiereSearch {
  id: string;
  code: string;
  nom: string;
}

export const GlobalCommandPalette = ({
  open: externalOpen,
  onOpenChange: externalOnOpenChange,
}: {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}) => {
  const [internalOpen, setInternalOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [students, setStudents] = useState<Student[]>([]);
  const [matieres, setMatieres] = useState<MatiereSearch[]>([]);
  const [cours, setCours] = useState<Course[]>([]);
  const navigate = useNavigate();
  const { hasAccess } = useRBAC();
  const isControlled = externalOpen !== undefined;
  const isOpen = isControlled ? externalOpen : internalOpen;
  const setOpen = useCallback(
    (value: boolean) => {
      if (isControlled) externalOnOpenChange?.(value);
      else setInternalOpen(value);
    },
    [externalOnOpenChange, isControlled]
  );

  const canSearchDirectory = hasAccess(["ADMIN", "DIRECTEUR_ETUDES", "SECRETARIAT", "COMPTABILITE"]);
  const canManageStudents = hasAccess(["ADMIN", "DIRECTEUR_ETUDES", "SECRETARIAT"]);
  const canManagePayments = hasAccess(["ADMIN", "COMPTABILITE"]);
  const canManageSessions = hasAccess(["ADMIN", "DIRECTEUR_ETUDES", "COMPTABILITE"]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen(!isOpen);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen, setOpen]);

  useEffect(() => {
    if (!isOpen || !canSearchDirectory || query.trim().length < 2) {
      setStudents([]);
      setMatieres([]);
      setCours([]);
      return;
    }
    const search = query.trim();
    void Promise.all([etudiantsApi.getAll({ search }), structureApi.getMatieres(), pedagogieApi.getCours()]).then(([s, m, c]) => {
      setStudents(s.data || []);
      setMatieres((m.data || []) as MatiereSearch[]);
      setCours(c.data || []);
    });
  }, [canSearchDirectory, isOpen, query]);

  const go = (path: string) => {
    setOpen(false);
    setQuery("");
    navigate(path);
  };

  return (
    <CommandDialog open={isOpen} onOpenChange={setOpen}>
      <CommandInput value={query} onValueChange={setQuery} placeholder="Rechercher une page, un étudiant ou une matière..." />
      <CommandList className="max-h-[420px]">
        <CommandEmpty>Aucun résultat disponible.</CommandEmpty>
        <CommandGroup heading="Actions rapides">
          {canManageStudents && (
            <CommandItem onSelect={() => go("/etudiants")}>
              <PlusCircle className="mr-2 h-4 w-4 text-primary" />Gérer les étudiants
            </CommandItem>
          )}
          {canManagePayments && (
            <CommandItem onSelect={() => go("/paiements")}>
              <CreditCard className="mr-2 h-4 w-4 text-amber-600" />Enregistrer un paiement
            </CommandItem>
          )}
          {canManageSessions && (
            <CommandItem onSelect={() => go("/sessions")}>
              <Calendar className="mr-2 h-4 w-4 text-emerald-600" />Gérer les sessions
            </CommandItem>
          )}
        </CommandGroup>
        {students.length > 0 && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Étudiants">
              {students.slice(0, 8).map((student) => (
                <CommandItem key={student.id} value={`${student.prenom} ${student.nom} ${student.matricule}`} onSelect={() => go(`/etudiants/${student.id}`)}>
                  <Users className="mr-2 h-4 w-4 text-primary" />
                  <span>{student.prenom} {student.nom}</span>
                  <Badge className="ml-auto" variant="outline">{student.matricule}</Badge>
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        )}
        {matieres.length > 0 && (
          <CommandGroup heading="Matières">
            {matieres.slice(0, 8).map((matiere) => (
              <CommandItem key={matiere.id} value={`${matiere.code} ${matiere.nom}`} onSelect={() => go("/matieres")}>
                <BookOpen className="mr-2 h-4 w-4 text-emerald-600" />
                <span>{matiere.code} — {matiere.nom}</span>
              </CommandItem>
            ))}
          </CommandGroup>
        )}
        {cours.length > 0 && (
          <CommandGroup heading="Cours">
            {cours.slice(0, 8).map((item) => (
              <CommandItem key={item.id} value={`${item.jour_semaine} ${item.salle}`} onSelect={() => go("/emplois-du-temps")}>
                <Calendar className="mr-2 h-4 w-4 text-primary" />
                <span>{item.jour_semaine} · {item.salle}</span>
              </CommandItem>
            ))}
          </CommandGroup>
        )}
      </CommandList>
    </CommandDialog>
  );
};

export default GlobalCommandPalette;
