import { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { ArrowLeft, BookOpen, GraduationCap, AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { structureApi } from "@/services/apiClient";
import type { Filiere } from "@/services/apiTypes";

export default function FiliereDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [filiere, setFiliere] = useState<Filiere | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadFiliere() {
      if (!id) return;
      setLoading(true);
      setError(null);
      try {
        const res = await structureApi.getFilieres();
        if (res.error) {
          setError(res.error);
        } else {
          const found = (res.data || []).find((f) => f.id === id);
          if (found) {
            setFiliere(found);
          } else {
            setError("Filière non trouvée dans la base de données.");
          }
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Erreur de connexion.");
      } finally {
        setLoading(false);
      }
    }
    loadFiliere();
  }, [id]);

  if (loading) {
    return (
      <div className="p-16 text-center space-y-3">
        <RefreshCw className="h-8 w-8 animate-spin mx-auto text-primary" />
        <p className="text-sm text-muted-foreground">Chargement de la filière...</p>
      </div>
    );
  }

  if (error || !filiere) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" size="sm" onClick={() => navigate("/filieres")}>
          <ArrowLeft className="h-4 w-4 mr-2" /> Retour aux filières
        </Button>
        <Card className="border-destructive/40 bg-destructive/5 p-6 rounded-xl text-center space-y-3">
          <AlertCircle className="h-8 w-8 text-destructive mx-auto" />
          <p className="font-semibold text-destructive">{error || "Filière introuvable"}</p>
          <Button size="sm" onClick={() => navigate("/filieres")} variant="outline">
            Retour à la liste
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link to="/filieres">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-3xl font-bold text-foreground">{filiere.nom}</h1>
              <Badge variant="outline" className="font-mono text-xs">{filiere.code}</Badge>
            </div>
            <p className="text-muted-foreground text-sm">Cursus académique accrédité</p>
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Diplôme Visé</CardTitle>
            <GraduationCap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{filiere.diplome || "Non renseigné"}</div>
            <p className="text-xs text-muted-foreground">Diplôme ciblé</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Durée du Cursus</CardTitle>
            <BookOpen className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{filiere.duree || 3} ans</div>
            <p className="text-xs text-muted-foreground">Standard ECTS</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Unités d'Enseignement</CardTitle>
            <BookOpen className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{filiere.unites_enseignement?.length || 0}</div>
            <p className="text-xs text-muted-foreground">UEs répertoriées</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Description de la Filière</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          <p className="text-foreground leading-relaxed">
            {filiere.description || "Aucune description détaillée enregistrée pour cette filière."}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
