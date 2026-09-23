import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

interface UE {
  id: string;
  code: string;
  nom: string;
  type: "UE";
  credits: number;
  coefficient: number;
  heures: number;
  filiere: string;
  niveau: string;
  semestre: string;
  responsable?: string;
  description?: string;
}

interface UEDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (data: Partial<UE>) => void;
  ue: UE | null;
}

export function UEDialog({ open, onOpenChange, onSave, ue }: UEDialogProps) {
  const [formData, setFormData] = useState<Partial<UE>>({
    code: "",
    nom: "",
    type: "UE",
    credits: 0,
    coefficient: 0,
    heures: 0,
    filiere: "",
    niveau: "",
    semestre: "",
    responsable: "",
    description: "",
  });

  useEffect(() => {
    if (ue) {
      setFormData(ue);
    } else {
      setFormData({
        code: "",
        nom: "",
        type: "UE",
        credits: 0,
        coefficient: 0,
        heures: 0,
        filiere: "",
        niveau: "",
        semestre: "",
        responsable: "",
        description: "",
      });
    }
  }, [ue, open]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{ue ? "Modifier l'UE" : "Créer une UE"}</DialogTitle>
          <DialogDescription>
            {ue ? "Modifiez les informations de l'unité d'enseignement" : "Créez une nouvelle unité d'enseignement"}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="code">Code UE *</Label>
                <Input
                  id="code"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                  placeholder="Ex: INF301"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="responsable">Responsable UE</Label>
                <Input
                  id="responsable"
                  value={formData.responsable || ""}
                  onChange={(e) => setFormData({ ...formData, responsable: e.target.value })}
                  placeholder="Nom du responsable"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="nom">Nom de l'UE *</Label>
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
                <Label htmlFor="credits">Crédits ECTS *</Label>
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
                <Label htmlFor="heures">Volume Horaire *</Label>
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
              <Label htmlFor="description">Description & Objectifs</Label>
              <Textarea
                id="description"
                value={formData.description || ""}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Objectifs pédagogiques de l'UE..."
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Annuler
            </Button>
            <Button type="submit" className="bg-primary hover:bg-primary-hover">
              {ue ? "Modifier" : "Créer"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
