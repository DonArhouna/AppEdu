import { useEffect, useState } from "react";
import { AlertCircle, CalendarDays, Loader2, RefreshCw, Save } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import InstitutionConfigCard from "@/components/institution/InstitutionConfigCard";
import { useRBAC } from "@/contexts/RBACContext";
import {
  academicContextApi,
  extractErrorMessage,
  PERMISSION_INSTITUTION_SETTINGS,
  sessionsApi,
  setupApi,
} from "@/services/apiClient";
import type { AcademicContext } from "@/services/apiTypes";
import { toast } from "sonner";

interface SessionRow {
  id: string;
  nom: string;
  code: string;
  annee_academique: string;
  date_debut: string;
  date_fin: string;
  statut: string;
}

const Parametrage = () => {
  // La lecture de l'identite est ouverte a tout le personnel ; seule son
  // modification exige la permission dediee. C'est le meme partage que cote
  // API : `academic.read` pour lire, `institution.settings` pour ecrire.
  const { hasPermission } = useRBAC();
  const canEditInstitution = hasPermission(PERMISSION_INSTITUTION_SETTINGS);
  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [academicContext, setAcademicContext] = useState<AcademicContext | null>(null);
  const [contextSessionId, setContextSessionId] = useState("");
  const [savingContext, setSavingContext] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    const [statusResult, sessionsResult, contextResult] = await Promise.all([
      setupApi.getStatus(),
      sessionsApi.getAll(),
      academicContextApi.get(),
    ]);
    if (statusResult.error || sessionsResult.error) {
      setError(extractErrorMessage(statusResult.error || sessionsResult.error));
    } else {
      setSessions((sessionsResult.data || []) as SessionRow[]);
    }
    if (contextResult.data) {
      setAcademicContext(contextResult.data);
      setContextSessionId(contextResult.data.session_id || "");
    } else {
      setAcademicContext(null);
    }
    setLoading(false);
  };

  useEffect(() => {
    void loadData();
  }, []);

  const saveAcademicContext = async () => {
    const selectedSession = sessions.find((session) => session.id === contextSessionId);
    if (!selectedSession) {
      toast.error("Sélectionnez une session à activer.");
      return;
    }
    setSavingContext(true);
    const result = await academicContextApi.update({
      annee_academique: selectedSession.annee_academique,
      session_id: selectedSession.id,
    });
    setSavingContext(false);
    if (result.error || !result.data) {
      toast.error(extractErrorMessage(result.error, "Le contexte académique n'a pas pu être enregistré."));
      return;
    }
    setAcademicContext(result.data);
    setContextSessionId(result.data.session_id || "");
    toast.success("Contexte académique global enregistré.");
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Paramétrage Général</h1>
          <p className="mt-1 text-muted-foreground">Les paramètres affichés proviennent de l'API EduManagePro.</p>
        </div>
        <Button variant="outline" onClick={loadData} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Actualiser
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Erreur de chargement</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <InstitutionConfigCard
        canEdit={canEditInstitution}
        onSaved={() => void loadData()}
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><CalendarDays className="h-4 w-4" /> Contexte académique global</CardTitle>
          <CardDescription>
            L'année et la session affichées dans l'application proviennent de ce contexte persistant.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4 sm:flex-row sm:items-end">
          <div className="flex-1 space-y-2">
            <Label htmlFor="context-session">Session active</Label>
            <Select value={contextSessionId || "aucune"} onValueChange={(value) => setContextSessionId(value === "aucune" ? "" : value)}>
              <SelectTrigger id="context-session">
                <SelectValue placeholder="Sélectionner une session" />
              </SelectTrigger>
              <SelectContent>
                {sessions.length === 0 && <SelectItem value="aucune">Aucune session disponible</SelectItem>}
                {sessions.map((session) => (
                  <SelectItem key={session.id} value={session.id}>
                    {session.code} · {session.annee_academique} · {session.statut}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              {academicContext?.configuree
                ? `Contexte enregistré : ${academicContext.annee_academique}.`
                : "Aucune configuration explicite ; une session active existante peut être affichée comme valeur dérivée."}
            </p>
          </div>
          <Button onClick={() => void saveAcademicContext()} disabled={savingContext || sessions.length === 0}>
            {savingContext ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Activer ce contexte
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><CalendarDays className="h-4 w-4" /> Sessions académiques</CardTitle>
          <CardDescription>Les années, périodes de paiement et créneaux sont gérés dans le module Sessions.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto border-t">
            {loading ? (
              <div className="flex items-center justify-center gap-2 p-12 text-sm text-muted-foreground"><Loader2 className="h-5 w-5 animate-spin" /> Chargement...</div>
            ) : sessions.length === 0 ? (
              <div className="p-12 text-center text-sm text-muted-foreground">Aucune session enregistrée.</div>
            ) : (
              <Table>
                <TableHeader><TableRow className="bg-muted/40"><TableHead>Session</TableHead><TableHead>Code</TableHead><TableHead>Année</TableHead><TableHead>Début</TableHead><TableHead>Fin</TableHead><TableHead>Statut</TableHead></TableRow></TableHeader>
                <TableBody>
                  {sessions.map((session) => (
                    <TableRow key={session.id}>
                      <TableCell className="font-medium">{session.nom}</TableCell>
                      <TableCell className="font-mono text-xs">{session.code}</TableCell>
                      <TableCell>{session.annee_academique}</TableCell>
                      <TableCell>{session.date_debut}</TableCell>
                      <TableCell>{session.date_fin}</TableCell>
                      <TableCell><Badge variant={session.statut === "active" ? "default" : "secondary"}>{session.statut}</Badge></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </CardContent>
      </Card>

      <Alert>
        <AlertTitle>Configuration non encore exposée par l'API</AlertTitle>
        <AlertDescription>
          Les semestres, sessions d'examen, seuils de notation et la nomenclature de matricule ne sont pas simulés ici. Ils seront ajoutés avec leurs endpoints et migrations backend.
        </AlertDescription>
      </Alert>
    </div>
  );
};

export default Parametrage;
