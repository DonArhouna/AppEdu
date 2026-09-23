import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { PersonnelRole } from "./RoleSelectionDialog";

interface Personnel {
  id: string;
  nom: string;
  prenom: string;
  email: string;
  telephone: string;
  role: PersonnelRole;
  departement: string;
  specialite?: string;
  dateEmbauche: string;
  statut: "actif" | "conge" | "inactif";
  // Champs spécifiques professeur
  grade?: string;
  matieres?: string[];
  // Champs spécifiques responsable
  departementGere?: string;
  // Champs spécifiques administratif
  service?: string;
  poste?: string;
}

interface PersonnelDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (data: Partial<Personnel>) => void;
  personnel: Personnel | null;
  selectedRole?: PersonnelRole;
}

const getRoleLabel = (role: PersonnelRole): string => {
  switch (role) {
    case "professeur":
      return "Professeur";
    case "responsable":
      return "Responsable de Département";
    case "assistant":
      return "Assistant(e)";
    case "administratif":
      return "Personnel Administratif";
    default:
      return role;
  }
};

export function PersonnelDialog({ open, onOpenChange, onSave, personnel, selectedRole }: PersonnelDialogProps) {
  const [formData, setFormData] = useState<Partial<Personnel>>({
    nom: "",
    prenom: "",
    email: "",
    telephone: "",
    role: selectedRole || "professeur",
    departement: "",
    specialite: "",
    dateEmbauche: "",
    statut: "actif",
    grade: "",
    departementGere: "",
    service: "",
    poste: "",
  });

  useEffect(() => {
    if (personnel) {
      setFormData(personnel);
    } else {
      setFormData({
        nom: "",
        prenom: "",
        email: "",
        telephone: "",
        role: selectedRole || "professeur",
        departement: "",
        specialite: "",
        dateEmbauche: "",
        statut: "actif",
        grade: "",
        departementGere: "",
        service: "",
        poste: "",
      });
    }
  }, [personnel, open, selectedRole]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  const currentRole = formData.role || selectedRole;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {personnel ? "Modifier le Personnel" : `Ajouter un ${getRoleLabel(currentRole as PersonnelRole)}`}
          </DialogTitle>
          <DialogDescription>
            {personnel
              ? "Modifiez les informations du membre du personnel"
              : `Remplissez les informations pour créer un nouveau ${getRoleLabel(currentRole as PersonnelRole).toLowerCase()}`}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="space-y-4 py-4">
            {/* Informations de base - communes à tous */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="prenom">Prénom *</Label>
                <Input
                  id="prenom"
                  value={formData.prenom}
                  onChange={(e) => setFormData({ ...formData, prenom: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="nom">Nom *</Label>
                <Input
                  id="nom"
                  value={formData.nom}
                  onChange={(e) => setFormData({ ...formData, nom: e.target.value })}
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email *</Label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="telephone">Téléphone *</Label>
                <Input
                  id="telephone"
                  value={formData.telephone}
                  onChange={(e) => setFormData({ ...formData, telephone: e.target.value })}
                  required
                />
              </div>
            </div>

            {/* Affichage du rôle (lecture seule si sélectionné avant) */}
            {!personnel && selectedRole && (
              <div className="space-y-2">
                <Label>Rôle</Label>
                <div className="px-3 py-2 bg-muted rounded-md text-sm">
                  {getRoleLabel(selectedRole)}
                </div>
              </div>
            )}

            {/* Sélection du rôle si modification */}
            {personnel && (
              <div className="space-y-2">
                <Label htmlFor="role">Rôle *</Label>
                <Select
                  value={formData.role}
                  onValueChange={(value) =>
                    setFormData({ ...formData, role: value as PersonnelRole })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="responsable">Responsable de Département</SelectItem>
                    <SelectItem value="professeur">Professeur</SelectItem>
                    <SelectItem value="assistant">Assistant(e)</SelectItem>
                    <SelectItem value="administratif">Personnel Administratif</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Champs spécifiques au Professeur */}
            {currentRole === "professeur" && (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="grade">Grade *</Label>
                    <Select
                      value={formData.grade}
                      onValueChange={(value) => setFormData({ ...formData, grade: value })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Sélectionner" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Professeur Titulaire">Professeur Titulaire</SelectItem>
                        <SelectItem value="Maître de Conférences">Maître de Conférences</SelectItem>
                        <SelectItem value="Chargé de Cours">Chargé de Cours</SelectItem>
                        <SelectItem value="Vacataire">Vacataire</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="departement">Département *</Label>
                    <Select
                      value={formData.departement}
                      onValueChange={(value) => setFormData({ ...formData, departement: value })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Sélectionner" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Informatique">Informatique</SelectItem>
                        <SelectItem value="Gestion">Gestion</SelectItem>
                        <SelectItem value="Commerce">Commerce</SelectItem>
                        <SelectItem value="Marketing">Marketing</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="specialite">Spécialité *</Label>
                  <Input
                    id="specialite"
                    value={formData.specialite || ""}
                    onChange={(e) => setFormData({ ...formData, specialite: e.target.value })}
                    placeholder="Ex: Développement Web, Intelligence Artificielle..."
                  />
                </div>
              </>
            )}

            {/* Champs spécifiques au Responsable */}
            {currentRole === "responsable" && (
              <div className="space-y-2">
                <Label htmlFor="departementGere">Département géré *</Label>
                <Select
                  value={formData.departementGere}
                  onValueChange={(value) => setFormData({ ...formData, departementGere: value, departement: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Sélectionner" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Informatique">Informatique</SelectItem>
                    <SelectItem value="Gestion">Gestion</SelectItem>
                    <SelectItem value="Commerce">Commerce</SelectItem>
                    <SelectItem value="Marketing">Marketing</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Champs spécifiques à l'Assistant */}
            {currentRole === "assistant" && (
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="departement">Département *</Label>
                  <Select
                    value={formData.departement}
                    onValueChange={(value) => setFormData({ ...formData, departement: value })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Sélectionner" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Informatique">Informatique</SelectItem>
                      <SelectItem value="Gestion">Gestion</SelectItem>
                      <SelectItem value="Commerce">Commerce</SelectItem>
                      <SelectItem value="Marketing">Marketing</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="poste">Poste *</Label>
                  <Input
                    id="poste"
                    value={formData.poste || ""}
                    onChange={(e) => setFormData({ ...formData, poste: e.target.value })}
                    placeholder="Ex: Assistant pédagogique..."
                  />
                </div>
              </div>
            )}

            {/* Champs spécifiques au Personnel Administratif */}
            {currentRole === "administratif" && (
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="service">Service *</Label>
                  <Select
                    value={formData.service}
                    onValueChange={(value) => setFormData({ ...formData, service: value })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Sélectionner" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Scolarité">Scolarité</SelectItem>
                      <SelectItem value="Comptabilité">Comptabilité</SelectItem>
                      <SelectItem value="Ressources Humaines">Ressources Humaines</SelectItem>
                      <SelectItem value="Direction">Direction</SelectItem>
                      <SelectItem value="Maintenance">Maintenance</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="poste">Poste *</Label>
                  <Input
                    id="poste"
                    value={formData.poste || ""}
                    onChange={(e) => setFormData({ ...formData, poste: e.target.value })}
                    placeholder="Ex: Secrétaire, Comptable..."
                  />
                </div>
              </div>
            )}

            {/* Champs communs restants */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="dateEmbauche">Date d'embauche *</Label>
                <Input
                  id="dateEmbauche"
                  type="date"
                  value={formData.dateEmbauche}
                  onChange={(e) => setFormData({ ...formData, dateEmbauche: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="statut">Statut *</Label>
                <Select
                  value={formData.statut}
                  onValueChange={(value) =>
                    setFormData({ ...formData, statut: value as Personnel["statut"] })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="actif">Actif</SelectItem>
                    <SelectItem value="conge">En congé</SelectItem>
                    <SelectItem value="inactif">Inactif</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Annuler
            </Button>
            <Button type="submit" className="bg-primary hover:bg-primary-hover">
              {personnel ? "Modifier" : "Ajouter"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
