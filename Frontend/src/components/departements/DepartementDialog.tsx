import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

interface Departement {
  id: string;
  nom: string;
  description: string;
  responsable: string;
  couleur: string;
}

interface DepartementDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  departement?: Departement;
  onSave: (departement: Departement) => void;
}

export function DepartementDialog({ open, onOpenChange, departement, onSave }: DepartementDialogProps) {
  const [formData, setFormData] = useState<Partial<Departement>>(
    departement || {
      nom: "",
      description: "",
      responsable: "",
      couleur: "#3b82f6",
    }
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.nom || !formData.description || !formData.responsable) {
      toast.error("Veuillez remplir tous les champs obligatoires");
      return;
    }

    const newDepartement: Departement = {
      id: departement?.id || `dep_${Date.now()}`,
      nom: formData.nom,
      description: formData.description,
      responsable: formData.responsable,
      couleur: formData.couleur || "#3b82f6",
    };

    onSave(newDepartement);
    toast.success(departement ? "Département modifié" : "Département créé");
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{departement ? "Modifier le département" : "Nouveau département"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="nom">Nom du département *</Label>
            <Input
              id="nom"
              value={formData.nom}
              onChange={(e) => setFormData({ ...formData, nom: e.target.value })}
              required
            />
          </div>
          <div>
            <Label htmlFor="description">Description *</Label>
            <Textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              required
            />
          </div>
          <div>
            <Label htmlFor="responsable">Responsable *</Label>
            <Input
              id="responsable"
              value={formData.responsable}
              onChange={(e) => setFormData({ ...formData, responsable: e.target.value })}
              required
            />
          </div>
          <div>
            <Label htmlFor="couleur">Couleur</Label>
            <Input
              id="couleur"
              type="color"
              value={formData.couleur}
              onChange={(e) => setFormData({ ...formData, couleur: e.target.value })}
            />
          </div>
          <div className="flex gap-2 justify-end">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Annuler
            </Button>
            <Button type="submit">Enregistrer</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
