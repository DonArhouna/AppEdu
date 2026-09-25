import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import {
  AlertCircle,
  BookOpenCheck,
  CheckCircle2,
  Edit3,
  GraduationCap,
  Layers3,
  Loader2,
  Plus,
  RefreshCw,
  School,
  Sparkles,
  Trash2,
} from "lucide-react";
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
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { KpiCard } from "@/components/ui/kpi-card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { academicApi, extractErrorMessage, structureApi } from "@/services/apiClient";
import type { AcademicClass, AcademicCycle, AcademicLevel, Filiere } from "@/services/apiTypes";

type EditorKind = "cycle" | "level" | "class" | null;
type DeleteKind = "cycle" | "level" | "class";

interface CycleForm {
  code: string;
  libelle: string;
  description: string;
  rang: string;
  actif: boolean;
}

interface LevelForm {
  code: string;
  libelle: string;
  cycle_id: string;
  rang: string;
  actif: boolean;
}

interface ClassForm {
  code: string;
  libelle: string;
  filiere_id: string;
  niveau_id: string;
  actif: boolean;
}

const emptyCycle: CycleForm = {
  code: "",
  libelle: "",
  description: "",
  rang: "",
  actif: true,
};

const emptyLevel: LevelForm = {
  code: "",
  libelle: "",
  cycle_id: "",
  rang: "",
  actif: true,
};

const emptyClass: ClassForm = {
  code: "",
  libelle: "",
  filiere_id: "",
  niveau_id: "",
  actif: true,
};

const statusBadge = (actif: boolean) => (
  <Badge variant={actif ? "default" : "secondary"}>{actif ? "Actif" : "Inactif"}</Badge>
);

