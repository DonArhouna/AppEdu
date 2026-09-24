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
import { BookOpen, Users, Plus, Edit, Trash2, Eye, RefreshCw, AlertCircle, GraduationCap } from "lucide-react";
import { FiliereDialog, type Filiere } from "@/components/filieres/FiliereDialog";
import { toast } from "sonner";
import { structureApi } from "@/services/apiClient";

const Filieres = () => {
  const [filieres, setFilieres] = useState<Filiere[]>([]);
  const [departements, setDepartements] = useState<{ id: string; nom: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedFiliere, setSelectedFiliere] = useState<Filiere>();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [filiereToDelete, setFiliereToDelete] = useState<string | null>(null);

  const loadFilieres = async () => {
    setLoading(true);
    setError(null);
    try {
      const [res, departementsRes] = await Promise.all([
        structureApi.getFilieres(),
        structureApi.getDepartements(),
      ]);
      if (res.error || departementsRes.error) {
        setError(res.error || departementsRes.error || "Impossible de charger les filières.");
        setFilieres([]);
        setDepartements([]);
      } else {
        setFilieres((res.data || []) as unknown as Filiere[]);
        setDepartements((departementsRes.data || []).map((item) => ({ id: item.id, nom: item.nom })));
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erreur de connexion au serveur backend.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFilieres();
  }, []);

  const handleSave = async (filiereData: Filiere) => {
    const payload = {
      nom: filiereData.nom,
      code: filiereData.code,
      description: filiereData.description || "",
      diplome: filiereData.diplome,
      duree: Number(filiereData.duree),
      departement_id: filiereData.departement_id || undefined,
    };

    const res = selectedFiliere
      ? await structureApi.updateFiliere(selectedFiliere.id, payload)
      : await structureApi.createFiliere(payload);
    if (res.error) {
      toast.error(`Erreur : ${res.error}`);
      return;
    }
    toast.success(selectedFiliere ? "Filière mise à jour." : "Filière enregistrée.");
    setDialogOpen(false);
    setSelectedFiliere(undefined);
    await loadFilieres();
  };

  const handleEdit = (filiere: Filiere) => {
    setSelectedFiliere(filiere);
    setDialogOpen(true);
  };

  const handleDelete = async () => {
    if (!filiereToDelete) return;
    const result = await structureApi.deleteFiliere(filiereToDelete);
    if (result.error) {
      toast.error(result.error);
      return;
    }
    toast.success("Filière supprimée.");
    setDeleteDialogOpen(false);
    setFiliereToDelete(null);
    await loadFilieres();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Filières & Offre de Formation</h1>
          <p className="text-muted-foreground mt-1">
            Gérez les cursus de Licence, Master et les maquettes d'enseignement
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={loadFilieres} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-1.5 ${loading ? "animate-spin" : ""}`} />
            Actualiser
          </Button>
          <Button onClick={() => { setSelectedFiliere(undefined); setDialogOpen(true); }}>
            <Plus className="h-4 w-4 mr-2" />
            Nouvelle Filière
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
            <Button variant="outline" size="sm" onClick={loadFilieres} className="border-destructive/30">
              Réessayer
            </Button>
          </div>
        </Card>
      )}

      {loading ? (
        <div className="p-16 text-center space-y-3">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto text-primary" />
          <p className="text-sm text-muted-foreground">Chargement des filières...</p>
        </div>
      ) : filieres.length === 0 ? (
        <div className="p-12 text-center text-sm text-muted-foreground space-y-3 border rounded-2xl bg-card">
          <GraduationCap className="h-10 w-10 mx-auto text-muted-foreground/40" />
          <p className="font-semibold text-foreground text-base">Aucune filière enregistrée</p>
          <p className="text-xs max-w-sm mx-auto">
            Définissez les filières d'enseignement de l'établissement.
          </p>
          <Button onClick={() => { setSelectedFiliere(undefined); setDialogOpen(true); }} className="mt-2">
            <Plus className="h-4 w-4 mr-1.5" /> Créer une Filière
          </Button>
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {filieres.map((filiere) => (
            <Card key={filiere.id} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-start gap-4">
                  <div className="rounded-lg bg-primary/10 text-primary p-3">
                    <GraduationCap className="h-6 w-6" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg">{filiere.nom}</CardTitle>
                      <Badge variant="outline" className="font-mono text-[10px]">
                        {filiere.code}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {filiere.description || "Aucune description fournie"}
                    </p>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="text-xs space-y-1 text-muted-foreground">
                  <div>Diplôme préparé : <Badge variant="secondary" className="text-[10px] ml-1">{filiere.diplome || "Non renseigné"}</Badge></div>
                  <div>Durée du cursus : <span className="font-medium text-foreground">{filiere.duree || 3} ans</span></div>
                  <div>Unités d'Enseignement (UEs) : <span className="font-semibold text-primary">{filiere.unites_enseignement?.length || 0}</span></div>
                </div>

                <div className="pt-2 flex gap-2">
                  <Link to={`/filieres/${filiere.id}`} className="flex-1">
                    <Button variant="outline" size="sm" className="w-full text-xs">
                      <Eye className="h-3.5 w-3.5 mr-1.5" />
                      Voir
                    </Button>
                  </Link>
                  <Button variant="outline" size="sm" className="flex-1 text-xs" onClick={() => handleEdit(filiere)}>
                    <Edit className="h-3.5 w-3.5 mr-1.5" />
                    Modifier
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-destructive hover:text-destructive"
                    onClick={() => {
                      setFiliereToDelete(filiere.id);
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

      <FiliereDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        filiere={selectedFiliere}
        departements={departements}
        onSave={handleSave}
      />

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Supprimer cette filière ?</AlertDialogTitle>
            <AlertDialogDescription>
              Les UEs et données qui lui sont rattachées peuvent être affectés par cette suppression.
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

export default Filieres;
