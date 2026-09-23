import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { MatiereDialog } from "@/components/matieres/MatiereDialog";
import { Plus, Search, Eye, Pencil, Trash2, BookOpen, AlertCircle, RefreshCw } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { structureApi, extractErrorMessage } from "@/services/apiClient";

interface Matiere {
  id: string;
  code: string;
  nom: string;
  type: "UE" | "ECUE";
  credits: number;
  coefficient: number;
  heures: number;
  filiere: string;
  niveau: string;
  semestre: string;
  enseignant?: string;
  ue_id?: string;
}

export default function Matieres() {
  const navigate = useNavigate();
  const [matieres, setMatieres] = useState<Matiere[]>([]);
  const [ues, setUes] = useState<any[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedMatiere, setSelectedMatiere] = useState<Matiere | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [matiereToDelete, setMatiereToDelete] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [mList, uList] = await Promise.all([
        structureApi.getMatieres(),
        structureApi.getUEs(),
      ]);
      setUes(uList || []);
      const mapped: Matiere[] = (mList || []).map((m: any) => {
        const totalH = (Number(m.heures_cm) || 0) + (Number(m.heures_td) || 0) + (Number(m.heures_tp) || 0);
        return {
          id: m.id,
          code: m.code,
          nom: m.nom,
          type: "ECUE" as const,
          credits: m.credits ?? 3,
          coefficient: m.coefficient ?? 1.5,
          heures: totalH > 0 ? totalH : 45,
          filiere: m.ue?.filiere?.nom || "Tronc Commun",
          niveau: m.ue?.niveau || "Licence",
          semestre: m.ue?.semestre || "S1",
          enseignant: m.enseignant_nom || "Non assigné",
          ue_id: m.ue_id,
        };
      });
      setMatieres(mapped);
    } catch (err: any) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const filteredMatieres = matieres.filter((m) => {
    return (
      m.nom.toLowerCase().includes(searchTerm.toLowerCase()) ||
      m.code.toLowerCase().includes(searchTerm.toLowerCase())
    );
  });

  const handleSaveMatiere = async (data: Partial<Matiere>) => {
    try {
      if (selectedMatiere) {
        await structureApi.updateMatiere(selectedMatiere.id, {
          nom: data.nom,
          code: data.code,
          credits: Number(data.credits || 3),
          coefficient: Number(data.coefficient || 1.5),
          heures_cm: Number(data.heures ? Math.round(data.heures * 0.4) : 20),
          heures_td: Number(data.heures ? Math.round(data.heures * 0.3) : 15),
          heures_tp: Number(data.heures ? Math.round(data.heures * 0.3) : 10),
          enseignant_nom: data.enseignant,
          ue_id: (data as any).ueId || selectedMatiere.ue_id,
        });
        toast.success("Matière mise à jour avec succès");
      } else {
        const ueId = (data as any).ueId || (ues.length > 0 ? ues[0].id : "UE-01");
        await structureApi.createMatiere({
          nom: data.nom,
          code: data.code,
          credits: Number(data.credits || 3),
          coefficient: Number(data.coefficient || 1.5),
          heures_cm: Number(data.heures ? Math.round(data.heures * 0.4) : 20),
          heures_td: Number(data.heures ? Math.round(data.heures * 0.3) : 15),
          heures_tp: Number(data.heures ? Math.round(data.heures * 0.3) : 10),
          enseignant_nom: data.enseignant,
          ue_id: ueId,
        });
        toast.success("Matière créée avec succès");
      }
      setDialogOpen(false);
      setSelectedMatiere(null);
      fetchData();
    } catch (err: any) {
      toast.error(extractErrorMessage(err));
    }
  };

  const handleEdit = (m: Matiere) => {
    setSelectedMatiere(m);
    setDialogOpen(true);
  };

  const handleDelete = (id: string) => {
    setMatiereToDelete(id);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!matiereToDelete) return;
    try {
      await structureApi.deleteMatiere(matiereToDelete);
      toast.success("Matière supprimée avec succès");
      setDeleteDialogOpen(false);
      setMatiereToDelete(null);
      fetchData();
    } catch (err: any) {
      toast.error(extractErrorMessage(err));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Matières & Éléments Constitutifs (ECUE)</h1>
          <p className="text-muted-foreground">Référentiel des cours et matières de formation</p>
        </div>
        <Button onClick={() => setDialogOpen(true)} className="bg-primary hover:bg-primary-hover">
          <Plus className="mr-2 h-4 w-4" />
          Ajouter Matière
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Erreur de communication avec le serveur</AlertTitle>
          <AlertDescription className="mt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <p>{error}</p>
            <Button variant="outline" size="sm" onClick={fetchData}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Réessayer
            </Button>
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Recherche</CardTitle>
          <CardDescription>Rechercher une matière par code ou intitulé</CardDescription>
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
          <CardTitle>Liste des Matières ({filteredMatieres.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border border-border">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/50">
                  <TableHead>Code</TableHead>
                  <TableHead>Matière</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Crédits</TableHead>
                  <TableHead>Coef.</TableHead>
                  <TableHead>Heures</TableHead>
                  <TableHead>Enseignant</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  [1, 2, 3].map((i) => (
                    <TableRow key={i}>
                      <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                      <TableCell><Skeleton className="h-4 w-40" /></TableCell>
                      <TableCell><Skeleton className="h-4 w-14" /></TableCell>
                      <TableCell><Skeleton className="h-4 w-10" /></TableCell>
                      <TableCell><Skeleton className="h-4 w-10" /></TableCell>
                      <TableCell><Skeleton className="h-4 w-12" /></TableCell>
                      <TableCell><Skeleton className="h-4 w-28" /></TableCell>
                      <TableCell className="text-right"><Skeleton className="h-8 w-20 ml-auto" /></TableCell>
                    </TableRow>
                  ))
                ) : filteredMatieres.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                      Aucune matière enregistrée ou correspondant à votre recherche.
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredMatieres.map((m) => (
                    <TableRow key={m.id} className="hover:bg-accent/50">
                      <TableCell className="font-mono font-medium">{m.code}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <BookOpen className="h-4 w-4 text-primary" />
                          <div>
                            <div className="font-medium">{m.nom}</div>
                            <div className="text-sm text-muted-foreground">
                              {m.filiere} - {m.niveau} - {m.semestre}
                            </div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{m.type}</Badge>
                      </TableCell>
                      <TableCell>{m.credits}</TableCell>
                      <TableCell>{m.coefficient}</TableCell>
                      <TableCell>{m.heures}h</TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {m.enseignant || "Non assigné"}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => navigate(`/matieres/${m.id}`)}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="icon" onClick={() => handleEdit(m)}>
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(m.id)}
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

      <MatiereDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onSave={handleSaveMatiere}
        matiere={selectedMatiere}
        ues={ues}
      />

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmer la suppression</AlertDialogTitle>
            <AlertDialogDescription>
              Êtes-vous sûr de vouloir supprimer cette matière ? Cette action est irréversible.
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

