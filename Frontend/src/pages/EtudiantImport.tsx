import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  CircleSlash,
  Download,
  FileSpreadsheet,
  History,
  Info,
  Loader2,
  RefreshCw,
  TriangleAlert,
  Upload,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { KpiCard } from "@/components/ui/kpi-card";
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
import { etudiantImportApi, extractErrorMessage } from "@/services/apiClient";
import type {
  ImportAnalyse,
  ImportAnalyseLigne,
  ImportBatch,
  ImportLigneStatut,
  ImportModele,
  ImportMode,
  ImportValidation,
} from "@/services/apiTypes";

const FILTRES = [
  { value: "tous", label: "Toutes les lignes" },
  { value: "valide", label: "Importables" },
  { value: "erreur", label: "En erreur" },
  { value: "ignore", label: "Ignorées" },
] as const;

const STATUT_LOT: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  analyse: { label: "Analysé", variant: "secondary" },
  valide: { label: "Validé", variant: "default" },
  termine: { label: "Terminé", variant: "default" },
  annule: { label: "Annulé", variant: "outline" },
  erreur: { label: "Erreur", variant: "destructive" },
};

const ICONE_LIGNE: Record<ImportLigneStatut, typeof CheckCircle2> = {
  valide: CheckCircle2,
  erreur: XCircle,
  ignore: CircleSlash,
};

