import { useEffect, useMemo, useState, type FormEvent } from "react";
import { AlertCircle, CalendarDays, CheckCircle2, Loader2, RefreshCw, Save, XCircle } from "lucide-react";
import { toast } from "sonner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { KpiCard } from "@/components/ui/kpi-card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { pedagogieApi, sessionsApi, structureApi, extractErrorMessage } from "@/services/apiClient";
import type { AcademicSession } from "@/services/apiTypes";

interface StudentRow {
  id: string;
  matricule: string;
  nom: string;
  prenom: string;
}

interface MatiereOption {
  id: string;
  code: string;
  nom: string;
}

const Absences = () => {
  const [students, setStudents] = useState<StudentRow[]>([]);
  const [matieres, setMatieres] = useState<MatiereOption[]>([]);
  const [sessions, setSessions] = useState<AcademicSession[]>([]);
  const [matiereId, setMatiereId] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [date, setDate] = useState("");
  const [duration, setDuration] = useState("");
  const [absentIds, setAbsentIds] = useState<Set<string>>(new Set());
  const [justifiedIds, setJustifiedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [rowsLoading, setRowsLoading] = useState(false);
  const [catalogVersion, setCatalogVersion] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    const [matieresResult, sessionsResult] = await Promise.all([
      structureApi.getMatieres(),
      sessionsApi.getAll(),
    ]);
    if (matieresResult.error || sessionsResult.error) {
      setError(extractErrorMessage(matieresResult.error || sessionsResult.error));
      setMatieres([]);
      setSessions([]);
    } else {
      setMatieres((matieresResult.data || []) as MatiereOption[]);
      setSessions(sessionsResult.data || []);
    }
    setCatalogVersion((version) => version + 1);
    setLoading(false);
  };

  useEffect(() => {
    void loadData();
  }, []);

  useEffect(() => {
    setAbsentIds(new Set());
    setJustifiedIds(new Set());
    if (!matiereId || !sessionId) {
      setStudents([]);
      return;
    }
    const loadStudents = async () => {
      setRowsLoading(true);
      const result = await pedagogieApi.getAssignedStudents(matiereId, sessionId);
      if (result.error) {
        toast.error(extractErrorMessage(result.error));
        setStudents([]);
      } else {
        setStudents((result.data || []) as StudentRow[]);
      }
      setRowsLoading(false);
    };
    void loadStudents();
  }, [matiereId, sessionId, catalogVersion]);

  const toggle = (setter: React.Dispatch<React.SetStateAction<Set<string>>>, id: string, checked: boolean) => {
    setter((current) => {
      const next = new Set(current);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  };

  const selectedMatiere = useMemo(
    () => matieres.find((matiere) => matiere.id === matiereId),
    [matieres, matiereId]
  );

  const saveAbsences = async (event: FormEvent) => {
    event.preventDefault();
    if (!matiereId || !sessionId || !date || !duration || Number(duration) <= 0) {
      toast.error("Sélectionnez une matière, une session, une date et une durée positive.");
      return;
    }
    if (absentIds.size === 0) {
      toast.info("Aucune absence sélectionnée.");
      return;
    }
    setSaving(true);
    const created: string[] = [];
    for (const studentId of absentIds) {
      const result = await pedagogieApi.declareAbsence({
        etudiant_id: studentId,
        matiere_id: matiereId,
        session_id: sessionId,
        date_absence: date,
        duree_heures: Number(duration),
        justifiee: justifiedIds.has(studentId),
      });
      if (result.error) {
        setSaving(false);
        toast.error(extractErrorMessage(result.error, "Une absence n'a pas pu être enregistrée."));
        return;
      }
      created.push(studentId);
    }
    setSaving(false);
    setAbsentIds(new Set());
    setJustifiedIds(new Set());
    toast.success(`${created.length} absence(s) enregistrée(s) dans l'API.`);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Suivi des absences</h1>
          <p className="mt-1 text-muted-foreground">Les absences déclarées sont enregistrées via le backend.</p>
        </div>
        <Button variant="outline" onClick={loadData} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Actualiser
        </Button>
      </div>

      {error && <Alert variant="destructive"><AlertCircle className="h-4 w-4" /><AlertTitle>Erreur backend</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}

      <div className="grid gap-4 md:grid-cols-3">
        <KpiCard
          title="Étudiants"
          value={students.length}
          icon={CheckCircle2}
          subtitle="Dossiers concernés"
          colorVariant="primary"
        />
        <KpiCard
          title="Absences sélectionnées"
          value={absentIds.size}
          icon={XCircle}
          subtitle="À enregistrer"
          colorVariant="rose"
        />
        <KpiCard
          title="Absences justifiées"
          value={justifiedIds.size}
          icon={CalendarDays}
          subtitle="Avec justificatif"
          colorVariant="amber"
        />
      </div>

      <Card>
        <CardHeader><CardTitle>Déclarer une absence</CardTitle><CardDescription>Sélectionnez la séance et les étudiants concernés.</CardDescription></CardHeader>
        <CardContent>
          <form onSubmit={saveAbsences} className="grid gap-4 md:grid-cols-2 xl:grid-cols-5 xl:items-end">
            <div className="space-y-2"><Label>Matière *</Label><Select value={matiereId} onValueChange={setMatiereId}><SelectTrigger><SelectValue placeholder="Sélectionner une matière" /></SelectTrigger><SelectContent>{matieres.map((matiere) => <SelectItem key={matiere.id} value={matiere.id}>{matiere.code} — {matiere.nom}</SelectItem>)}</SelectContent></Select></div>
            <div className="space-y-2"><Label>Session *</Label><Select value={sessionId} onValueChange={setSessionId}><SelectTrigger><SelectValue placeholder="Sélectionner une session" /></SelectTrigger><SelectContent>{sessions.map((session) => <SelectItem key={session.id} value={session.id}>{session.nom} ({session.annee_academique})</SelectItem>)}</SelectContent></Select></div>
            <div className="space-y-2"><Label>Date *</Label><Input type="date" value={date} onChange={(event) => setDate(event.target.value)} required /></div>
             <div className="space-y-2"><Label>Durée (heures) *</Label><Input type="number" min="0.25" step="0.25" value={duration} onChange={(event) => setDuration(event.target.value)} required /></div>
            <Button type="submit" disabled={saving || loading || rowsLoading || students.length === 0}>{saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}Enregistrer</Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Liste des étudiants autorisés</CardTitle><CardDescription>{selectedMatiere ? `${selectedMatiere.code} — ${selectedMatiere.nom}` : "Sélectionnez une matière et une session pour commencer"}</CardDescription></CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto border-t">
            <Table>
              <TableHeader><TableRow className="bg-muted/50"><TableHead>Matricule</TableHead><TableHead>Étudiant</TableHead><TableHead className="text-center">Absent</TableHead><TableHead className="text-center">Justifiée</TableHead><TableHead>Statut</TableHead></TableRow></TableHeader>
              <TableBody>
                {rowsLoading ? <TableRow><TableCell colSpan={5} className="py-10 text-center"><Loader2 className="mx-auto h-5 w-5 animate-spin" /></TableCell></TableRow> : students.length === 0 ? <TableRow><TableCell colSpan={5} className="py-10 text-center text-muted-foreground">Aucun étudiant disponible.</TableCell></TableRow> : students.map((student) => {
                  const absent = absentIds.has(student.id);
                  const justified = justifiedIds.has(student.id);
                  return <TableRow key={student.id}>
                    <TableCell className="font-mono text-xs">{student.matricule}</TableCell>
                    <TableCell className="font-medium">{student.prenom} {student.nom}</TableCell>
                    <TableCell className="text-center"><Checkbox checked={absent} onCheckedChange={(checked) => toggle(setAbsentIds, student.id, Boolean(checked))} /></TableCell>
                    <TableCell className="text-center"><Checkbox checked={justified} disabled={!absent} onCheckedChange={(checked) => toggle(setJustifiedIds, student.id, Boolean(checked))} /></TableCell>
                    <TableCell>{absent ? <Badge variant="destructive">{justified ? "Absence justifiée" : "Absence"}</Badge> : <Badge variant="outline">Présent</Badge>}</TableCell>
                  </TableRow>;
                })}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Absences;
