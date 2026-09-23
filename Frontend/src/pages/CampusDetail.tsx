import { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Users, MapPin, Building2, Edit, AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { structureApi } from "@/services/apiClient";

export default function CampusDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [campus, setCampus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadCampus() {
      if (!id) return;
      setLoading(true);
      setError(null);
      try {
        const res = await structureApi.getCampuses();
        if (res.error) {
          setError(res.error);
        } else {
          const found = (res.data || []).find((c: any) => c.id === id);
          if (found) {
            setCampus(found);
          } else {
            setError("Campus non trouvé dans la base de données.");
          }
        }
      } catch (err: any) {
        setError(err?.message || "Erreur de connexion.");
      } finally {
        setLoading(false);
      }
    }
    loadCampus();
  }, [id]);

  if (loading) {
    return (
      <div className="p-16 text-center space-y-3">
        <RefreshCw className="h-8 w-8 animate-spin mx-auto text-primary" />
        <p className="text-sm text-muted-foreground">Chargement des détails du campus...</p>
      </div>
    );
  }

  if (error || !campus) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" size="sm" onClick={() => navigate("/campus")}>
          <ArrowLeft className="h-4 w-4 mr-2" /> Retour aux campus
        </Button>
        <Card className="border-destructive/40 bg-destructive/5 p-6 rounded-xl text-center space-y-3">
          <AlertCircle className="h-8 w-8 text-destructive mx-auto" />
          <p className="font-semibold text-destructive">{error || "Campus introuvable"}</p>
          <Button size="sm" onClick={() => navigate("/campus")} variant="outline">
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
          <Link to="/campus">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-3xl font-bold text-foreground">{campus.nom}</h1>
              <Badge variant="outline" className="font-mono text-xs">{campus.code}</Badge>
            </div>
            <p className="text-muted-foreground text-sm">Détails de l'infrastructure campus</p>
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Ville / Implantation</CardTitle>
            <MapPin className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">{campus.ville || "Abidjan"}</div>
            <p className="text-xs text-muted-foreground">{campus.adresse || "Adresse non renseignée"}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Départements Rattachés</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{campus.departements?.length || 0}</div>
            <p className="text-xs text-muted-foreground">Unités pédagogiques actives</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Direction</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold">{campus.responsable || "Non assigné"}</div>
            <p className="text-xs text-muted-foreground">Directeur / Responsable du site</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Informations Générales & Contact</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div>
            <h3 className="font-semibold text-xs text-muted-foreground uppercase">Description</h3>
            <p className="text-foreground mt-1">{campus.description || "Aucune description détaillée enregistrée."}</p>
          </div>
          <div>
            <h3 className="font-semibold text-xs text-muted-foreground uppercase">Contact Technique / Secrétariat</h3>
            <p className="text-foreground mt-1">{campus.email || "Non renseigné"} • {campus.telephone || "Non renseigné"}</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
