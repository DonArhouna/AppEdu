import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  Download,
  FileCheck2,
  FileText,
  Filter,
  History,
  LoaderCircle,
  RefreshCw,
  Search,
  Upload,
  UserCheck,
} from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
import { admissionsApi, extractErrorMessage } from "@/services/apiClient";
import type {
  AdmissionDecision,
  AdmissionDecisionType,
  AdmissionDocument,
  AdmissionDocumentStatus,
  Candidature,
  CandidatureStatus,
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

const DOCUMENT_LABELS: Record<AdmissionDocumentStatus, string> = {
  requise: "Requise",
  recue: "Reçue",
  validee: "Validée",
  rejetee: "Rejetée",
};

const DOCUMENT_STYLES: Record<AdmissionDocumentStatus, string> = {
  requise: "border-gray-200 bg-gray-50 text-gray-600",
  recue: "border-blue-200 bg-blue-50 text-blue-700",
  validee: "border-green-200 bg-green-50 text-green-700",
  rejetee: "border-red-200 bg-red-50 text-red-700",
};

const STATUS_OPTIONS: Array<CandidatureStatus | "tous"> = [
  "tous",
  "nouvelle",
  "en_verification",
  "complete",
  "liste_attente",
  "acceptee",
  "refusee",
  "converti",
  "annulee",
];

const formatDate = (value?: string | null) => {
  if (!value) return "—";
  const date = /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T00:00:00`) : new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString("fr-FR");
};

const formatDateTime = (value?: string | null) => {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("fr-FR");
};

const statusLabel = (status: CandidatureStatus) => STATUS_LABELS[status] || status;

const StatusBadge = ({ status }: { status: CandidatureStatus }) => (
  <Badge variant="outline" className={STATUS_STYLES[status] || ""}>
    {statusLabel(status)}
  </Badge>
);

const DocumentBadge = ({ status }: { status: AdmissionDocumentStatus }) => (
  <Badge variant="outline" className={DOCUMENT_STYLES[status] || ""}>
    {DOCUMENT_LABELS[status] || status}
  </Badge>
);

const DecisionBadge = ({ decision }: { decision: AdmissionDecisionType }) => {
  const labels: Record<AdmissionDecisionType, string> = {
    acceptee: "Acceptée",
    refusee: "Refusée",
    liste_attente: "Liste d'attente",
  };
  return <Badge variant="outline">{labels[decision]}</Badge>;
};

const PAGE_SIZE = 20;

const Validation = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialCandidatureId = searchParams.get("candidature") || "";
  const [candidatures, setCandidatures] = useState<Candidature[]>([]);
  const [selectedId, setSelectedId] = useState(initialCandidatureId);
  const [selected, setSelected] = useState<Candidature | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<CandidatureStatus | "tous">("tous");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [conversionDialogOpen, setConversionDialogOpen] = useState(false);

  const [documentType, setDocumentType] = useState("");
  const [documentFilename, setDocumentFilename] = useState("");
  const [documentFile, setDocumentFile] = useState<File | null>(null);
  const [documentComment, setDocumentComment] = useState("");
  const [decision, setDecision] = useState<AdmissionDecisionType>("acceptee");
  const [decisionMotif, setDecisionMotif] = useState("");

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setError(null);
    const result = await admissionsApi.getAll({
      search: search.trim() || undefined,
      statut: statusFilter === "tous" ? undefined : statusFilter,
      page,
      page_size: PAGE_SIZE,
    });
    if (result.error) {
      setError(extractErrorMessage(result.error, "Impossible de charger la file des dossiers."));
    } else {
      setCandidatures(result.data?.items || []);
      setTotal(result.data?.total || 0);
      setTotalPages(result.data?.pages || 0);
    }
    setLoading(false);
  }, [page, search, statusFilter]);

  const loadDetail = useCallback(async (id: string) => {
    if (!id) {
      setSelected(null);
      return;
    }
    setDetailLoading(true);
    setDetailError(null);
    const result = await admissionsApi.getById(id);
    if (result.error || !result.data) {
      setSelected(null);
      setDetailError(extractErrorMessage(result.error, "Impossible de charger le dossier."));
    } else {
      setSelected(result.data);
    }
    setDetailLoading(false);
  }, []);

  useEffect(() => {
    void loadQueue();
  }, [loadQueue]);

  useEffect(() => {
    if (initialCandidatureId && initialCandidatureId !== selectedId) {
      setSelectedId(initialCandidatureId);
    }
  }, [initialCandidatureId, selectedId]);

  useEffect(() => {
    void loadDetail(selectedId);
  }, [loadDetail, selectedId]);

  const selectCandidature = (id: string) => {
    setSelectedId(id);
    setSearchParams({ candidature: id });
  };

  const refreshAll = async () => {
    await loadQueue();
    if (selectedId) await loadDetail(selectedId);
  };

  const handleStatusAction = async () => {
    if (!selected) return;
    const nextStatus: CandidatureStatus | undefined =
      selected.statut === "nouvelle"
        ? "en_verification"
        : selected.statut === "en_verification"
          ? "complete"
          : selected.statut === "complete" || selected.statut === "liste_attente"
            ? "en_verification"
            : undefined;
    if (!nextStatus) return;

    setBusyAction("status");
    const result = await admissionsApi.updateStatus(selected.id, nextStatus);
    setBusyAction(null);
    if (result.error) {
      toast.error(extractErrorMessage(result.error, "Le statut n'a pas pu être mis à jour."));
      return;
    }
    toast.success("Statut du dossier mis à jour.");
    await refreshAll();
  };

  const handleAddDocument = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selected) return;
    if (!documentType.trim()) {
      toast.error("Le type de pièce est obligatoire.");
      return;
    }
    setBusyAction("add-document");
    const result = await admissionsApi.addDocument(selected.id, {
      type: documentType.trim(),
      nom_fichier: documentFilename.trim() || undefined,
      commentaire: documentComment.trim() || undefined,
    });
    if (result.error || !result.data) {
      setBusyAction(null);
      toast.error(extractErrorMessage(result.error, "La pièce n'a pas pu être ajoutée."));
      return;
    }

    let uploaded = false;
    if (documentFile) {
      const uploadResult = await admissionsApi.uploadDocument(result.data.id, documentFile);
      if (uploadResult.error) {
        setBusyAction(null);
        toast.error(
          `La pièce a été créée, mais le fichier n'a pas pu être déposé : ${extractErrorMessage(uploadResult.error)}`
        );
        await refreshAll();
        return;
      }
      uploaded = true;
    }
    setBusyAction(null);
    setDocumentType("");
    setDocumentFilename("");
    setDocumentFile(null);
    setDocumentComment("");
    toast.success(uploaded ? "Pièce et fichier enregistrés." : "Pièce ajoutée au dossier.");
    await refreshAll();
  };

  const handleUploadDocument = async (document: AdmissionDocument, file: File | null) => {
    if (!file) return;
    setBusyAction(`upload-${document.id}`);
    const result = await admissionsApi.uploadDocument(document.id, file);
    setBusyAction(null);
    if (result.error) {
      toast.error(extractErrorMessage(result.error, "Le fichier n'a pas pu être déposé."));
      return;
    }
    toast.success("Fichier déposé et enregistré.");
    await refreshAll();
  };

  const handleDownloadDocument = async (document: AdmissionDocument) => {
    setBusyAction(`download-${document.id}`);
    const result = await admissionsApi.downloadDocument(document.id);
    setBusyAction(null);
    if (result.error || !result.data) {
      toast.error(extractErrorMessage(result.error, "Le fichier n'a pas pu être téléchargé."));
      return;
    }
    const url = URL.createObjectURL(result.data);
    const link = window.document.createElement("a");
    const safeName = (document.nom_fichier || `${document.type}.bin`).replace(/[\\/:*?"<>|]/g, "_");
    link.href = url;
    link.download = safeName;
    window.document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const handleDocumentStatus = async (document: AdmissionDocument, value: string) => {
    setBusyAction(`document-${document.id}`);
    const result = await admissionsApi.updateDocument(document.id, {
      statut: value as AdmissionDocumentStatus,
    });
    setBusyAction(null);
    if (result.error) {
      toast.error(extractErrorMessage(result.error, "Le statut de la pièce n'a pas pu être mis à jour."));
      return;
    }
    toast.success("Statut de la pièce mis à jour.");
    await refreshAll();
  };

  const handleDecision = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selected) return;
    setBusyAction("decision");
    const result = await admissionsApi.decide(selected.id, {
      decision,
      motif: decisionMotif.trim() || undefined,
    });
    setBusyAction(null);
    if (result.error) {
      toast.error(extractErrorMessage(result.error, "La décision n'a pas pu être enregistrée."));
      return;
    }
    setDecisionMotif("");
    toast.success("Décision d'admission enregistrée.");
    await refreshAll();
  };

  const handleConversion = async () => {
    if (!selected) return;
    setBusyAction("convert");
    const result = await admissionsApi.convert(selected.id);
    setBusyAction(null);
    if (result.error) {
      toast.error(extractErrorMessage(result.error, "La conversion n'a pas pu être effectuée."));
      return;
    }
    toast.success(`Dossier étudiant créé : ${result.data?.etudiant.matricule || "matricule généré"}.`);
    await refreshAll();
  };

  const selectedPieces = useMemo(() => selected?.pieces || [], [selected]);
  const canProgress = selected
    ? ["nouvelle", "en_verification", "complete", "liste_attente"].includes(selected.statut)
    : false;
  const canDecide = selected
    ? ["en_verification", "complete", "liste_attente"].includes(selected.statut)
    : false;
  const canConvert = selected?.statut === "acceptee" && !selected.etudiant_id;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="mb-2 flex items-center gap-2 text-sm text-muted-foreground">
            <Link to="/pre-inscription" className="inline-flex items-center gap-1 hover:text-primary">
              <ArrowLeft className="h-4 w-4" /> Pré-inscriptions
            </Link>
          </div>
          <h1 className="text-3xl font-bold text-foreground">Validation des dossiers</h1>
          <p className="mt-1 text-muted-foreground">
            Vérifiez les pièces, enregistrez une décision et convertissez les dossiers acceptés.
          </p>
        </div>
        <Button variant="outline" onClick={() => void refreshAll()} disabled={loading || detailLoading}>
          <RefreshCw className={loading || detailLoading ? "animate-spin" : ""} />
          Actualiser
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertTitle>File des dossiers indisponible</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(420px,0.95fr)]">
        <Card className="min-w-0">
          <CardHeader className="gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <CardTitle>File de traitement</CardTitle>
              <CardDescription>Sélectionnez un dossier pour consulter son circuit.</CardDescription>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              <div className="relative sm:w-64">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={search}
                  onChange={(event) => {
                    setSearch(event.target.value);
                    setPage(1);
                  }}
                  placeholder="Rechercher"
                  className="pl-9"
                  aria-label="Rechercher un dossier"
                />
              </div>
              <Select value={statusFilter} onValueChange={(value) => {
                setStatusFilter(value as CandidatureStatus | "tous");
                setPage(1);
              }}>
                <SelectTrigger className="sm:w-48" aria-label="Filtrer les dossiers par statut">
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
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex min-h-56 items-center justify-center gap-2 text-sm text-muted-foreground">
                <LoaderCircle className="h-5 w-5 animate-spin" /> Chargement de la file...
              </div>
            ) : candidatures.length === 0 ? (
              <div className="flex min-h-56 flex-col items-center justify-center gap-3 text-center">
                <div className="rounded-full bg-muted p-4 text-muted-foreground"><ClipboardCheck className="h-7 w-7" /></div>
                <div>
                  <p className="font-medium">Aucun dossier à afficher</p>
                  <p className="mt-1 text-sm text-muted-foreground">Les candidatures correspondant aux filtres apparaîtront ici.</p>
                </div>
              </div>
            ) : (
              <div className="rounded-xl border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Candidat</TableHead>
                      <TableHead>Formation</TableHead>
                      <TableHead>Pièces</TableHead>
                      <TableHead>Statut</TableHead>
                      <TableHead className="text-right">Ouvrir</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {candidatures.map((candidature) => (
                      <TableRow key={candidature.id} data-state={candidature.id === selectedId ? "selected" : undefined} className={candidature.id === selectedId ? "bg-muted/70" : undefined}>
                        <TableCell>
                          <div className="font-medium">{candidature.prenom} {candidature.nom}</div>
                          <div className="text-xs text-muted-foreground">{candidature.reference}</div>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm font-medium">{candidature.filiere?.nom || "—"}</div>
                          <div className="text-xs text-muted-foreground">{candidature.niveau}</div>
                        </TableCell>
                        <TableCell>
                          <span className="inline-flex items-center gap-1 text-sm text-muted-foreground">
                            <FileText className="h-4 w-4" /> {candidature.pieces?.length || 0}
                          </span>
                        </TableCell>
                        <TableCell><StatusBadge status={candidature.statut} /></TableCell>
                        <TableCell className="text-right">
                          <Button variant={candidature.id === selectedId ? "default" : "outline"} size="sm" onClick={() => selectCandidature(candidature.id)}>
                            Consulter
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
                  Page {page} sur {totalPages} · {total} dossier(s)
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

        <Card className="min-w-0">
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle className="flex items-center gap-2"><UserCheck className="h-5 w-5 text-primary" /> Dossier sélectionné</CardTitle>
                <CardDescription>Consultation et actions autorisées du personnel d'admissions.</CardDescription>
              </div>
              {selected && <StatusBadge status={selected.statut} />}
            </div>
          </CardHeader>
          <CardContent>
            {detailLoading ? (
              <div className="flex min-h-72 items-center justify-center gap-2 text-sm text-muted-foreground">
                <LoaderCircle className="h-5 w-5 animate-spin" /> Chargement du dossier...
              </div>
            ) : detailError ? (
              <Alert variant="destructive">
                <AlertCircle />
                <AlertTitle>Dossier indisponible</AlertTitle>
                <AlertDescription>{detailError}</AlertDescription>
              </Alert>
            ) : !selected ? (
              <div className="flex min-h-72 flex-col items-center justify-center gap-3 text-center">
                <div className="rounded-full bg-muted p-4 text-muted-foreground"><ClipboardCheck className="h-7 w-7" /></div>
                <p className="font-medium">Sélectionnez une candidature</p>
                <p className="max-w-sm text-sm text-muted-foreground">Choisissez une ligne dans la file pour afficher les coordonnées, pièces et décisions.</p>
              </div>
            ) : (
              <div className="space-y-6">
                <div className="rounded-xl border bg-muted/30 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-mono text-xs text-muted-foreground">{selected.reference}</p>
                      <h2 className="mt-1 text-xl font-semibold">{selected.prenom} {selected.nom}</h2>
                      <p className="text-sm text-muted-foreground">{selected.email}</p>
                    </div>
                    {selected.etudiant_id && <Badge variant="secondary">Dossier étudiant lié</Badge>}
                  </div>
                  <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                    <div><dt className="text-muted-foreground">Filière</dt><dd className="font-medium">{selected.filiere?.nom || "—"}</dd></div>
                    <div><dt className="text-muted-foreground">Niveau</dt><dd className="font-medium">{selected.niveau}</dd></div>
                    <div><dt className="text-muted-foreground">Session cible</dt><dd className="font-medium">{selected.session?.code || "Non définie"}</dd></div>
                    <div><dt className="text-muted-foreground">Date de demande</dt><dd className="font-medium">{formatDate(selected.date_demande)}</dd></div>
                    <div><dt className="text-muted-foreground">Téléphone</dt><dd className="font-medium">{selected.telephone || "—"}</dd></div>
                    <div><dt className="text-muted-foreground">Adresse</dt><dd className="font-medium">{selected.adresse || "—"}</dd></div>
                  </dl>
                </div>

                {canProgress && (
                  <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-primary/20 bg-primary/5 p-3">
                    <div className="flex items-center gap-2 text-sm">
                      <Filter className="h-4 w-4 text-primary" />
                      <span>Prochaine étape du circuit : <strong>{selected.statut === "nouvelle" ? "mettre en vérification" : selected.statut === "en_verification" ? "marquer le dossier complet" : "réexaminer le dossier"}</strong></span>
                    </div>
                    <Button size="sm" onClick={() => void handleStatusAction()} disabled={busyAction !== null}>
                      {busyAction === "status" ? <LoaderCircle className="animate-spin" /> : <CheckCircle2 />}
                      Mettre à jour
                    </Button>
                  </div>
                )}

                <section aria-labelledby="pieces-title" className="space-y-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <h3 id="pieces-title" className="flex items-center gap-2 font-semibold"><FileCheck2 className="h-4 w-4 text-primary" /> Pièces justificatives</h3>
                      <p className="text-xs text-muted-foreground">Les métadonnées, validations et fichiers éventuels sont enregistrés dans le dossier.</p>
                    </div>
                    <Badge variant="outline">{selectedPieces.length} pièce(s)</Badge>
                  </div>
                  {selectedPieces.length === 0 ? (
                    <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">Aucune pièce enregistrée pour ce dossier.</div>
                  ) : (
                    <div className="space-y-2">
                      {selectedPieces.map((document) => (
                        <div key={document.id} className="flex flex-col gap-3 rounded-lg border p-3 sm:flex-row sm:items-center sm:justify-between">
                          <div className="min-w-0">
                            <p className="truncate text-sm font-medium">{document.type}</p>
                            <p className="truncate text-xs text-muted-foreground">{document.fichier_disponible ? (document.nom_fichier || "Fichier stocké") : "Aucun fichier joint"}</p>
                            {document.commentaire && <p className="mt-1 text-xs text-muted-foreground">{document.commentaire}</p>}
                          </div>
                          <div className="flex items-center gap-2">
                            <Select
                              value={document.statut}
                              onValueChange={(value) => void handleDocumentStatus(document, value)}
                              disabled={busyAction !== null || ["converti", "annulee"].includes(selected.statut)}
                            >
                              <SelectTrigger className="w-36" aria-label={`Statut de ${document.type}`}><SelectValue /></SelectTrigger>
                              <SelectContent>
                                {Object.entries(DOCUMENT_LABELS).map(([value, label]) => (
                                  <SelectItem key={value} value={value}>{label}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                            <DocumentBadge status={document.statut} />
                             {document.fichier_disponible && (
                               <Button
                                 type="button"
                                 variant="outline"
                                 size="sm"
                                 onClick={() => void handleDownloadDocument(document)}
                                 disabled={busyAction !== null}
                                 aria-label={`Télécharger ${document.nom_fichier || document.type}`}
                               >
                                 {busyAction === `download-${document.id}` ? <LoaderCircle className="animate-spin" /> : <Download />}
                                 Télécharger
                               </Button>
                             )}
                             <label className="inline-flex h-9 cursor-pointer items-center gap-1 rounded-md border border-input bg-background px-3 text-xs font-medium hover:bg-accent focus-within:ring-2 focus-within:ring-ring">
                               {busyAction === `upload-${document.id}` ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : <Upload className="h-3.5 w-3.5" />}
                               {document.fichier_disponible ? "Remplacer" : "Joindre"}
                               <input
                                 type="file"
                                 className="sr-only"
                                 accept=".pdf,.jpg,.jpeg,.png,.webp,.doc,.docx"
                                 disabled={busyAction !== null || ["converti", "annulee"].includes(selected.statut)}
                                 onChange={(event) => {
                                   void handleUploadDocument(document, event.target.files?.[0] || null);
                                   event.currentTarget.value = "";
                                 }}
                                 aria-label={`Choisir un fichier pour ${document.type}`}
                               />
                             </label>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  <form onSubmit={handleAddDocument} className="rounded-lg border bg-muted/20 p-3">
                    <p className="mb-3 text-xs text-muted-foreground">
                      Le fichier sera conservé dans le stockage local du projet, hors base de données. Formats acceptés : PDF, JPG, PNG, WEBP, DOC et DOCX (limite configurée côté serveur).
                    </p>
                    <div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto]">
                      <div className="space-y-1">
                        <Label htmlFor="document-type">Type de pièce</Label>
                        <Input id="document-type" value={documentType} onChange={(event) => setDocumentType(event.target.value)} placeholder="Diplôme, acte de naissance..." />
                      </div>
                      <div className="space-y-1">
                        <Label htmlFor="document-filename">Nom du fichier</Label>
                        <Input id="document-filename" value={documentFilename} onChange={(event) => setDocumentFilename(event.target.value)} placeholder="diplome.pdf" />
                       </div>
                       <div className="space-y-1 sm:col-span-2">
                         <Label htmlFor="document-file">Fichier joint</Label>
                         <Input
                           id="document-file"
                           type="file"
                           accept=".pdf,.jpg,.jpeg,.png,.webp,.doc,.docx"
                           disabled={busyAction !== null || ["converti", "annulee"].includes(selected.statut)}
                           onChange={(event) => {
                             const file = event.target.files?.[0] || null;
                             setDocumentFile(file);
                             if (file) setDocumentFilename(file.name);
                           }}
                         />
                       </div>
                      <Button type="submit" className="self-end" disabled={busyAction !== null || ["converti", "annulee"].includes(selected.statut)}>
                        {busyAction === "add-document" ? <LoaderCircle className="animate-spin" /> : <FileText />}
                        Ajouter
                      </Button>
                    </div>
                    <div className="mt-3 space-y-1">
                      <Label htmlFor="document-comment">Commentaire</Label>
                      <Input id="document-comment" value={documentComment} onChange={(event) => setDocumentComment(event.target.value)} placeholder="Précision pour le personnel" />
                    </div>
                  </form>
                </section>

                {canDecide && (
                  <section aria-labelledby="decision-title" className="space-y-3 rounded-lg border border-primary/20 p-4">
                    <div>
                      <h3 id="decision-title" className="flex items-center gap-2 font-semibold"><ClipboardCheck className="h-4 w-4 text-primary" /> Décision d'admission</h3>
                      <p className="mt-1 text-xs text-muted-foreground">La décision est historisée avec son auteur et sa date. L'acceptation exige que les pièces présentes soient reçues ou validées.</p>
                    </div>
                    <form onSubmit={handleDecision} className="grid gap-3 sm:grid-cols-[180px_1fr_auto] sm:items-end">
                      <div className="space-y-1">
                        <Label htmlFor="decision-type">Décision</Label>
                        <Select value={decision} onValueChange={(value) => setDecision(value as AdmissionDecisionType)}>
                          <SelectTrigger id="decision-type"><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="acceptee">Accepter</SelectItem>
                            <SelectItem value="liste_attente">Liste d'attente</SelectItem>
                            <SelectItem value="refusee">Refuser</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-1">
                        <Label htmlFor="decision-motif">Motif / observations</Label>
                        <Input id="decision-motif" value={decisionMotif} onChange={(event) => setDecisionMotif(event.target.value)} placeholder="Dossier complet, éléments manquants..." />
                      </div>
                      <Button type="submit" disabled={busyAction !== null}>
                        {busyAction === "decision" ? <LoaderCircle className="animate-spin" /> : <ClipboardCheck />}
                        Enregistrer
                      </Button>
                    </form>
                  </section>
                )}

                {canConvert && (
                  <section className="rounded-lg border border-green-200 bg-green-50 p-4" aria-labelledby="convert-title">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <h3 id="convert-title" className="flex items-center gap-2 font-semibold text-green-800"><UserCheck className="h-4 w-4" /> Convertir en dossier étudiant</h3>
                        <p className="mt-1 text-sm text-green-800/80">La conversion créera un dossier étudiant sans créer de compte ni définir de mot de passe.</p>
                      </div>
                      <Button onClick={() => setConversionDialogOpen(true)} disabled={busyAction !== null}>
                        {busyAction === "convert" ? <LoaderCircle className="animate-spin" /> : <UserCheck />}
                        Convertir
                      </Button>
                    </div>
                  </section>
                )}

                {selected.etudiant_id && (
                  <Alert>
                    <CheckCircle2 />
                    <AlertTitle>Dossier déjà converti</AlertTitle>
                    <AlertDescription>Ce dossier étudiant est lié à la candidature. Aucun compte utilisateur n'a été créé automatiquement.</AlertDescription>
                  </Alert>
                )}

                <section aria-labelledby="history-title" className="space-y-3">
                  <h3 id="history-title" className="flex items-center gap-2 font-semibold"><History className="h-4 w-4 text-primary" /> Historique des décisions</h3>
                  {selected.decisions?.length ? (
                    <div className="space-y-2">
                      {selected.decisions.map((item: AdmissionDecision) => (
                        <div key={item.id} className="flex flex-col gap-2 rounded-lg border p-3 sm:flex-row sm:items-start sm:justify-between">
                          <div>
                            <div className="flex items-center gap-2"><DecisionBadge decision={item.decision} /><span className="text-xs text-muted-foreground">{formatDateTime(item.date_decision)}</span></div>
                            {item.motif && <p className="mt-2 text-sm">{item.motif}</p>}
                          </div>
                          <span className="text-xs text-muted-foreground">Par utilisateur #{item.decisionnaire_id}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">Aucune décision enregistrée.</p>
                  )}
                </section>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <AlertDialog open={conversionDialogOpen} onOpenChange={setConversionDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmer la conversion</AlertDialogTitle>
            <AlertDialogDescription>
              Un dossier étudiant sera créé pour {selected?.prenom || "ce candidat"} {selected?.nom || ""}. Aucun compte utilisateur ni mot de passe ne sera créé. Cette action est enregistrée dans le dossier d'admission.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={busyAction !== null}>Annuler</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                setConversionDialogOpen(false);
                void handleConversion();
              }}
              disabled={busyAction !== null}
            >
              Confirmer la conversion
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default Validation;
