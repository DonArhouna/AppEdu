import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { MapPin, Building, Users, Plus, Edit, Trash2, Eye, RefreshCw, AlertCircle } from "lucide-react";
import { CampusDialog, type Campus } from "@/components/campus/CampusDialog";
import { toast } from "sonner";
import { structureApi } from "@/services/apiClient";

const Campus = () => {
  const [campusList, setCampusList] = useState<Campus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedCampus, setSelectedCampus] = useState<Campus>();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [campusToDelete, setCampusToDelete] = useState<string | null>(null);

  const loadCampuses = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await structureApi.getCampuses();
      if (res.error) {
        setError(res.error);
        setCampusList([]);
      } else {
        setCampusList((res.data || []) as Campus[]);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erreur de connexion au serveur backend.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCampuses();
  }, []);

  const handleSave = async (campusData: Campus) => {
    const payload = {
      nom: campusData.nom,
      code: campusData.code,
      description: campusData.description || "",
      responsable: campusData.responsable || "",
      ville: campusData.ville || "",
      adresse: campusData.adresse || "",
      telephone: campusData.telephone || "",
      email: campusData.email || "",
    };

    if (selectedCampus?.id) {
      const res = await structureApi.updateCampus(selectedCampus.id, payload);
      if (res.error) {
        toast.error(`Erreur : ${res.error}`);
        return;
      }
      toast.success("Campus modifié avec succès.");
    } else {
      const res = await structureApi.createCampus(payload);
      if (res.error) {
        toast.error(`Erreur : ${res.error}`);
        return;
      }
      toast.success("Nouveau campus créé avec succès.");
    }

    setDialogOpen(false);
    setSelectedCampus(undefined);
    await loadCampuses();
  };

  const handleEdit = (campus: Campus) => {
    setSelectedCampus(campus);
    setDialogOpen(true);
  };

  const handleDelete = async (id: string) => {
    const res = await structureApi.deleteCampus(id);
    if (res.error) {
      toast.error(`Erreur : ${res.error}`);
    } else {
      toast.success("Campus supprimé avec succès.");
      await loadCampuses();
    }
    setDeleteDialogOpen(false);
    setCampusToDelete(null);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Campus & Sites</h1>
          <p className="text-muted-foreground mt-1">
            Gérez les campus universitaires et leurs infrastructures réelles
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={loadCampuses} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-1.5 ${loading ? "animate-spin" : ""}`} />
            Actualiser
          </Button>
          <Button
            onClick={() => {
              setSelectedCampus(undefined);
              setDialogOpen(true);
            }}
          >
            <Plus className="h-4 w-4 mr-2" />
            Nouveau Campus
          </Button>
        </div>
      </div>

      {error && (
        <Card className="border-destructive/40 bg-destructive/5 p-4 rounded-xl">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-destructive shrink-0" />
            <div className="flex-1 text-sm text-destructive">
              <strong>Erreur backend :</strong> {error}
            </div>
            <Button variant="outline" size="sm" onClick={loadCampuses} className="border-destructive/30">
              Réessayer
            </Button>
          </div>
        </Card>
      )}

      {loading ? (
        <div className="p-16 text-center space-y-3">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto text-primary" />
          <p className="text-sm text-muted-foreground">Chargement des campus...</p>
        </div>
      ) : campusList.length === 0 ? (
        <div className="p-12 text-center text-sm text-muted-foreground space-y-3 border rounded-2xl bg-card">
          <Building className="h-10 w-10 mx-auto text-muted-foreground/40" />
          <p className="font-semibold text-foreground text-base">Aucun campus enregistré</p>
          <p className="text-xs max-w-sm mx-auto">
            Votre établissement n'a pas encore de campus configuré. Cliquez sur le bouton ci-dessous pour ajouter votre premier site.
          </p>
          <Button
            onClick={() => {
              setSelectedCampus(undefined);
              setDialogOpen(true);
            }}
            className="mt-2"
          >
            <Plus className="h-4 w-4 mr-1.5" /> Créer un Campus
          </Button>
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {campusList.map((campus) => (
            <Card key={campus.id} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-start gap-4">
                  <div className="rounded-lg bg-primary/10 text-primary p-3">
                    <MapPin className="h-6 w-6" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg">{campus.nom}</CardTitle>
                      <Badge variant="outline" className="font-mono text-[10px]">
                        {campus.code}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {campus.description || "Aucune description fournie"}
                    </p>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="text-xs space-y-1 text-muted-foreground">
                  <div>Ville : <span className="font-medium text-foreground">{campus.ville || "Non renseignée"}</span></div>
                  <div>Responsable : <span className="font-medium text-foreground">{campus.responsable || "Non assigné"}</span></div>
                  <div>Départements rattachés : <span className="font-semibold text-primary">{campus.departements?.length || 0}</span></div>
                </div>

                <div className="pt-2 flex gap-2">
                  <Link to={`/campus/${campus.id}`} className="flex-1">
                    <Button variant="outline" size="sm" className="w-full text-xs">
                      <Eye className="h-3.5 w-3.5 mr-1.5" />
                      Voir
                    </Button>
                  </Link>
                  <Button variant="outline" size="sm" className="flex-1 text-xs" onClick={() => handleEdit(campus)}>
                    <Edit className="h-3.5 w-3.5 mr-1.5" />
                    Modifier
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-destructive hover:text-destructive"
                    onClick={() => {
                      setCampusToDelete(campus.id);
                      setDeleteDialogOpen(true);
                    }}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <CampusDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        campus={selectedCampus}
        onSave={handleSave}
      />

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmer la suppression</AlertDialogTitle>
            <AlertDialogDescription>
              Êtes-vous sûr de vouloir supprimer ce campus ? Cette action supprimera également les départements et filières associés.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction onClick={() => campusToDelete && handleDelete(campusToDelete)} className="bg-destructive text-destructive-foreground">
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default Campus;
