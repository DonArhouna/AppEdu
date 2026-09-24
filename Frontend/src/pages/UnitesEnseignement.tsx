import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { UEDialog } from "@/components/matieres/UEDialog";
import { Plus, Search, Eye, Pencil, Trash2, BookOpen, AlertCircle, RefreshCw } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { structureApi, extractErrorMessage } from "@/services/apiClient";
import type { Matiere, TeachingUnit } from "@/services/apiTypes";

interface UE {
  id: string;
  code: string;
  nom: string;
  type: "UE";
  credits: number;
  coefficient: number;
  heures: number;
  filiere: string;
  filiere_id: string;
  niveau: string;
  semestre: string;
  responsable?: string;
  nbMatieres?: number;
  matieres?: Matiere[];
}

export default function UnitesEnseignement() {
  const navigate = useNavigate();
  const [ues, setUes] = useState<UE[]>([]);
  const [filieres, setFilieres] = useState<{ id: string; nom: string }[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedUE, setSelectedUE] = useState<UE | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [ueToDelete, setUeToDelete] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUEs = async () => {
    setLoading(true);
    setError(null);
    try {
      const [result, filieresResult] = await Promise.all([
        structureApi.getUEs(),
        structureApi.getFilieres(),
      ]);
      if (result.error || filieresResult.error) {
        throw new Error(result.error || filieresResult.error || "Impossible de charger les UE.");
      }
      const filiereMap = new Map((filieresResult.data || []).map((filiere) => [filiere.id, filiere.nom]));
      const mapped = (result.data || []).map((u: TeachingUnit) => ({
        id: u.id,
        code: u.code,
        nom: u.nom,
        type: "UE" as const,
        credits: u.credits ?? 0,
        coefficient: u.coefficient ?? 0,
        heures: u.heures ?? 0,
        filiere: filiereMap.get(u.filiere_id) || u.filiere?.nom || "",
        filiere_id: u.filiere_id || "",
        niveau: u.niveau || "",
        semestre: u.semestre || "",
        responsable: u.responsable || "",
        nbMatieres: Array.isArray(u.matieres) ? u.matieres.length : 0,
        matieres: u.matieres || [],
      }));
      setUes(mapped);
      setFilieres((filieresResult.data || []) as { id: string; nom: string }[]);
    } catch (err: unknown) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUEs();
  }, []);

  const filteredUEs = ues.filter((ue) =>
    ue.nom.toLowerCase().includes(searchTerm.toLowerCase()) ||
    ue.code.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleSaveUE = async (data: Partial<UE>) => {
    if (!data.nom || !data.code || !data.filiere) {
      toast.error("Le nom, le code et la filière sont obligatoires.");
      return;
    }
    const payload = {
      nom: data.nom,
      code: data.code,
      credits: Number(data.credits),
      coefficient: Number(data.coefficient),
      heures: Number(data.heures),
      semestre: data.semestre || "",
      niveau: data.niveau || "",
      responsable: data.responsable || "",
      filiere_id: data.filiere,
    };
    const result = selectedUE
      ? await structureApi.updateUE(selectedUE.id, payload)
      : await structureApi.createUE(payload);
    if (result.error) {
      toast.error(result.error);
      return;
    }
    toast.success(selectedUE ? "UE modifiée." : "UE ajoutée.");
    setDialogOpen(false);
    setSelectedUE(null);
    await fetchUEs();
  };

  const handleEdit = (ue: UE) => {
    setSelectedUE({ ...ue, filiere: ue.filiere_id });
    setDialogOpen(true);
  };

  const handleDelete = (id: string) => {
    setUeToDelete(id);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!ueToDelete) return;
    try {
      await structureApi.deleteUE(ueToDelete);
      toast.success("UE supprimée avec succès");
      setDeleteDialogOpen(false);
      setUeToDelete(null);
      fetchUEs();
    } catch (err: unknown) {
      toast.error(extractErrorMessage(err));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Unités d'Enseignement (UE)</h1>
          <p className="text-muted-foreground">Référentiel des UE</p>
        </div>
        <Button onClick={() => setDialogOpen(true)} className="bg-primary hover:bg-primary-hover">
          <Plus className="mr-2 h-4 w-4" />
          Créer UE
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Erreur de communication avec le serveur</AlertTitle>
          <AlertDescription className="mt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <p>{error}</p>
            <Button variant="outline" size="sm" onClick={fetchUEs}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Réessayer
            </Button>
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Recherche</CardTitle>
          <CardDescription>Rechercher une UE</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="relative">
            <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Rechercher par nom ou code..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Liste des UE ({filteredUEs.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border border-border">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/50">
                  <TableHead>Code</TableHead>
                  <TableHead>UE</TableHead>
                  <TableHead>Crédits</TableHead>
                  <TableHead>Coef.</TableHead>
                  <TableHead>Heures</TableHead>
                  <TableHead>Matières</TableHead>
                  <TableHead>Responsable</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  [1, 2, 3].map((i) => (
                    <TableRow key={i}>
                      <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                      <TableCell><Skeleton className="h-4 w-40" /></TableCell>
                      <TableCell><Skeleton className="h-4 w-10" /></TableCell>
                      <TableCell><Skeleton className="h-4 w-10" /></TableCell>
                      <TableCell><Skeleton className="h-4 w-12" /></TableCell>
                      <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                      <TableCell><Skeleton className="h-4 w-28" /></TableCell>
                      <TableCell className="text-right"><Skeleton className="h-8 w-20 ml-auto" /></TableCell>
                    </TableRow>
                  ))
                ) : filteredUEs.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                      Aucune Unité d'Enseignement enregistrée ou correspondant à votre recherche.
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredUEs.map((ue) => (
                    <TableRow key={ue.id} className="hover:bg-accent/50">
                      <TableCell className="font-mono font-medium">{ue.code}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <BookOpen className="h-4 w-4 text-primary" />
                          <div>
                            <div className="font-medium">{ue.nom}</div>
                            <div className="text-sm text-muted-foreground">
                              {ue.filiere} - {ue.niveau} - {ue.semestre}
                            </div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>{ue.credits}</TableCell>
                      <TableCell>{ue.coefficient}</TableCell>
                      <TableCell>{ue.heures}h</TableCell>
                      <TableCell>
                        <Badge variant="outline">{ue.nbMatieres || 0} matières</Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {ue.responsable || "Non assigné"}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => navigate(`/ue/${ue.id}`)}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="icon" onClick={() => handleEdit(ue)}>
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(ue.id)}
                            className="text-destructive hover:text-destructive"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <UEDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onSave={handleSaveUE}
        ue={selectedUE}
        filieres={filieres}
      />

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmer la suppression</AlertDialogTitle>
            <AlertDialogDescription>
              Êtes-vous sûr de vouloir supprimer cette UE ? Cette action est irréversible.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
