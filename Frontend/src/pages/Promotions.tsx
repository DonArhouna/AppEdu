import { useEffect, useMemo, useState } from "react";
import { AlertCircle, GraduationCap, Loader2, RefreshCw } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { academicApi, extractErrorMessage, sessionsApi, structureApi } from "@/services/apiClient";
import type { AcademicClass, AcademicSession, Enrollment, Filiere } from "@/services/apiTypes";

interface PromotionRow {
  key: string;
  classe: AcademicClass;
  session: AcademicSession;
  effectif: number;
}

const Promotions = () => {
  const [sessions, setSessions] = useState<AcademicSession[]>([]);
  const [classes, setClasses] = useState<AcademicClass[]>([]);
  const [filieres, setFilieres] = useState<Filiere[]>([]);
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    const [sessionsResult, classesResult, filieresResult, enrollmentsResult] = await Promise.all([
      sessionsApi.getAll(),
      academicApi.getClasses(),
      structureApi.getFilieres(),
      academicApi.listEnrollments(undefined, true),
    ]);
    const firstError =
      sessionsResult.error || classesResult.error || filieresResult.error || enrollmentsResult.error;
    if (firstError) {
      setError(extractErrorMessage(firstError, "Les promotions n'ont pas pu être chargées."));
      setSessions([]);
      setClasses([]);
      setFilieres([]);
      setEnrollments([]);
    } else {
      setSessions(sessionsResult.data || []);
      setClasses(classesResult.data || []);
      setFilieres(filieresResult.data || []);
      setEnrollments(enrollmentsResult.data || []);
    }
    setLoading(false);
  };

  useEffect(() => {
    void load();
  }, []);

  const sessionById = useMemo(() => new Map(sessions.map((item) => [item.id, item])), [sessions]);
  const classById = useMemo(() => new Map(classes.map((item) => [item.id, item])), [classes]);
  const filiereById = useMemo(() => new Map(filieres.map((item) => [item.id, item])), [filieres]);

  const promotions = useMemo(() => {
    const groups = new Map<string, PromotionRow>();
    enrollments
      .filter((item) => item.actif || item.statut === "active")
      .forEach((enrollment) => {
        const session = sessionById.get(enrollment.session_id);
        const academicClass = classById.get(enrollment.classe_id);
        if (!session || !academicClass) return;
        const key = `${session.id}:${academicClass.id}`;
        const current = groups.get(key);
        if (current) {
          current.effectif += 1;
        } else {
          groups.set(key, { key, session, classe: academicClass, effectif: 1 });
        }
      });
    return Array.from(groups.values()).sort(
      (left, right) =>
        right.session.date_debut.localeCompare(left.session.date_debut) ||
        left.classe.code.localeCompare(right.classe.code)
    );
  }, [enrollments, sessionById, classById]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Promotions & cohortes</h1>
          <p className="mt-1 text-muted-foreground">Chaque promotion regroupe les inscriptions actives d'une classe pendant une session.</p>
        </div>
        <Button variant="outline" onClick={load} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />Actualiser
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
            <GraduationCap className="h-5 w-5 text-primary" />Promotions annuelles
          </CardTitle>
          <CardDescription>Les cohortes sont calculées depuis les inscriptions persistées, sans données fictives.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader><TableRow><TableHead>Promotion</TableHead><TableHead>Classe</TableHead><TableHead>Filière</TableHead><TableHead>Session</TableHead><TableHead>Effectif</TableHead><TableHead>Statut</TableHead></TableRow></TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow><TableCell colSpan={6} className="py-10 text-center"><Loader2 className="mx-auto h-5 w-5 animate-spin text-primary" /></TableCell></TableRow>
                ) : promotions.length === 0 ? (
                  <TableRow><TableCell colSpan={6} className="py-10 text-center text-muted-foreground">Aucune inscription active ne définit encore de promotion.</TableCell></TableRow>
                ) : promotions.map((promotion) => (
                  <TableRow key={promotion.key}>
                    <TableCell className="font-medium">{promotion.classe.code} · {promotion.session.code}</TableCell>
                    <TableCell>{promotion.classe.libelle}</TableCell>
                    <TableCell>{filiereById.get(promotion.classe.filiere_id)?.nom || "Non résolue"}</TableCell>
                    <TableCell>{promotion.session.nom}<span className="block text-xs text-muted-foreground">{promotion.session.annee_academique}</span></TableCell>
                    <TableCell className="font-semibold">{promotion.effectif}</TableCell>
                    <TableCell><Badge variant="outline">Active</Badge></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Promotions;
