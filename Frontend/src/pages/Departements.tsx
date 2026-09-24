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
import { Building2, BookOpen, Users, Plus, Edit, Trash2, Eye, RefreshCw, AlertCircle } from "lucide-react";
import { DepartementDialog, type Departement } from "@/components/departements/DepartementDialog";
import { toast } from "sonner";
import { structureApi } from "@/services/apiClient";

const Departements = () => {
  const [departements, setDepartements] = useState<Departement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedDepartement, setSelectedDepartement] = useState<Departement>();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [departementToDelete, setDepartementToDelete] = useState<string | null>(null);

  const loadDepartements = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await structureApi.getDepartements();
      if (res.error) {
        setError(res.error);
        setDepartements([]);
      } else {
        setDepartements(res.data || []);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erreur de connexion au serveur backend.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDepartements();
  }, []);

  const handleSave = async (deptData: Departement) => {
    const payload = {
      nom: deptData.nom,
      code: deptData.code,
      description: deptData.description || "",
      responsable: deptData.responsable || "",
      campus_id: deptData.campus_id || undefined,
    };

    const res = selectedDepartement
      ? await structureApi.updateDepartement(selectedDepartement.id, payload)
      : await structureApi.createDepartement(payload);
    if (res.error) {
      toast.error(`Erreur : ${res.error}`);
      return;
    }
    toast.success(selectedDepartement ? "Département mis à jour." : "Département enregistré.");
    setDialogOpen(false);
    setSelectedDepartement(undefined);
    await loadDepartements();
  };

  const handleEdit = (dept: Departement) => {
    setSelectedDepartement(dept);
    setDialogOpen(true);
  };

  const handleDelete = async () => {
    if (!departementToDelete) return;
    const result = await structureApi.deleteDepartement(departementToDelete);
    if (result.error) {
      toast.error(result.error);
      return;
    }
    toast.success("Département supprimé.");
    setDeleteDialogOpen(false);
    setDepartementToDelete(null);
    await loadDepartements();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Départements</h1>
          <p className="text-muted-foreground mt-1">
            Gérez les départements académiques et les filières rattachées
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={loadDepartements} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-1.5 ${loading ? "animate-spin" : ""}`} />
            Actualiser
          </Button>
          <Button onClick={() => { setSelectedDepartement(undefined); setDialogOpen(true); }}>
            <Plus className="h-4 w-4 mr-2" />
            Nouveau Département
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
            <Button variant="outline" size="sm" onClick={loadDepartements} className="border-destructive/30">
              Réessayer
            </Button>
          </div>
        </Card>
      )}

      {loading ? (
        <div className="p-16 text-center space-y-3">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto text-primary" />
          <p className="text-sm text-muted-foreground">Chargement des départements...</p>
        </div>
      ) : departements.length === 0 ? (
        <div className="p-12 text-center text-sm text-muted-foreground space-y-3 border rounded-2xl bg-card">
          <Building2 className="h-10 w-10 mx-auto text-muted-foreground/40" />
          <p className="font-semibold text-foreground text-base">Aucun département enregistré</p>
          <p className="text-xs max-w-sm mx-auto">
            Créez votre premier département pour regrouper vos filières et maquettes pédagogiques.
          </p>
          <Button onClick={() => { setSelectedDepartement(undefined); setDialogOpen(true); }} className="mt-2">
            <Plus className="h-4 w-4 mr-1.5" /> Créer un Département
          </Button>
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {departements.map((departement) => (
            <Card key={departement.id} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-start gap-4">
                  <div className="rounded-lg bg-primary/10 text-primary p-3">
                    <Building2 className="h-6 w-6" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg">{departement.nom}</CardTitle>
                      <Badge variant="outline" className="font-mono text-[10px]">
                        {departement.code}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {departement.description || "Aucune description fournie"}
                    </p>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="text-xs space-y-1 text-muted-foreground">
                  <div>Responsable : <span className="font-medium text-foreground">{departement.responsable || "Non assigné"}</span></div>
                  <div>Filières rattachées : <span className="font-semibold text-primary">{departement.filieres?.length || 0}</span></div>
                </div>

                <div className="pt-2 flex gap-2">
                  <Link to={`/departements/${departement.id}`} className="flex-1">
                    <Button variant="outline" size="sm" className="w-full text-xs">
                      <Eye className="h-3.5 w-3.5 mr-1.5" />
                      Voir
                    </Button>
                  </Link>
                  <Button variant="outline" size="sm" className="flex-1 text-xs" onClick={() => handleEdit(departement)}>
                    <Edit className="h-3.5 w-3.5 mr-1.5" />
                    Modifier
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-destructive hover:text-destructive"
                    onClick={() => {
                      setDepartementToDelete(departement.id);
                      setDeleteDialogOpen(true);
                    }}
                    aria-label="Supprimer"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <DepartementDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        departement={selectedDepartement}
        onSave={handleSave}
      />

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Supprimer ce département ?</AlertDialogTitle>
            <AlertDialogDescription>
              Les filières rattachées seront également supprimées si aucune donnée métier ne les protège.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-destructive text-destructive-foreground">
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default Departements;
