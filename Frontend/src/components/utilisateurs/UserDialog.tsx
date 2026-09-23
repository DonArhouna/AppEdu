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
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";

interface UserDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  userToEdit?: any;
}

export const UserDialog = ({ open, onOpenChange, userToEdit }: UserDialogProps) => {
  const [formData, setFormData] = useState({
    nom: userToEdit?.nom || "",
    prenom: userToEdit?.prenom || "",
    email: userToEdit?.email || "",
    telephone: userToEdit?.telephone || "",
    role: userToEdit?.role || "Enseignant",
    departement: userToEdit?.departement || "Informatique",
    statut: userToEdit?.statut || "Actif",
    sendWelcomeEmail: true,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (userToEdit) {
      toast.success(`L'utilisateur ${formData.prenom} ${formData.nom} a été mis à jour.`);
    } else {
      toast.success(`L'utilisateur ${formData.prenom} ${formData.nom} a été créé avec succès.`);
    }
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[550px]">
        <DialogHeader>
          <DialogTitle>
            {userToEdit ? "Modifier l'utilisateur" : "Créer un nouvel utilisateur"}
          </DialogTitle>
          <DialogDescription>
            {userToEdit
              ? "Mettez à jour les informations et permissions de cet utilisateur."
              : "Renseignez les informations pour créer un accès au système EduManagePro."}
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
                placeholder="Ex: Jean"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="nom">Nom *</Label>
              <Input
                id="nom"
                required
                value={formData.nom}
                onChange={(e) => setFormData({ ...formData, nom: e.target.value })}
                placeholder="Ex: Dupont"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">Adresse Email Pro *</Label>
            <Input
              id="email"
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              placeholder="j.dupont@univ-edumanage.com"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="telephone">Téléphone</Label>
              <Input
                id="telephone"
                value={formData.telephone}
                onChange={(e) => setFormData({ ...formData, telephone: e.target.value })}
                placeholder="+33 6 12 34 56 78"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="role">Rôle Système *</Label>
              <Select
                value={formData.role}
                onValueChange={(val) => setFormData({ ...formData, role: val })}
              >
                <SelectTrigger id="role">
                  <SelectValue placeholder="Sélectionnez un rôle" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Administrateur">Administrateur</SelectItem>
                  <SelectItem value="Secrétariat">Secrétariat / Scolarité</SelectItem>
                  <SelectItem value="Enseignant">Enseignant / Intervenant</SelectItem>
                  <SelectItem value="Comptable">Comptable / Agent Financier</SelectItem>
                  <SelectItem value="Étudiant">Étudiant</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="departement">Rattachement / Département</Label>
              <Select
                value={formData.departement}
                onValueChange={(val) => setFormData({ ...formData, departement: val })}
              >
                <SelectTrigger id="departement">
                  <SelectValue placeholder="Département" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Informatique">Informatique & Tech</SelectItem>
                  <SelectItem value="Gestion">Gestion & Finance</SelectItem>
                  <SelectItem value="Commerce">Commerce & Marketing</SelectItem>
                  <SelectItem value="Direction">Direction Générale</SelectItem>
                  <SelectItem value="Aucun">Aucun (Global)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="statut">Statut du compte</Label>
              <Select
                value={formData.statut}
                onValueChange={(val) => setFormData({ ...formData, statut: val })}
              >
                <SelectTrigger id="statut">
                  <SelectValue placeholder="Statut" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Actif">Actif</SelectItem>
                  <SelectItem value="En attente">En attente d'activation</SelectItem>
                  <SelectItem value="Inactif">Inactif / Suspendu</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {!userToEdit && (
            <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50 border">
              <div className="space-y-0.5">
                <Label className="text-sm font-medium">Envoyer une invitation par email</Label>
                <p className="text-xs text-muted-foreground">
                  L'utilisateur recevra un lien sécurisé pour définir son mot de passe.
                </p>
              </div>
              <Switch
                checked={formData.sendWelcomeEmail}
                onCheckedChange={(val) => setFormData({ ...formData, sendWelcomeEmail: val })}
              />
            </div>
          )}

          <div className="flex justify-end gap-3 pt-4 border-t">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Annuler
            </Button>
            <Button type="submit">
              {userToEdit ? "Enregistrer les modifications" : "Créer l'utilisateur"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};
