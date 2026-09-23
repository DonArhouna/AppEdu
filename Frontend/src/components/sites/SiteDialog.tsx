import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";

interface Site {
  id: string;
  nom: string;
  campus: string;
  adresse: string;
  superficie: string;
  capacite: number;
}

interface SiteDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  site?: Site;
  onSave: (site: Site) => void;
}

export function SiteDialog({ open, onOpenChange, site, onSave }: SiteDialogProps) {
  const [formData, setFormData] = useState<Partial<Site>>(
    site || {
      nom: "",
      campus: "",
      adresse: "",
      superficie: "",
      capacite: 0,
    }
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.nom || !formData.campus || !formData.adresse) {
      toast.error("Veuillez remplir tous les champs obligatoires");
      return;
    }

    const newSite: Site = {
      id: site?.id || `site_${Date.now()}`,
      nom: formData.nom!,
      campus: formData.campus!,
      adresse: formData.adresse!,
      superficie: formData.superficie || "",
      capacite: formData.capacite || 0,
    };

    onSave(newSite);
    toast.success(site ? "Site modifié" : "Site créé");
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{site ? "Modifier le site" : "Nouveau site"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="nom">Nom du site *</Label>
            <Input
              id="nom"
              value={formData.nom}
              onChange={(e) => setFormData({ ...formData, nom: e.target.value })}
              required
            />
          </div>
          <div>
            <Label htmlFor="campus">Campus *</Label>
            <Select
              value={formData.campus}
              onValueChange={(value) => setFormData({ ...formData, campus: value })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Sélectionner un campus" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Campus Principal">Campus Principal</SelectItem>
                <SelectItem value="Campus Nord">Campus Nord</SelectItem>
                <SelectItem value="Campus Sud">Campus Sud</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="adresse">Adresse *</Label>
            <Textarea
              id="adresse"
              value={formData.adresse}
              onChange={(e) => setFormData({ ...formData, adresse: e.target.value })}
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="superficie">Superficie</Label>
              <Input
                id="superficie"
                value={formData.superficie}
                onChange={(e) => setFormData({ ...formData, superficie: e.target.value })}
                placeholder="Ex: 5000 m²"
              />
            </div>
            <div>
              <Label htmlFor="capacite">Capacité</Label>
              <Input
                id="capacite"
                type="number"
                value={formData.capacite}
                onChange={(e) => setFormData({ ...formData, capacite: parseInt(e.target.value) || 0 })}
              />
            </div>
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
