import { useEffect, useMemo, useState, type FormEvent } from "react";
import { AlertTriangle, Clock } from "lucide-react";
import { toast } from "sonner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export interface CoursSessionItem {
  id: string;
  jour: number;
  heureDebut: string;
  heureFin: string;
  matiere: string;
  matiereId?: string;
  prof: string;
  salle: string;
  filiere?: string;
  niveau?: string;
  typeCours?: string;
}

interface MatiereOption { id: string; code: string; nom: string; filiere?: string; niveau?: string; }
interface EnseignantOption { id: string; nom: string; }

interface Props { open: boolean; onOpenChange: (open: boolean) => void; sessionToEdit?: CoursSessionItem; initialJour?: number; initialHeureDebut?: string; existingSessions?: CoursSessionItem[]; matieres?: MatiereOption[]; enseignants?: EnseignantOption[]; onSave: (session: CoursSessionItem) => void; }

const jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"];
const timeToMinutes = (value: string) => { const [h, m] = value.split(":").map(Number); return (h || 0) * 60 + (m || 0); };
const minutesToTime = (value: number) => `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(value % 60).padStart(2, "0")}`;

export const EmploiDuTempsDialog = ({ open, onOpenChange, sessionToEdit, initialJour = 0, initialHeureDebut = "08:00", existingSessions = [], matieres = [], enseignants = [], onSave }: Props) => {
  const [form, setForm] = useState<CoursSessionItem>({ id: "", jour: initialJour, heureDebut: initialHeureDebut, heureFin: "", matiere: "", matiereId: "", prof: "", salle: "", filiere: "", niveau: "", typeCours: "CM" });
  useEffect(() => { if (open) setForm(sessionToEdit ? { ...sessionToEdit } : { id: "", jour: initialJour, heureDebut: initialHeureDebut, heureFin: minutesToTime(timeToMinutes(initialHeureDebut) + 120), matiere: "", matiereId: "", prof: "", salle: "", filiere: "", niveau: "", typeCours: "CM" }); }, [open, sessionToEdit, initialJour, initialHeureDebut]);
  const duration = timeToMinutes(form.heureFin) - timeToMinutes(form.heureDebut);
  const conflicts = useMemo(() => existingSessions.filter((item) => item.id !== form.id && item.jour === form.jour && timeToMinutes(form.heureDebut) < timeToMinutes(item.heureFin) && timeToMinutes(form.heureFin) > timeToMinutes(item.heureDebut) && (item.salle === form.salle || item.prof === form.prof)), [existingSessions, form]);
  const selectMatiere = (id: string) => { const item = matieres.find((matiere) => matiere.id === id); setForm((current) => ({ ...current, matiereId: id, matiere: item?.nom || "", filiere: item?.filiere || current.filiere, niveau: item?.niveau || current.niveau })); };
  const submit = (event: FormEvent) => { event.preventDefault(); if (!form.matiereId || !form.prof || !form.salle || duration <= 0) { toast.error("Renseignez la matière, l'enseignant, la salle et des horaires valides."); return; } onSave(form); if (conflicts.length) toast.warning("Des chevauchements ont été détectés."); onOpenChange(false); };
  return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent className="sm:max-w-[600px]"><DialogHeader><DialogTitle className="flex items-center gap-2 text-xl"><Clock className="h-5 w-5 text-primary" />{sessionToEdit ? "Modifier la séance" : "Planifier un cours"}</DialogTitle><DialogDescription>Les cours, matières et enseignants sont sélectionnés depuis les données API.</DialogDescription></DialogHeader><form onSubmit={submit} className="space-y-4 py-2"><div className="space-y-2"><Label>Matière *</Label><Select value={form.matiereId || ""} onValueChange={selectMatiere}><SelectTrigger><SelectValue placeholder="Sélectionner une matière" /></SelectTrigger><SelectContent>{matieres.map((matiere) => <SelectItem key={matiere.id} value={matiere.id}>{matiere.code} — {matiere.nom}</SelectItem>)}</SelectContent></Select></div><div className="grid grid-cols-2 gap-4"><div className="space-y-2"><Label>Enseignant *</Label><Select value={form.prof} onValueChange={(value) => setForm({ ...form, prof: value })}><SelectTrigger><SelectValue placeholder="Sélectionner" /></SelectTrigger><SelectContent>{enseignants.map((teacher) => <SelectItem key={teacher.id} value={teacher.nom}>{teacher.nom}</SelectItem>)}</SelectContent></Select></div><div className="space-y-2"><Label>Salle *</Label><Input value={form.salle} onChange={(event) => setForm({ ...form, salle: event.target.value })} placeholder="Saisie de la salle" required /></div></div><div className="grid grid-cols-3 gap-4"><div className="space-y-2"><Label>Jour</Label><Select value={String(form.jour)} onValueChange={(value) => setForm({ ...form, jour: Number(value) })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{jours.map((jour, index) => <SelectItem key={jour} value={String(index)}>{jour}</SelectItem>)}</SelectContent></Select></div><div className="space-y-2"><Label>Début</Label><Input type="time" value={form.heureDebut} onChange={(event) => setForm({ ...form, heureDebut: event.target.value })} required /></div><div className="space-y-2"><Label>Fin</Label><Input type="time" value={form.heureFin} onChange={(event) => setForm({ ...form, heureFin: event.target.value })} required /></div></div><div className="grid grid-cols-2 gap-4"><div className="space-y-2"><Label>Type</Label><Select value={form.typeCours || "CM"} onValueChange={(value) => setForm({ ...form, typeCours: value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="CM">CM</SelectItem><SelectItem value="TD">TD</SelectItem><SelectItem value="TP">TP</SelectItem></SelectContent></Select></div><div className="space-y-2"><Label>Filière / niveau</Label><Input value={`${form.filiere || ""} ${form.niveau || ""}`} readOnly placeholder="Déduit de la matière" /></div></div>{conflicts.length > 0 && <Alert className="border-amber-500/30 bg-amber-500/10"><AlertTriangle className="h-4 w-4" /><AlertTitle>Chevauchement détecté</AlertTitle><AlertDescription>Un cours existant utilise la même salle ou le même enseignant sur ce créneau.</AlertDescription></Alert>}<div className="flex justify-end gap-2 border-t pt-4"><Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Annuler</Button><Button type="submit">Enregistrer</Button></div></form></DialogContent></Dialog>;
};

export default EmploiDuTempsDialog;
