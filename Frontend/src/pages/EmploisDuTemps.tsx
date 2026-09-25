import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, CalendarDays, Edit2, Loader2, Plus, Printer, RefreshCw, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { EmploiDuTempsDialog, type CoursSessionItem } from "@/components/pedagogie/EmploiDuTempsDialog";
import { pedagogieApi, structureApi, usersApi, extractErrorMessage } from "@/services/apiClient";
import type { Course, Matiere, User } from "@/services/apiTypes";

const jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"];
const slots = [{ label: "08:00 - 10:00", debut: "08:00" }, { label: "10:00 - 12:00", debut: "10:00" }, { label: "14:00 - 16:00", debut: "14:00" }, { label: "16:00 - 18:00", debut: "16:00" }, { label: "18:00 - 20:00", debut: "18:00" }];

interface EnseignantOption { id: string; nom: string; }

const EmploisDuTemps = () => {
  const [cours, setCours] = useState<CoursSessionItem[]>([]);
  const [matieres, setMatieres] = useState<Matiere[]>([]);
  const [enseignants, setEnseignants] = useState<EnseignantOption[]>([]);
  const [filiereFilter, setFiliereFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selected, setSelected] = useState<CoursSessionItem | undefined>();
  const [selectedSlot, setSelectedSlot] = useState({ jour: 0, heureDebut: "08:00" });

  const load = async () => {
    setLoading(true); setError(null);
    const [courseResult, matiereResult, userResult] = await Promise.all([pedagogieApi.getCours(), structureApi.getMatieres(), usersApi.getAll({ role: "ENSEIGNANT" })]);
    if (courseResult.error || matiereResult.error || userResult.error) setError(extractErrorMessage(courseResult.error || matiereResult.error || userResult.error));
    const matiereList = matiereResult.data || [];
    setMatieres(matiereList);
    setEnseignants((userResult.data || []).filter((user: User) => user.role === "ENSEIGNANT").map((user) => ({ id: String(user.id), nom: `${user.prenom} ${user.nom}` })));
    setCours((courseResult.data || []).map((item: Course) => { const matiere = matiereList.find((candidate) => candidate.id === item.matiere_id); return { id: item.id, jour: Math.max(0, jours.indexOf(item.jour_semaine)), heureDebut: item.heure_debut, heureFin: item.heure_fin, matiere: matiere?.nom || item.matiere_id, matiereId: item.matiere_id, prof: item.enseignant_nom || "", salle: item.salle, typeCours: item.type_cours }; }));
    setLoading(false);
  };
  useEffect(() => { void load(); }, []);

  const filieres = useMemo(() => Array.from(new Set(matieres.map((matiere) => matiere.ue?.filiere?.nom).filter(Boolean))), [matieres]);
  const visibleCours = useMemo(() => cours.filter((item) => filiereFilter === "all" || !item.filiere || item.filiere === filiereFilter), [cours, filiereFilter]);
  const openAdd = (jour: number, heureDebut: string) => { setSelected(undefined); setSelectedSlot({ jour, heureDebut }); setDialogOpen(true); };
  const openEdit = (item: CoursSessionItem) => { setSelected(item); setDialogOpen(true); };
  const save = async (item: CoursSessionItem) => {
    const teacher = enseignants.find((candidate) => candidate.nom === item.prof);
    const payload = {
      matiere_id: item.matiereId,
      enseignant_id: teacher ? Number(teacher.id) : undefined,
      enseignant_nom: item.prof,
      salle: item.salle,
      jour_semaine: jours[item.jour],
      heure_debut: item.heureDebut,
      heure_fin: item.heureFin,
      type_cours: item.typeCours || "CM",
    };
    const result = selected ? await pedagogieApi.updateCours(selected.id, payload) : await pedagogieApi.createCours(payload);
    if (result.error) {
      toast.error(result.error);
      return;
    }
    toast.success(selected ? "Cours mis à jour." : "Cours planifié.");
    setDialogOpen(false);
    await load();
  };
  const remove = async (item: CoursSessionItem) => { if (!window.confirm("Supprimer ce cours ?")) return; const result = await pedagogieApi.deleteCours(item.id); if (result.error) toast.error(result.error); else { toast.success("Cours supprimé."); await load(); } };

  return <div className="space-y-6"><div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><div><h1 className="text-3xl font-bold text-foreground">Emplois du temps</h1><p className="mt-1 text-muted-foreground">Planning hebdomadaire alimenté par l'API.</p></div><div className="flex gap-2"><Button variant="outline" onClick={() => window.print()}><Printer className="mr-2 h-4 w-4" />Imprimer</Button><Button onClick={() => openAdd(0, "08:00")}><Plus className="mr-2 h-4 w-4" />Planifier</Button></div></div>{error && <Alert variant="destructive"><AlertTriangle className="h-4 w-4" /><AlertTitle>Erreur backend</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}<Card><CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center"><div className="flex min-w-0 flex-1 flex-col gap-1.5 sm:flex-row sm:items-center"><Label htmlFor="filiere-filter" className="shrink-0 text-sm text-muted-foreground">Filière</Label><Select value={filiereFilter} onValueChange={setFiliereFilter}><SelectTrigger id="filiere-filter" className="w-full sm:w-64"><SelectValue placeholder="Filière" /></SelectTrigger><SelectContent><SelectItem value="all">Toutes les filières</SelectItem>{filieres.map((filiere) => <SelectItem key={filiere} value={filiere}>{filiere}</SelectItem>)}</SelectContent></Select></div><div className="flex shrink-0 items-center gap-3 sm:ml-auto"><Badge variant="secondary">{visibleCours.length} cours</Badge><Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}><RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />Actualiser</Button></div></CardContent></Card><Card><CardHeader><CardTitle className="flex items-center gap-2"><CalendarDays className="h-5 w-5 text-primary" />Planning hebdomadaire</CardTitle><CardDescription>Cliquez sur une case libre pour créer une séance.</CardDescription></CardHeader><CardContent className="p-0"><div className="overflow-x-auto border-t"><div className="min-w-[1000px]"><div className="grid grid-cols-7 gap-1 bg-muted/40 p-2"><div />{jours.map((jour) => <div key={jour} className="p-2 text-center text-xs font-semibold">{jour}</div>)}</div>{slots.map((slot) => <div key={slot.debut} className="grid grid-cols-7 gap-1 border-t p-1"><div className="p-2 text-center font-mono text-[10px] text-muted-foreground">{slot.label}</div>{jours.map((_, day) => { const item = visibleCours.find((candidate) => candidate.jour === day && candidate.heureDebut === slot.debut); return <button key={`${day}-${slot.debut}`} type="button" onClick={() => item ? openEdit(item) : openAdd(day, slot.debut)} className={`min-h-24 rounded-lg border p-2 text-left text-xs ${item ? "border-primary/30 bg-primary/5" : "border-dashed border-border/60 hover:bg-accent/30"}`}>{item ? <><div className="flex justify-between gap-1"><span className="font-semibold">{item.matiere}</span><span className="flex gap-1"><Edit2 className="h-3 w-3" /><Trash2 className="h-3 w-3" onClick={(event) => { event.stopPropagation(); void remove(item); }} /></span></div><p className="mt-2 text-muted-foreground">{item.prof || "Enseignant non renseigné"}</p><p className="mt-1 font-mono text-[10px]">{item.salle}</p></> : <Plus className="mx-auto mt-7 h-4 w-4 text-muted-foreground/40" />}</button>; })}</div>)}</div></div></CardContent></Card><EmploiDuTempsDialog open={dialogOpen} onOpenChange={setDialogOpen} sessionToEdit={selected} initialJour={selectedSlot.jour} initialHeureDebut={selectedSlot.heureDebut} existingSessions={visibleCours} matieres={matieres} enseignants={enseignants} onSave={save} /></div>;
};

export default EmploisDuTemps;