const EtudiantImport = () => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [modele, setModele] = useState<ImportModele | null>(null);
  const [historique, setHistorique] = useState<ImportBatch[]>([]);
  const [mode, setMode] = useState<ImportMode>("creation");
  const [fichier, setFichier] = useState<File | null>(null);
  const [analyse, setAnalyse] = useState<ImportAnalyse | null>(null);
  const [validation, setValidation] = useState<ImportValidation | null>(null);
  const [filtre, setFiltre] = useState<string>("tous");
  const [chargement, setChargement] = useState(true);
  const [analyseEnCours, setAnalyseEnCours] = useState(false);
  const [validationEnCours, setValidationEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState(false);

  const charger = useCallback(async () => {
    setChargement(true);
    setErreur(null);
    const [modeleRes, historiqueRes] = await Promise.all([
      etudiantImportApi.getModele(),
      etudiantImportApi.lister(10),
    ]);
    if (modeleRes.error) {
      setErreur(extractErrorMessage(modeleRes.error, "Contrat du fichier indisponible."));
    } else {
      setModele(modeleRes.data ?? null);
    }
    if (historiqueRes.error) {
      setErreur((precedent) =>
        precedent ?? extractErrorMessage(historiqueRes.error, "Historique indisponible.")
      );
    } else {
      setHistorique(historiqueRes.data ?? []);
    }
    setChargement(false);
  }, []);

  useEffect(() => {
    void charger();
  }, [charger]);

  const reinitialiser = () => {
    setFichier(null);
    setAnalyse(null);
    setValidation(null);
    setFiltre("tous");
    if (inputRef.current) inputRef.current.value = "";
  };

  const lancerAnalyse = async () => {
    if (!fichier) {
      toast.warning("Sélectionnez d'abord un fichier .csv ou .xlsx.");
      return;
    }
    setAnalyseEnCours(true);
    setErreur(null);
    setValidation(null);
    const result = await etudiantImportApi.analyser(fichier, mode);
    setAnalyseEnCours(false);
    if (result.error) {
      setErreur(extractErrorMessage(result.error, "Le fichier n'a pas pu être analysé."));
      return;
    }
    setAnalyse(result.data ?? null);
    toast.success("Analyse terminée. Vérifiez le rapport avant de valider.");
    void charger();
  };

  const lancerValidation = async () => {
    if (!analyse) return;
    setValidationEnCours(true);
    setErreur(null);
    const result = await etudiantImportApi.valider(analyse.batch_id);
    setValidationEnCours(false);
    if (result.error) {
      setErreur(extractErrorMessage(result.error, "L'import n'a pas pu être enregistré."));
      return;
    }
    setValidation(result.data ?? null);
    toast.success(
      `${result.data?.nb_importes ?? 0} dossier(s) importé(s), ${
        result.data?.nb_mises_a_jour ?? 0
      } mis à jour.`
    );
    void charger();
  };

  const annulerLot = async () => {
    if (!analyse) return;
    const result = await etudiantImportApi.annuler(analyse.batch_id);
    if (result.error) {
      toast.error(extractErrorMessage(result.error, "Annulation impossible."));
      return;
    }
    toast.success("Import annulé. Aucune donnée n'a été écrite.");
    reinitialiser();
    void charger();
  };

  const lignes = useMemo(() => {
    if (!analyse) return [];
    if (filtre === "tous") return analyse.lignes;
    return analyse.lignes.filter((ligne) => ligne.statut === filtre);
  }, [analyse, filtre]);

  const totaux = useMemo(() => {
    if (!analyse) return { creer: 0, maj: 0, erreurs: 0, avertissements: 0, ignorees: 0 };
    return {
      creer: analyse.nb_creer,
      maj: analyse.nb_mettre_a_jour,
      erreurs: analyse.nb_erreurs,
      avertissements: analyse.nb_avertissements,
      ignorees: analyse.nb_ignorees,
    };
  }, [analyse]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="mb-2 flex items-center gap-2 text-sm text-muted-foreground">
            <Link to="/etudiants" className="inline-flex items-center gap-1 hover:text-primary">
              <ArrowLeft className="h-4 w-4" /> Registre Étudiants
            </Link>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Import d'étudiants</h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            Chargez votre fichier Excel en deux temps : une analyse sans aucune écriture, puis la
            validation des lignes valides. Le rapport indique précisément ce qui passera et ce qui
            échouera.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => void charger()} disabled={chargement}>
          <RefreshCw className={`mr-2 h-4 w-4 ${chargement ? "animate-spin" : ""}`} />
          Actualiser
        </Button>
      </div>

      {erreur && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Import indisponible</AlertTitle>
          <AlertDescription>{erreur}</AlertDescription>
        </Alert>
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Étape 1 : le fichier                                             */}
      {/* ---------------------------------------------------------------- */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileSpreadsheet className="h-5 w-5 text-primary" /> 1. Préparer le fichier
          </CardTitle>
          <CardDescription>
            Formats acceptés : CSV (UTF-8, séparateur « ; ») ou XLSX. Colonnes reconnues
            automatiquement, même avec accents ou libellés différents.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" asChild>
              <a href={etudiantImportApi.urlModeleCsv()} download>
                <Download className="mr-2 h-4 w-4" />
                Télécharger le modèle CSV
              </a>
            </Button>
            <span className="self-center text-xs text-muted-foreground">
              Le modèle contient uniquement les en-têtes : aucune donnée fictive.
            </span>
          </div>

          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
            <div className="space-y-2">
              <Label htmlFor="import-fichier">Fichier à analyser</Label>
              <Input
                id="import-fichier"
                ref={inputRef}
                type="file"
                accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                onChange={(event) => {
                  setFichier(event.target.files?.[0] ?? null);
                  setAnalyse(null);
                  setValidation(null);
                }}
                disabled={analyseEnCours}
              />
              {fichier && (
                <p className="text-xs text-muted-foreground">
                  {fichier.name} · {(fichier.size / 1024).toFixed(0)} Ko
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="import-mode">Comportement en cas de doublon</Label>
              <Select
                value={mode}
                onValueChange={(value) => {
                  setMode(value as ImportMode);
                  setAnalyse(null);
                }}
              >
                <SelectTrigger id="import-mode">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="creation">Refuser les doublons (recommandé)</SelectItem>
                  <SelectItem value="mise_a_jour">Mettre à jour les dossiers existants</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {mode === "creation"
                  ? "Un matricule ou un email déjà connu signale une erreur de ligne : rien n'est écrasé."
                  : "Un matricule ou un email déjà connu met à jour le dossier existant au lieu d'en créer un second."}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button onClick={() => void lancerAnalyse()} disabled={!fichier || analyseEnCours}>
              {analyseEnCours ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Analyse en cours...
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-4 w-4" />
                  Analyser le fichier
                </>
              )}
            </Button>
            {analyse && (
              <Button variant="ghost" onClick={reinitialiser} disabled={validationEnCours}>
                Réinitialiser
              </Button>
            )}
          </div>

          <Alert>
            <Info className="h-4 w-4" />
            <AlertTitle>Aucune donnée n'est écrite pendant l'analyse</AlertTitle>
            <AlertDescription>
              Une filière, une session ou une classe inconnue produit une erreur de ligne. L'import
              ne crée jamais de référentiel : préparez-les au préalable.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>

      {/* ---------------------------------------------------------------- */}
      {/* Étape 2 : le rapport                                             */}
      {/* ---------------------------------------------------------------- */}
      {analyse && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-primary" /> 2. Rapport d'analyse
            </CardTitle>
            <CardDescription>
              {analyse.nom_fichier} · {analyse.format_source.toUpperCase()} ·{" "}
              {analyse.nb_lignes} ligne(s) lue(s)
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <KpiCard
                title="À créer"
                value={totaux.creer}
                icon={CheckCircle2}
                subtitle="Nouveaux dossiers"
                colorVariant="emerald"
              />
              <KpiCard
                title="À mettre à jour"
                value={totaux.maj}
                icon={RefreshCw}
                subtitle="Dossiers existants"
                colorVariant="sky"
              />
              <KpiCard
                title="En erreur"
                value={totaux.erreurs}
                icon={XCircle}
                subtitle="Non importables"
                colorVariant="rose"
              />
              <KpiCard
                title="Avertissements"
                value={totaux.avertissements}
                icon={TriangleAlert}
                subtitle="Importables sous réserve"
                colorVariant="amber"
              />
            </div>

            {analyse.colonnes_ignorees.length > 0 && (
              <Alert>
                <Info className="h-4 w-4" />
                <AlertTitle>Colonnes non utilisées</AlertTitle>
                <AlertDescription>
                  {analyse.colonnes_ignorees.join(", ")} — ignorées silencieusement, sans impact sur
                  l'import.
                </AlertDescription>
              </Alert>
            )}

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-2">
                <Label htmlFor="import-filtre" className="shrink-0 text-sm text-muted-foreground">
                  Afficher
                </Label>
                <Select value={filtre} onValueChange={setFiltre}>
                  <SelectTrigger id="import-filtre" className="w-full sm:w-56">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {FILTRES.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <p className="text-xs text-muted-foreground">
                {lignes.length} ligne(s) affichée(s) sur {analyse.lignes.length}
              </p>
            </div>

            <div className="max-h-[28rem] overflow-auto rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/50">
                    <TableHead className="w-16">Ligne</TableHead>
                    <TableHead className="w-32">État</TableHead>
                    <TableHead>Étudiant</TableHead>
                    <TableHead>Filière / Niveau</TableHead>
                    <TableHead>Diagnostic</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {lignes.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="py-10 text-center text-sm text-muted-foreground">
                        Aucune ligne pour ce filtre.
                      </TableCell>
                    </TableRow>
                  ) : (
                    lignes.map((ligne: ImportAnalyseLigne) => {
                      const Icone = ICONE_LIGNE[ligne.statut];
                      return (
                        <TableRow key={ligne.ligne}>
                          <TableCell className="font-mono text-xs">{ligne.ligne}</TableCell>
                          <TableCell>
                            <Badge
                              variant={
                                ligne.statut === "erreur"
                                  ? "destructive"
                                  : ligne.statut === "valide"
                                  ? "secondary"
                                  : "outline"
                              }
                              className="gap-1"
                            >
                              <Icone className="h-3 w-3" />
                              {ligne.statut === "valide"
                                ? ligne.action === "mettre_a_jour"
                                  ? "Mise à jour"
                                  : "Créer"
                                : ligne.statut === "erreur"
                                ? "Erreur"
                                : "Ignorée"}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <p className="font-medium">
                              {ligne.nom || "—"} {ligne.prenom || ""}
                            </p>
                            <p className="font-mono text-xs text-muted-foreground">
                              {ligne.matricule || "matricule à générer"}
                            </p>
                          </TableCell>
                          <TableCell className="text-sm">
                            {ligne.filiere || "—"}
                            {ligne.niveau && (
                              <span className="text-muted-foreground"> · {ligne.niveau}</span>
                            )}
                          </TableCell>
                          <TableCell>
                            {ligne.erreurs.length === 0 && ligne.avertissements.length === 0 ? (
                              <span className="text-sm text-muted-foreground">Prêt</span>
                            ) : (
                              <ul className="space-y-1 text-xs">
                                {ligne.erreurs.map((message, index) => (
                                  <li key={`e${index}`} className="flex gap-1.5 text-destructive">
                                    <XCircle className="mt-0.5 h-3 w-3 shrink-0" />
                                    {message}
                                  </li>
                                ))}
                                {ligne.avertissements.map((message, index) => (
                                  <li
                                    key={`w${index}`}
                                    className="flex gap-1.5 text-amber-600 dark:text-amber-400"
                                  >
                                    <TriangleAlert className="mt-0.5 h-3 w-3 shrink-0" />
                                    {message}
                                  </li>
                                ))}
                              </ul>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </div>

            {/* ------------------------------------------------------ */}
            {/* Étape 3 : validation                                  */}
            {/* ------------------------------------------------------ */}
            <div className="rounded-xl border border-primary/30 bg-primary/5 p-4">
              <h3 className="font-semibold text-foreground">3. Valider l'import</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                {totaux.creer + totaux.maj} dossier(s) seront enregistrés. Les {totaux.erreurs} ligne(s)
                en erreur seront ignorées et restent visibles dans le rapport.
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <Button
                  onClick={() => setConfirmation(true)}
                  disabled={totaux.creer + totaux.maj === 0}
                >
                  <CheckCircle2 className="mr-2 h-4 w-4" />
                  Valider {totaux.creer + totaux.maj} dossier(s)
                </Button>
                <Button variant="ghost" onClick={() => void annulerLot()}>
                  Annuler l'import
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Résultat de la validation                                       */}
      {/* ---------------------------------------------------------------- */}
      {validation && (
        <Alert variant={validation.nb_importes + validation.nb_mises_a_jour > 0 ? "default" : "destructive"}>
          <CheckCircle2 className="h-4 w-4" />
          <AlertTitle>Import terminé</AlertTitle>
          <AlertDescription>
            <ul className="space-y-1">
              <li>{validation.nb_importes} dossier(s) créé(s)</li>
              <li>{validation.nb_mises_a_jour} dossier(s) mis à jour</li>
              <li>{validation.nb_erreurs} ligne(s) en erreur non enregistrée(s)</li>
            </ul>
            {validation.message && <p className="mt-2">{validation.message}</p>}
            <Button variant="outline" size="sm" className="mt-3" asChild>
              <Link to="/etudiants">Consulter le registre</Link>
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Historique                                                       */}
      {/* ---------------------------------------------------------------- */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <History className="h-5 w-5 text-primary" /> Imports récents
          </CardTitle>
          <CardDescription>Traçabilité des dépôts de fichiers, y compris non validés.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {historique.length === 0 ? (
            <p className="px-5 py-10 text-center text-sm text-muted-foreground">
              Aucun import enregistré pour le moment.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/50">
                  <TableHead>Fichier</TableHead>
                  <TableHead>Déposé le</TableHead>
                  <TableHead>État</TableHead>
                  <TableHead className="text-right">Lignes</TableHead>
                  <TableHead className="text-right">Créés</TableHead>
                  <TableHead className="text-right">Erreurs</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {historique.map((lot) => {
                  const info = STATUT_LOT[lot.statut] ?? { label: lot.statut, variant: "outline" as const };
                  return (
                    <TableRow key={lot.id}>
                      <TableCell>
                        <p className="font-medium">{lot.nom_fichier}</p>
                        <p className="text-xs text-muted-foreground">
                          {lot.format_source.toUpperCase()} · {lot.mode === "mise_a_jour" ? "mise à jour" : "création"}
                        </p>
                      </TableCell>
                      <TableCell className="text-sm">
                        {lot.created_at ? new Date(lot.created_at).toLocaleString("fr-FR") : "—"}
                      </TableCell>
                      <TableCell>
                        <Badge variant={info.variant}>{info.label}</Badge>
                      </TableCell>
                      <TableCell className="text-right">{lot.nb_lignes}</TableCell>
                      <TableCell className="text-right">{lot.nb_importes}</TableCell>
                      <TableCell className="text-right">
                        {lot.nb_erreurs > 0 ? (
                          <span className="text-destructive">{lot.nb_erreurs}</span>
                        ) : (
                          0
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* ---------------------------------------------------------------- */}
      {/* Contrat du fichier                                               */}
      {/* ---------------------------------------------------------------- */}
      {modele && (
        <Card>
          <CardHeader>
            <CardTitle>Colonnes attendues</CardTitle>
            <CardDescription>
              Les en-têtes sont normalisés : « Date de naissance », « date_naissance » et
              « DATE_DE_NAISSANCE » sont tous reconnus.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="overflow-auto rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/50">
                    <TableHead>Colonne</TableHead>
                    <TableHead>Obligatoire</TableHead>
                    <TableHead>Description</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {modele.colonnes.map((colonne) => (
                    <TableRow key={colonne.colonne}>
                      <TableCell className="font-mono text-xs">{colonne.colonne}</TableCell>
                      <TableCell>
                        {colonne.obligatoire ? (
                          <Badge variant="destructive">Oui</Badge>
                        ) : (
                          <Badge variant="outline">Non</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">{colonne.description}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <div>
              <p className="mb-2 text-sm font-medium text-foreground">Règles de traitement</p>
              <ul className="space-y-1.5">
                {modele.notes.map((note) => (
                  <li key={note} className="flex gap-2 text-sm text-muted-foreground">
                    <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                    {note}
                  </li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>
      )}

      <AlertDialog open={confirmation} onOpenChange={setConfirmation}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Enregistrer {totaux.creer + totaux.maj} dossier(s) étudiant(s) ?
            </AlertDialogTitle>
            <AlertDialogDescription>
              Les matricules manquants seront générés automatiquement. Cette action est
              idempotente : la relancer ne créera pas de doublon. Les {totaux.erreurs} ligne(s) en
              erreur resteront non enregistrées.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                setConfirmation(false);
                void lancerValidation();
              }}
              disabled={validationEnCours}
            >
              {validationEnCours ? "Enregistrement..." : "Valider l'import"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default EtudiantImport;
