import { useEffect, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import { Textarea } from "@/components/ui/textarea";

export interface SalleEditee {
  id?: string;
  nom: string;
  code: string;
  campus_id?: string | null;
  batiment?: string | null;
  etage?: string | null;
  capacite?: number | null;
  type_salle: string;
  equipements?: string | null;
  disponible: boolean;
}

interface CampusOption {
  id: string;
  nom: string;
}

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  salle?: SalleEditee;
  campus: CampusOption[];
  onSave: (salle: SalleEditee) => Promise<boolean>;
}

const TYPES = ["Salle de classe", "Amphithéâtre", "Laboratoire", "Atelier", "Salle informatique"];

const SalleDialog = ({ open, onOpenChange, salle, campus, onSave }: Props) => {
  const [form, setForm] = useState<SalleEditee>({ nom: "", code: "", type_salle: TYPES[0], disponible: true });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setForm(salle ? { ...salle } : { nom: "", code: "", type_salle: TYPES[0], disponible: true });
    }
  }, [open, salle]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!form.nom.trim() || !form.code.trim()) {
      toast.error("Le nom et le code de la salle sont obligatoires.");
      return;
    }
    setSaving(true);
    const ok = await onSave({ ...form, nom: form.nom.trim(), code: form.code.trim() });
    setSaving(false);
    if (ok) onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[560px]">
        <DialogHeader>
          <DialogTitle>{salle ? "Modifier la salle" : "Nouvelle salle"}</DialogTitle>
          <DialogDescription>
            Le nom identifie la salle dans l'emploi du temps : la détection de conflits s'appuie dessus.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-4 py-2">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="salle-nom">Nom *</Label>
              <Input
                id="salle-nom"
                value={form.nom}
                onChange={(event) => setForm({ ...form, nom: event.target.value })}
                placeholder="Amphi A"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="salle-code">Code *</Label>
              <Input
                id="salle-code"
                value={form.code}
                onChange={(event) => setForm({ ...form, code: event.target.value })}
                placeholder="AMPHI-A"
                required
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="salle-type">Type</Label>
              <Select value={form.type_salle} onValueChange={(value) => setForm({ ...form, type_salle: value })}>
                <SelectTrigger id="salle-type"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {TYPES.map((type) => <SelectItem key={type} value={type}>{type}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="salle-capacite">Capacité</Label>
              <Input
                id="salle-capacite"
                type="number"
                min={0}
                value={form.capacite ?? ""}
                onChange={(event) =>
                  setForm({ ...form, capacite: event.target.value === "" ? null : Number(event.target.value) })
                }
                placeholder="150"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="salle-batiment">Bâtiment</Label>
              <Input
                id="salle-batiment"
                value={form.batiment ?? ""}
                onChange={(event) => setForm({ ...form, batiment: event.target.value })}
                placeholder="Bâtiment principal"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="salle-etage">Étage</Label>
              <Input
                id="salle-etage"
                value={form.etage ?? ""}
                onChange={(event) => setForm({ ...form, etage: event.target.value })}
                placeholder="RDC"
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="salle-campus">Campus</Label>
            <Select
              value={form.campus_id || "none"}
              onValueChange={(value) => setForm({ ...form, campus_id: value === "none" ? null : value })}
            >
              <SelectTrigger id="salle-campus"><SelectValue placeholder="Aucun campus" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="none">Aucun campus</SelectItem>
                {campus.map((item) => <SelectItem key={item.id} value={item.id}>{item.nom}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="salle-equipements">Équipements</Label>
            <Textarea
              id="salle-equipements"
              value={form.equipements ?? ""}
              onChange={(event) => setForm({ ...form, equipements: event.target.value })}
              placeholder="Vidéoprojecteur, tableau blanc..."
              rows={2}
            />
          </div>
          <div className="flex items-center justify-between rounded-lg border p-3">
            <div>
              <Label htmlFor="salle-disponible" className="cursor-pointer">Disponible</Label>
              <p className="text-xs text-muted-foreground">Une salle indisponible refuse toute nouvelle séance.</p>
            </div>
            <Switch
              id="salle-disponible"
              checked={form.disponible}
              onCheckedChange={(checked) => setForm({ ...form, disponible: checked })}
            />
          </div>
          <DialogFooter className="border-t pt-4">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Annuler</Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Enregistrement..." : "Enregistrer"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default SalleDialog;
