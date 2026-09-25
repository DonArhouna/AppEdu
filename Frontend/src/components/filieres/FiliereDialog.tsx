import { useEffect, useState, type FormEvent } from "react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";

export interface Filiere {
  id: string;
  code: string;
  nom: string;
  description: string;
  diplome: string;
  duree: number | string;
  departement_id?: string | null;
  departement?: string;
  unites_enseignement?: Array<{ id: string; code: string; nom: string }>;
}

interface DepartementOption { id: string; nom: string; }

interface FiliereDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  filiere?: Filiere;
  departements?: DepartementOption[];
  onSave: (filiere: Filiere) => Promise<boolean>;
}

const emptyFiliere: Partial<Filiere> = {
  id: "",
  code: "",
  nom: "",
  description: "",
  diplome: "",
  duree: "",
  departement_id: null,
};

export function FiliereDialog({ open, onOpenChange, filiere, departements = [], onSave }: FiliereDialogProps) {
  const [formData, setFormData] = useState<Partial<Filiere>>(emptyFiliere);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) setFormData(filiere || emptyFiliere);
  }, [filiere, open]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!formData.nom || !formData.code || !formData.departement_id || !formData.diplome || !formData.duree) {
      toast.error("Le code, le nom, le département, le diplôme et la durée sont obligatoires.");
      return;
    }
    setSaving(true);
    try {
      const saved = await onSave({
        id: filiere?.id || "",
        code: formData.code.trim(),
        nom: formData.nom.trim(),
        description: formData.description || "",
        diplome: formData.diplome.trim(),
        duree: Number(formData.duree),
        departement_id: formData.departement_id,
      });
      if (saved) onOpenChange(false);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{filiere ? "Modifier la filière" : "Nouvelle filière"}</DialogTitle>
          <DialogDescription>
            Renseignez le programme de formation et son rattachement institutionnel.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="filiere-code">Code *</Label>
              <Input id="filiere-code" value={formData.code || ""} onChange={(event) => setFormData({ ...formData, code: event.target.value })} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="filiere-nom">Nom *</Label>
              <Input id="filiere-nom" value={formData.nom || ""} onChange={(event) => setFormData({ ...formData, nom: event.target.value })} required />
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="filiere-departement">Département *</Label>
              <Select value={formData.departement_id || ""} onValueChange={(value) => setFormData({ ...formData, departement_id: value })}>
                <SelectTrigger id="filiere-departement"><SelectValue placeholder="Sélectionner" /></SelectTrigger>
                <SelectContent>{departements.map((item) => <SelectItem key={item.id} value={item.id}>{item.nom}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="filiere-diplome">Diplôme *</Label>
              <Input id="filiere-diplome" value={formData.diplome || ""} onChange={(event) => setFormData({ ...formData, diplome: event.target.value })} required />
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="filiere-duree">Durée (années) *</Label>
              <Input id="filiere-duree" type="number" min="1" value={formData.duree ?? ""} onChange={(event) => setFormData({ ...formData, duree: event.target.value })} required />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="filiere-description">Description</Label>
            <Textarea id="filiere-description" value={formData.description || ""} onChange={(event) => setFormData({ ...formData, description: event.target.value })} />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>Annuler</Button>
            <Button type="submit" disabled={saving}>{saving ? "Enregistrement..." : "Enregistrer"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
