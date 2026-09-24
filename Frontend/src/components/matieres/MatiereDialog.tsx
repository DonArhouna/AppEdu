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
  heures_cm: number;
  heures_td: number;
  heures_tp: number;
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
  filiere?: string;
  niveau?: string;
  semestre?: string;
}

interface FiliereOption {
  id: string;
  nom: string;
}

interface MatiereDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (data: Partial<Matiere>) => void;
  matiere: Matiere | null;
  fixedType?: "ECUE";
  ues?: UE[];
  filieres?: FiliereOption[];
}

export function MatiereDialog({ open, onOpenChange, onSave, matiere, fixedType, ues = [], filieres = [] }: MatiereDialogProps) {
  const [formData, setFormData] = useState<Partial<Matiere>>({
    code: "",
    nom: "",
    type: fixedType || "UE",
    credits: 0,
    coefficient: 0,
    heures_cm: 0,
    heures_td: 0,
    heures_tp: 0,
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
        heures_cm: 0,
    heures_td: 0,
    heures_tp: 0,
        filiere: "",
        niveau: "",
        semestre: "",
        enseignant: "",
        description: "",
        ueId: "",
      });
    }
  }, [matiere, open, fixedType]);

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
                  placeholder="Code matière"
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
                  onValueChange={(value) => {
                    const ue = ues.find((item) => item.id === value);
                    setFormData({
                      ...formData,
                      ueId: value,
                      filiere: ue?.filiere || formData.filiere,
                      niveau: ue?.niveau || formData.niveau,
                      semestre: ue?.semestre || formData.semestre,
                    });
                  }}
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
                placeholder="Intitulé de la matière"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="credits">Crédits *</Label>
                <Input id="credits" type="number" min="0" value={formData.credits} onChange={(e) => setFormData({ ...formData, credits: parseInt(e.target.value) })} required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="coefficient">Coefficient *</Label>
                <Input id="coefficient" type="number" min="0" step="0.1" value={formData.coefficient} onChange={(e) => setFormData({ ...formData, coefficient: parseFloat(e.target.value) })} required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="heures-cm">Heures CM</Label>
                <Input id="heures-cm" type="number" min="0" value={formData.heures_cm} onChange={(e) => setFormData({ ...formData, heures_cm: parseInt(e.target.value) })} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="heures-td">Heures TD</Label>
                <Input id="heures-td" type="number" min="0" value={formData.heures_td} onChange={(e) => setFormData({ ...formData, heures_td: parseInt(e.target.value) })} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="heures-tp">Heures TP</Label>
                <Input id="heures-tp" type="number" min="0" value={formData.heures_tp} onChange={(e) => setFormData({ ...formData, heures_tp: parseInt(e.target.value) })} />
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
                    {filieres.map((filiere) => (
                      <SelectItem key={filiere.id} value={filiere.nom}>
                        {filiere.nom}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="niveau">Niveau *</Label>
                <Input id="niveau" value={formData.niveau || ""} onChange={(e) => setFormData({ ...formData, niveau: e.target.value })} required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="semestre">Semestre *</Label>
                <Input id="semestre" value={formData.semestre || ""} onChange={(e) => setFormData({ ...formData, semestre: e.target.value })} required />
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
