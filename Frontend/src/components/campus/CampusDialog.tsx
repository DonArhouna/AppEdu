import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

interface Campus {
  id: string;
  nom: string;
  description: string;
  responsable: string;
}

interface CampusDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  campus?: Campus;
  onSave: (campus: Campus) => void;
}

export function CampusDialog({ open, onOpenChange, campus, onSave }: CampusDialogProps) {
  const [formData, setFormData] = useState<Partial<Campus>>(
    campus || {
      nom: "",
      description: "",
      responsable: "",
    }
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.nom || !formData.description || !formData.responsable) {
      toast.error("Veuillez remplir tous les champs obligatoires");
      return;
    }

    const newCampus: Campus = {
      id: campus?.id || `campus_${Date.now()}`,
      nom: formData.nom!,
      description: formData.description!,
      responsable: formData.responsable!,
    };

    onSave(newCampus);
    toast.success(campus ? "Campus modifié" : "Campus créé");
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{campus ? "Modifier le campus" : "Nouveau campus"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="nom">Nom du campus *</Label>
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