const AcademicStructure = () => {
  const [searchParams] = useSearchParams();
  const [cycles, setCycles] = useState<AcademicCycle[]>([]);
  const [levels, setLevels] = useState<AcademicLevel[]>([]);
  const [classes, setClasses] = useState<AcademicClass[]>([]);
  const [filieres, setFilieres] = useState<Filiere[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [editor, setEditor] = useState<EditorKind>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [cycleForm, setCycleForm] = useState<CycleForm>(emptyCycle);
  const [levelForm, setLevelForm] = useState<LevelForm>(emptyLevel);
  const [classForm, setClassForm] = useState<ClassForm>(emptyClass);

  const [templateDialogOpen, setTemplateDialogOpen] = useState(false);
  const [templateLoading, setTemplateLoading] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ kind: DeleteKind; id: string; label: string } | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const [classFiliereFilter, setClassFiliereFilter] = useState(() => searchParams.get("filiere") || "all");
  const [classCycleFilter, setClassCycleFilter] = useState("all");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    const [cyclesResult, levelsResult, classesResult, filieresResult] = await Promise.all([
      academicApi.getCycles(),
      academicApi.getLevels(),
      academicApi.getClasses(),
      structureApi.getFilieres(),
    ]);
    const firstError =
      cyclesResult.error || levelsResult.error || classesResult.error || filieresResult.error;
    if (firstError) {
      setError(extractErrorMessage(firstError, "Le référentiel académique est indisponible."));
      setCycles([]);
      setLevels([]);
      setClasses([]);
      setFilieres([]);
    } else {
      setCycles(cyclesResult.data || []);
      setLevels(levelsResult.data || []);
      setClasses(classesResult.data || []);
      setFilieres(filieresResult.data || []);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    setClassFiliereFilter(searchParams.get("filiere") || "all");
  }, [searchParams]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const filiereById = useMemo(
    () => new Map(filieres.map((item) => [item.id, item])),
    [filieres]
  );
  const cycleById = useMemo(
    () => new Map(cycles.map((item) => [item.id, item])),
    [cycles]
  );
  const levelById = useMemo(
    () => new Map(levels.map((item) => [item.id, item])),
    [levels]
  );

  const filteredClasses = useMemo(
    () =>
      classes.filter((item) => {
        const matchesFiliere = classFiliereFilter === "all" || item.filiere_id === classFiliereFilter;
        const level = levelById.get(item.niveau_id);
        const matchesCycle = classCycleFilter === "all" || level?.cycle_id === classCycleFilter;
        return matchesFiliere && matchesCycle;
      }),
    [classes, classFiliereFilter, classCycleFilter, levelById]
  );

  const closeEditor = () => {
    setEditor(null);
    setEditingId(null);
    setCycleForm(emptyCycle);
    setLevelForm(emptyLevel);
    setClassForm(emptyClass);
  };

  const openCycleEditor = (item?: AcademicCycle) => {
    setEditor("cycle");
    setEditingId(item?.id || null);
    setCycleForm(
      item
        ? {
            code: item.code,
            libelle: item.libelle,
            description: item.description || "",
            rang: String(item.rang),
            actif: item.actif,
          }
        : emptyCycle
    );
  };

  const openLevelEditor = (item?: AcademicLevel) => {
    setEditor("level");
    setEditingId(item?.id || null);
    setLevelForm(
      item
        ? {
            code: item.code,
            libelle: item.libelle,
            cycle_id: item.cycle_id,
            rang: String(item.rang),
            actif: item.actif,
          }
        : emptyLevel
    );
  };

  const openClassEditor = (item?: AcademicClass) => {
    setEditor("class");
    setEditingId(item?.id || null);
    setClassForm(
      item
        ? {
            code: item.code,
            libelle: item.libelle,
            filiere_id: item.filiere_id,
            niveau_id: item.niveau_id,
            actif: item.actif,
          }
        : emptyClass
    );
  };

  const saveCycle = async (event: FormEvent) => {
    event.preventDefault();
    if (!cycleForm.code.trim() || !cycleForm.libelle.trim() || cycleForm.rang === "") {
      toast.error("Le code, le libellé et l'ordre du cycle sont obligatoires.");
      return;
    }
    setSaving(true);
    const payload = {
      code: cycleForm.code.trim().toUpperCase(),
      nom: cycleForm.libelle.trim(),
      description: cycleForm.description.trim() || null,
      ordre: Number(cycleForm.rang),
      actif: cycleForm.actif,
    };
    const result = editingId
      ? await academicApi.updateCycle(editingId, payload)
      : await academicApi.createCycle(payload);
    setSaving(false);
    if (result.error) {
      toast.error(extractErrorMessage(result.error));
      return;
    }
    toast.success(editingId ? "Cycle mis à jour." : "Cycle créé.");
    closeEditor();
    await loadData();
  };

  const saveLevel = async (event: FormEvent) => {
    event.preventDefault();
    if (!levelForm.code.trim() || !levelForm.libelle.trim() || !levelForm.cycle_id || levelForm.rang === "") {
      toast.error("Le code, le libellé, le cycle et l'ordre du niveau sont obligatoires.");
      return;
    }
    setSaving(true);
    const payload = {
      code: levelForm.code.trim().toUpperCase(),
      nom: levelForm.libelle.trim(),
      cycle_id: levelForm.cycle_id,
      ordre: Number(levelForm.rang),
      actif: levelForm.actif,
    };
    const result = editingId
      ? await academicApi.updateLevel(editingId, payload)
      : await academicApi.createLevel(payload);
    setSaving(false);
    if (result.error) {
      toast.error(extractErrorMessage(result.error));
      return;
    }
    toast.success(editingId ? "Niveau mis à jour." : "Niveau créé.");
    closeEditor();
    await loadData();
  };

  const saveClass = async (event: FormEvent) => {
    event.preventDefault();
    if (!classForm.code.trim() || !classForm.libelle.trim() || !classForm.filiere_id || !classForm.niveau_id) {
      toast.error("Le code, le libellé, la filière et le niveau sont obligatoires.");
      return;
    }
    setSaving(true);
    const payload = {
      nom: classForm.libelle.trim(),
      filiere_id: classForm.filiere_id,
      niveau_id: classForm.niveau_id,
      actif: classForm.actif,
    };
    const result = editingId
      ? await academicApi.updateClass(editingId, payload)
      : await academicApi.createClass(payload);
    setSaving(false);
    if (result.error) {
      toast.error(extractErrorMessage(result.error));
      return;
    }
    toast.success(editingId ? "Classe mise à jour." : "Classe créée.");
    closeEditor();
    await loadData();
  };

  const loadLmdTemplate = async () => {
    setTemplateLoading(true);
    const result = await academicApi.loadLmdTemplate();
    setTemplateLoading(false);
    if (result.error || !result.data) {
      toast.error(extractErrorMessage(result.error, "Le modèle LMD n'a pas pu être chargé."));
      return;
    }
    const detail = result.data.created
      ? `${result.data.cycles_crees} cycle(s) et ${result.data.niveaux_crees} niveau(s) créés.`
      : "Le modèle LMD était déjà présent : aucun doublon n'a été créé.";
    toast.success(detail);
    setTemplateDialogOpen(false);
    await loadData();
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleteLoading(true);
    const result =
      deleteTarget.kind === "cycle"
        ? await academicApi.deleteCycle(deleteTarget.id)
        : deleteTarget.kind === "level"
          ? await academicApi.deleteLevel(deleteTarget.id)
          : await academicApi.deleteClass(deleteTarget.id);
    setDeleteLoading(false);
    if (result.error) {
      toast.error(extractErrorMessage(result.error));
      return;
    }
    toast.success("Élément supprimé.");
    setDeleteTarget(null);
    await loadData();
  };

  const selectedClassLevel = levelById.get(classForm.niveau_id);
  const selectedClassCycle = selectedClassLevel ? cycleById.get(selectedClassLevel.cycle_id) : undefined;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Cycles, niveaux & classes</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Définissez la taxonomie académique utilisée par les filières, les inscriptions et les maquettes.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => void loadData()} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Actualiser
          </Button>
          <Button variant="secondary" onClick={() => setTemplateDialogOpen(true)}>
            <Sparkles className="mr-2 h-4 w-4" />
            Charger le modèle LMD
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Référentiel indisponible</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        <KpiCard title="Cycles" value={cycles.length} icon={School} subtitle="Cycles de diplôme" colorVariant="primary" />
        <KpiCard title="Niveaux" value={levels.length} icon={GraduationCap} subtitle="Niveaux réutilisables" colorVariant="emerald" />
        <KpiCard title="Classes" value={classes.length} icon={BookOpenCheck} subtitle="Classes par filière" colorVariant="amber" />
      </div>

      <Card>
        <CardContent className="p-4 sm:p-6">
          <Tabs defaultValue="classes">
            <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <TabsList>
                <TabsTrigger value="cycles">Cycles</TabsTrigger>
                <TabsTrigger value="levels">Niveaux</TabsTrigger>
                <TabsTrigger value="classes">Classes</TabsTrigger>
              </TabsList>
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" size="sm" onClick={() => openCycleEditor()}>
                  <Plus className="mr-2 h-4 w-4" />Cycle
                </Button>
                <Button variant="outline" size="sm" onClick={() => openLevelEditor()} disabled={cycles.length === 0}>
                  <Plus className="mr-2 h-4 w-4" />Niveau
                </Button>
                <Button size="sm" onClick={() => openClassEditor()} disabled={filieres.length === 0 || levels.length === 0}>
                  <Plus className="mr-2 h-4 w-4" />Classe
                </Button>
              </div>
            </div>

            <TabsContent value="cycles">
              {cycles.length === 0 ? (
                <EmptyState icon={School} title="Aucun cycle configuré" description="Créez un cycle ou chargez explicitement le modèle LMD proposé." />
              ) : (
                <TableFrame loading={loading}>
                  <TableHeader><TableRow><TableHead>Code</TableHead><TableHead>Libellé</TableHead><TableHead>Ordre</TableHead><TableHead>Statut</TableHead><TableHead className="text-right">Actions</TableHead></TableRow></TableHeader>
                  <TableBody>{cycles.map((item) => <TableRow key={item.id}>
                    <TableCell className="font-mono text-xs">{item.code}</TableCell>
                    <TableCell><p className="font-medium">{item.libelle}</p><p className="text-xs text-muted-foreground">{item.description || "Sans description"}</p></TableCell>
                    <TableCell>{item.rang}</TableCell>
                    <TableCell>{statusBadge(item.actif)}</TableCell>
                    <TableCell className="text-right"><RowActions onEdit={() => openCycleEditor(item)} onDelete={() => setDeleteTarget({ kind: "cycle", id: item.id, label: item.libelle })} /></TableCell>
                  </TableRow>)}</TableBody>
                </TableFrame>
              )}
            </TabsContent>

            <TabsContent value="levels">
              {levels.length === 0 ? (
                <EmptyState icon={GraduationCap} title="Aucun niveau configuré" description="Créez les niveaux d'un cycle, par exemple L1, L2 ou M1." />
              ) : (
                <TableFrame loading={loading}>
                  <TableHeader><TableRow><TableHead>Code</TableHead><TableHead>Niveau</TableHead><TableHead>Cycle</TableHead><TableHead>Ordre</TableHead><TableHead>Statut</TableHead><TableHead className="text-right">Actions</TableHead></TableRow></TableHeader>
                  <TableBody>{levels.map((item) => <TableRow key={item.id}>
                    <TableCell className="font-mono text-xs">{item.code}</TableCell>
                    <TableCell className="font-medium">{item.libelle}</TableCell>
                    <TableCell>{cycleById.get(item.cycle_id)?.libelle || "—"}</TableCell>
                    <TableCell>{item.rang}</TableCell>
                    <TableCell>{statusBadge(item.actif)}</TableCell>
                    <TableCell className="text-right"><RowActions onEdit={() => openLevelEditor(item)} onDelete={() => setDeleteTarget({ kind: "level", id: item.id, label: item.libelle })} /></TableCell>
                  </TableRow>)}</TableBody>
                </TableFrame>
              )}
            </TabsContent>

            <TabsContent value="classes" className="space-y-4">
              <div className="grid gap-3 md:grid-cols-2">
                <Select value={classFiliereFilter} onValueChange={setClassFiliereFilter}><SelectTrigger><SelectValue placeholder="Toutes les filières" /></SelectTrigger><SelectContent><SelectItem value="all">Toutes les filières</SelectItem>{filieres.map((item) => <SelectItem key={item.id} value={item.id}>{item.nom}</SelectItem>)}</SelectContent></Select>
                <Select value={classCycleFilter} onValueChange={setClassCycleFilter}><SelectTrigger><SelectValue placeholder="Tous les cycles" /></SelectTrigger><SelectContent><SelectItem value="all">Tous les cycles</SelectItem>{cycles.map((item) => <SelectItem key={item.id} value={item.id}>{item.libelle}</SelectItem>)}</SelectContent></Select>
              </div>
              {classes.length === 0 ? (
                <EmptyState icon={Layers3} title="Aucune classe configurée" description="Une classe combine une filière et un niveau réutilisable, par exemple GL L1." />
              ) : (
                <TableFrame loading={loading}>
                  <TableHeader><TableRow><TableHead>Code</TableHead><TableHead>Classe</TableHead><TableHead>Filière</TableHead><TableHead>Cycle / Niveau</TableHead><TableHead>Statut</TableHead><TableHead className="text-right">Actions</TableHead></TableRow></TableHeader>
                  <TableBody>{filteredClasses.map((item) => {
                    const level = levelById.get(item.niveau_id);
                    const cycle = level ? cycleById.get(level.cycle_id) : undefined;
                    return <TableRow key={item.id}>
                      <TableCell className="font-mono text-xs">{item.code}</TableCell>
                      <TableCell className="font-medium">{item.libelle}</TableCell>
                      <TableCell>{filiereById.get(item.filiere_id)?.nom || "—"}</TableCell>
                      <TableCell><Badge variant="outline">{cycle?.libelle || "Cycle non résolu"}</Badge><span className="ml-2 text-xs text-muted-foreground">{level?.libelle || "Niveau non résolu"}</span></TableCell>
                      <TableCell>{statusBadge(item.actif)}</TableCell>
                      <TableCell className="text-right"><RowActions onEdit={() => openClassEditor(item)} onDelete={() => setDeleteTarget({ kind: "class", id: item.id, label: item.libelle })} /></TableCell>
                    </TableRow>;
                  })}</TableBody>
                </TableFrame>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      <Dialog open={editor === "cycle"} onOpenChange={(open) => !open && closeEditor()}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader><DialogTitle>{editingId ? "Modifier le cycle" : "Créer un cycle"}</DialogTitle><DialogDescription>Un cycle regroupe plusieurs niveaux, par exemple Licence ou Master.</DialogDescription></DialogHeader>
          <form onSubmit={saveCycle} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-[140px_1fr]"><div className="space-y-2"><Label htmlFor="cycle-code">Code *</Label><Input id="cycle-code" value={cycleForm.code} onChange={(event) => setCycleForm({ ...cycleForm, code: event.target.value })} placeholder="LICENCE" required /></div><div className="space-y-2"><Label htmlFor="cycle-label">Libellé *</Label><Input id="cycle-label" value={cycleForm.libelle} onChange={(event) => setCycleForm({ ...cycleForm, libelle: event.target.value })} placeholder="Licence" required /></div></div>
            <div className="space-y-2"><Label htmlFor="cycle-rank">Ordre *</Label><Input id="cycle-rank" type="number" min="1" value={cycleForm.rang} onChange={(event) => setCycleForm({ ...cycleForm, rang: event.target.value })} required /></div>
            <div className="space-y-2"><Label htmlFor="cycle-description">Description</Label><Textarea id="cycle-description" value={cycleForm.description} onChange={(event) => setCycleForm({ ...cycleForm, description: event.target.value })} /></div>
            <div className="flex items-center justify-between rounded-lg border p-3"><div><Label htmlFor="cycle-active">Cycle actif</Label><p className="text-xs text-muted-foreground">Les cycles inactifs ne sont plus proposés aux nouveaux formulaires.</p></div><Switch id="cycle-active" checked={cycleForm.actif} onCheckedChange={(actif) => setCycleForm({ ...cycleForm, actif })} /></div>
            <DialogFooter><Button type="button" variant="outline" onClick={closeEditor}>Annuler</Button><Button type="submit" disabled={saving}>{saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Enregistrer</Button></DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={editor === "level"} onOpenChange={(open) => !open && closeEditor()}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader><DialogTitle>{editingId ? "Modifier le niveau" : "Créer un niveau"}</DialogTitle><DialogDescription>Le niveau appartient à un cycle et reste réutilisable chaque année.</DialogDescription></DialogHeader>
          <form onSubmit={saveLevel} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-[140px_1fr]"><div className="space-y-2"><Label htmlFor="level-code">Code *</Label><Input id="level-code" value={levelForm.code} onChange={(event) => setLevelForm({ ...levelForm, code: event.target.value })} placeholder="L1" required /></div><div className="space-y-2"><Label htmlFor="level-label">Libellé *</Label><Input id="level-label" value={levelForm.libelle} onChange={(event) => setLevelForm({ ...levelForm, libelle: event.target.value })} placeholder="Licence 1" required /></div></div>
            <div className="space-y-2"><Label htmlFor="level-cycle">Cycle *</Label><Select value={levelForm.cycle_id} onValueChange={(cycle_id) => setLevelForm({ ...levelForm, cycle_id })}><SelectTrigger id="level-cycle"><SelectValue placeholder="Sélectionner un cycle" /></SelectTrigger><SelectContent>{cycles.map((item) => <SelectItem key={item.id} value={item.id}>{item.libelle}</SelectItem>)}</SelectContent></Select></div>
            <div className="space-y-2"><Label htmlFor="level-rank">Ordre *</Label><Input id="level-rank" type="number" min="1" value={levelForm.rang} onChange={(event) => setLevelForm({ ...levelForm, rang: event.target.value })} required /></div>
            <div className="flex items-center justify-between rounded-lg border p-3"><div><Label htmlFor="level-active">Niveau actif</Label><p className="text-xs text-muted-foreground">Le niveau reste consultable mais n'est plus proposé si désactivé.</p></div><Switch id="level-active" checked={levelForm.actif} onCheckedChange={(actif) => setLevelForm({ ...levelForm, actif })} /></div>
            <DialogFooter><Button type="button" variant="outline" onClick={closeEditor}>Annuler</Button><Button type="submit" disabled={saving}>{saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Enregistrer</Button></DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={editor === "class"} onOpenChange={(open) => !open && closeEditor()}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader><DialogTitle>{editingId ? "Modifier la classe" : "Créer une classe"}</DialogTitle><DialogDescription>La classe combine une filière et un niveau. Le cycle sera déduit du niveau sélectionné.</DialogDescription></DialogHeader>
          <form onSubmit={saveClass} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2"><Label htmlFor="class-filiere">Filière *</Label><Select value={classForm.filiere_id} onValueChange={(filiere_id) => { const filiere = filiereById.get(filiere_id); const level = levelById.get(classForm.niveau_id); setClassForm({ ...classForm, filiere_id, code: filiere && level ? `${filiere.code}-${level.code}`.toUpperCase() : classForm.code, libelle: filiere && level ? `${filiere.nom} — ${level.libelle}` : classForm.libelle }); }}><SelectTrigger id="class-filiere"><SelectValue placeholder="Sélectionner" /></SelectTrigger><SelectContent>{filieres.map((item) => <SelectItem key={item.id} value={item.id}>{item.nom}</SelectItem>)}</SelectContent></Select></div>
              <div className="space-y-2"><Label htmlFor="class-level">Niveau *</Label><Select value={classForm.niveau_id} onValueChange={(niveau_id) => { const filiere = filiereById.get(classForm.filiere_id); const level = levelById.get(niveau_id); setClassForm({ ...classForm, niveau_id, code: filiere && level ? `${filiere.code}-${level.code}`.toUpperCase() : classForm.code, libelle: filiere && level ? `${filiere.nom} — ${level.libelle}` : classForm.libelle }); }}><SelectTrigger id="class-level"><SelectValue placeholder="Sélectionner" /></SelectTrigger><SelectContent>{levels.filter((item) => item.actif).map((item) => <SelectItem key={item.id} value={item.id}>{cycleById.get(item.cycle_id)?.libelle} — {item.libelle}</SelectItem>)}</SelectContent></Select></div>
            </div>
            {selectedClassCycle && <div className="flex items-center gap-2 rounded-lg border border-primary/20 bg-primary/5 p-3 text-sm"><CheckCircle2 className="h-4 w-4 text-primary" /><span>Cycle déduit : <strong>{selectedClassCycle.libelle}</strong></span></div>}
            <div className="grid gap-4 sm:grid-cols-[180px_1fr]"><div className="space-y-2"><Label htmlFor="class-code">Code généré</Label><Input id="class-code" value={classForm.code} readOnly placeholder="Choisir filière et niveau" /></div><div className="space-y-2"><Label htmlFor="class-label">Libellé *</Label><Input id="class-label" value={classForm.libelle} onChange={(event) => setClassForm({ ...classForm, libelle: event.target.value })} required /></div></div>
            <div className="flex items-center justify-between rounded-lg border p-3"><div><Label htmlFor="class-active">Classe active</Label><p className="text-xs text-muted-foreground">Les classes inactives restent consultables mais ne sont plus proposées aux inscriptions.</p></div><Switch id="class-active" checked={classForm.actif} onCheckedChange={(actif) => setClassForm({ ...classForm, actif })} /></div>
            <DialogFooter><Button type="button" variant="outline" onClick={closeEditor}>Annuler</Button><Button type="submit" disabled={saving}>{saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Enregistrer</Button></DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={templateDialogOpen} onOpenChange={setTemplateDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader><AlertDialogTitle>Charger le modèle LMD recommandé ?</AlertDialogTitle><AlertDialogDescription>L’action créera uniquement les éléments manquants : Licence (L1, L2, L3) et Master (M1, M2). Aucune classe ne sera créée et aucune donnée existante ne sera remplacée.</AlertDialogDescription></AlertDialogHeader>
          <AlertDialogFooter><AlertDialogCancel>Annuler</AlertDialogCancel><AlertDialogAction onClick={() => void loadLmdTemplate()} disabled={templateLoading}>{templateLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Charger le modèle</AlertDialogAction></AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={Boolean(deleteTarget)} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader><AlertDialogTitle>Supprimer « {deleteTarget?.label} » ?</AlertDialogTitle><AlertDialogDescription>La suppression est refusée si des niveaux, classes ou inscriptions dépendent de cet élément. Préférez la désactivation pour conserver l’historique.</AlertDialogDescription></AlertDialogHeader>
          <AlertDialogFooter><AlertDialogCancel>Annuler</AlertDialogCancel><AlertDialogAction onClick={() => void confirmDelete()} disabled={deleteLoading} className="bg-destructive text-destructive-foreground">{deleteLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Supprimer</AlertDialogAction></AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

const TableFrame = ({ loading, children }: { loading: boolean; children: React.ReactNode }) => (
  <div className="overflow-x-auto rounded-lg border">
    <Table>
      {loading ? <TableBody><TableRow><TableCell className="py-12 text-center"><Loader2 className="mx-auto h-5 w-5 animate-spin" /></TableCell></TableRow></TableBody> : children}
    </Table>
  </div>
);

const EmptyState = ({ icon: Icon, title, description }: { icon: React.ElementType; title: string; description: string }) => (
  <div className="rounded-xl border border-dashed bg-muted/20 px-6 py-12 text-center">
    <Icon className="mx-auto h-9 w-9 text-muted-foreground/50" />
    <p className="mt-3 font-semibold text-foreground">{title}</p>
    <p className="mx-auto mt-1 max-w-md text-sm text-muted-foreground">{description}</p>
  </div>
);

const RowActions = ({ onEdit, onDelete }: { onEdit: () => void; onDelete: () => void }) => (
  <div className="flex justify-end gap-1">
    <Button variant="ghost" size="icon" onClick={onEdit} aria-label="Modifier"><Edit3 className="h-4 w-4" /></Button>
    <Button variant="ghost" size="icon" className="text-destructive" onClick={onDelete} aria-label="Supprimer"><Trash2 className="h-4 w-4" /></Button>
  </div>
);

export default AcademicStructure;
