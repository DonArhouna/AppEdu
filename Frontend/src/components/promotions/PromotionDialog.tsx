import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";

interface Promotion {
  id: string;
  nom: string;
  annee: string;
  dateDebut: string;
  dateFin: string;
  statut: string;
}

interface PromotionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  promotion?: Promotion;
  onSave: (promotion: Promotion) => void;
}

export function PromotionDialog({ open, onOpenChange, promotion, onSave }: PromotionDialogProps) {
  const [formData, setFormData] = useState<Partial<Promotion>>(
    promotion || {
      nom: "",
      annee: "",
      dateDebut: "",
      dateFin: "",
      statut: "active",
    }
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.nom || !formData.annee || !formData.dateDebut || !formData.dateFin) {
      toast.error("Veuillez remplir tous les champs obligatoires");
      return;
    }

    const newPromotion: Promotion = {
      id: promotion?.id || `promo_${Date.now()}`,
      nom: formData.nom!,
      annee: formData.annee!,
      dateDebut: formData.dateDebut!,
      dateFin: formData.dateFin!,
      statut: formData.statut || "active",
    };

    onSave(newPromotion);
    toast.success(promotion ? "Promotion modifiée" : "Promotion créée");
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{promotion ? "Modifier la promotion" : "Nouvelle promotion"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="nom">Nom de la promotion *</Label>
            <Input
              id="nom"
              value={formData.nom}
              onChange={(e) => setFormData({ ...formData, nom: e.target.value })}
              placeholder="Ex: Promotion 2024-2025"
              required
            />
          </div>
          <div>
            <Label htmlFor="annee">Année académique *</Label>
            <Input
              id="annee"
              value={formData.annee}
              onChange={(e) => setFormData({ ...formData, annee: e.target.value })}
              placeholder="Ex: 2024-2025"
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="dateDebut">Date de début *</Label>
              <Input
                id="dateDebut"
                type="date"
                value={formData.dateDebut}
                onChange={(e) => setFormData({ ...formData, dateDebut: e.target.value })}
                required
              />
            </div>
            <div>
              <Label htmlFor="dateFin">Date de fin *</Label>
              <Input
                id="dateFin"
                type="date"
                value={formData.dateFin}
                onChange={(e) => setFormData({ ...formData, dateFin: e.target.value })}
                required
              />
            </div>
          </div>
          <div>
            <Label htmlFor="statut">Statut</Label>
            <Select
              value={formData.statut}
              onValueChange={(value) => setFormData({ ...formData, statut: value })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="terminee">Terminée</SelectItem>
                <SelectItem value="a-venir">À venir</SelectItem>
              </SelectContent>
            </Select>
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
