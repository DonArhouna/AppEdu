import { useEffect, useMemo, useState } from "react";
import { AlertCircle, BarChart3, CheckCircle2, DollarSign, GraduationCap, Loader2, RefreshCw, Users } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { KpiCard } from "@/components/ui/kpi-card";
import { Progress } from "@/components/ui/progress";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { etudiantsApi, financesApi, pedagogieApi, sessionsApi, structureApi, setupApi, extractErrorMessage } from "@/services/apiClient";
import type { AcademicSession, Filiere, Invoice, Note, Payment, Student } from "@/services/apiTypes";

const Analytics = () => {
  const [students, setStudents] = useState<Student[]>([]);
  const [filieres, setFilieres] = useState<Filiere[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [factures, setFactures] = useState<Invoice[]>([]);
  const [sessions, setSessions] = useState<AcademicSession[]>([]);
  const [currency, setCurrency] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    const results = await Promise.all([
      etudiantsApi.getSummary(), structureApi.getFilieres(), pedagogieApi.getNotes(),
      financesApi.getPaiements(), financesApi.getFactures(), sessionsApi.getAll(), setupApi.getStatus(),
    ]);
    const firstError = results.find((result) => result.error)?.error;
    if (firstError) {
      setError(extractErrorMessage(firstError));
    }
    setStudents(results[0].data || []);
    setFilieres(results[1].data || []);
    setNotes(results[2].data || []);
    setPayments(results[3].data || []);
    setFactures(results[4].data || []);
    setSessions(results[5].data || []);
    setCurrency(results[6].data?.devise || "");
    setLoading(false);
  };

  useEffect(() => { void load(); }, []);

  const totalPaid = payments.reduce((sum, payment) => sum + Number(payment.montant || 0), 0);
  const totalInvoiced = factures.reduce((sum, facture) => sum + Number(facture.montant_total || 0), 0);
  const recoveryRate = totalInvoiced ? Math.round((totalPaid / totalInvoiced) * 100) : 0;
  const averageNote = notes.length ? notes.reduce((sum, note) => sum + Number(note.valeur || 0), 0) / notes.length : 0;
  const filiereDistribution = useMemo(() => {
    const counts = new Map<string, number>();
    students.forEach((student) => counts.set(student.filiere || "Non renseignée", (counts.get(student.filiere || "Non renseignée") || 0) + 1));
    return Array.from(counts.entries()).map(([name, value]) => ({ name, value }));
  }, [students]);
  const currencyLabel = currency || "devise de l'établissement";

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><div><h1 className="text-3xl font-bold text-foreground">Analytics & Business Intelligence</h1><p className="mt-1 text-muted-foreground">Indicateurs calculés à partir des données actuellement enregistrées dans l'API.</p></div><Button variant="outline" onClick={load} disabled={loading}><RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />Actualiser</Button></div>
      {error && <Alert variant="destructive"><AlertCircle className="h-4 w-4" /><AlertTitle>Erreur backend</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}
      {loading ? <div className="flex items-center justify-center gap-2 p-16 text-sm text-muted-foreground"><Loader2 className="h-5 w-5 animate-spin" />Calcul des indicateurs...</div> : <>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <KpiCard title="Étudiants" value={students.length} icon={Users} subtitle="Dossiers enregistrés" colorVariant="primary" />
          <KpiCard title="Filières" value={filieres.length} icon={GraduationCap} subtitle="Référentiel actuel" colorVariant="emerald" />
          <KpiCard title="Encaissé" value={`${totalPaid.toLocaleString("fr-FR")} ${currencyLabel}`} icon={DollarSign} subtitle={`${payments.length} paiement(s)`} colorVariant="amber" />
          <KpiCard title="Moyenne des notes" value={averageNote ? `${averageNote.toFixed(2)}/20` : "—"} icon={BarChart3} subtitle={`${notes.length} note(s)`} colorVariant="purple" />
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          <Card><CardHeader><CardTitle>Répartition des étudiants par filière</CardTitle><CardDescription>Calculée depuis les dossiers étudiants.</CardDescription></CardHeader><CardContent className="space-y-4">{filiereDistribution.length === 0 ? <p className="text-sm text-muted-foreground">Aucun étudiant enregistré.</p> : filiereDistribution.map((item) => <div key={item.name}><div className="mb-1 flex justify-between text-sm"><span>{item.name}</span><span className="font-mono">{item.value}</span></div><Progress value={students.length ? (item.value / students.length) * 100 : 0} /></div>)}</CardContent></Card>
          <Card><CardHeader><CardTitle>Santé financière</CardTitle><CardDescription>Montants des factures et paiements enregistrés.</CardDescription></CardHeader><CardContent className="space-y-4"><div className="flex justify-between text-sm"><span>Facturé</span><span className="font-mono">{totalInvoiced.toLocaleString("fr-FR")} {currencyLabel}</span></div><div className="flex justify-between text-sm"><span>Encaissé</span><span className="font-mono text-emerald-600">{totalPaid.toLocaleString("fr-FR")} {currencyLabel}</span></div><div className="flex justify-between text-sm"><span>Taux de recouvrement</span><span className="font-mono font-semibold">{recoveryRate}%</span></div><Progress value={Math.min(100, recoveryRate)} /><p className="text-xs text-muted-foreground">Les historiques et prévisions ne sont pas simulés : ils devront provenir d'un module de reporting backend.</p></CardContent></Card>
        </div>
        <Card><CardHeader><CardTitle>Sessions et volumes</CardTitle></CardHeader><CardContent className="p-0"><Table><TableHeader><TableRow><TableHead>Session</TableHead><TableHead>Code</TableHead><TableHead>Statut</TableHead><TableHead>Étudiants rattachés</TableHead></TableRow></TableHeader><TableBody>{sessions.length === 0 ? <TableRow><TableCell colSpan={4} className="py-8 text-center text-muted-foreground">Aucune session.</TableCell></TableRow> : sessions.map((session) => <TableRow key={session.id}><TableCell>{session.nom}</TableCell><TableCell className="font-mono text-xs">{session.code}</TableCell><TableCell><Badge variant={session.statut === "active" ? "default" : "secondary"}>{session.statut}</Badge></TableCell><TableCell>{students.filter((student) => student.session_id === session.id).length}</TableCell></TableRow>)}</TableBody></Table></CardContent></Card>
      </>}
    </div>
  );
};

export default Analytics;
