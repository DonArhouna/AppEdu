import { useEffect, useState } from "react";
import { AlertCircle, BookOpen, Edit, Eye, Loader2, Plus, RefreshCw, Trash2 } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { MatiereDialog } from "@/components/matieres/MatiereDialog";
import { structureApi, extractErrorMessage } from "@/services/apiClient";
import type { Matiere as MatiereApi, TeachingUnit } from "@/services/apiTypes";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

interface UE {
  id: string;
  code: string;
  nom: string;
  filiere: string;
  niveau: string;
  semestre: string;
}

interface MatiereForm extends Partial<Matiere> {
  ueId?: string;
  description?: string;
  enseignant?: string;
}

interface Matiere {
  id: string;
  type: "ECUE";
  code: string;
  nom: string;
  credits: number;
  coefficient: number;
  heures_cm: number;
  heures_td: number;
  heures_tp: number;
  filiere: string;
  niveau: string;
  semestre: string;
  enseignant_nom: string;
  ue_id: string;
  ue: string;
}

const MatieresECUE = () => {
  const navigate = useNavigate();
  const [matieres, setMatieres] = useState<Matiere[]>([]);
  const [ues, setUes] = useState<UE[]>([]);
  const [filieres, setFilieres] = useState<{ id: string; nom: string }[]>([]);
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
    const [matiereResult, ueResult, filiereResult] = await Promise.all([
      structureApi.getMatieres(),
      structureApi.getUEs(),
      structureApi.getFilieres(),
    ]);
    if (matiereResult.error || ueResult.error || filiereResult.error) {
      setError(extractErrorMessage(matiereResult.error || ueResult.error || filiereResult.error));
      setMatieres([]);
      setUes([]);
      setFilieres([]);
      setLoading(false);
      return;
    }

    const filiereMap = new Map((filiereResult.data || []).map((filiere) => [filiere.id, filiere.nom]));
    const mappedUes: UE[] = (ueResult.data || []).map((ue: TeachingUnit) => ({
      id: ue.id,
      code: ue.code,
      nom: ue.nom,
      filiere: filiereMap.get(ue.filiere_id) || ue.filiere?.nom || "",
      niveau: ue.niveau || "",
      semestre: ue.semestre || "",
    }));
    setUes(mappedUes);
    setFilieres((filiereResult.data || []) as { id: string; nom: string }[]);

    setMatieres(
      (matiereResult.data || []).map((matiere: MatiereApi) => {
        const parent = mappedUes.find((ue) => ue.id === matiere.ue_id);
        return {
          type: "ECUE" as const,
          id: matiere.id,
          code: matiere.code,
          nom: matiere.nom,
          credits: Number(matiere.credits) || 0,
          coefficient: Number(matiere.coefficient) || 0,
          heures_cm: Number(matiere.heures_cm) || 0,
          heures_td: Number(matiere.heures_td) || 0,
          heures_tp: Number(matiere.heures_tp) || 0,
          filiere: parent?.filiere || "",
          niveau: parent?.niveau || "",
          semestre: parent?.semestre || "",
          enseignant_nom: matiere.enseignant_nom || "",
          ue_id: matiere.ue_id || "",
          ue: parent?.nom || "",
        };
      })
    );
    setLoading(false);
  };

  useEffect(() => {
    void fetchData();
  }, []);

  const filteredMatieres = matieres.filter((matiere) => {
    const search = searchTerm.trim().toLowerCase();
    return !search || matiere.nom.toLowerCase().includes(search) || matiere.code.toLowerCase().includes(search);
  });

  const handleSave = async (data: MatiereForm) => {
    if (!data.nom || !data.code || !data.ueId) {
      toast.error("Le code, le nom et l'UE parente sont obligatoires.");
      return;
    }
    const payload = {
      nom: data.nom,
      code: data.code,
      credits: Number(data.credits),
      coefficient: Number(data.coefficient),
      heures_cm: Number(data.heures_cm) || 0,
      heures_td: Number(data.heures_td) || 0,
      heures_tp: Number(data.heures_tp) || 0,
      enseignant_nom: data.enseignant || "",
      ue_id: data.ueId,
      description: data.description || "",
    };
    const result = selectedMatiere
      ? await structureApi.updateMatiere(selectedMatiere.id, payload)
      : await structureApi.createMatiere(payload);
    if (result.error) {
      toast.error(result.error);
      return;
    }
    toast.success(selectedMatiere ? "Matière mise à jour." : "Matière créée.");
    setDialogOpen(false);
    setSelectedMatiere(null);
    await fetchData();
  };

  const confirmDelete = async () => {
    if (!matiereToDelete) return;
    const result = await structureApi.deleteMatiere(matiereToDelete);
    if (result.error) {
      toast.error(result.error);
      return;
    }
    toast.success("Matière supprimée.");
    setDeleteDialogOpen(false);
    setMatiereToDelete(null);
    await fetchData();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Matières (ECUE)</h1>
          <p className="text-muted-foreground">Référentiel des matières rattachées aux UE de l'établissement.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={fetchData} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Actualiser
          </Button>
          <Button onClick={() => setDialogOpen(true)} disabled={loading || ues.length === 0}>
            <Plus className="mr-2 h-4 w-4" />
            Créer une matière
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Erreur backend</AlertTitle>
          <AlertDescription className="flex items-center justify-between gap-3">
            <span>{error}</span>
            <Button variant="outline" size="sm" onClick={fetchData}>Réessayer</Button>
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader><CardTitle>Rechercher une matière</CardTitle></CardHeader>
        <CardContent>
          <Input value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} placeholder="Nom ou code" />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Matières enregistrées ({filteredMatieres.length})</CardTitle>
          <CardDescription>Aucune matière de démonstration n'est injectée dans cette liste.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto border-t">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/50">
                  <TableHead>Code</TableHead><TableHead>Matière</TableHead><TableHead>UE parente</TableHead>
                  <TableHead>Crédits</TableHead><TableHead>Coef.</TableHead><TableHead>Heures</TableHead>
                  <TableHead>Enseignant</TableHead><TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow><TableCell colSpan={8} className="py-10 text-center"><Loader2 className="mx-auto h-5 w-5 animate-spin" /></TableCell></TableRow>
                ) : filteredMatieres.length === 0 ? (
                  <TableRow><TableCell colSpan={8} className="py-10 text-center text-muted-foreground">Aucune matière enregistrée.</TableCell></TableRow>
                ) : filteredMatieres.map((matiere) => (
                  <TableRow key={matiere.id}>
                    <TableCell className="font-mono font-medium">{matiere.code}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2"><BookOpen className="h-4 w-4 text-primary" /><div><p className="font-medium">{matiere.nom}</p><p className="text-xs text-muted-foreground">{matiere.filiere} {matiere.niveau && `· ${matiere.niveau}`}</p></div></div>
                    </TableCell>
                    <TableCell>{matiere.ue || "Non rattachée"}</TableCell>
                    <TableCell>{matiere.credits}</TableCell>
                    <TableCell>{matiere.coefficient}</TableCell>
                    <TableCell>{matiere.heures_cm + matiere.heures_td + matiere.heures_tp}h</TableCell>
                    <TableCell>{matiere.enseignant_nom || "Non assigné"}</TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon" onClick={() => navigate(`/matieres/${matiere.id}`)} aria-label="Voir"><Eye className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon" onClick={() => { setSelectedMatiere(matiere); setDialogOpen(true); }} aria-label="Modifier"><Edit className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon" onClick={() => { setMatiereToDelete(matiere.id); setDeleteDialogOpen(true); }} aria-label="Supprimer"><Trash2 className="h-4 w-4 text-destructive" /></Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <MatiereDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onSave={handleSave}
        matiere={selectedMatiere}
        fixedType="ECUE"
        ues={ues}
        filieres={filieres}
      />

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Supprimer cette matière ?</AlertDialogTitle>
            <AlertDialogDescription>Cette action est irréversible dans le référentiel.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} className="bg-destructive text-destructive-foreground">Supprimer</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default MatieresECUE;
