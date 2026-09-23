import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { ArrowLeft, BookOpen, Clock, Users, GraduationCap, AlertCircle, RefreshCw } from "lucide-react";
import { structureApi, extractErrorMessage } from "@/services/apiClient";

const UEDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [ue, setUe] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUE = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await structureApi.getUEById(id);
      setUe(data);
    } catch (err: any) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUE();
  }, [id]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10 rounded" />
          <div className="space-y-2">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-32" />
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-64 rounded-xl" />
      </div>
    );
  }

  if (error || !ue) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" size="icon" onClick={() => navigate("/ue")}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Erreur lors du chargement de l'UE</AlertTitle>
          <AlertDescription className="mt-2 flex flex-col gap-4">
            <p>{error || "Unité d'enseignement introuvable ou inaccessible."}</p>
            <Button variant="outline" className="w-fit" onClick={fetchUE}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Réessayer
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const matieres = Array.isArray(ue.matieres) ? ue.matieres : [];
  const heuresCM = matieres.reduce((acc: number, m: any) => acc + (Number(m.heures_cm) || 0), 0);
  const heuresTD = matieres.reduce((acc: number, m: any) => acc + (Number(m.heures_td) || 0), 0);
  const heuresTP = matieres.reduce((acc: number, m: any) => acc + (Number(m.heures_tp) || 0), 0);
  const heuresTotal = Number(ue.heures) || (heuresCM + heuresTD + heuresTP) || 45;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate("/ue")}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-foreground">{ue.nom}</h1>
              <Badge variant="outline">{ue.code}</Badge>
            </div>
            <p className="text-muted-foreground">
              {ue.niveau || "Licence"} - {ue.semestre || "S1"}
            </p>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="border-border bg-card">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Crédits ECTS</CardTitle>
            <GraduationCap className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">{ue.credits ?? 6} ECTS</div>
            <p className="text-xs text-muted-foreground mt-1">Coefficient: {ue.coefficient ?? 3}</p>
          </CardContent>
        </Card>

        <Card className="border-border bg-card">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Volume Horaire</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">{heuresTotal}h</div>
            <p className="text-xs text-muted-foreground mt-1">CM, TD & TP inclus</p>
          </CardContent>
        </Card>

        <Card className="border-border bg-card">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Matières (ECUE)</CardTitle>
            <BookOpen className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">{matieres.length}</div>
            <p className="text-xs text-muted-foreground mt-1">Éléments constitutifs</p>
          </CardContent>
        </Card>

        <Card className="border-border bg-card">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Responsable UE</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold text-foreground truncate">{ue.responsable || "Non assigné"}</div>
            <p className="text-xs text-muted-foreground mt-1">Coordonnateur pédagogique</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="matieres" className="space-y-4">
        <TabsList className="bg-muted">
          <TabsTrigger value="matieres">Matières (ECUE) ({matieres.length})</TabsTrigger>
          <TabsTrigger value="repartition">Répartition Horaire</TabsTrigger>
        </TabsList>

        <TabsContent value="matieres" className="space-y-4">
          <Card className="border-border bg-card">
            <CardHeader>
              <CardTitle>Matières composant l'Unité d'Enseignement</CardTitle>
            </CardHeader>
            <CardContent>
              {matieres.length === 0 ? (
                <p className="text-muted-foreground text-center py-6">
                  Aucune matière (ECUE) n'est rattachée à cette Unité d'Enseignement.
                </p>
              ) : (
                <div className="space-y-3">
                  {matieres.map((matiere: any) => (
                    <div
                      key={matiere.id}
                      className="flex items-center justify-between rounded-lg border border-border p-4 bg-background hover:bg-muted/30 transition-colors"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="font-semibold text-foreground">{matiere.nom}</p>
                          <Badge variant="outline" className="text-xs font-mono">
                            {matiere.code}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                          Crédits: {matiere.credits || 3} | Coefficient: {matiere.coefficient || 1.5} | 
                          CM: {matiere.heures_cm || 0}h, TD: {matiere.heures_td || 0}h, TP: {matiere.heures_tp || 0}h
                        </p>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => navigate(`/matieres/${matiere.id}`)}
                      >
                        Voir détails
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="repartition" className="space-y-4">
          <Card className="border-border bg-card">
            <CardHeader>
              <CardTitle>Répartition des heures d'enseignement</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between rounded-lg border border-border p-4 bg-background">
                  <div>
                    <p className="font-medium text-foreground">Cours Magistraux (CM)</p>
                    <p className="text-xs text-muted-foreground">Cours théoriques en amphithéâtre ou salle de cours</p>
                  </div>
                  <span className="text-lg font-bold text-foreground">{heuresCM}h</span>
                </div>
                <div className="flex items-center justify-between rounded-lg border border-border p-4 bg-background">
                  <div>
                    <p className="font-medium text-foreground">Travaux Dirigés (TD)</p>
                    <p className="text-xs text-muted-foreground">Exercices dirigés en petits groupes</p>
                  </div>
                  <span className="text-lg font-bold text-foreground">{heuresTD}h</span>
                </div>
                <div className="flex items-center justify-between rounded-lg border border-border p-4 bg-background">
                  <div>
                    <p className="font-medium text-foreground">Travaux Pratiques (TP)</p>
                    <p className="text-xs text-muted-foreground">Séances d'application pratique en laboratoire informatique</p>
                  </div>
                  <span className="text-lg font-bold text-foreground">{heuresTP}h</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default UEDetail;
