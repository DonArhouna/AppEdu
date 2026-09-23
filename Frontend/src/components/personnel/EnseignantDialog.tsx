import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";

interface EnseignantDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  enseignantToEdit?: any;
  onSave: (enseignant: any) => void;
}

export const EnseignantDialog = ({
  open,
  onOpenChange,
  enseignantToEdit,
  onSave,
}: EnseignantDialogProps) => {
  const [formData, setFormData] = useState({
    id: enseignantToEdit?.id || "",
    nom: enseignantToEdit?.nom || "",
    prenom: enseignantToEdit?.prenom || "",
    email: enseignantToEdit?.email || "",
    telephone: enseignantToEdit?.telephone || "",
    specialite: enseignantToEdit?.specialite || "Informatique & Web",
    statut: enseignantToEdit?.statut || "Vacataire",
    tarifHoraire: enseignantToEdit?.tarifHoraire || "15 000 FCFA/h",
    heuresHebdo: enseignantToEdit?.heuresHebdo || 8,
    departement: enseignantToEdit?.departement || "Génie Informatique",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const enseignantData = {
      ...formData,
      id: enseignantToEdit?.id || `ENS-${Math.floor(1000 + Math.random() * 9000)}`,
    };
    onSave(enseignantData);
    toast.success(
      enseignantToEdit
        ? `Fiche enseignant de ${formData.prenom} ${formData.nom} mise à jour.`
        : `L'enseignant ${formData.prenom} ${formData.nom} a été créé avec succès.`
    );
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[550px]">
        <DialogHeader>
          <DialogTitle>
            {enseignantToEdit ? "Modifier la fiche Enseignant" : "Nouveau Professeur / Intervenant"}
          </DialogTitle>
          <DialogDescription>
            Renseignez les informations de l'enseignant, statut et spécialités.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 py-2">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="prenom">Prénom *</Label>
              <Input
                id="prenom"
                required
                value={formData.prenom}
                onChange={(e) => setFormData({ ...formData, prenom: e.target.value })}
                placeholder="Ex: Mamadou"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="nom">Nom *</Label>
              <Input
                id="nom"
                required
                value={formData.nom}
                onChange={(e) => setFormData({ ...formData, nom: e.target.value })}
                placeholder="Ex: Diallo"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email Pro *</Label>
              <Input
                id="email"
                type="email"
                required
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="m.diallo@univ-edumanage.com"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="telephone">Téléphone</Label>
              <Input
                id="telephone"
                value={formData.telephone}
                onChange={(e) => setFormData({ ...formData, telephone: e.target.value })}
                placeholder="+225 07 12 34 56 78"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="statut">Statut Contractuel *</Label>
              <Select
                value={formData.statut}
                onValueChange={(val) => setFormData({ ...formData, statut: val })}
              >
                <SelectTrigger id="statut">
                  <SelectValue placeholder="Statut" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Vacataire">Vacataire (Paiement à l'heure)</SelectItem>
                  <SelectItem value="Permanent">Permanent (Plein Temps)</SelectItem>
                  <SelectItem value="Professeur Invité">Professeur Invité</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="tarifHoraire">Tarif Horaire (Vacation)</Label>
              <Input
                id="tarifHoraire"
                value={formData.tarifHoraire}
                onChange={(e) => setFormData({ ...formData, tarifHoraire: e.target.value })}
                placeholder="15 000 FCFA/h"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="specialite">Domaine & Spécialité</Label>
              <Input
                id="specialite"
                value={formData.specialite}
                onChange={(e) => setFormData({ ...formData, specialite: e.target.value })}
                placeholder="Programmation Web, React"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="departement">Département de Rattachement</Label>
              <Select
                value={formData.departement}
                onValueChange={(val) => setFormData({ ...formData, departement: val })}
              >
                <SelectTrigger id="departement">
                  <SelectValue placeholder="Département" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Génie Informatique">Génie Informatique & Tech</SelectItem>
                  <SelectItem value="Gestion & Finance">Gestion & Finance</SelectItem>
                  <SelectItem value="Commerce & Marketing">Commerce & Marketing</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Annuler
            </Button>
            <Button type="submit">
              {enseignantToEdit ? "Enregistrer les modifications" : "Créer l'Enseignant"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};
