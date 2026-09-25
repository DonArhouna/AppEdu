import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import {
  AlertCircle,
  Bookmark,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  FilePlus2,
  Filter,
  GraduationCap,
  ListChecks,
  Plus,
  RefreshCw,
  Save,
  Search,
  Trash2,
  UserRound,
} from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { academicApi, admissionsApi, extractErrorMessage, sessionsApi, structureApi } from "@/services/apiClient";
import type {
  AcademicClass,
  AcademicCycle,
  AcademicLevel,
  AcademicSession,
  AdmissionView,
  AdmissionViewFilters,
  BulkAdmissionAction,
  Candidature,
  CandidatureCreatePayload,
  CandidatureStatus,
  Filiere,
} from "@/services/apiTypes";

const STATUS_LABELS: Record<CandidatureStatus, string> = {
  nouvelle: "Nouvelle",
  en_verification: "En vérification",
  complete: "Dossier complet",
  acceptee: "Acceptée",
  refusee: "Refusée",
  liste_attente: "Liste d'attente",
  converti: "Convertie",
  annulee: "Annulée",
};

const STATUS_STYLES: Record<CandidatureStatus, string> = {
  nouvelle: "border-blue-200 bg-blue-50 text-blue-700",
  en_verification: "border-amber-200 bg-amber-50 text-amber-700",
  complete: "border-cyan-200 bg-cyan-50 text-cyan-700",
  acceptee: "border-green-200 bg-green-50 text-green-700",
  refusee: "border-red-200 bg-red-50 text-red-700",
  liste_attente: "border-violet-200 bg-violet-50 text-violet-700",
  converti: "border-emerald-200 bg-emerald-50 text-emerald-700",
  annulee: "border-gray-200 bg-gray-50 text-gray-600",
};

const STATUS_OPTIONS: Array<CandidatureStatus | "tous"> = [
  "tous",
  "nouvelle",
  "en_verification",
  "complete",
  "acceptee",
  "refusee",
  "liste_attente",
  "converti",
  "annulee",
];

const createEmptyForm = (sessionId = ""): CandidatureCreatePayload => ({
  nom: "",
  prenom: "",
  sexe: "",
  date_naissance: "",
  email: "",
  telephone: "",
  adresse: "",
  filiere_id: "",
  niveau_id: "",
  classe_id: "",
  niveau: "",
  session_id: sessionId,
  notes: "",
  source: "",
});

