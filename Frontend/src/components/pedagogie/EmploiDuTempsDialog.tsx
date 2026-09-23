import { useState, useEffect, useMemo } from "react";
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
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertTriangle, Clock, Sparkles } from "lucide-react";
import { toast } from "sonner";

export interface CoursSessionItem {
  id: string;
  jour: number;
  heureDebut: string;
  heureFin: string;
  matiere: string;
  prof: string;
  salle: string;
  filiere?: string;
  niveau?: string;
  isCoursDuSoir?: boolean;
}

interface EmploiDuTempsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  sessionToEdit?: CoursSessionItem;
  initialJour?: number;
  initialHeureDebut?: string;
  existingSessions?: CoursSessionItem[];
  onSave: (session: CoursSessionItem) => void;
}

// Convert "HH:mm" to total minutes since midnight
const timeToMinutes = (timeStr: string): number => {
  if (!timeStr || !timeStr.includes(":")) return 0;
  const [hours, minutes] = timeStr.split(":").map(Number);
  return (hours || 0) * 60 + (minutes || 0);
};

// Convert total minutes to "HH:mm"
const minutesToTime = (totalMinutes: number): string => {
  const h = Math.floor(totalMinutes / 60) % 24;
  const m = totalMinutes % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
};

export const EmploiDuTempsDialog = ({
  open,
  onOpenChange,
  sessionToEdit,
  initialJour = 0,
  initialHeureDebut = "08:00",
  existingSessions = [],
  onSave,
}: EmploiDuTempsDialogProps) => {
  const [formData, setFormData] = useState<CoursSessionItem>({
    id: sessionToEdit?.id || "",
    matiere: sessionToEdit?.matiere || "Programmation Web React",
    prof: sessionToEdit?.prof || "M. Mamadou Diallo",
    salle: sessionToEdit?.salle || "Salle A101",
    jour: sessionToEdit?.jour !== undefined ? sessionToEdit.jour : initialJour,
    heureDebut: sessionToEdit?.heureDebut || initialHeureDebut,
    heureFin: sessionToEdit?.heureFin || "11:00",
    filiere: sessionToEdit?.filiere || "Génie Informatique",
    niveau: sessionToEdit?.niveau || "Licence 3",
  });

  useEffect(() => {
    if (sessionToEdit) {
      setFormData({
        id: sessionToEdit.id,
        matiere: sessionToEdit.matiere,
        prof: sessionToEdit.prof,
        salle: sessionToEdit.salle,
        jour: sessionToEdit.jour,
        heureDebut: sessionToEdit.heureDebut || "08:00",
        heureFin: sessionToEdit.heureFin || "10:00",
        filiere: sessionToEdit.filiere || "Génie Informatique",
        niveau: sessionToEdit.niveau || "Licence 3",
      });
    } else {
      setFormData({
        id: String(Date.now()),
        matiere: "Programmation Web React",
        prof: "M. Mamadou Diallo",
        salle: "Salle A101",
        jour: initialJour,
        heureDebut: initialHeureDebut,
        heureFin: minutesToTime(timeToMinutes(initialHeureDebut) + 180), // default +3h
        filiere: "Génie Informatique",
        niveau: "Licence 3",
      });
    }
  }, [sessionToEdit, initialJour, initialHeureDebut, open]);

  // Validation: heureFin must be strictly after heureDebut
  const startMins = timeToMinutes(formData.heureDebut);
  const endMins = timeToMinutes(formData.heureFin);
  const durationMins = endMins - startMins;
  const isTimeOrderValid = durationMins > 0;

  // Conflict Detection
  const conflicts = useMemo(() => {
    if (!isTimeOrderValid) return [];

    const foundConflicts: { type: "salle" | "prof" | "classe"; message: string; session: CoursSessionItem }[] = [];

    existingSessions.forEach((item) => {
      // Exclude the current session if editing
      if (item.id === formData.id) return;
      // Only check the same day
      if (item.jour !== formData.jour) return;

      const itemStart = timeToMinutes(item.heureDebut);
      const itemEnd = timeToMinutes(item.heureFin);

      // Overlap condition: start < itemEnd && end > itemStart
      const hasOverlap = startMins < itemEnd && endMins > itemStart;

      if (hasOverlap) {
        if (item.salle === formData.salle) {
          foundConflicts.push({
            type: "salle",
            message: `La salle "${formData.salle}" est déjà occupée par [${item.matiere}] de ${item.heureDebut} à ${item.heureFin}.`,
            session: item,
          });
        }
        if (item.prof === formData.prof) {
          foundConflicts.push({
            type: "prof",
            message: `L'enseignant(e) ${formData.prof} a déjà un cours de [${item.matiere}] de ${item.heureDebut} à ${item.heureFin}.`,
            session: item,
          });
        }
        if (item.filiere === formData.filiere && item.niveau === formData.niveau && formData.filiere) {
          foundConflicts.push({
            type: "classe",
            message: `La promotion ${formData.filiere} (${formData.niveau}) a déjà une séance de [${item.matiere}] de ${item.heureDebut} à ${item.heureFin}.`,
            session: item,
          });
        }
      }
    });

    return foundConflicts;
  }, [formData, startMins, endMins, isTimeOrderValid, existingSessions]);

  // Quick duration helper: sets heureFin based on heureDebut + minutes
  const applyDuration = (durationInMinutes: number) => {
    const newEndMins = startMins + durationInMinutes;
    setFormData((prev) => ({
      ...prev,
      heureFin: minutesToTime(newEndMins),
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!isTimeOrderValid) {
      toast.error("L'heure de fin doit être postérieure à l'heure de début.");
      return;
    }

    onSave(formData);

    if (conflicts.length > 0) {
      toast.warning(
        `Cours planifié avec ${conflicts.length} chevauchement(s) détecté(s).`,
        { duration: 4000 }
      );
    } else {
      toast.success(
        sessionToEdit
          ? "Le cours a été mis à jour."
          : `Cours planifié avec succès (${formData.heureDebut} à ${formData.heureFin}).`
      );
    }
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[560px] rounded-2xl">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold flex items-center gap-2">
            <Clock className="h-5 w-5 text-primary" />
            {sessionToEdit ? "Modifier la séance de cours" : "Planifier un cours (Saisie Libre des Horaires)"}
          </DialogTitle>
          <DialogDescription>
            Saisie libre des horaires au clavier ou sélecteur (cours standard, blocs de 3h, ou cours du soir jusqu'à 22h).
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 py-2">
          {/* Matière */}
          <div className="space-y-1.5">
            <Label htmlFor="matiere" className="text-xs font-semibold text-muted-foreground uppercase">
              Matière (ECUE) *
            </Label>
            <Select
              value={formData.matiere}
              onValueChange={(val) => setFormData({ ...formData, matiere: val })}
            >
              <SelectTrigger id="matiere" className="h-10 rounded-xl">
                <SelectValue placeholder="Choisir la matière" />
              </SelectTrigger>
              <SelectContent className="rounded-xl">
                <SelectItem value="Programmation Web React">INF301 - Programmation Web React</SelectItem>
                <SelectItem value="Base de données SQL">INF302 - Base de données SQL</SelectItem>
                <SelectItem value="Algorithmique Avancée">INF303 - Algorithmique Avancée</SelectItem>
                <SelectItem value="Architecture Réseaux">INF304 - Architecture Réseaux</SelectItem>
                <SelectItem value="Développement Mobile">INF305 - Développement Mobile</SelectItem>
                <SelectItem value="Gestion de projet Agile">MGT201 - Gestion de projet Agile</SelectItem>
                <SelectItem value="Sécurité & Cryptographie">INF306 - Sécurité & Cryptographie</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Enseignant & Salle */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="prof" className="text-xs font-semibold text-muted-foreground uppercase">
                Enseignant *
              </Label>
              <Select
                value={formData.prof}
                onValueChange={(val) => setFormData({ ...formData, prof: val })}
              >
                <SelectTrigger id="prof" className="h-10 rounded-xl">
                  <SelectValue placeholder="Enseignant" />
                </SelectTrigger>
                <SelectContent className="rounded-xl">
                  <SelectItem value="M. Mamadou Diallo">M. Mamadou Diallo</SelectItem>
                  <SelectItem value="Mme Sophie Ndiaye">Mme Sophie Ndiaye</SelectItem>
                  <SelectItem value="M. Jean-Philippe Sow">M. Jean-Philippe Sow</SelectItem>
                  <SelectItem value="Mme Fatou Traoré">Mme Fatou Traoré</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="salle" className="text-xs font-semibold text-muted-foreground uppercase">
                Salle de Classe *
              </Label>
              <Select
                value={formData.salle}
                onValueChange={(val) => setFormData({ ...formData, salle: val })}
              >
                <SelectTrigger id="salle" className="h-10 rounded-xl">
                  <SelectValue placeholder="Salle" />
                </SelectTrigger>
                <SelectContent className="rounded-xl">
                  <SelectItem value="Salle A101">Salle A101 (Informatique)</SelectItem>
                  <SelectItem value="Salle A204">Salle A204 (Cours)</SelectItem>
                  <SelectItem value="Labo 1">Labo Réseau 1</SelectItem>
                  <SelectItem value="Labo 2">Labo Mobile 2</SelectItem>
                  <SelectItem value="Amphi A">Amphithéâtre A</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Filière & Niveau */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="filiere" className="text-xs font-semibold text-muted-foreground uppercase">
                Filière / Programme
              </Label>
              <Select
                value={formData.filiere}
                onValueChange={(val) => setFormData({ ...formData, filiere: val })}
              >
                <SelectTrigger id="filiere" className="h-10 rounded-xl">
                  <SelectValue placeholder="Filière" />
                </SelectTrigger>
                <SelectContent className="rounded-xl">
                  <SelectItem value="Génie Informatique">Génie Informatique</SelectItem>
                  <SelectItem value="Gestion & Finance">Gestion & Finance</SelectItem>
                  <SelectItem value="Réseaux & Télécoms">Réseaux & Télécoms</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="niveau" className="text-xs font-semibold text-muted-foreground uppercase">
                Niveau d'étude
              </Label>
              <Select
                value={formData.niveau}
                onValueChange={(val) => setFormData({ ...formData, niveau: val })}
              >
                <SelectTrigger id="niveau" className="h-10 rounded-xl">
                  <SelectValue placeholder="Niveau" />
                </SelectTrigger>
                <SelectContent className="rounded-xl">
                  <SelectItem value="Licence 1">Licence 1 (L1)</SelectItem>
                  <SelectItem value="Licence 2">Licence 2 (L2)</SelectItem>
                  <SelectItem value="Licence 3">Licence 3 (L3)</SelectItem>
                  <SelectItem value="Master 1">Master 1 (M1)</SelectItem>
                  <SelectItem value="Master 2">Master 2 (M2)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Jour & Horaires en Saisie Libre */}
          <div className="p-4 rounded-xl bg-muted/25 border border-border/70 space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {/* Jour */}
              <div className="space-y-1.5">
                <Label htmlFor="jour" className="text-xs font-semibold text-muted-foreground uppercase">
                  Jour *
                </Label>
                <Select
                  value={String(formData.jour)}
                  onValueChange={(val) => setFormData({ ...formData, jour: parseInt(val) })}
                >
                  <SelectTrigger id="jour" className="h-10 rounded-xl bg-background">
                    <SelectValue placeholder="Jour" />
                  </SelectTrigger>
                  <SelectContent className="rounded-xl">
                    <SelectItem value="0">Lundi</SelectItem>
                    <SelectItem value="1">Mardi</SelectItem>
                    <SelectItem value="2">Mercredi</SelectItem>
                    <SelectItem value="3">Jeudi</SelectItem>
                    <SelectItem value="4">Vendredi</SelectItem>
                    <SelectItem value="5">Samedi</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Heure Début (Saisie Libre) */}
              <div className="space-y-1.5">
                <Label htmlFor="h-start" className="text-xs font-semibold text-muted-foreground uppercase flex items-center justify-between">
                  <span>Heure Début *</span>
                </Label>
                <Input
                  id="h-start"
                  type="time"
                  step="900"
                  value={formData.heureDebut}
                  onChange={(e) => setFormData({ ...formData, heureDebut: e.target.value })}
                  required
                  className="h-10 rounded-xl bg-background font-mono text-sm"
                />
              </div>

              {/* Heure Fin (Saisie Libre) */}
              <div className="space-y-1.5">
                <Label htmlFor="h-end" className="text-xs font-semibold text-muted-foreground uppercase flex items-center justify-between">
                  <span>Heure Fin *</span>
                  {isTimeOrderValid && (
                    <span className="text-[10px] text-primary font-bold lowercase">
                      ({Math.floor(durationMins / 60)}h{durationMins % 60 > 0 ? `${durationMins % 60}m` : ""})
                    </span>
                  )}
                </Label>
                <Input
                  id="h-end"
                  type="time"
                  step="900"
                  value={formData.heureFin}
                  onChange={(e) => setFormData({ ...formData, heureFin: e.target.value })}
                  required
                  className={`h-10 rounded-xl bg-background font-mono text-sm ${
                    !isTimeOrderValid ? "border-destructive text-destructive focus-visible:ring-destructive" : ""
                  }`}
                />
              </div>
            </div>

            {/* Quick duration helpers */}
            <div className="flex items-center gap-1.5 flex-wrap pt-1">
              <span className="text-[10px] uppercase font-bold text-muted-foreground flex items-center gap-1 mr-1">
                <Sparkles className="h-2.5 w-2.5 text-amber-500" /> Durée rapide :
              </span>
              {[
                { label: "+1h", mins: 60 },
                { label: "+1h30", mins: 90 },
                { label: "+2h", mins: 120 },
                { label: "+3h", mins: 180 },
                { label: "+4h", mins: 240 },
              ].map((pill) => (
                <button
                  key={pill.label}
                  type="button"
                  onClick={() => applyDuration(pill.mins)}
                  className="px-2 py-0.5 rounded-lg text-xs font-medium bg-background border border-border/80 hover:bg-primary/10 hover:text-primary hover:border-primary/40 transition-colors"
                >
                  {pill.label}
                </button>
              ))}
            </div>

            {/* Inversion Error Message */}
            {!isTimeOrderValid && (
              <p className="text-xs font-semibold text-destructive flex items-center gap-1 pt-1">
                <AlertTriangle className="h-3.5 w-3.5" />
                L'heure de fin ({formData.heureFin}) doit être strictement postérieure à l'heure de début ({formData.heureDebut}).
              </p>
            )}
          </div>

          {/* Conflict Warning Banner (Non-blocking as requested) */}
          {conflicts.length > 0 && (
            <Alert className="border-amber-500/30 bg-amber-500/10 text-amber-900 dark:text-amber-200 rounded-xl">
              <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
              <AlertTitle className="text-xs font-bold uppercase tracking-wider">
                {conflicts.length === 1 ? "Chevauchement détecté" : `${conflicts.length} conflits d'horaires détectés`}
              </AlertTitle>
              <AlertDescription className="text-xs space-y-1 mt-1">
                {conflicts.map((c, idx) => (
                  <div key={idx} className="flex items-start gap-1">
                    <span>•</span>
                    <span>{c.message}</span>
                  </div>
                ))}
                <p className="text-[11px] opacity-80 pt-1 italic">
                  Vous pouvez enregistrer tout de même si une dérogation est autorisée.
                </p>
              </AlertDescription>
            </Alert>
          )}

          <div className="flex justify-end gap-3 pt-3 border-t">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} className="rounded-xl">
              Annuler
            </Button>
            <Button type="submit" disabled={!isTimeOrderValid} className="rounded-xl shadow-sm">
              {sessionToEdit ? "Enregistrer les modifications" : "Ajouter au Planning"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};
