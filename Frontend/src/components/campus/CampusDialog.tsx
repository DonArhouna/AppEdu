import { useEffect, useState, type FormEvent } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

export interface Campus {
  id: string;
  code: string;
  nom: string;
  description: string;
  ville: string;
  adresse: string;
  responsable: string;
  telephone?: string;
  email?: string;
  departements?: unknown[];
}

interface CampusDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  campus?: Campus;
  onSave: (campus: Campus) => void;
}

const emptyCampus: Partial<Campus> = {
  code: "",
  nom: "",
  description: "",
  ville: "",
  adresse: "",
  responsable: "",
  telephone: "",
  email: "",
};

export function CampusDialog({ open, onOpenChange, campus, onSave }: CampusDialogProps) {
  const [formData, setFormData] = useState<Partial<Campus>>(emptyCampus);

  useEffect(() => {
    setFormData(campus || emptyCampus);
  }, [campus, open]);

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!formData.nom || !formData.code) {
      toast.error("Le nom et le code du campus sont obligatoires.");
      return;
    }

    onSave({
      id: campus?.id || "",
      code: formData.code.trim(),
      nom: formData.nom.trim(),
      description: formData.description || "",
      ville: formData.ville || "",
      adresse: formData.adresse || "",
      responsable: formData.responsable || "",
      telephone: formData.telephone || "",
      email: formData.email || "",
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{campus ? "Modifier le campus" : "Nouveau campus"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="campus-code">Code *</Label>
              <Input id="campus-code" value={formData.code || ""} onChange={(e) => setFormData({ ...formData, code: e.target.value })} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="campus-nom">Nom du campus *</Label>
              <Input id="campus-nom" value={formData.nom || ""} onChange={(e) => setFormData({ ...formData, nom: e.target.value })} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="campus-ville">Ville</Label>
              <Input id="campus-ville" value={formData.ville || ""} onChange={(e) => setFormData({ ...formData, ville: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="campus-responsable">Responsable</Label>
              <Input id="campus-responsable" value={formData.responsable || ""} onChange={(e) => setFormData({ ...formData, responsable: e.target.value })} />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="campus-description">Description</Label>
            <Textarea id="campus-description" value={formData.description || ""} onChange={(e) => setFormData({ ...formData, description: e.target.value })} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="campus-adresse">Adresse</Label>
            <Input id="campus-adresse" value={formData.adresse || ""} onChange={(e) => setFormData({ ...formData, adresse: e.target.value })} />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="campus-telephone">Téléphone</Label>
              <Input id="campus-telephone" value={formData.telephone || ""} onChange={(e) => setFormData({ ...formData, telephone: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="campus-email">Email</Label>
              <Input id="campus-email" type="email" value={formData.email || ""} onChange={(e) => setFormData({ ...formData, email: e.target.value })} />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Annuler</Button>
            <Button type="submit">Enregistrer</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
