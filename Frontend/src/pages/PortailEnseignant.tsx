import { useCallback, useEffect, useState } from "react";
import { AlertCircle, CalendarDays, FileText, Loader2, RefreshCw, User } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAuth } from "@/contexts/AuthContext";
import { portalsApi } from "@/services/apiClient";
import type { Course, Matiere, Note, TeacherPortalData } from "@/services/apiTypes";

const PortailEnseignant = () => {
  const { user } = useAuth();
  const [data, setData] = useState<TeacherPortalData>({ cours: [], matieres: [], notes: [], etudiants: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    const result = await portalsApi.getTeacherPortal();
    if (result.error || !result.data) {
      setError(result.error || "Le portail enseignant est indisponible.");
      setData({ cours: [], matieres: [], notes: [], etudiants: [] });
    } else {
      setData(result.data);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const matiereName = (id: string) => {
    const item: Matiere | undefined = data.matieres.find((matiere) => matiere.id === id);
    return item?.nom || "Matière";
  };

  const studentLabel = (id: string) => {
    const student = data.etudiants.find((item) => item.id === id);
    return student ? `${student.matricule} — ${student.prenom} ${student.nom}` : "Dossier étudiant";
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <User className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-foreground">Portail enseignant</h1>
            <p className="text-sm text-muted-foreground">
              {user ? `${user.prenom} ${user.nom}` : "Compte enseignant"}
            </p>
          </div>
        </div>
        <Button variant="outline" onClick={loadData} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Actualiser
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Portail indisponible</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {loading ? (
        <div className="flex items-center justify-center gap-2 p-16 text-sm text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin" /> Chargement...
        </div>
      ) : (
        <Tabs defaultValue="cours" className="space-y-4">
          <TabsList>
            <TabsTrigger value="cours">
              <CalendarDays className="mr-2 h-4 w-4" />Mes cours
            </TabsTrigger>
            <TabsTrigger value="notes">
              <FileText className="mr-2 h-4 w-4" />Notes
            </TabsTrigger>
          </TabsList>

          <TabsContent value="cours">
            <Card>
              <CardHeader>
                <CardTitle>Cours enregistrés</CardTitle>
                <CardDescription>Seuls les cours explicitement affectés à votre compte sont affichés.</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Matière</TableHead>
                      <TableHead>Jour</TableHead>
                      <TableHead>Horaire</TableHead>
                      <TableHead>Salle</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.cours.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={4} className="py-8 text-center text-muted-foreground">
                          Aucun cours affecté à votre compte.
                        </TableCell>
                      </TableRow>
                    ) : (
                      data.cours.map((item: Course) => (
                        <TableRow key={item.id}>
                          <TableCell>{matiereName(item.matiere_id)}</TableCell>
                          <TableCell>{item.jour_semaine}</TableCell>
                          <TableCell>{item.heure_debut}–{item.heure_fin}</TableCell>
                          <TableCell>{item.salle}</TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="notes">
            <Card>
              <CardHeader>
                <CardTitle>Notes des matières affectées</CardTitle>
                <CardDescription>Les notes sont filtrées par les matières de vos cours.</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Étudiant</TableHead>
                      <TableHead>Matière</TableHead>
                      <TableHead>Note</TableHead>
                      <TableHead>Statut</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.notes.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={4} className="py-8 text-center text-muted-foreground">
                          Aucune note enregistrée pour vos matières.
                        </TableCell>
                      </TableRow>
                    ) : (
                      data.notes.map((note: Note) => (
                        <TableRow key={note.id}>
                          <TableCell>{studentLabel(note.etudiant_id)}</TableCell>
                          <TableCell>{matiereName(note.matiere_id)}</TableCell>
                          <TableCell className="font-mono font-semibold">{note.valeur}/20</TableCell>
                          <TableCell><Badge variant="outline">{note.statut}</Badge></TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

        </Tabs>
      )}
    </div>
  );
};

export default PortailEnseignant;
