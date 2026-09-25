import { useEffect, useMemo, useState, type FormEvent } from "react";
import { AlertCircle, CheckCircle2, Loader2, RefreshCw, Save } from "lucide-react";
import { toast } from "sonner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { pedagogieApi, sessionsApi, structureApi, extractErrorMessage } from "@/services/apiClient";
import type { Note as NoteApi } from "@/services/apiTypes";

interface StudentOption {
  id: string;
  matricule: string;
  nom: string;
  prenom: string;
  session_id?: string | null;
}
interface MatiereOption { id: string; code: string; nom: string; }
interface SessionOption { id: string; nom: string; annee_academique: string; }
interface NoteRow {
  id?: string;
  etudiant_id: string;
  valeur: string;
  coefficient: string;
  saved: boolean;
}

const Notes = () => {
  const [students, setStudents] = useState<StudentOption[]>([]);
  const [matieres, setMatieres] = useState<MatiereOption[]>([]);
  const [sessions, setSessions] = useState<SessionOption[]>([]);
  const [selectedMatiere, setSelectedMatiere] = useState("");
  const [selectedSession, setSelectedSession] = useState("");
  const [rows, setRows] = useState<NoteRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [rowsLoading, setRowsLoading] = useState(false);
  const [catalogVersion, setCatalogVersion] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadCatalogs = async () => {
    setLoading(true);
    setError(null);
    const [matiereResult, sessionResult] = await Promise.all([
      structureApi.getMatieres(),
      sessionsApi.getAll(),
    ]);
    if (matiereResult.error || sessionResult.error) {
      setError(extractErrorMessage(matiereResult.error || sessionResult.error));
      setMatieres([]); setSessions([]);
    } else {
      setMatieres((matiereResult.data || []) as MatiereOption[]);
      setSessions((sessionResult.data || []) as SessionOption[]);
    }
    setCatalogVersion((version) => version + 1);
    setLoading(false);
  };

  useEffect(() => { void loadCatalogs(); }, []);

  useEffect(() => {
    if (!selectedMatiere || !selectedSession) {
      setStudents([]);
      setRows([]);
      return;
    }
    const loadRows = async () => {
      setRowsLoading(true);
      const [studentsResult, notesResult] = await Promise.all([
        pedagogieApi.getAssignedStudents(selectedMatiere, selectedSession),
        pedagogieApi.getNotes({ matiere_id: selectedMatiere, session_id: selectedSession }),
      ]);
      if (studentsResult.error || notesResult.error) {
        toast.error(extractErrorMessage(studentsResult.error || notesResult.error));
        setStudents([]);
        setRows([]);
        setRowsLoading(false);
        return;
      }

      const sessionStudents = (studentsResult.data || []) as StudentOption[];
      const noteMap = new Map<string, NoteApi>(
        (notesResult.data || []).map((note) => [note.etudiant_id, note])
      );
      setStudents(sessionStudents);
      setRows(sessionStudents.map((student) => {
        const note = noteMap.get(student.id);
        return {
          id: note?.id,
          etudiant_id: student.id,
          valeur: note ? String(note.valeur) : "",
          coefficient: note ? String(note.coefficient ?? 1) : "1",
          saved: Boolean(note),
        };
      }));
      setRowsLoading(false);
    };
    void loadRows();
  }, [selectedMatiere, selectedSession, catalogVersion]);

  const average = useMemo(() => {
    const valid = rows.map((row) => ({ value: Number(row.valeur), coefficient: Number(row.coefficient) })).filter((row) => Number.isFinite(row.value) && row.value >= 0 && row.value <= 20 && row.coefficient > 0);
    const total = valid.reduce((sum, row) => sum + row.value * row.coefficient, 0);
    const coefficient = valid.reduce((sum, row) => sum + row.coefficient, 0);
    return coefficient ? (total / coefficient).toFixed(2) : "—";
  }, [rows]);

  const updateRow = (id: string, field: "valeur" | "coefficient", value: string) => {
    setRows((current) => current.map((row) => row.etudiant_id === id ? { ...row, [field]: value, saved: false } : row));
  };

  const saveNotes = async (event: FormEvent) => {
    event.preventDefault();
    if (!selectedMatiere || !selectedSession) return;
    const invalid = rows.find((row) => row.valeur !== "" && (Number(row.valeur) < 0 || Number(row.valeur) > 20));
    if (invalid) { toast.error("Les notes doivent être comprises entre 0 et 20."); return; }
    setSaving(true);
    for (const row of rows) {
      if (row.valeur === "") continue;
      const payload = {
        etudiant_id: row.etudiant_id,
        matiere_id: selectedMatiere,
        session_id: selectedSession,
        valeur: Number(row.valeur),
        coefficient: Number(row.coefficient) || 1,
      };
      const result = row.id
        ? await pedagogieApi.updateNote(row.id, payload)
        : await pedagogieApi.saveNote(payload);
      if (result.error) {
        setSaving(false);
        toast.error(extractErrorMessage(result.error, "Une note n'a pas pu être enregistrée."));
        return;
      }
      if (!row.id && result.data?.id) {
        setRows((current) => current.map((item) => item.etudiant_id === row.etudiant_id ? { ...item, id: result.data.id } : item));
      }
    }
    setSaving(false);
    toast.success("Notes enregistrées dans le backend.");
    setRows((current) => current.map((row) => row.valeur === "" ? row : { ...row, saved: true }));
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div><h1 className="text-3xl font-bold text-foreground">Carnet de notes</h1><p className="mt-1 text-muted-foreground">Saisie des notes via l'API, sans lignes de démonstration.</p></div>
        <Button variant="outline" onClick={loadCatalogs} disabled={loading}><RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />Actualiser</Button>
      </div>

      {error && <Alert variant="destructive"><AlertCircle className="h-4 w-4" /><AlertTitle>Erreur backend</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}

      <Card>
        <CardHeader><CardTitle>Sélection de l'évaluation</CardTitle><CardDescription>Une matière et une session sont nécessaires pour charger les étudiants.</CardDescription></CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2"><Label>Matière *</Label><Select value={selectedMatiere} onValueChange={setSelectedMatiere}><SelectTrigger><SelectValue placeholder="Sélectionner une matière" /></SelectTrigger><SelectContent>{matieres.map((matiere) => <SelectItem key={matiere.id} value={matiere.id}>{matiere.code} — {matiere.nom}</SelectItem>)}</SelectContent></Select></div>
            <div className="space-y-2"><Label>Session *</Label><Select value={selectedSession} onValueChange={setSelectedSession}><SelectTrigger><SelectValue placeholder="Sélectionner une session" /></SelectTrigger><SelectContent>{sessions.map((session) => <SelectItem key={session.id} value={session.id}>{session.nom} ({session.annee_academique})</SelectItem>)}</SelectContent></Select></div>
          </div>
        </CardContent>
      </Card>

      {selectedMatiere && selectedSession && <Card>
        <CardHeader><div className="flex items-center justify-between gap-3"><div><CardTitle>Notes des étudiants</CardTitle><CardDescription>{rows.length} étudiant(s) rattaché(s) à la session</CardDescription></div><Badge>Moyenne : {average}/20</Badge></div></CardHeader>
        <CardContent className="p-0">
          <form onSubmit={saveNotes}>
            <div className="overflow-x-auto border-t">
              <Table><TableHeader><TableRow className="bg-muted/50"><TableHead>Matricule</TableHead><TableHead>Étudiant</TableHead><TableHead>Note / 20</TableHead><TableHead>Coefficient</TableHead><TableHead>Statut</TableHead></TableRow></TableHeader>
                <TableBody>{rowsLoading ? <TableRow><TableCell colSpan={5} className="py-10 text-center"><Loader2 className="mx-auto h-5 w-5 animate-spin" /></TableCell></TableRow> : rows.length === 0 ? <TableRow><TableCell colSpan={5} className="py-10 text-center text-muted-foreground">Aucun étudiant rattaché à cette session.</TableCell></TableRow> : rows.map((row) => { const student = students.find((item) => item.id === row.etudiant_id); return <TableRow key={row.etudiant_id}>
                  <TableCell className="font-mono text-xs">{student?.matricule}</TableCell><TableCell className="font-medium">{student?.prenom} {student?.nom}</TableCell>
                  <TableCell><Input aria-label={`Note de ${student?.matricule}`} type="number" min="0" max="20" step="0.25" value={row.valeur} onChange={(event) => updateRow(row.etudiant_id, "valeur", event.target.value)} className="w-28" /></TableCell>
                  <TableCell><Input aria-label={`Coefficient de ${student?.matricule}`} type="number" min="0.1" step="0.5" value={row.coefficient} onChange={(event) => updateRow(row.etudiant_id, "coefficient", event.target.value)} className="w-24" /></TableCell>
                  <TableCell>{row.saved ? <Badge className="bg-emerald-600 text-white">Enregistrée</Badge> : <Badge variant="outline">À enregistrer</Badge>}</TableCell>
                </TableRow>; })}</TableBody>
              </Table>
            </div>
            <div className="flex justify-end border-t p-4"><Button type="submit" disabled={saving || rows.length === 0}>{saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}Enregistrer les notes</Button></div>
          </form>
        </CardContent>
      </Card>}

      {!selectedMatiere || !selectedSession ? <Card><CardContent className="py-12 text-center text-sm text-muted-foreground"><CheckCircle2 className="mx-auto mb-2 h-8 w-8 text-muted-foreground/50" />Sélectionnez une matière et une session pour commencer.</CardContent></Card> : null}
    </div>
  );
};

export default Notes;
