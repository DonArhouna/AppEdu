import { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { ArrowLeft, BookOpen, Users, Building2, AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { structureApi } from "@/services/apiClient";

export default function DepartementDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [dept, setDept] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDept() {
      if (!id) return;
      setLoading(true);
      setError(null);
      try {
        const res = await structureApi.getDepartements();
        if (res.error) {
          setError(res.error);
        } else {
          const found = (res.data || []).find((d: any) => d.id === id);
          if (found) {
            setDept(found);
          } else {
            setError("Département non trouvé dans la base de données.");
          }
        }
      } catch (err: any) {
        setError(err?.message || "Erreur de connexion.");
      } finally {
        setLoading(false);
      }
    }
    loadDept();
  }, [id]);

  if (loading) {
    return (
      <div className="p-16 text-center space-y-3">
        <RefreshCw className="h-8 w-8 animate-spin mx-auto text-primary" />
        <p className="text-sm text-muted-foreground">Chargement du département...</p>
      </div>
    );
  }

  if (error || !dept) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" size="sm" onClick={() => navigate("/departements")}>
          <ArrowLeft className="h-4 w-4 mr-2" /> Retour aux départements
        </Button>
        <Card className="border-destructive/40 bg-destructive/5 p-6 rounded-xl text-center space-y-3">
          <AlertCircle className="h-8 w-8 text-destructive mx-auto" />
          <p className="font-semibold text-destructive">{error || "Département introuvable"}</p>
          <Button size="sm" onClick={() => navigate("/departements")} variant="outline">
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
          <Link to="/departements">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-3xl font-bold text-foreground">{dept.nom}</h1>
              <Badge variant="outline" className="font-mono text-xs">{dept.code}</Badge>
            </div>
            <p className="text-muted-foreground text-sm">Détails du département académique</p>
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Filières Rattachées</CardTitle>
            <BookOpen className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dept.filieres?.length || 0}</div>
            <p className="text-xs text-muted-foreground">Parcours de formation proposés</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Responsable / Direction</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold">{dept.responsable || "Non assigné"}</div>
            <p className="text-xs text-muted-foreground">Chef de département</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filières et Spécialités</CardTitle>
        </CardHeader>
        <CardContent>
          {!dept.filieres || dept.filieres.length === 0 ? (
            <p className="text-xs text-muted-foreground">Aucune filière n'est encore assignée à ce département.</p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {dept.filieres.map((f: any) => (
                <div key={f.id} className="p-3 border rounded-xl flex items-center justify-between text-xs">
                  <div>
                    <p className="font-semibold text-foreground">{f.nom}</p>
                    <p className="text-muted-foreground">{f.diplome || "Licence"} • {f.code}</p>
                  </div>
                  <Link to={`/filieres`}>
                    <Button variant="ghost" size="sm" className="text-xs">
                      Voir
                    </Button>
                  </Link>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
