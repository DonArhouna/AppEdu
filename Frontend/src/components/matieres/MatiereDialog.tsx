import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

interface Matiere {
  id: string;
  code: string;
  nom: string;
  type: "UE" | "ECUE";
  credits: number;
  coefficient: number;
  heures: number;
  filiere: string;
  niveau: string;
  semestre: string;
  enseignant?: string;
  description?: string;
  ueId?: string;
}

interface UE {
  id: string;
  code: string;
  nom: string;
}

// Mock UEs - à remplacer par des données réelles
const mockUEs: UE[] = [
  { id: "1", code: "UE-INF301", nom: "Développement Web" },
  { id: "2", code: "UE-INF302", nom: "Base de données" },
  { id: "3", code: "UE-INF303", nom: "Réseaux et Systèmes" },
  { id: "4", code: "UE-GES201", nom: "Comptabilité Générale" },
  { id: "5", code: "UE-MKT101", nom: "Marketing Fondamental" },
];

interface MatiereDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (data: Partial<Matiere>) => void;
  matiere: Matiere | null;
  fixedType?: "ECUE";
  ues?: UE[];
}

export function MatiereDialog({ open, onOpenChange, onSave, matiere, fixedType, ues = mockUEs }: MatiereDialogProps) {
  const [formData, setFormData] = useState<Partial<Matiere>>({
    code: "",
    nom: "",
    type: fixedType || "UE",
    credits: 0,
    coefficient: 0,
    heures: 0,
    filiere: "",
    niveau: "",
    semestre: "",
    enseignant: "",
    description: "",
    ueId: "",
  });

  useEffect(() => {
    if (matiere) {
      setFormData(matiere);
    } else {
      setFormData({
        code: "",
        nom: "",
        type: fixedType || "UE",
        credits: 0,
        coefficient: 0,
        heures: 0,
        filiere: "",
        niveau: "",
        semestre: "",
        enseignant: "",
        description: "",
        ueId: "",
      });
    }
  }, [matiere, open]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{matiere ? "Modifier la Matière" : "Ajouter une Matière"}</DialogTitle>
          <DialogDescription>
            {matiere ? "Modifiez les informations de la matière" : "Ajoutez une nouvelle matière ou unité d'enseignement"}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="code">Code *</Label>
                <Input
                  id="code"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                  placeholder="Ex: INF301"
                  required
                />
              </div>
              {!fixedType && (
                <div className="space-y-2">
                  <Label htmlFor="type">Type *</Label>
                  <Select
                    value={formData.type}
                    onValueChange={(value) => setFormData({ ...formData, type: value as "UE" | "ECUE" })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="UE">UE (Unité d'Enseignement)</SelectItem>
                      <SelectItem value="ECUE">ECUE (Elément Constitutif)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}
              {fixedType && (
                <div className="space-y-2">
                  <Label>Type</Label>
                  <div className="px-3 py-2 bg-muted rounded-md text-sm">ECUE (Elément Constitutif)</div>
                </div>
              )}
            </div>

            {/* Champ UE pour les ECUE */}
            {(fixedType === "ECUE" || formData.type === "ECUE") && (
              <div className="space-y-2">
                <Label htmlFor="ueId">Unité d'Enseignement (UE) *</Label>
                <Select
                  value={formData.ueId}
                  onValueChange={(value) => setFormData({ ...formData, ueId: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Sélectionner l'UE parente" />
                  </SelectTrigger>
                  <SelectContent>
                    {ues.map((ue) => (
                      <SelectItem key={ue.id} value={ue.id}>
                        {ue.code} - {ue.nom}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="nom">Nom de la Matière *</Label>
              <Input
                id="nom"
                value={formData.nom}
                onChange={(e) => setFormData({ ...formData, nom: e.target.value })}
                placeholder="Ex: Programmation Web"
                required
              />
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="credits">Crédits *</Label>
                <Input
                  id="credits"
                  type="number"
                  min="0"
                  value={formData.credits}
                  onChange={(e) => setFormData({ ...formData, credits: parseInt(e.target.value) })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="coefficient">Coefficient *</Label>
                <Input
                  id="coefficient"
                  type="number"
                  min="0"
                  value={formData.coefficient}
                  onChange={(e) => setFormData({ ...formData, coefficient: parseInt(e.target.value) })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="heures">Heures *</Label>
                <Input
                  id="heures"
                  type="number"
                  min="0"
                  value={formData.heures}
                  onChange={(e) => setFormData({ ...formData, heures: parseInt(e.target.value) })}
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="filiere">Filière *</Label>
                <Select
                  value={formData.filiere}
                  onValueChange={(value) => setFormData({ ...formData, filiere: value })}
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
                <Label htmlFor="niveau">Niveau *</Label>
                <Select
                  value={formData.niveau}
                  onValueChange={(value) => setFormData({ ...formData, niveau: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Sélectionner" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="L1">L1</SelectItem>
                    <SelectItem value="L2">L2</SelectItem>
                    <SelectItem value="L3">L3</SelectItem>
                    <SelectItem value="M1">M1</SelectItem>
                    <SelectItem value="M2">M2</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="semestre">Semestre *</Label>
                <Select
                  value={formData.semestre}
                  onValueChange={(value) => setFormData({ ...formData, semestre: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Sélectionner" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="S1">S1</SelectItem>
                    <SelectItem value="S2">S2</SelectItem>
                    <SelectItem value="S3">S3</SelectItem>
                    <SelectItem value="S4">S4</SelectItem>
                    <SelectItem value="S5">S5</SelectItem>
                    <SelectItem value="S6">S6</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="enseignant">Enseignant</Label>
              <Input
                id="enseignant"
                value={formData.enseignant || ""}
                onChange={(e) => setFormData({ ...formData, enseignant: e.target.value })}
                placeholder="Nom de l'enseignant"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={formData.description || ""}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Description du contenu de la matière..."
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Annuler
            </Button>
            <Button type="submit" className="bg-primary hover:bg-primary-hover">
              {matiere ? "Modifier" : "Ajouter"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
