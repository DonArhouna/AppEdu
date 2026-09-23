import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { GraduationCap, Users, Briefcase, UserCog } from "lucide-react";

export type PersonnelRole = "professeur" | "responsable" | "assistant" | "administratif";

interface RoleOption {
  value: PersonnelRole;
  label: string;
  description: string;
  icon: React.ReactNode;
}

const roleOptions: RoleOption[] = [
  {
    value: "professeur",
    label: "Professeur",
    description: "Enseignant chargé des cours et des évaluations",
    icon: <GraduationCap className="h-8 w-8" />,
  },
  {
    value: "responsable",
    label: "Responsable de Département",
    description: "Responsable de la gestion d'un département",
    icon: <Users className="h-8 w-8" />,
  },
  {
    value: "assistant",
    label: "Assistant(e)",
    description: "Assistant administratif ou pédagogique",
    icon: <Briefcase className="h-8 w-8" />,
  },
  {
    value: "administratif",
    label: "Personnel Administratif",
    description: "Personnel de gestion et administration",
    icon: <UserCog className="h-8 w-8" />,
  },
];

interface RoleSelectionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelectRole: (role: PersonnelRole) => void;
}

export function RoleSelectionDialog({ open, onOpenChange, onSelectRole }: RoleSelectionDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Choisir le type de personnel</DialogTitle>
          <DialogDescription>
            Sélectionnez le rôle du membre du personnel à ajouter. Les champs du formulaire seront adaptés en fonction du rôle choisi.
          </DialogDescription>
        </DialogHeader>
        <div className="grid grid-cols-2 gap-4 py-4">
          {roleOptions.map((option) => (
            <Button
              key={option.value}
              variant="outline"
              className="h-auto flex flex-col items-center gap-3 p-6 hover:bg-primary/10 hover:border-primary transition-colors"
              onClick={() => onSelectRole(option.value)}
            >
              <div className="text-primary">{option.icon}</div>
              <div className="text-center">
                <div className="font-semibold">{option.label}</div>
                <div className="text-xs text-muted-foreground mt-1">{option.description}</div>
              </div>
            </Button>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
