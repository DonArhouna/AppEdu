import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";

interface Filiere {
  id: string;
  nom: string;
  code: string;
  departement: string;
  description: string;
  duree: string;
  diplome: string;
  formatMatricule?: string;
  sequenceDebut?: string;
}

interface FiliereDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  filiere?: Filiere;
  onSave: (filiere: Filiere) => void;
}

export function FiliereDialog({ open, onOpenChange, filiere, onSave }: FiliereDialogProps) {
  const [formData, setFormData] = useState<Partial<Filiere>>(
    filiere || {
      nom: "",
      code: "",
      departement: "",
      description: "",
      duree: "3",
      diplome: "Licence",
      formatMatricule: "{ANNEE}-{CODE}-{SEQ}",
      sequenceDebut: "1"
    }
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.nom || !formData.code || !formData.departement || !formData.description) {
      toast.error("Veuillez remplir tous les champs obligatoires");
      return;
    }

    const newFiliere: Filiere = {
      id: filiere?.id || `fil_${Date.now()}`,
      nom: formData.nom!,
      code: formData.code!,
      departement: formData.departement!,
      description: formData.description!,
      duree: formData.duree || "3",
      diplome: formData.diplome || "Licence",
      formatMatricule: formData.formatMatricule || "{ANNEE}-{CODE}-{SEQ}",
      sequenceDebut: formData.sequenceDebut || "1",
    };

    onSave(newFiliere);
    toast.success(filiere ? "Filière modifiée" : "Filière créée");
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{filiere ? "Modifier la filière" : "Nouvelle filière"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="nom">Nom de la filière *</Label>
              <Input
                id="nom"
                value={formData.nom}
                onChange={(e) => setFormData({ ...formData, nom: e.target.value })}
                required
              />
            </div>
            <div>
              <Label htmlFor="code">Code *</Label>
              <Input
                id="code"
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                required
              />
            </div>
          </div>
          <div>
            <Label htmlFor="departement">Département *</Label>
            <Select
              value={formData.departement}
              onValueChange={(value) => setFormData({ ...formData, departement: value })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Sélectionner un département" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Génie Informatique">Génie Informatique</SelectItem>
                <SelectItem value="Management">Management</SelectItem>
                <SelectItem value="Génie Civil">Génie Civil</SelectItem>
              </SelectContent>
            </Select>
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
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="diplome">Cycle Académique</Label>
              <Select
                value={formData.diplome}
                onValueChange={(value) => setFormData({ ...formData, diplome: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Licence">Licence</SelectItem>
                  <SelectItem value="Master">Master</SelectItem>
                  <SelectItem value="Doctorat">Doctorat</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="duree">Durée (années)</Label>
              <Input
                id="duree"
                type="number"
                value={formData.duree}
                onChange={(e) => setFormData({ ...formData, duree: e.target.value })}
              />
            </div>
          </div>
          
          {/* Nomenclature config */}
          <div className="p-3 border rounded-lg bg-muted/20 space-y-3">
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Nomenclature des Matricules (Spécifique à cette Filière)
            </h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="formatMatricule" className="text-xs">Format</Label>
                <Input
                  id="formatMatricule"
                  value={formData.formatMatricule}
                  onChange={(e) => setFormData({ ...formData, formatMatricule: e.target.value })}
                  placeholder="Ex: {ANNEE}-GL-{SEQ}"
                  className="h-8 text-sm"
                />
              </div>
              <div>
                <Label htmlFor="sequenceDebut" className="text-xs">Séquence de départ</Label>
                <Input
                  id="sequenceDebut"
                  type="number"
                  value={formData.sequenceDebut}
                  onChange={(e) => setFormData({ ...formData, sequenceDebut: e.target.value })}
                  placeholder="Ex: 1"
                  className="h-8 text-sm"
                />
              </div>
            </div>
            <p className="text-[10px] text-muted-foreground">
              Variables : <code>{'{ANNEE}'}</code> (Année d'inscription), <code>{'{SEQ}'}</code> (Numéro auto-incrémenté).
            </p>
          </div>

          <div className="flex gap-2 justify-end pt-2">
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
