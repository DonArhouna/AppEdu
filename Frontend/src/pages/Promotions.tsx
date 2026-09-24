import { useEffect, useState } from "react";
import { AlertCircle, GraduationCap, Loader2, RefreshCw } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { etudiantsApi, extractErrorMessage, sessionsApi } from "@/services/apiClient";
import type { AcademicSession, Student } from "@/services/apiTypes";

const Promotions = () => {
  const [sessions, setSessions] = useState<AcademicSession[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    const [sessionsResult, studentsResult] = await Promise.all([
      sessionsApi.getAll(),
      etudiantsApi.getAll(),
    ]);
    const firstError = sessionsResult.error || studentsResult.error;
    if (firstError || !sessionsResult.data || !studentsResult.data) {
      setError(extractErrorMessage(firstError, "Les promotions n'ont pas pu être chargées."));
      setSessions([]);
      setStudents([]);
    } else {
      setSessions(sessionsResult.data);
      setStudents(studentsResult.data);
    }
    setLoading(false);
  };

  useEffect(() => {
    void load();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Promotions & cohortes</h1>
          <p className="mt-1 text-muted-foreground">Les cohortes sont dérivées des sessions et des rattachements étudiants.</p>
        </div>
        <Button variant="outline" onClick={load} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Actualiser
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Erreur de chargement</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <GraduationCap className="h-5 w-5 text-primary" />
            Sessions / promotions
          </CardTitle>
          <CardDescription>Aucune promotion fictive n'est affichée.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Session</TableHead>
                <TableHead>Code</TableHead>
                <TableHead>Effectif</TableHead>
                <TableHead>Statut</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={4} className="py-10 text-center">
                    <Loader2 className="mx-auto h-5 w-5 animate-spin text-primary" />
                  </TableCell>
                </TableRow>
              ) : sessions.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="py-10 text-center text-muted-foreground">
                    Aucune session enregistrée.
                  </TableCell>
                </TableRow>
              ) : (
                sessions.map((session) => (
                  <TableRow key={session.id}>
                    <TableCell>{session.nom}</TableCell>
                    <TableCell className="font-mono text-xs">{session.code}</TableCell>
                    <TableCell>{students.filter((student) => student.session_id === session.id).length}</TableCell>
                    <TableCell>{session.statut}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
};

export default Promotions;
