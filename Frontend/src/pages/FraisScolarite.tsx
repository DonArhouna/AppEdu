import { useEffect, useMemo, useState, type FormEvent } from "react";
import { AlertCircle, DollarSign, Edit, Layers, Loader2, Plus, RefreshCw, Trash2 } from "lucide-react";
import { toast } from "sonner";
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
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { KpiCard } from "@/components/ui/kpi-card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { extractErrorMessage, financesApi, setupApi, structureApi } from "@/services/apiClient";

interface TarificationConfig {
  id: string;
  filiere_id: string | null;
  filiere: string;
  niveau: string;
  droits_inscription: number;
  scolarite_mensuelle: number;
  nombre_mois: number;
  total_annuel: number;
  actif: boolean;
}

interface FiliereOption {
  id: string;
  nom: string;
}

const emptyForm = {
  filiere_id: "",
  filiere: "",
  niveau: "",
  droits_inscription: "",
  scolarite_mensuelle: "",
  nombre_mois: "",
};

const FraisScolarite = () => {
  const [configs, setConfigs] = useState<TarificationConfig[]>([]);
  const [filieres, setFilieres] = useState<FiliereOption[]>([]);
  const [currency, setCurrency] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingConfig, setEditingConfig] = useState<TarificationConfig | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [formData, setFormData] = useState(emptyForm);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    const [grillesResult, filieresResult, setupResult] = await Promise.all([
      financesApi.getGrillesTarifaires(),
      structureApi.getFilieres(),
      setupApi.getStatus(),
    ]);

    if (grillesResult.error || filieresResult.error) {
      setError(
        extractErrorMessage(
          grillesResult.error || filieresResult.error,
          "Impossible de charger les grilles tarifaires."
        )
      );
      setConfigs([]);
      setFilieres([]);
    } else {
      setConfigs((grillesResult.data || []) as TarificationConfig[]);
      setFilieres((filieresResult.data || []) as FiliereOption[]);
    }
    setCurrency(setupResult.data?.devise || "");
    setLoading(false);
  };

  useEffect(() => {
    void loadData();
  }, []);

  const activeConfigs = useMemo(() => configs.filter((config) => config.actif), [configs]);
  const averageInscription = useMemo(
    () =>
      activeConfigs.length
        ? activeConfigs.reduce((sum, config) => sum + Number(config.droits_inscription), 0) /
          activeConfigs.length
        : 0,
    [activeConfigs]
  );
  const averageMensualite = useMemo(
    () =>
      activeConfigs.length
        ? activeConfigs.reduce((sum, config) => sum + Number(config.scolarite_mensuelle), 0) /
          activeConfigs.length
        : 0,
    [activeConfigs]
  );

  const openCreateDialog = () => {
    setEditingConfig(null);
    setFormData(emptyForm);
    setShowForm(true);
  };

  const openEditDialog = (config: TarificationConfig) => {
    setEditingConfig(config);
    setFormData({
      filiere_id: config.filiere_id || "",
      filiere: config.filiere,
      niveau: config.niveau,
      droits_inscription: String(config.droits_inscription),
      scolarite_mensuelle: String(config.scolarite_mensuelle),
      nombre_mois: String(config.nombre_mois),
    });
    setShowForm(true);
  };

  const handleFiliereChange = (filiereId: string) => {
    const filiere = filieres.find((item) => item.id === filiereId);
    setFormData((current) => ({
      ...current,
      filiere_id: filiereId,
      filiere: filiere?.nom || "",
    }));
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const droitsInscription = Number(formData.droits_inscription);
    const scolariteMensuelle = Number(formData.scolarite_mensuelle);
    const nombreMois = Number(formData.nombre_mois);

    if (!formData.filiere || !formData.niveau.trim()) {
      toast.error("La filière et le niveau sont obligatoires.");
      return;
    }
    if (
      !Number.isFinite(droitsInscription) ||
      !Number.isFinite(scolariteMensuelle) ||
      !Number.isInteger(nombreMois) ||
      droitsInscription < 0 ||
      scolariteMensuelle < 0 ||
      nombreMois < 1
    ) {
      toast.error("Renseignez des montants et un nombre de mois valides.");
      return;
    }

    const payload = {
      filiere_id: formData.filiere_id || null,
      filiere: formData.filiere.trim(),
      niveau: formData.niveau.trim(),
      droits_inscription: droitsInscription,
      scolarite_mensuelle: scolariteMensuelle,
      nombre_mois: nombreMois,
      actif: true,
    };

    setSaving(true);
    const result = editingConfig
      ? await financesApi.updateGrilleTarifaire(editingConfig.id, payload)
      : await financesApi.createGrilleTarifaire(payload);
    setSaving(false);

    if (result.error) {
      toast.error(extractErrorMessage(result.error));
      return;
    }

    toast.success(editingConfig ? "Grille tarifaire mise à jour." : "Grille tarifaire créée.");
    setShowForm(false);
    setEditingConfig(null);
    await loadData();
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    const result = await financesApi.deleteGrilleTarifaire(deleteId);
    if (result.error) {
      toast.error(extractErrorMessage(result.error));
      return;
    }
    toast.success("Grille tarifaire supprimée.");
    setDeleteId(null);
    await loadData();
  };

  const currencyLabel = currency || "devise de l'établissement";

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Frais de scolarité</h1>
          <p className="mt-1 text-muted-foreground">
            Configurez les droits et montants par filière et niveau. Les données proviennent de l'API.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadData} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Actualiser
          </Button>
          <Button onClick={openCreateDialog} disabled={loading || filieres.length === 0}>
            <Plus className="mr-2 h-4 w-4" />
            Nouvelle grille
          </Button>
        </div>
      </div>

      {error && (
        <Card className="border-destructive/40 bg-destructive/5 p-4">
          <div className="flex items-center gap-3 text-sm text-destructive">
            <AlertCircle className="h-5 w-5 shrink-0" />
            <span>{error}</span>
            <Button variant="outline" size="sm" className="ml-auto" onClick={loadData}>
              Réessayer
            </Button>
          </div>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <KpiCard title="Grilles actives" value={activeConfigs.length} icon={Layers} subtitle="Configurations disponibles" colorVariant="primary" />
        <KpiCard title="Droits moyens" value={`${averageInscription.toLocaleString("fr-FR")} ${currencyLabel}`} icon={DollarSign} subtitle="Moyenne des grilles actives" colorVariant="emerald" />
        <KpiCard title="Mensualité moyenne" value={`${averageMensualite.toLocaleString("fr-FR")} ${currencyLabel}`} icon={DollarSign} subtitle="Montant mensuel moyen déclaré" colorVariant="purple" />
      </div>

      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle>{editingConfig ? "Modifier la grille" : "Créer une grille"}</CardTitle>
            <CardDescription>
              Les montants saisis seront utilisés par le guichet et les écrans de paiement.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="grid gap-4 md:grid-cols-3">
                <div className="space-y-2">
                  <Label htmlFor="fee-filiere">Filière *</Label>
                  <Select value={formData.filiere_id} onValueChange={handleFiliereChange}>
                    <SelectTrigger id="fee-filiere">
                      <SelectValue placeholder="Sélectionner une filière" />
                    </SelectTrigger>
                    <SelectContent>
                      {filieres.map((filiere) => (
                        <SelectItem key={filiere.id} value={filiere.id}>
                          {filiere.nom}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="fee-niveau">Niveau / classe *</Label>
                  <Input
                    id="fee-niveau"
                    value={formData.niveau}
                    onChange={(event) => setFormData((current) => ({ ...current, niveau: event.target.value }))}
                    placeholder="Niveau défini par l'établissement"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="fee-mois">Nombre de mois *</Label>
                  <Input
                    id="fee-mois"
                    type="number"
                    min={1}
                    max={24}
                    value={formData.nombre_mois}
                    onChange={(event) => setFormData((current) => ({ ...current, nombre_mois: event.target.value }))}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="fee-inscription">Droits d'inscription ({currencyLabel}) *</Label>
                  <Input
                    id="fee-inscription"
                    type="number"
                    min={0}
                    step="0.01"
                    value={formData.droits_inscription}
                    onChange={(event) => setFormData((current) => ({ ...current, droits_inscription: event.target.value }))}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="fee-mensualite">Scolarité mensuelle ({currencyLabel}) *</Label>
                  <Input
                    id="fee-mensualite"
                    type="number"
                    min={0}
                    step="0.01"
                    value={formData.scolarite_mensuelle}
                    onChange={(event) => setFormData((current) => ({ ...current, scolarite_mensuelle: event.target.value }))}
                    required
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2 border-t pt-4">
                <Button type="button" variant="outline" onClick={() => setShowForm(false)}>
                  Annuler
                </Button>
                <Button type="submit" disabled={saving}>
                  {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Enregistrer
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Grilles enregistrées</CardTitle>
          <CardDescription>Aucune grille n'est créée automatiquement lors du setup.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto border-t">
            {loading ? (
              <div className="flex items-center justify-center gap-2 p-12 text-sm text-muted-foreground">
                <Loader2 className="h-5 w-5 animate-spin" /> Chargement des grilles...
              </div>
            ) : configs.length === 0 ? (
              <div className="p-12 text-center text-sm text-muted-foreground">
                Aucune grille configurée. Créez la première grille depuis cette page.
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/40">
                    <TableHead>Filière</TableHead>
                    <TableHead>Niveau</TableHead>
                    <TableHead>Droits d'inscription</TableHead>
                    <TableHead>Mensualité</TableHead>
                    <TableHead>Durée</TableHead>
                    <TableHead>Total annuel</TableHead>
                    <TableHead>Statut</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {configs.map((config) => (
                    <TableRow key={config.id}>
                      <TableCell className="font-medium">{config.filiere}</TableCell>
                      <TableCell><Badge variant="outline">{config.niveau}</Badge></TableCell>
                      <TableCell className="font-mono">{config.droits_inscription.toLocaleString("fr-FR")} {currencyLabel}</TableCell>
                      <TableCell className="font-mono">{config.scolarite_mensuelle.toLocaleString("fr-FR")} {currencyLabel}</TableCell>
                      <TableCell>{config.nombre_mois} mois</TableCell>
                      <TableCell className="font-mono font-semibold text-emerald-600">{config.total_annuel.toLocaleString("fr-FR")} {currencyLabel}</TableCell>
                      <TableCell>
                        <Badge variant={config.actif ? "default" : "secondary"}>
                          {config.actif ? "Active" : "Inactive"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="icon" onClick={() => openEditDialog(config)} aria-label="Modifier">
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => setDeleteId(config.id)} aria-label="Supprimer">
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </CardContent>
      </Card>

      <AlertDialog open={Boolean(deleteId)} onOpenChange={(open) => !open && setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Supprimer cette grille ?</AlertDialogTitle>
            <AlertDialogDescription>
              Les paiements déjà enregistrés ne seront pas supprimés, mais cette grille ne sera plus proposée.
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

export default FraisScolarite;
