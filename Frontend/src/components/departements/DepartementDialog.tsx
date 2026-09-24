import { useEffect, useState, type FormEvent } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

export interface Departement {
  id: string;
  code: string;
  nom: string;
  description: string;
  responsable?: string | null;
  campus_id?: string | null;
  filieres?: Array<{ id: string; nom: string; code: string; diplome?: string }>;
}

interface DepartementDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  departement?: Departement;
  onSave: (departement: Departement) => void;
}

const emptyDepartement: Partial<Departement> = {
  id: "",
  code: "",
  nom: "",
  description: "",
  responsable: "",
  campus_id: null,
};

export function DepartementDialog({ open, onOpenChange, departement, onSave }: DepartementDialogProps) {
  const [formData, setFormData] = useState<Partial<Departement>>(emptyDepartement);

  useEffect(() => {
    if (open) setFormData(departement || emptyDepartement);
  }, [departement, open]);

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!formData.nom || !formData.code) {
      toast.error("Le nom et le code du département sont obligatoires.");
      return;
    }
    onSave({
      id: departement?.id || "",
      code: formData.code.trim(),
      nom: formData.nom.trim(),
      description: formData.description || "",
      responsable: formData.responsable || null,
      campus_id: formData.campus_id || null,
    });
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader><DialogTitle>{departement ? "Modifier le département" : "Nouveau département"}</DialogTitle></DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2"><Label htmlFor="departement-code">Code *</Label><Input id="departement-code" value={formData.code || ""} onChange={(event) => setFormData({ ...formData, code: event.target.value })} required /></div>
          <div className="space-y-2"><Label htmlFor="departement-nom">Nom du département *</Label><Input id="departement-nom" value={formData.nom || ""} onChange={(event) => setFormData({ ...formData, nom: event.target.value })} required /></div>
          <div className="space-y-2"><Label htmlFor="departement-description">Description</Label><Textarea id="departement-description" value={formData.description || ""} onChange={(event) => setFormData({ ...formData, description: event.target.value })} /></div>
          <div className="space-y-2"><Label htmlFor="departement-responsable">Responsable</Label><Input id="departement-responsable" value={formData.responsable || ""} onChange={(event) => setFormData({ ...formData, responsable: event.target.value })} /></div>
          <div className="flex gap-2 justify-end"><Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Annuler</Button><Button type="submit">Enregistrer</Button></div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
