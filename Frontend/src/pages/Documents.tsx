import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  BadgeCheck,
  CheckCircle2,
  Copy,
  Download,
  FileCheck2,
  FileText,
  History,
  Info,
  Layers,
  Loader2,
  Printer,
  RefreshCw,
  ScrollText,
  Search,
  ShieldCheck,
  Wallet,
} from "lucide-react";
import { toast } from "sonner";

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
import { KpiCard } from "@/components/ui/kpi-card";
import IdentiteDocument from "@/components/institution/IdentiteDocument";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import {
  academicApi,
  documentsApi,
  etudiantsApi,
  extractErrorMessage,
  sessionsApi,
} from "@/services/apiClient";
import type { DocumentOfficiel, Student, TypeDocument } from "@/services/apiTypes";

const TOUTES = "__toutes__";

const ICONES: Record<string, typeof FileCheck2> = {
  certificat_scolarite: BadgeCheck,
  releve_notes: FileText,
  quitus_financier: Wallet,
};

const Documents = () => {
  const [types, setTypes] = useState<TypeDocument[]>([]);
  const [documents, setDocuments] = useState<DocumentOfficiel[]>([]);
  const [etudiants, setEtudiants] = useState<Student[]>([]);
  const [sessions, setSessions] = useState<{ id: string; nom: string; code: string }[]>([]);
  const [classes, setClasses] = useState<{ id: string; nom?: string | null; code: string }[]>([]);

  const [typeActif, setTypeActif] = useState("");
  const [sessionId, setSessionId] = useState<string>(TOUTES);
  const [etudiantId, setEtudiantId] = useState("");
  const [recherche, setRecherche] = useState("");
  const [filtreType, setFiltreType] = useState<string>(TOUTES);
  const [classeId, setClasseId] = useState<string>(TOUTES);

  const [chargement, setChargement] = useState(true);
  const [actionEnCours, setActionEnCours] = useState<string | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [duplicataCible, setDuplicataCible] = useState<DocumentOfficiel | null>(null);
  const [motifDuplicata, setMotifDuplicata] = useState("");
  const [lotOuvert, setLotOuvert] = useState(false);

  const charger = useCallback(async () => {
    setChargement(true);
    setErreur(null);
    const [typesRes, docsRes, etudiantsRes, sessionsRes, structureRes] = await Promise.all([
      documentsApi.getTypes(),
      documentsApi.lister({ limite: 100 }),
      etudiantsApi.getAll(),
      sessionsApi.getAll(),
      academicApi.getClasses(),
    ]);
    if (typesRes.error) {
      setErreur(extractErrorMessage(typesRes.error, "Catalogue indisponible."));
    } else {
      setTypes(typesRes.data || []);
      setTypeActif((precedent) => precedent || typesRes.data?.[0]?.code || "");
    }
    if (docsRes.error) {
      setErreur((p) => p ?? extractErrorMessage(docsRes.error, "Historique indisponible."));
    } else {
      setDocuments(docsRes.data || []);
    }
    setEtudiants(etudiantsRes.data || []);
    setSessions(
      (sessionsRes.data || []).map((s) => ({ id: s.id, nom: s.nom, code: s.code }))
    );
    setClasses(structureRes.data || []);
    setChargement(false);
  }, []);

  useEffect(() => {
    void charger();
  }, [charger]);

  const definition = types.find((t) => t.code === typeActif);

  const etudiantsFiltres = useMemo(() => {
    const requete = recherche.trim().toLocaleLowerCase("fr");
    if (!requete) return etudiants;
    return etudiants.filter((e) =>
      `${e.nom} ${e.prenom} ${e.matricule}`.toLocaleLowerCase("fr").includes(requete)
    );
  }, [etudiants, recherche]);

  const documentsAffiches = useMemo(() => {
    if (filtreType === TOUTES) return documents;
    return documents.filter((d) => d.type_document === filtreType);
  }, [documents, filtreType]);

  const totaux = useMemo(
    () => ({
      total: documents.length,
      delivres: documents.filter((d) => d.delivre_le).length,
      duplicatas: documents.filter((d) => d.remplace_document_id).length,
      types: types.length,
    }),
    [documents, types]
  );

  const emettrePour = async (cible: string) => {
    if (!typeActif) {
      toast.warning("Choisissez un type de document.");
      return;
    }
    setActionEnCours(cible);
    setErreur(null);
    const result = await documentsApi.emettre(cible, {
      type_document: typeActif,
      session_id: sessionId === TOUTES ? null : sessionId,
    });
    setActionEnCours(null);
    if (result.error) {
      toast.error(extractErrorMessage(result.error, "Émission impossible."));
      return;
    }
    toast.success(`Document ${result.data?.numero} émis.`);
    void charger();
  };

  const lancerLot = async () => {
    if (!typeActif || classeId === TOUTES) {
      toast.warning("Choisissez un type et une classe.");
      return;
    }
    setActionEnCours("lot");
    const result = await documentsApi.emettreLot({
      type_document: typeActif,
      classe_id: classeId,
      session_id: sessionId === TOUTES ? null : sessionId,
      ignorer_les_non_eligibles: true,
    });
    setActionEnCours(null);
    if (result.error) {
      toast.error(extractErrorMessage(result.error, "Émission en série impossible."));
      return;
    }
    const bilan = result.data;
    toast.success(
      `${bilan?.emis ?? 0} document(s) émis, ${bilan?.echoues ?? 0} dossier(s) non éligible(s).`,
      { description: "Le détail figure dans le tableau de bord." }
    );
    setLotOuvert(false);
    void charger();
  };

  const demanderDuplicata = async () => {
    if (!duplicataCible || motifDuplicata.trim().length < 3) {
      toast.warning("Indiquez le motif du duplicata (3 caractères minimum).");
      return;
    }
    setActionEnCours(duplicataCible.id);
    const result = await documentsApi.duplicata(duplicataCible.id, motifDuplicata.trim());
    setActionEnCours(null);
    if (result.error) {
      toast.error(extractErrorMessage(result.error, "Duplicata impossible."));
      return;
    }
    toast.success(`Duplicata ${result.data?.numero} émis.`);
    setDuplicataCible(null);
    setMotifDuplicata("");
    void charger();
  };

  const marquerDelivrance = async (document: DocumentOfficiel) => {
    setActionEnCours(document.id);
    const result = await documentsApi.marquerDelivrance(document.id);
    setActionEnCours(null);
    if (result.error) {
      toast.error(extractErrorMessage(result.error, "Délivrance non enregistrée."));
      return;
    }
    toast.success("Délivrance enregistrée.");
    void charger();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Documents officiels</h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            Certificats de scolarité, relevés de notes et quitus, générés à partir des données
            enregistrées et numérotés pour la traçabilité. Un document n'est émis que si les
            données qu'il atteste existent réellement.
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
          <AlertTitle>Module indisponible</AlertTitle>
          <AlertDescription>{erreur}</AlertDescription>
        </Alert>
      )}

      {/* Identité qui figurera sur les documents. Le secrétariat n'a pas la
          permission de la modifier, mais il doit la voir avant d'émettre. */}
      <IdentiteDocument />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          title="Documents émis"
          value={totaux.total}
          icon={ScrollText}
          subtitle="Tous types confondus"
          colorVariant="primary"
        />
        <KpiCard
          title="Délivrés"
          value={totaux.delivres}
          icon={CheckCircle2}
          subtitle="Remis à l'étudiant"
          colorVariant="emerald"
        />
        <KpiCard
          title="Duplicatas"
          value={totaux.duplicatas}
          icon={Copy}
          subtitle="Remplacement d'original"
          colorVariant="amber"
        />
        <KpiCard
          title="Types disponibles"
          value={totaux.types}
          icon={FileCheck2}
          subtitle="Adossés aux données"
          colorVariant="sky"
        />
      </div>

      {/* --------------------------------------------------- */}
      {/* Émission unitaire                                   */}
      {/* --------------------------------------------------- */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileCheck2 className="h-5 w-5 text-primary" /> Émettre un document
          </CardTitle>
          <CardDescription>
            Choisissez un type, puis un étudiant. L'émission crée un PDF numéroté et l'inscrit au
            registre.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="doc-type">Type de document</Label>
              <Select value={typeActif} onValueChange={setTypeActif}>
                <SelectTrigger id="doc-type">
                  <SelectValue placeholder="Type de document" />
                </SelectTrigger>
                <SelectContent>
                  {types.map((type) => {
                    const Icone = ICONES[type.code] ?? FileText;
                    return (
                      <SelectItem key={type.code} value={type.code}>
                        <span className="flex items-center gap-2">
                          <Icone className="h-4 w-4" />
                          {type.libelle}
                        </span>
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="doc-session">Session (optionnel)</Label>
              <Select value={sessionId} onValueChange={setSessionId}>
                <SelectTrigger id="doc-session">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={TOUTES}>Toutes les sessions</SelectItem>
                  {sessions.map((session) => (
                    <SelectItem key={session.id} value={session.id}>
                      {session.nom} ({session.code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {definition && (
            <Alert>
              <Info className="h-4 w-4" />
              <AlertTitle>{definition.libelle}</AlertTitle>
              <AlertDescription>
                {definition.description}
                {definition.conditions.length > 0 && (
                  <span className="mt-1 block text-xs">
                    Conditions vérifiées avant émission : {definition.conditions.join(" · ")}.
                  </span>
                )}
              </AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <Label htmlFor="doc-recherche">Étudiant</Label>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="doc-recherche"
                value={recherche}
                onChange={(event) => setRecherche(event.target.value)}
                placeholder="Rechercher par nom, prénom ou matricule"
                className="pl-9"
              />
            </div>
          </div>

          <div className="max-h-72 overflow-auto rounded-lg border">
            {etudiantsFiltres.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                Aucun étudiant ne correspond à cette recherche.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/50">
                    <TableHead>Matricule</TableHead>
                    <TableHead>Étudiant</TableHead>
                    <TableHead>Filière</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {etudiantsFiltres.slice(0, 50).map((etudiant) => (
                    <TableRow
                      key={etudiant.id}
                      className={etudiantId === etudiant.id ? "bg-primary/5" : undefined}
                    >
                      <TableCell className="font-mono text-xs">{etudiant.matricule}</TableCell>
                      <TableCell className="font-medium">
                        {etudiant.nom} {etudiant.prenom}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {etudiant.filiere}
                        {etudiant.niveau ? ` · ${etudiant.niveau}` : ""}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          size="sm"
                          variant={etudiantId === etudiant.id ? "default" : "outline"}
                          disabled={actionEnCours !== null}
                          onClick={() => {
                            setEtudiantId(etudiant.id);
                            void emettrePour(etudiant.id);
                          }}
                        >
                          {actionEnCours === etudiant.id ? (
                            <>
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              Émission
                            </>
                          ) : (
                            <>
                              <Download className="mr-2 h-4 w-4" />
                              Émettre
                            </>
                          )}
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => setLotOuvert(true)} disabled={classes.length === 0}>
              <Layers className="mr-2 h-4 w-4" />
              Émettre pour une classe entière
            </Button>
            <Button variant="ghost" asChild>
              <Link to="/etudiants">
                <Search className="mr-2 h-4 w-4" />
                Ouvrir le registre
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* --------------------------------------------------- */}
      {/* Registre                                             */}
      {/* --------------------------------------------------- */}
      <Card>
        <CardHeader className="gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <History className="h-5 w-5 text-primary" /> Registre d'émission
            </CardTitle>
            <CardDescription>
              Chaque document émis est conservé : numéro, empreinte, auteur et instantané des
              données au moment de l'émission.
            </CardDescription>
          </div>
          <Select value={filtreType} onValueChange={setFiltreType}>
            <SelectTrigger className="w-full sm:w-64" aria-label="Filtrer par type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={TOUTES}>Tous les types</SelectItem>
              {types.map((type) => (
                <SelectItem key={type.code} value={type.code}>
                  {type.libelle}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardHeader>
        <CardContent className="p-0">
          {documentsAffiches.length === 0 ? (
            <p className="px-5 py-12 text-center text-sm text-muted-foreground">
              Aucun document émis pour l'instant.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/50">
                    <TableHead>Numéro</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Étudiant</TableHead>
                    <TableHead>Émis le</TableHead>
                    <TableHead>État</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {documentsAffiches.map((document) => {
                    const Icone = ICONES[document.type_document] ?? FileText;
                    return (
                      <TableRow key={document.id}>
                        <TableCell className="font-mono text-xs">{document.numero}</TableCell>
                        <TableCell>
                          <span className="flex items-center gap-2 text-sm">
                            <Icone className="h-4 w-4 text-muted-foreground" />
                            {document.libelle ?? document.type_document}
                          </span>
                        </TableCell>
                        <TableCell>
                          <p className="text-sm font-medium">
                            {document.etudiant_nom} {document.etudiant_prenom}
                          </p>
                          <p className="font-mono text-xs text-muted-foreground">
                            {document.etudiant_matricule}
                          </p>
                        </TableCell>
                        <TableCell className="text-sm">
                          {new Date(document.emis_le).toLocaleString("fr-FR")}
                        </TableCell>
                        <TableCell>
                          {document.remplace_document_id ? (
                            <Badge variant="outline" className="gap-1">
                              <Copy className="h-3 w-3" />
                              Duplicata
                            </Badge>
                          ) : document.delivre_le ? (
                            <Badge variant="default" className="gap-1">
                              <CheckCircle2 className="h-3 w-3" />
                              Délivré
                            </Badge>
                          ) : (
                            <Badge variant="secondary">Émis</Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-1">
                            <Button variant="ghost" size="icon" asChild aria-label="Télécharger le PDF">
                              <a
                                href={documentsApi.urlTelecharger(document.id)}
                                target="_blank"
                                rel="noreferrer"
                              >
                                <Download className="h-4 w-4" />
                              </a>
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              aria-label="Imprimer"
                              onClick={() => window.open(documentsApi.urlTelecharger(document.id), "_blank")}
                            >
                              <Printer className="h-4 w-4" />
                            </Button>
                            {!document.delivre_le && (
                              <Button
                                variant="ghost"
                                size="sm"
                                disabled={actionEnCours === document.id}
                                onClick={() => void marquerDelivrance(document)}
                              >
                                Marquer délivré
                              </Button>
                            )}
                            {!document.remplace_document_id && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  setDuplicataCible(document);
                                  setMotifDuplicata("");
                                }}
                              >
                                Duplicata
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* --------------------------------------------------- */}
      {/* Types et leurs conditions                           */}
      {/* --------------------------------------------------- */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-primary" /> Ce qui peut être attesté
          </CardTitle>
          <CardDescription>
            Seuls les documents adossés à des données réellement enregistrées sont proposés. Une
            décision de délibération, par exemple, n'existe pas en base : aucun document ne peut donc
            l'attester.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3">
          {types.map((type) => {
            const Icone = ICONES[type.code] ?? FileText;
            return (
              <div key={type.code} className="rounded-xl border p-4">
                <div className="mb-2 flex items-center gap-2">
                  <Icone className="h-4 w-4 text-primary" />
                  <p className="text-sm font-semibold">{type.libelle}</p>
                </div>
                <p className="text-xs leading-relaxed text-muted-foreground">{type.description}</p>
                <p className="mt-2 font-mono text-[11px] text-muted-foreground">
                  Préfixe {type.prefixe} · permission {type.permission}
                </p>
              </div>
            );
          })}
        </CardContent>
      </Card>

      {/* --------------------------------------------------- */}
      {/* Duplicata                                           */}
      {/* --------------------------------------------------- */}
      <AlertDialog open={Boolean(duplicataCible)} onOpenChange={(open) => !open && setDuplicataCible(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Réémettre {duplicataCible?.numero} ?</AlertDialogTitle>
            <AlertDialogDescription>
              Le duplicata porte un nouveau numéro et l'instantané des données actuelles. Le document
              d'origine reste au registre : c'est lui qui prouve ce qui avait été délivré la
              première fois.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="space-y-2 py-2">
            <Label htmlFor="motif-duplicata">Motif du duplicata</Label>
            <Textarea
              id="motif-duplicata"
              value={motifDuplicata}
              onChange={(event) => setMotifDuplicata(event.target.value)}
              placeholder="Perte, vol, destruction, erreur de saisie sur l'original…"
            />
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction onClick={() => void demanderDuplicata()}>
              Émettre le duplicata
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* --------------------------------------------------- */}
      {/* Émission en série                                   */}
      {/* --------------------------------------------------- */}
      <AlertDialog open={lotOuvert} onOpenChange={setLotOuvert}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Émettre pour une classe entière</AlertDialogTitle>
            <AlertDialogDescription>
              Les dossiers non éligibles sont listés sans interrompre le lot : une école doit pouvoir
              sortir ses 300 certificats même si deux dossiers sont incomplets.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="space-y-2 py-2">
            <Label htmlFor="lot-classe">Classe</Label>
            <Select value={classeId} onValueChange={setClasseId}>
              <SelectTrigger id="lot-classe">
                <SelectValue placeholder="Classe" />
              </SelectTrigger>
              <SelectContent>
                {classes.map((classe) => (
                  <SelectItem key={classe.id} value={classe.id}>
                    {classe.nom || classe.code}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Type : {definition?.libelle ?? "—"}
              {sessionId !== TOUTES
                ? ` · Session : ${sessions.find((s) => s.id === sessionId)?.nom ?? ""}`
                : " · Toutes sessions"}
            </p>
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => void lancerLot()}
              disabled={actionEnCours === "lot" || classeId === TOUTES}
            >
              {actionEnCours === "lot" ? "Émission en cours..." : "Lancer l'émission"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default Documents;