const formatDate = (value?: string | null) => {
  if (!value) return "—";
  const date = /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T00:00:00`) : new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString("fr-FR");
};

const statusLabel = (status: CandidatureStatus) => STATUS_LABELS[status] || status;

const StatusBadge = ({ status }: { status: CandidatureStatus }) => (
  <Badge variant="outline" className={STATUS_STYLES[status] || ""}>
    {statusLabel(status)}
  </Badge>
);

const PAGE_SIZE = 20;

const PreInscription = () => {
  const [candidatures, setCandidatures] = useState<Candidature[]>([]);
  const [filieres, setFilieres] = useState<Filiere[]>([]);
  const [classes, setClasses] = useState<AcademicClass[]>([]);
  const [levels, setLevels] = useState<AcademicLevel[]>([]);
  const [cycles, setCycles] = useState<AcademicCycle[]>([]);
  const [sessions, setSessions] = useState<AcademicSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<CandidatureStatus | "tous">("tous");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [statusCounts, setStatusCounts] = useState<Partial<Record<CandidatureStatus, number>>>({});
  const [views, setViews] = useState<AdmissionView[]>([]);
  const [activeViewId, setActiveViewId] = useState("");
  const [viewName, setViewName] = useState("");
  const [viewError, setViewError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [bulkAction, setBulkAction] = useState<BulkAdmissionAction>("mettre_en_verification");
  const [bulkLoading, setBulkLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [form, setForm] = useState<CandidatureCreatePayload>(createEmptyForm());

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    const [candidaturesResult, filieresResult, sessionsResult, classesResult, levelsResult, cyclesResult] = await Promise.all([
      admissionsApi.getAll({
        search: search.trim() || undefined,
        statut: statusFilter === "tous" ? undefined : statusFilter,
        page,
        page_size: PAGE_SIZE,
      }),
      structureApi.getFilieres(),
      sessionsApi.getAll(),
      academicApi.getClasses(),
      academicApi.getLevels(),
      academicApi.getCycles(),
    ]);

    const firstError =
      candidaturesResult.error || filieresResult.error || sessionsResult.error ||
      classesResult.error || levelsResult.error || cyclesResult.error;
    if (firstError) {
      setError(extractErrorMessage(firstError, "Impossible de charger le module d'admissions."));
    }

    // Une réponse réussie reste utilisable même si une ressource de référence
    // est temporairement indisponible; aucune donnée fictive n'est injectée.
    const pageData = candidaturesResult.data;
    setCandidatures(pageData?.items || []);
    setTotal(pageData?.total || 0);
    setTotalPages(pageData?.pages || 0);
    setStatusCounts(pageData?.counts || {});
    setFilieres(filieresResult.data || []);
    setSessions(sessionsResult.data || []);
    setClasses(classesResult.data || []);
    setLevels(levelsResult.data || []);
    setCycles(cyclesResult.data || []);
    setLoading(false);
  }, [page, search, statusFilter]);

  const loadViews = useCallback(async () => {
    const result = await admissionsApi.listViews();
    if (result.error) {
      setViewError(extractErrorMessage(result.error, "Impossible de charger les vues enregistrées."));
      return;
    }
    setViewError(null);
    setViews(result.data || []);
  }, []);

  useEffect(() => {
    void loadViews();
  }, [loadViews]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  useEffect(() => {
    if (form.filiere_id || filieres.length === 0) return;
    setForm((current) => ({ ...current, filiere_id: filieres[0].id }));
  }, [filieres, form.filiere_id]);

  const activeSession = useMemo(
    () => sessions.find((session) => session.statut === "active") || sessions[0],
    [sessions]
  );
  const availableClasses = useMemo(
    () => classes.filter((item) => item.actif && item.filiere_id === form.filiere_id),
    [classes, form.filiere_id]
  );
  const selectedClass = classes.find((item) => item.id === form.classe_id);
  const selectedLevel = levels.find((item) => item.id === selectedClass?.niveau_id);
  const selectedCycle = cycles.find((item) => item.id === selectedLevel?.cycle_id);

  const openCreateDialog = () => {
    setFormError(null);
    setForm(createEmptyForm(activeSession?.id || ""));
    setDialogOpen(true);
  };

  const updateField = (field: keyof CandidatureCreatePayload, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const applyView = (viewId: string) => {
    if (!viewId) {
      setActiveViewId("");
      return;
    }
    const view = views.find((item) => item.id === viewId);
    if (!view) return;
    setActiveViewId(view.id);
    setSearch(view.filtres.search || "");
    setStatusFilter(view.filtres.statut || "tous");
    setPage(1);
  };

  const saveView = async () => {
    if (!viewName.trim()) {
      toast.error("Donnez un nom à la vue enregistrée.");
      return;
    }
    const filtres: AdmissionViewFilters = {
      search: search.trim() || undefined,
      statut: statusFilter === "tous" ? undefined : statusFilter,
    };
    const result = await admissionsApi.createView({ nom: viewName.trim(), filtres });
    if (result.error || !result.data) {
      toast.error(extractErrorMessage(result.error, "La vue n'a pas pu être enregistrée."));
      return;
    }
    setViews((current) => [...current, result.data as AdmissionView].sort((a, b) => a.nom.localeCompare(b.nom)));
    setActiveViewId(result.data.id);
    setViewName("");
    toast.success("Vue d'admissions enregistrée.");
  };

  const deleteView = async (viewId: string) => {
    const result = await admissionsApi.deleteView(viewId);
    if (result.error) {
      toast.error(extractErrorMessage(result.error, "La vue n'a pas pu être supprimée."));
      return;
    }
    setViews((current) => current.filter((view) => view.id !== viewId));
    if (activeViewId === viewId) setActiveViewId("");
    toast.success("Vue supprimée.");
  };

  const toggleSelected = (id: string) => {
    setSelectedIds((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  };

  const togglePageSelection = () => {
    const pageIds = candidatures.map((candidature) => candidature.id);
    const allSelected = pageIds.length > 0 && pageIds.every((id) => selectedIds.includes(id));
    setSelectedIds((current) => allSelected
      ? current.filter((id) => !pageIds.includes(id))
      : Array.from(new Set([...current, ...pageIds])));
  };

  const applyBulkAction = async () => {
    if (selectedIds.length === 0) return;
    setBulkLoading(true);
    const result = await admissionsApi.bulkAction({ ids: selectedIds, action: bulkAction });
    setBulkLoading(false);
    if (result.error) {
      toast.error(extractErrorMessage(result.error, "L'action groupée n'a pas pu être appliquée."));
      return;
    }
    const updatedCount = result.data?.updated_ids.length || 0;
    const errorCount = result.data?.errors.length || 0;
    if (errorCount > 0) {
      toast.warning(`${updatedCount} dossier(s) mis à jour, ${errorCount} en erreur.`);
    } else {
      toast.success(`${updatedCount} dossier(s) mis à jour.`);
    }
    setSelectedIds([]);
    await loadData();
  };

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);

    if (!form.nom.trim() || !form.prenom.trim() || !form.email.trim()) {
      setFormError("Le nom, le prénom et l'email du candidat sont obligatoires.");
      return;
    }
    if (!form.filiere_id) {
      setFormError("La filière visée est obligatoire.");
      return;
    }
    if (availableClasses.length > 0 && !form.classe_id) {
      setFormError("Sélectionnez la classe visée par le candidat.");
      return;
    }
    if (availableClasses.length === 0 && !form.niveau.trim()) {
      setFormError("Le niveau visé est obligatoire jusqu'à ce qu'une classe soit configurée.");
      return;
    }

    const payload: CandidatureCreatePayload = {
      ...form,
      nom: form.nom.trim(),
      prenom: form.prenom.trim(),
      email: form.email.trim(),
      niveau: selectedLevel?.libelle || form.niveau.trim(),
      filiere_id: selectedClass?.filiere_id || form.filiere_id,
      classe_id: selectedClass?.id,
      niveau_id: selectedLevel?.id,
      session_id: form.session_id || undefined,
      sexe: form.sexe || undefined,
      date_naissance: form.date_naissance || undefined,
      telephone: form.telephone || undefined,
      adresse: form.adresse || undefined,
      notes: form.notes || undefined,
      source: form.source || undefined,
    };

    setSaving(true);
    const result = await admissionsApi.create(payload);
    setSaving(false);
    if (result.error || !result.data) {
      const message = extractErrorMessage(result.error, "La candidature n'a pas pu être enregistrée.");
      setFormError(message);
      toast.error(message);
      return;
    }

    toast.success(`Candidature ${result.data.reference} enregistrée.`);
    setDialogOpen(false);
    setForm(createEmptyForm(activeSession?.id || ""));
    await loadData();
  };

  const counts = useMemo(
    () => ({
      total,
      nouvelles: statusCounts.nouvelle || 0,
      verification: statusCounts.en_verification || 0,
      acceptees: statusCounts.acceptee || 0,
    }),
    [statusCounts, total]
  );
  const hasFilters = Boolean(search.trim()) || statusFilter !== "tous";
  const allPageSelected = candidatures.length > 0 && candidatures.every((item) => selectedIds.includes(item.id));

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Pré-inscriptions</h1>
          <p className="mt-1 text-muted-foreground">
            Enregistrez les candidatures et suivez leur parcours d'admission.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => void loadData()} disabled={loading}>
            <RefreshCw className={loading ? "animate-spin" : ""} />
            Actualiser
          </Button>
          <Button onClick={openCreateDialog} disabled={filieres.length === 0}>
            <Plus />
            Nouvelle candidature
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertTitle>Le module n'a pas pu être entièrement chargé</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {filieres.length === 0 && !loading && (
        <Alert>
          <GraduationCap />
          <AlertTitle>Filière non configurée</AlertTitle>
          <AlertDescription>
            Créez d'abord une filière dans la structure académique avant d'enregistrer une candidature.
          </AlertDescription>
        </Alert>
      )}

      {hasFilters && (
        <p className="text-xs text-muted-foreground">Les indicateurs ci-dessous correspondent aux résultats filtrés.</p>
      )}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          title={hasFilters ? "Total filtré" : "Total candidatures"}
          value={counts.total}
          icon={UserRound}
          subtitle="Dossiers correspondant aux critères"
          colorVariant="primary"
        />
        <KpiCard
          title="Nouvelles"
          value={counts.nouvelles}
          icon={FilePlus2}
          subtitle="Dossiers à instruire"
          colorVariant="sky"
        />
        <KpiCard
          title="En vérification"
          value={counts.verification}
          icon={Filter}
          subtitle="Dossiers en cours de traitement"
          colorVariant="amber"
        />
        <KpiCard
          title="Acceptées"
          value={counts.acceptees}
          icon={CheckCircle2}
          subtitle="Dossiers validés"
          colorVariant="emerald"
        />
      </div>

      <Card>
        <CardHeader className="gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <CardTitle>Registre des candidatures</CardTitle>
            <CardDescription>
              Les données proviennent de l'API et sont filtrées côté serveur.
            </CardDescription>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative sm:w-72">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
                  setActiveViewId("");
                  setPage(1);
                }}
                placeholder="Nom, email ou référence"
                className="pl-9"
                aria-label="Rechercher une candidature"
              />
            </div>
            <Select value={statusFilter} onValueChange={(value) => {
              setStatusFilter(value as CandidatureStatus | "tous");
              setActiveViewId("");
              setPage(1);
            }}>
              <SelectTrigger className="sm:w-52" aria-label="Filtrer par statut">
                <SelectValue placeholder="Tous les statuts" />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map((status) => (
                  <SelectItem key={status} value={status}>
                    {status === "tous" ? "Tous les statuts" : STATUS_LABELS[status]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex w-full flex-col gap-2 border-t pt-3 sm:flex-row sm:items-center">
            <Select value={activeViewId || "none"} onValueChange={applyView}>
              <SelectTrigger className="sm:w-56" aria-label="Appliquer une vue enregistrée">
                <SelectValue placeholder="Vue enregistrée" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">Vue personnalisée</SelectItem>
                {views.map((view) => <SelectItem key={view.id} value={view.id}>{view.nom}</SelectItem>)}
              </SelectContent>
            </Select>
            <Input
              value={viewName}
              onChange={(event) => setViewName(event.target.value)}
              placeholder="Nom de la vue"
              className="sm:w-48"
              aria-label="Nom de la vue enregistrée"
            />
            <Button type="button" variant="outline" size="sm" onClick={() => void saveView()}>
              <Save /> Enregistrer la vue
            </Button>
            {activeViewId && (
              <Button type="button" variant="ghost" size="sm" onClick={() => void deleteView(activeViewId)} aria-label="Supprimer la vue sélectionnée">
                <Trash2 />
              </Button>
            )}
          </div>
          {viewError && <p className="text-xs text-destructive">{viewError}</p>}
        </CardHeader>
        <CardContent>
          {selectedIds.length > 0 && (
            <div className="mb-4 flex flex-col gap-3 rounded-lg border border-primary/20 bg-primary/5 p-3 sm:flex-row sm:items-center">
              <div className="flex items-center gap-2 text-sm font-medium">
                <ListChecks className="h-4 w-4 text-primary" />
                {selectedIds.length} sélectionné(s)
              </div>
              <Select value={bulkAction} onValueChange={(value) => setBulkAction(value as BulkAdmissionAction)}>
                <SelectTrigger className="sm:w-56" aria-label="Action groupée">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="mettre_en_verification">Mettre en vérification</SelectItem>
                  <SelectItem value="marquer_complete">Marquer complet</SelectItem>
                  <SelectItem value="annuler">Annuler le dossier</SelectItem>
                </SelectContent>
              </Select>
              <Button size="sm" onClick={() => void applyBulkAction()} disabled={bulkLoading}>
                {bulkLoading ? <RefreshCw className="animate-spin" /> : <ListChecks />}
                Appliquer
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setSelectedIds([])} disabled={bulkLoading}>
                Annuler la sélection
              </Button>
            </div>
          )}
          {loading ? (
            <div className="flex min-h-48 items-center justify-center gap-2 text-sm text-muted-foreground">
              <RefreshCw className="h-5 w-5 animate-spin" /> Chargement des candidatures...
            </div>
          ) : candidatures.length === 0 ? (
            <div className="flex min-h-48 flex-col items-center justify-center gap-3 text-center">
              <div className="rounded-full bg-muted p-4 text-muted-foreground"><FilePlus2 className="h-7 w-7" /></div>
              <div>
                <p className="font-medium">Aucune candidature pour ces critères</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Enregistrez une première candidature pour lancer le circuit d'admission.
                </p>
              </div>
              <Button onClick={openCreateDialog} disabled={filieres.length === 0}>
                <Plus /> Enregistrer une candidature
              </Button>
            </div>
          ) : (
            <div className="rounded-xl border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-10">
                      <input
                        type="checkbox"
                        checked={allPageSelected}
                        onChange={togglePageSelection}
                        disabled={loading || candidatures.length === 0}
                        aria-label="Sélectionner toute la page"
                      />
                    </TableHead>
                    <TableHead>Candidat</TableHead>
                    <TableHead>Référence</TableHead>
                    <TableHead>Formation visée</TableHead>
                    <TableHead>Session</TableHead>
                    <TableHead>Déposée le</TableHead>
                    <TableHead>Statut</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {candidatures.map((candidature) => (
                    <TableRow key={candidature.id}>
                      <TableCell>
                        <input
                          type="checkbox"
                          checked={selectedIds.includes(candidature.id)}
                          onChange={() => toggleSelected(candidature.id)}
                          aria-label={`Sélectionner ${candidature.prenom} ${candidature.nom}`}
                        />
                      </TableCell>
                      <TableCell>
                        <div className="font-medium">{candidature.prenom} {candidature.nom}</div>
                        <div className="text-xs text-muted-foreground">{candidature.email}</div>
                      </TableCell>
                      <TableCell className="font-mono text-xs">{candidature.reference}</TableCell>
                      <TableCell>
                        <div className="font-medium">{candidature.filiere?.nom || "—"}</div>
                        <div className="text-xs text-muted-foreground">{candidature.niveau}</div>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {candidature.session?.code || "—"}
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-sm text-muted-foreground">
                        {formatDate(candidature.date_demande)}
                      </TableCell>
                      <TableCell><StatusBadge status={candidature.statut} /></TableCell>
                      <TableCell className="text-right">
                        <Button asChild variant="outline" size="sm">
                          <Link to={`/validation?candidature=${encodeURIComponent(candidature.id)}`}>
                            Traiter
                          </Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-between gap-3 border-t pt-4">
              <p className="text-sm text-muted-foreground">
                Page {page} sur {totalPages} · {total} résultat(s)
              </p>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => setPage((current) => Math.max(1, current - 1))} disabled={page <= 1 || loading}>
                  <ChevronLeft /> Précédent
                </Button>
                <Button variant="outline" size="sm" onClick={() => setPage((current) => Math.min(totalPages, current + 1))} disabled={page >= totalPages || loading}>
                  Suivant <ChevronRight />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Nouvelle candidature</DialogTitle>
            <DialogDescription>
              Les informations seront persistées dans le registre des admissions. Les pièces pourront ensuite être déposées depuis l'écran de validation.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-5">
            {formError && (
              <Alert variant="destructive">
                <AlertCircle />
                <AlertTitle>Enregistrement impossible</AlertTitle>
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            )}
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="candidature-nom">Nom</Label>
                <Input id="candidature-nom" value={form.nom} onChange={(event) => updateField("nom", event.target.value)} required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="candidature-prenom">Prénom</Label>
                <Input id="candidature-prenom" value={form.prenom} onChange={(event) => updateField("prenom", event.target.value)} required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="candidature-email">Email</Label>
                <Input id="candidature-email" type="email" value={form.email} onChange={(event) => updateField("email", event.target.value)} required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="candidature-telephone">Téléphone</Label>
                <Input id="candidature-telephone" value={form.telephone} onChange={(event) => updateField("telephone", event.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="candidature-filière">Filière</Label>
                <Select value={form.filiere_id} onValueChange={(value) => setForm((current) => ({ ...current, filiere_id: value, classe_id: "", niveau_id: "", niveau: "" }))}>
                  <SelectTrigger id="candidature-filière"><SelectValue placeholder="Sélectionner une filière" /></SelectTrigger>
                  <SelectContent>
                    {filieres.map((filiere) => (
                      <SelectItem key={filiere.id} value={filiere.id}>{filiere.nom} ({filiere.code})</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="candidature-classe">Classe / Niveau</Label>
                {availableClasses.length > 0 ? (
                  <Select
                    value={form.classe_id || undefined}
                    onValueChange={(value) => {
                      const selected = classes.find((item) => item.id === value);
                      const level = levels.find((item) => item.id === selected?.niveau_id);
                      setForm((current) => ({
                        ...current,
                        classe_id: value,
                        filiere_id: selected?.filiere_id || current.filiere_id,
                        niveau_id: level?.id,
                        niveau: level?.libelle || "",
                      }));
                    }}
                  >
                    <SelectTrigger id="candidature-classe"><SelectValue placeholder="Sélectionner une classe" /></SelectTrigger>
                    <SelectContent>
                      {availableClasses.map((item) => (
                        <SelectItem key={item.id} value={item.id}>{item.code} — {item.libelle}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <Input id="candidature-classe" value={form.niveau} placeholder="Licence 1" onChange={(event) => updateField("niveau", event.target.value)} required />
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="candidature-session">Session cible</Label>
                <Select value={form.session_id || "aucune"} onValueChange={(value) => updateField("session_id", value === "aucune" ? "" : value)}>
                  <SelectTrigger id="candidature-session"><SelectValue placeholder="Sélectionner une session" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="aucune">Aucune session pour l'instant</SelectItem>
                    {sessions.map((session) => (
                      <SelectItem key={session.id} value={session.id}>{session.code} · {session.annee_academique}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="candidature-naissance">Date de naissance</Label>
                <Input id="candidature-naissance" type="date" value={form.date_naissance} onChange={(event) => updateField("date_naissance", event.target.value)} />
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="candidature-adresse">Adresse</Label>
                <Input id="candidature-adresse" value={form.adresse} onChange={(event) => updateField("adresse", event.target.value)} />
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="candidature-notes">Notes internes</Label>
                <Textarea id="candidature-notes" value={form.notes} onChange={(event) => updateField("notes", event.target.value)} placeholder="Informations visibles uniquement par le personnel autorisé" />
              </div>
            </div>
            {selectedClass && (
              <div className="flex flex-wrap items-center gap-2 rounded-lg border border-primary/20 bg-primary/5 p-3 text-sm">
                <Badge variant="outline">{selectedCycle?.libelle || "Cycle non résolu"}</Badge>
                <span className="text-muted-foreground">Niveau :</span>
                <strong>{selectedLevel?.libelle || "Niveau non résolu"}</strong>
              </div>
            )}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)} disabled={saving}>Annuler</Button>
              <Button type="submit" disabled={saving || filieres.length === 0}>
                {saving ? <RefreshCw className="animate-spin" /> : <FilePlus2 />}
                Enregistrer la candidature
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default PreInscription;
