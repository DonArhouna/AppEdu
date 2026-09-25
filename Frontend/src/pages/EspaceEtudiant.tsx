import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertCircle, BarChart3, CalendarDays, FileText, Loader2, RefreshCw } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { KpiCard } from "@/components/ui/kpi-card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAuth } from "@/contexts/AuthContext";
import { portalsApi } from "@/services/apiClient";
import type { Absence, AcademicSession, Course, Invoice, Matiere, Note, Student } from "@/services/apiTypes";

const EspaceEtudiant = () => {
  const { user } = useAuth();
  const [student, setStudent] = useState<Student | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [absences, setAbsences] = useState<Absence[]>([]);
  const [factures, setFactures] = useState<Invoice[]>([]);
  const [cours, setCours] = useState<Course[]>([]);
  const [matieres, setMatieres] = useState<Matiere[]>([]);
  const [sessions, setSessions] = useState<AcademicSession[]>([]);
  const [currency, setCurrency] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    const result = await portalsApi.getStudentPortal();
    if (result.error || !result.data) {
      setError(result.error || "Le portail étudiant est indisponible.");
      setStudent(null);
      setNotes([]);
      setAbsences([]);
      setFactures([]);
      setCours([]);
      setMatieres([]);
      setSessions([]);
      setLoading(false);
      return;
    }

    const portal = result.data;
    setStudent(portal.etudiant);
    setNotes(portal.notes || []);
    setAbsences(portal.absences || []);
    setFactures(portal.factures || []);
    setCours(portal.cours || []);
    setMatieres(portal.matieres || []);
    setSessions(portal.sessions || []);
    setCurrency(portal.devise || "");
    setLoading(false);
  }, []);

  useEffect(() => { void loadData(); }, [loadData]);

  const matiereName = (id: string) => matieres.find((matiere) => matiere.id === id)?.nom || "Matière";
  const sessionName = (id: string) => sessions.find((session) => session.id === id)?.nom || "Session";
  const average = useMemo(() => {
    const weighted = notes.reduce((sum, note) => sum + Number(note.valeur || 0) * Number(note.coefficient || 1), 0);
    const coefficients = notes.reduce((sum, note) => sum + Number(note.coefficient || 1), 0);
    return coefficients ? (weighted / coefficients).toFixed(2) : "—";
  }, [notes]);
  const currencyLabel = currency || "devise de l'établissement";

  if (loading) return <div className="flex items-center justify-center gap-2 p-16 text-sm text-muted-foreground"><Loader2 className="h-5 w-5 animate-spin" /> Chargement de votre espace...</div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><div><h1 className="text-3xl font-bold text-foreground">Espace étudiant</h1><p className="mt-1 text-muted-foreground">{student ? `${student.prenom} ${student.nom} · ${student.matricule}` : "Aucun dossier associé"}</p></div><Button variant="outline" onClick={loadData}><RefreshCw className="mr-2 h-4 w-4" />Actualiser</Button></div>
      {error && <Alert variant="destructive"><AlertCircle className="h-4 w-4" /><AlertTitle>Espace indisponible</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}
      {student && <>
        <div className="grid gap-4 md:grid-cols-3"><KpiCard title="Moyenne pondérée" value={`${average}/20`} icon={BarChart3} subtitle={`${notes.length} note(s) enregistrée(s)`} colorVariant="primary" /><KpiCard title="Absences" value={absences.length} icon={AlertCircle} subtitle={`${absences.filter((item) => !item.justifiee).length} non justifiée(s)`} colorVariant="amber" /><KpiCard title="Factures soldées" value={`${factures.filter((item) => item.statut === "payee").length}/${factures.length}`} icon={FileText} subtitle="Données de facturation" colorVariant="emerald" /></div>
        <Tabs defaultValue="notes" className="space-y-4"><TabsList><TabsTrigger value="emploi"><CalendarDays className="mr-2 h-4 w-4" />Emploi du temps</TabsTrigger><TabsTrigger value="notes"><FileText className="mr-2 h-4 w-4" />Notes</TabsTrigger><TabsTrigger value="absences"><AlertCircle className="mr-2 h-4 w-4" />Absences</TabsTrigger><TabsTrigger value="factures"><FileText className="mr-2 h-4 w-4" />Factures</TabsTrigger></TabsList>
          <TabsContent value="emploi"><Card><CardHeader><CardTitle>Emploi du temps disponible</CardTitle><CardDescription>Les cours sont ceux enregistrés dans le backend.</CardDescription></CardHeader><CardContent className="space-y-3">{cours.length === 0 ? <p className="text-sm text-muted-foreground">Aucun cours enregistré.</p> : cours.map((item) => <div key={item.id} className="flex justify-between rounded-lg border p-3 text-sm"><div><p className="font-medium">{matiereName(item.matiere_id)}</p><p className="text-muted-foreground">{item.jour_semaine} · {item.heure_debut}–{item.heure_fin} · {item.salle}</p></div><Badge variant="outline">{item.type_cours}</Badge></div>)}</CardContent></Card></TabsContent>
          <TabsContent value="notes"><Card><CardHeader><CardTitle>Mes notes</CardTitle></CardHeader><CardContent className="p-0"><Table><TableHeader><TableRow><TableHead>Matière</TableHead><TableHead>Session</TableHead><TableHead>Note</TableHead><TableHead>Coefficient</TableHead><TableHead>Statut</TableHead></TableRow></TableHeader><TableBody>{notes.length === 0 ? <TableRow><TableCell colSpan={5} className="py-8 text-center text-muted-foreground">Aucune note.</TableCell></TableRow> : notes.map((note) => <TableRow key={note.id}><TableCell>{matiereName(note.matiere_id)}</TableCell><TableCell>{sessionName(note.session_id)}</TableCell><TableCell className="font-mono font-semibold">{note.valeur}/20</TableCell><TableCell>{note.coefficient}</TableCell><TableCell><Badge variant={note.statut === "Validé" ? "default" : "destructive"}>{note.statut}</Badge></TableCell></TableRow>)}</TableBody></Table></CardContent></Card></TabsContent>
          <TabsContent value="absences"><Card><CardHeader><CardTitle>Mes absences</CardTitle></CardHeader><CardContent className="space-y-3">{absences.length === 0 ? <p className="text-sm text-muted-foreground">Aucune absence enregistrée.</p> : absences.map((absence) => <div key={absence.id} className="flex justify-between rounded-lg border p-3 text-sm"><div><p className="font-medium">{matiereName(absence.matiere_id)}</p><p className="text-muted-foreground">{absence.date_absence} · {absence.motif || "Motif non renseigné"}</p></div><Badge variant={absence.justifiee ? "default" : "destructive"}>{absence.justifiee ? "Justifiée" : "Non justifiée"}</Badge></div>)}</CardContent></Card></TabsContent>
          <TabsContent value="factures"><Card><CardHeader><CardTitle>Mes factures</CardTitle></CardHeader><CardContent className="space-y-3">{factures.length === 0 ? <p className="text-sm text-muted-foreground">Aucune facture.</p> : factures.map((facture) => <div key={facture.id} className="flex justify-between rounded-lg border p-3 text-sm"><div><p className="font-mono font-medium">{facture.numero_facture}</p><p className="text-muted-foreground">Échéance : {facture.date_echeance}</p></div><div className="text-right"><p className="font-semibold">{Number(facture.montant_total).toLocaleString("fr-FR")} {currencyLabel}</p><Badge variant={facture.statut === "payee" ? "default" : "secondary"}>{facture.statut}</Badge></div></div>)}</CardContent></Card></TabsContent>
        </Tabs>
      </>}
    </div>
  );
};

export default EspaceEtudiant;
