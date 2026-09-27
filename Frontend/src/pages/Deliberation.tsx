/**
 * Ecran de deliberation : reglement, seances de jury, decisions.
 *
 * L'ecran reflete la separation des roles retenue cote serveur :
 *
 * - le **moteur** calcule une proposition, visible pour chaque etudiant ;
 * - le **jury** consigne une decision, et doit motiver tout ecart ;
 * - la **cloture** arrete le verdict et le rend immuable.
 *
 * Deux garde-fous sont affiches explicitement, parce qu'ils sont la raison
 * d'etre de l'ecran : un reglement non confirme, et l'ecart entre proposition
 * et decision. Un jury qui ne se voit pas decider ne peut pas controler.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Download,
  Gavel,
  Loader2,
  Lock,
  Plus,
  RefreshCw,
  Scale,
  Trash2,
  Users,
} from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import { useRBAC } from "@/contexts/RBACContext";
import {
  academicApi,
  deliberationApi,
  extractErrorMessage,
  PERMISSION_INSTITUTION_SETTINGS,
  sessionsApi,
  telechargerProcesVerbal,
} from "@/services/apiClient";
import type {
  Deliberation,
  DeliberationDetail,
  MoyenneUEProposee,
  PropositionEtudiant,
  ReglesDeliberation,
  ValidationUE,
} from "@/services/apiTypes";
import { VALIDATIONS_UE } from "@/services/apiTypes";
import { toast } from "sonner";

const STATUTS = ["Admis", "Rattrapage", "Ajourné"] as const;

const mentionPour = (
  moyenne: number,
  bareme: { libelle: string; seuil_min: number }[]
): string | null => {
  const trouvee = [...bareme]
    .sort((a, b) => b.seuil_min - a.seuil_min)
    .find((entree) => moyenne >= entree.seuil_min);
  return trouvee?.libelle ?? null;
};

const dateFr = (iso: string | null | undefined): string => {
  if (!iso) return "—";
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? iso
    : date.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric" });
};

const badgeStatut = (statut: string | null | undefined) => {
  if (!statut) return <Badge variant="outline">Non statue</Badge>;
  if (statut === "Admis") return <Badge className="bg-emerald-600 text-white">Admis</Badge>;
  if (statut === "Rattrapage") return <Badge className="bg-amber-600 text-white">Rattrapage</Badge>;
  return <Badge variant="destructive">Ajourné</Badge>;
};

const DeliberationPage = () => {
  const { hasPermission } = useRBAC();
  // Tenir une seance releve du metier academique, comme la saisie des notes.
  // Le reglement, lui, est une decision d'institut.
  const peutDeliberer = hasPermission("pedagogy.write");
  const peutConfigurer = hasPermission(PERMISSION_INSTITUTION_SETTINGS);

  const [regles, setRegles] = useState<ReglesDeliberation | null>(null);
  const [seances, setSeances] = useState<Deliberation[]>([]);
  const [active, setActive] = useState<DeliberationDetail | null>(null);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enregistrement, setEnregistrement] = useState<string | null>(null);

  const [editionRegles, setEditionRegles] = useState(false);
  const [nouvelleSeance, setNouvelleSeance] = useState(false);
  const [decisionEnCours, setDecisionEnCours] = useState<PropositionEtudiant | null>(null);
  /** Ecriture des decisions par UE en cours : desactive le bouton. */
  const [enregistrementUnites, setEnregistrementUnites] = useState(false);

  const charger = useCallback(async () => {
    setChargement(true);
    setErreur(null);
    const [reglesResult, listeResult] = await Promise.all([
      deliberationApi.getRegles(),
      deliberationApi.list(),
    ]);
    if (reglesResult.error) {
      setErreur(extractErrorMessage(reglesResult.error, "Regles de deliberation illisibles."));
    } else if (reglesResult.data) {
      setRegles(reglesResult.data);
    }
    setSeances(listeResult.data ?? []);
    setChargement(false);
  }, []);

  useEffect(() => {
    void charger();
  }, [charger]);

  const ouvrirSeance = async (id: string) => {
    setChargement(true);
    const resultat = await deliberationApi.get(id);
    setChargement(false);
    if (resultat.error || !resultat.data) {
      toast.error(extractErrorMessage(resultat.error, "Seance illisible."));
      return;
    }
    setActive(resultat.data);
  };

  const enregistrerDecision = async (
    etudiant: PropositionEtudiant,
    statut: string,
    mention: string | null,
    motif: string
  ) => {
    if (!active) return;
    setEnregistrement(etudiant.etudiant_id);
    const resultat = await deliberationApi.recordDecision(active.id, etudiant.etudiant_id, {
      statut,
      mention,
      motif_ecart: motif.trim() || null,
    });
    setEnregistrement(null);
    setDecisionEnCours(null);

    if (resultat.error) {
      toast.error(extractErrorMessage(resultat.error, "Decision non consignee."));
      return;
    }
    toast.success(`Decision consignee pour ${etudiant.matricule}.`);
    await ouvrirSeance(active.id);
  };

  /**
   * Consigne le sort de chaque UE.
   *
   * C'est un enregistrement a part du verdict d'ensemble : le jury peut statuer
   * sur l'etudiant sans avoir tranche chaque UE, et l'inverse. Le dialogue
   * reste ouvert, parce qu'il reste des UE non tranchees a traiter — le fermer
   * ferait perdre le travail en cours.
   */
  const enregistrerDecisionsUnites = async (
    decisions: Array<{
      ue_id: string;
      validation: ValidationUE;
      credits_obtenus?: number | null;
      mention?: string | null;
      motif?: string | null;
    }>
  ) => {
    if (!active || !decisionEnCours) return;
    setEnregistrementUnites(true);
    const resultat = await deliberationApi.recordDecisionsUnites(
      active.id,
      decisionEnCours.etudiant_id,
      decisions
    );
    setEnregistrementUnites(false);

    if (resultat.error) {
      toast.error(
        extractErrorMessage(resultat.error, "Décisions par UE non consignées.")
      );
      return;
    }
    const aReprendre = decisions.filter(
      (d) => d.validation === "À reprendre"
    ).length;
    toast.success(
      aReprendre > 0
        ? `Décisions consignées. ${aReprendre} UE à reprendre : le rattrapage est ouvert.`
        : "Décisions consignées. Aucune UE à reprendre."
    );
    await ouvrirSeance(active.id);
  };

  const cloturer = async () => {
    if (!active) return;
    const restants = active.nb_inscrits - active.decisions.length;
    if (restants > 0) {
      toast.error(
        `Encore ${restants} inscrit(s) sans decision : le jury doit statuer sur chacun.`
      );
      return;
    }
    const confirme = window.confirm(
      "Arreter definitivement le verdict de cette seance ?\n\n" +
        "Les decisions ne pourront plus etre modifiees, et c'est ce verdict " +
        "qui fondra l'attestation de reussite."
    );
    if (!confirme) return;

    const resultat = await deliberationApi.cloturer(active.id);
    if (resultat.error) {
      toast.error(extractErrorMessage(resultat.error, "Cloture impossible."));
      return;
    }
    toast.success("Verdict arrete. La seance est close.");
    await ouvrirSeance(active.id);
  };

  const telechargerPv = async () => {
    if (!active) return;
    const resultat = await telechargerProcesVerbal(active.id);
    if (resultat.error || !resultat.data) {
      toast.error(extractErrorMessage(resultat.error, "Proces-verbal indisponible."));
      return;
    }
    const url = URL.createObjectURL(resultat.data);
    const lien = document.createElement("a");
    lien.href = url;
    lien.download = `PV_${active.date_deliberation}_${active.id.slice(0, 8)}.pdf`;
    lien.click();
    URL.revokeObjectURL(url);
  };

  /**
   * Inscrits sans decision consignee.
   *
   * On compte les **inscrits**, pas les propositions : un inscrit sans note
   * n'a aucune proposition, et disparaitrait du compte. L'ecran activerait
   * alors une fermeture que le serveur refuse, puisque le jury n'a statue
   * sur personne. Les deux compteurs viennent de l'API, qui compte les
   * inscrits et les decisions.
   */
  const sansDecision = useMemo(() => {
    if (!active) return 0;
    return Math.max(0, active.nb_inscrits - active.nb_decisions);
  }, [active]);

  if (chargement && !active) {
    return (
      <div className="flex items-center justify-center gap-2 p-12 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" /> Chargement des délibérations…
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Délibération</h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            Le moteur calcule une proposition à partir des notes enregistrées. Le jury
            tranche, et motive tout écart. Seul un verdict arrêté fonde une attestation
            de réussite.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={charger} disabled={chargement}>
            <RefreshCw className="mr-2 h-4 w-4" /> Actualiser
          </Button>
          {peutDeliberer && (
            <Button onClick={() => setNouvelleSeance(true)}>
              <Plus className="mr-2 h-4 w-4" /> Ouvrir une séance
            </Button>
          )}
        </div>
      </div>

      {erreur && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Module indisponible</AlertTitle>
          <AlertDescription>{erreur}</AlertDescription>
        </Alert>
      )}

      {regles && !regles.confirmee && (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Règlement non confirmé par l'établissement</AlertTitle>
          <AlertDescription>
            Ces seuils sont des valeurs de départ issues du moteur, jamais revues.
            Une délibération ouverte dessus produit un procès-verbal fragile.
            {peutConfigurer && " Confirmez-les, ou corrigez-les, depuis le bouton « Règlement »."}
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
        {/* ---------------- Regles ---------------- */}
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between gap-3">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Scale className="h-4 w-4" /> Règlement de délibération
                </CardTitle>
                <CardDescription>
                  Les seuils appliqués par le jury. Ils sont figés dans chaque séance :
                  les modifier n'affecte que les prochaines.
                </CardDescription>
              </div>
              {peutConfigurer && (
                <Button variant="outline" size="sm" onClick={() => setEditionRegles(true)}>
                  Modifier
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {regles ? (
              <dl className="space-y-2 text-sm">
                <Regle libelle="Moyenne de validation" valeur={`${regles.seuil_validation_moyenne}/20`} />
                <Regle libelle="Rattrapage à partir de" valeur={`${regles.seuil_rattrapage_minimale}/20`} />
                <Regle libelle="Note éliminatoire" valeur={`< ${regles.seuil_eliminatoire}/20`} />
                <Regle
                  libelle="Passage conditionnel"
                  valeur={`${regles.seuil_passage_conditionnel_ects} ECTS`}
                />
                <Regle
                  libelle="Compensation entre UE"
                  valeur={regles.compensation_autorisee ? "autorisée" : "non autorisée"}
                />
                <div className="pt-2">
                  <dt className="font-medium">Mentions</dt>
                  <dd className="text-muted-foreground">
                    {[...regles.bareme_mentions]
                      .sort((a, b) => b.seuil_min - a.seuil_min)
                      .map((m) => `${m.libelle} ≥ ${m.seuil_min}`)
                      .join(" · ") || "—"}
                  </dd>
                </div>
                <div className="pt-2">
                  {regles.confirmee ? (
                    <p className="text-xs text-muted-foreground">
                      Confirmé par {regles.confirme_par} le{" "}
                      {regles.confirme_le ? dateFr(regles.confirme_le) : "—"}
                    </p>
                  ) : (
                    <p className="text-xs font-medium text-amber-600 dark:text-amber-400">
                      Jamais confirmé par l'établissement
                    </p>
                  )}
                </div>
              </dl>
            ) : (
              <p className="text-sm text-muted-foreground">Règlement illisible.</p>
            )}
          </CardContent>
        </Card>

        {/* ---------------- Seances ---------------- */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Gavel className="h-4 w-4" /> Séances de jury
            </CardTitle>
            <CardDescription>
              Une séance par promotion et par session. Sa clôture arrête le verdict.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {seances.length === 0 ? (
              <div className="rounded-lg border border-dashed py-10 text-center">
                <Gavel className="mx-auto h-8 w-8 text-muted-foreground" />
                <p className="mt-3 font-medium">Aucune séance ouverte</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {peutDeliberer
                    ? "Ouvrez une séance pour calculer les propositions et consigner les décisions."
                    : "Aucune séance n'a encore été tenue."}
                </p>
              </div>
            ) : (
              <ul className="space-y-2">
                {seances.map((seance) => (
                  <li key={seance.id}>
                    <button
                      type="button"
                      onClick={() => void ouvrirSeance(seance.id)}
                      className={`w-full rounded-lg border p-3 text-left transition-colors hover:bg-muted/50 ${
                        active?.id === seance.id ? "border-primary bg-muted/50" : ""
                      }`}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div>
                          <p className="font-medium">
                            {seance.classe_nom ?? "Promotion inconnue"}
                            {seance.session_nom ? ` — ${seance.session_nom}` : ""}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            {dateFr(seance.date_deliberation)}
                            {seance.lieu ? ` · ${seance.lieu}` : ""}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          {seance.statut === "close" ? (
                            <Badge className="bg-slate-600 text-white">
                              <Lock className="mr-1 h-3 w-3" /> Close
                            </Badge>
                          ) : (
                            <Badge variant="secondary">Brouillon</Badge>
                          )}
                          <span className="text-sm text-muted-foreground">
                            {seance.nb_decisions}/{seance.nb_inscrits} décisions
                          </span>
                        </div>
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ---------------- Detail de la seance ---------------- */}
      {active && (
        <Card>
          <CardHeader>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <CardTitle>
                  {active.classe_nom} — {dateFr(active.date_deliberation)}
                </CardTitle>
                <CardDescription>
                  Président : {active.president}
                  {active.membres.length > 0 &&
                    ` · ${active.membres.length} membre(s) : ${active.membres
                      .map((m) => m.nom)
                      .join(", ")}`}
                </CardDescription>
              </div>
              <div className="flex flex-wrap gap-2">
                {active.nb_decisions > 0 && (
                  <Button variant="outline" size="sm" onClick={() => void telechargerPv()}>
                    <Download className="mr-2 h-4 w-4" /> Procès-verbal
                  </Button>
                )}
                {peutDeliberer && active.statut === "brouillon" && (
                  <Button size="sm" onClick={() => void cloturer()} disabled={sansDecision > 0}>
                    <CheckCircle2 className="mr-2 h-4 w-4" />
                    Arrêter le verdict
                    {sansDecision > 0 && ` (${sansDecision} restant${sansDecision > 1 ? "s" : ""})`}
                  </Button>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {active.statut === "close" && (
              <Alert>
                <Lock className="h-4 w-4" />
                <AlertTitle>Verdict arrêté</AlertTitle>
                <AlertDescription>
                  Séance close le {active.close_le ? dateFr(active.close_le) : "—"}. Les
                  décisions ne sont plus modifiables : c'est ce verdict qui fonde
                  l'attestation de réussite.
                </AlertDescription>
              </Alert>
            )}

            {active.avertissements.map((avertissement) => (
              <Alert key={avertissement}>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{avertissement}</AlertDescription>
              </Alert>
            ))}

            {active.propositions.length === 0 ? (
              <div className="rounded-lg border border-dashed py-10 text-center">
                <Users className="mx-auto h-8 w-8 text-muted-foreground" />
                <p className="mt-3 font-medium">Rien à délibérer</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Aucun inscrit de cette promotion n'a de note sur la session. Un
                  étudiant sans note n'est pas évalué — et il bloque tout de même
                  la clôture tant que le jury n'a pas pris position à son sujet.
                </p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Matricule</TableHead>
                    <TableHead>Nom et prénom</TableHead>
                    <TableHead className="text-right">Moyenne</TableHead>
                    <TableHead className="text-right">ECTS</TableHead>
                    <TableHead>Proposition du moteur</TableHead>
                    <TableHead>Décision du jury</TableHead>
                    {peutDeliberer && active.statut === "brouillon" && <TableHead />}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {active.propositions.map((proposition) => (
                    <TableRow key={proposition.etudiant_id}>
                      <TableCell className="font-mono text-xs">
                        {proposition.matricule}
                      </TableCell>
                      <TableCell>
                        {proposition.nom} {proposition.prenom}
                        {proposition.notes_eliminatoires.length > 0 && (
                          <p className="text-xs text-destructive">
                            Note éliminatoire :{" "}
                            {proposition.notes_eliminatoires
                              .map((n) => `${n.matiere} (${n.note})`)
                              .join(", ")}
                          </p>
                        )}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {proposition.moyenne_generale}/20
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {proposition.ects_acquis}/{proposition.ects_total}
                      </TableCell>
                      <TableCell>
                        {badgeStatut(proposition.proposition_statut)}
                        {proposition.proposition_mention && (
                          <p className="mt-1 text-xs text-muted-foreground">
                            {proposition.proposition_mention}
                          </p>
                        )}
                      </TableCell>
                      <TableCell>
                        {proposition.decision_statut ? (
                          <>
                            {badgeStatut(proposition.decision_statut)}
                            {proposition.decision_mention && (
                              <p className="mt-1 text-xs text-muted-foreground">
                                {proposition.decision_mention}
                              </p>
                            )}
                            {proposition.ecart && proposition.motif_ecart && (
                              <p className="mt-1 text-xs italic text-muted-foreground">
                                Écart motivé : {proposition.motif_ecart}
                              </p>
                            )}
                          </>
                        ) : (
                          <span className="text-sm text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      {peutDeliberer && active.statut === "brouillon" && (
                        <TableCell>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setDecisionEnCours(proposition)}
                            disabled={enregistrement === proposition.etudiant_id}
                          >
                            {enregistrement === proposition.etudiant_id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              "Décider"
                            )}
                          </Button>
                        </TableCell>
                      )}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}

      <ReglesDialog
        ouvert={editionRegles}
        regles={regles}
        onClose={() => setEditionRegles(false)}
        onEnregistre={async () => {
          setEditionRegles(false);
          await charger();
        }}
      />

      <SeanceDialog
        ouvert={nouvelleSeance}
        seancesExistantes={seances}
        onClose={() => setNouvelleSeance(false)}
        onCree={async (id) => {
          setNouvelleSeance(false);
          await charger();
          await ouvrirSeance(id);
        }}
      />

      <DecisionDialog
        proposition={decisionEnCours}
        bareme={regles?.bareme_mentions ?? []}
        onClose={() => setDecisionEnCours(null)}
        onEnregistre={(statut, mention, motif) =>
          decisionEnCours
            ? enregistrerDecision(decisionEnCours, statut, mention, motif)
            : undefined
        }
        onEnregistreUnites={(decisions) => {
          if (!active || !decisionEnCours) return Promise.resolve();
          return enregistrerDecisionsUnites(decisions);
        }}
        enCours={enregistrementUnites}
      />
    </div>
  );
};

/* -------------------------------------------------------------------------- */
/* Fragments                                                                  */
/* -------------------------------------------------------------------------- */
const Regle = ({ libelle, valeur }: { libelle: string; valeur: string }) => (
  <div className="flex items-baseline justify-between gap-3">
    <dt className="text-muted-foreground">{libelle}</dt>
    <dd className="font-mono text-sm">{valeur}</dd>
  </div>
);

interface ReglesDialogProps {
  ouvert: boolean;
  regles: ReglesDeliberation | null;
  onClose: () => void;
  onEnregistre: () => Promise<void>;
}

const ReglesDialog = ({ ouvert, regles, onClose, onEnregistre }: ReglesDialogProps) => {
  const [valeurs, setValeurs] = useState({
    seuil_validation_moyenne: "10",
    seuil_eliminatoire: "7",
    seuil_rattrapage_minimale: "8.5",
    seuil_passage_conditionnel_ects: "18",
    compensation_autorisee: true,
    confirme: false,
  });
  const [bareme, setBareme] = useState<{ libelle: string; seuil_min: number }[]>([]);
  const [envoi, setEnvoi] = useState(false);

  useEffect(() => {
    if (regles && ouvert) {
      setValeurs({
        seuil_validation_moyenne: String(regles.seuil_validation_moyenne),
        seuil_eliminatoire: String(regles.seuil_eliminatoire),
        seuil_rattrapage_minimale: String(regles.seuil_rattrapage_minimale),
        seuil_passage_conditionnel_ects: String(regles.seuil_passage_conditionnel_ects),
        compensation_autorisee: regles.compensation_autorisee,
        confirme: regles.confirmee,
      });
      setBareme(regles.bareme_mentions);
    }
  }, [regles, ouvert]);

  const enregistrer = async () => {
    setEnvoi(true);
    const resultat = await deliberationApi.updateRegles({
      seuil_validation_moyenne: Number(valeurs.seuil_validation_moyenne),
      seuil_eliminatoire: Number(valeurs.seuil_eliminatoire),
      seuil_rattrapage_minimale: Number(valeurs.seuil_rattrapage_minimale),
      seuil_passage_conditionnel_ects: Number(valeurs.seuil_passage_conditionnel_ects),
      compensation_autorisee: valeurs.compensation_autorisee,
      bareme_mentions: bareme,
      confirme: valeurs.confirme,
    });
    setEnvoi(false);
    if (resultat.error) {
      toast.error(extractErrorMessage(resultat.error, "Règlement non enregistré."));
      return;
    }
    toast.success(messageConfirmation(valeurs.confirme));
    await onEnregistre();
  };

  return (
    <Dialog open={ouvert} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Règlement de délibération</DialogTitle>
          <DialogDescription>
            Un règlement académique n'est pas une constante technique. Les valeurs
            appliquées sont figées dans chaque séance : les changer n'affecte que les
            prochaines.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 sm:grid-cols-2">
          <ChampNombre
            label="Moyenne de validation (/20)"
            valeur={valeurs.seuil_validation_moyenne}
            onChange={(v) => setValeurs((c) => ({ ...c, seuil_validation_moyenne: v }))}
          />
          <ChampNombre
            label="Rattrapage à partir de (/20)"
            valeur={valeurs.seuil_rattrapage_minimale}
            onChange={(v) => setValeurs((c) => ({ ...c, seuil_rattrapage_minimale: v }))}
          />
          <ChampNombre
            label="Note éliminatoire en dessous de (/20)"
            valeur={valeurs.seuil_eliminatoire}
            onChange={(v) => setValeurs((c) => ({ ...c, seuil_eliminatoire: v }))}
          />
          <ChampNombre
            label="Passage conditionnel (ECTS)"
            valeur={valeurs.seuil_passage_conditionnel_ects}
            onChange={(v) =>
              setValeurs((c) => ({ ...c, seuil_passage_conditionnel_ects: v }))
            }
          />
        </div>

        <div className="flex items-center gap-2">
          <input
            id="compensation"
            type="checkbox"
            checked={valeurs.compensation_autorisee}
            onChange={(e) =>
              setValeurs((c) => ({ ...c, compensation_autorisee: e.target.checked }))
            }
          />
          <Label htmlFor="compensation">Compensation entre UE autorisée</Label>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label>Barème des mentions</Label>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                setBareme((c) => [...c, { libelle: "", seuil_min: 0 }])
              }
            >
              <Plus className="mr-2 h-4 w-4" /> Ajouter
            </Button>
          </div>
          {bareme.map((entree, index) => (
            <div key={index} className="flex items-end gap-2">
              <div className="flex-1">
                <Input
                  aria-label="Libellé de la mention"
                  value={entree.libelle}
                  placeholder="Libellé"
                  onChange={(e) =>
                    setBareme((c) =>
                      c.map((item, i) =>
                        i === index ? { ...item, libelle: e.target.value } : item
                      )
                    )
                  }
                />
              </div>
              <div className="w-28">
                <Input
                  aria-label="Seuil de la mention"
                  type="number"
                  step="0.5"
                  value={entree.seuil_min}
                  onChange={(e) =>
                    setBareme((c) =>
                      c.map((item, i) =>
                        i === index ? { ...item, seuil_min: Number(e.target.value) } : item
                      )
                    )
                  }
                />
              </div>
              <Button
                variant="ghost"
                size="sm"
                aria-label="Retirer la mention"
                onClick={() => setBareme((c) => c.filter((_, i) => i !== index))}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>

        <div className="flex items-start gap-2 rounded-lg border p-3">
          <input
            id="confirme"
            type="checkbox"
            className="mt-1"
            checked={valeurs.confirme}
            onChange={(e) => setValeurs((c) => ({ ...c, confirme: e.target.checked }))}
          />
          <div>
            <Label htmlFor="confirme">L'établissement valide ce règlement</Label>
            <p className="text-xs text-muted-foreground">
              Sans cette confirmation, le règlement reste signalé « à confirmer » et
              les procès-verbaux le mentionnent.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Annuler
          </Button>
          <Button onClick={() => void enregistrer()} disabled={envoi || bareme.length === 0}>
            {envoi ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Enregistrer
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

const messageConfirmation = (confirme: boolean): string =>
  confirme
    ? "Règlement enregistré et confirmé par l'établissement."
    : "Règlement enregistré, mais toujours non confirmé.";

interface SeanceDialogProps {
  ouvert: boolean;
  seancesExistantes: Deliberation[];
  onClose: () => void;
  onCree: (id: string) => Promise<void>;
}

const SeanceDialog = ({ ouvert, seancesExistantes, onClose, onCree }: SeanceDialogProps) => {
  const [classes, setClasses] = useState<{ id: string; nom: string }[]>([]);
  const [sessions, setSessions] = useState<{ id: string; nom: string }[]>([]);
  const [promotion, setPromotion] = useState("");
  const [session, setSession] = useState("");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [lieu, setLieu] = useState("");
  const [president, setPresident] = useState("");
  const [membres, setMembres] = useState<{ nom: string; qualite: string }[]>([
    { nom: "", qualite: "" },
  ]);
  const [envoi, setEnvoi] = useState(false);

  useEffect(() => {
    if (!ouvert) return;
    // Les promotions et sessions viennent de l'API : rien n'est saisi a la main
    // dans un identifiant, et rien n'est invente.
    void Promise.all([academicApi.getClasses(), sessionsApi.getAll()]).then(
      ([promotions, listeSessions]) => {
        setClasses(
          (promotions.data ?? []).map((classe) => ({
            id: String(classe.id),
            nom: String(classe.nom ?? classe.code ?? classe.id),
          }))
        );
        setSessions(
          (listeSessions.data ?? []).map((item) => ({
            id: String(item.id),
            nom: String(item.nom),
          }))
        );
      }
    );
  }, [ouvert]);

  const dejaOuverte = seancesExistantes.some(
    (s) => s.classe_id === promotion && s.session_id === session
  );

  const creer = async () => {
    setEnvoi(true);
    const resultat = await deliberationApi.create({
      classe_id: promotion,
      session_id: session,
      date_deliberation: date,
      president,
      lieu: lieu || null,
      membres: membres.filter((m) => m.nom.trim()).map((m) => ({ nom: m.nom, qualite: m.qualite })),
    });
    setEnvoi(false);
    if (resultat.error || !resultat.data) {
      toast.error(extractErrorMessage(resultat.error, "Séance non ouverte."));
      return;
    }
    toast.success("Séance ouverte.");
    await onCree(resultat.data.id);
  };

  return (
    <Dialog open={ouvert} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Ouvrir une séance de jury</DialogTitle>
          <DialogDescription>
            La composition du jury est saisie, jamais déduite : un procès-verbal qui
            inventerait ses membres n'aurait aucune valeur.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="promotion-seance">Promotion</Label>
              <Select value={promotion} onValueChange={setPromotion}>
                <SelectTrigger id="promotion-seance">
                  <SelectValue placeholder="Sélectionner une promotion" />
                </SelectTrigger>
                <SelectContent>
                  {classes.map((classe) => (
                    <SelectItem key={classe.id} value={classe.id}>
                      {classe.nom}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="session-seance">Session</Label>
              <Select value={session} onValueChange={setSession}>
                <SelectTrigger id="session-seance">
                  <SelectValue placeholder="Sélectionner une session" />
                </SelectTrigger>
                <SelectContent>
                  {sessions.map((item) => (
                    <SelectItem key={item.id} value={item.id}>
                      {item.nom}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="date-seance">Date de la séance</Label>
              <Input
                id="date-seance"
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="lieu-seance">Lieu</Label>
              <Input
                id="lieu-seance"
                value={lieu}
                onChange={(e) => setLieu(e.target.value)}
                placeholder="Salle du conseil"
              />
            </div>
          </div>

          {dejaOuverte && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Une séance existe déjà pour cette promotion et cette session. Deux
                procès-verbaux contradictoires ne peuvent pas coexister.
              </AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <Label htmlFor="president">Président de jury</Label>
            <Input
              id="president"
              value={president}
              onChange={(e) => setPresident(e.target.value)}
              placeholder="Nom du président"
            />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Membres du jury</Label>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setMembres((c) => [...c, { nom: "", qualite: "" }])}
              >
                <Plus className="mr-2 h-4 w-4" /> Ajouter
              </Button>
            </div>
            {membres.map((membre, index) => (
              <div key={index} className="flex gap-2">
                <Input
                  aria-label="Nom du membre"
                  value={membre.nom}
                  placeholder="Nom"
                  onChange={(e) =>
                    setMembres((c) =>
                      c.map((m, i) => (i === index ? { ...m, nom: e.target.value } : m))
                    )
                  }
                />
                <Input
                  aria-label="Qualité du membre"
                  value={membre.qualite}
                  placeholder="Qualité"
                  onChange={(e) =>
                    setMembres((c) =>
                      c.map((m, i) => (i === index ? { ...m, qualite: e.target.value } : m))
                    )
                  }
                />
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label="Retirer le membre"
                  onClick={() => setMembres((c) => c.filter((_, i) => i !== index))}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Annuler
          </Button>
          <Button
            onClick={() => void creer()}
            disabled={
              envoi ||
              dejaOuverte ||
              !promotion ||
              !session ||
              president.trim().length < 2 ||
              membres.every((m) => !m.nom.trim())
            }
          >
            {envoi ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Ouvrir la séance
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

interface DecisionDialogProps {
  proposition: PropositionEtudiant | null;
  bareme: { libelle: string; seuil_min: number }[];
  onClose: () => void;
  onEnregistre: (statut: string, mention: string | null, motif: string) => Promise<void> | void;
  /**
   * Enregistre les decisions du jury, unite par unite. C'est un **second**
   * enregistrement : le verdict d'ensemble et le sort de chaque UE sont deux
   * ecrits distincts, et l'agent peut trancher l'un sans l'autre. Un seul
   * bouton quiPretendrait faire les deux mentirait sur ce qu'il fait.
   */
  onEnregistreUnites: (
    decisions: Array<{
      ue_id: string;
      validation: ValidationUE;
      credits_obtenus?: number | null;
      mention?: string | null;
      motif?: string | null;
    }>
  ) => Promise<void>;
  enCours?: boolean;
}

/** Les decisions par UE, que le jury confirme ou corrige. */
const DecisionUnitesGrid = ({
  proposition,
  onEnregistre,
  enCours,
}: {
  proposition: PropositionEtudiant;
  onEnregistre: DecisionDialogProps["onEnregistreUnites"];
  enCours?: boolean;
}) => {
  // ``entrees`` est **memoise** : sans cela il serait un nouveau tableau a
  // chaque rendu, et l'effet de reinitialisation en dessous — qui depend de
  // lui — se relancerait indefiniment, en effacant les choix du jury a chaque
  // frappe.
  const entrees = useMemo(
    () => Object.entries(proposition.moyennes_ue ?? {}),
    [proposition.moyennes_ue]
  );
  // Index unique, construit une fois. Le recomputer dans une boucle — ou
  // utiliser ``Object.fromEntries`` a chaque rendu — transforme un tableau de
  // six elements en travail repete, et masque le lecteur derriere du bruit.
  const parUe: Record<string, MoyenneUEProposee> = {};
  for (const [ueId, brut] of entrees) parUe[ueId] = brut as MoyenneUEProposee;

  // Point de depart : la proposition du moteur, ou la decision deja prise si
  // le jury a tranche. Un jury qui revient sur une seance en cours retrouve
  // ce qu'il avait dit, pas la proposition — la difference est entiere.
  const [choix, setChoix] = useState<Record<string, ValidationUE>>({});
  const [motifs, setMotifs] = useState<Record<string, string>>({});

  useEffect(() => {
    const depart: Record<string, ValidationUE> = {};
    for (const [ueId, entree] of entrees) {
      const retenue = (entree as MoyenneUEProposee);
      depart[ueId] =
        (retenue.validation as ValidationUE | undefined) ??
        (retenue.proposition_validation as ValidationUE | undefined) ??
        "À reprendre";
    }
    setChoix(depart);
    setMotifs({});
  }, [entrees]);

  if (entrees.length === 0) {
    // Aucune UE : ce n'est pas un etat vide banal. Cela veut dire que le
    // moteur n'a rien a proposer, donc que les moyennes sont illisibles ou
    // qu'aucune UE ne porte de credits. Le dire, plutot que d'afficher un
    // tableau sans ligne que l'agent prendrait pour « tout est tranche ».
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Aucune unité d'enseignement à trancher</AlertTitle>
        <AlertDescription>
          Le moteur n'a produit aucune moyenne par UE pour cet étudiant. Le
          verdict d'ensemble reste enregistrable, mais aucune décision par UE
          ne peut l'être : vérifiez que les matières sont rattachées à une UE et
          que cette UE porte des crédits.
        </AlertDescription>
      </Alert>
    );
  }

  const ecarts = entrees.filter(([ueId]) => {
    const proposee = parUe[ueId]?.proposition_validation;
    if (!proposee) return false;
    if (choix[ueId] === proposee) return false;
    return !(motifs[ueId] ?? "").trim();
  });

  const tranchees = entrees.filter(([ueId]) => !!parUe[ueId]?.validation).length;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <Label>Décision par unité d'enseignement</Label>
        <Badge variant="outline">
          {tranchees} / {entrees.length} tranchées
        </Badge>
      </div>

      <p className="text-xs text-muted-foreground">
        Ces décisions commandent le rattrapage : une UE « À reprendre » donne
        droit à une seconde épreuve sur ses matières. Elles s'enregistrent à
        part du verdict d'ensemble — le jury peut trancher l'un sans l'autre.
      </p>

      <div className="max-h-72 overflow-y-auto rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>UE</TableHead>
              <TableHead className="text-right">Moyenne</TableHead>
              <TableHead className="text-right">ECTS</TableHead>
              <TableHead>Proposition</TableHead>
              <TableHead>Décision du jury</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {entrees.map(([ueId]) => {
              const ue = parUe[ueId];
              const retenue = choix[ueId];
              const proposition_ = ue.proposition_validation;
              const dejaTranchee = !!ue.validation;
              const ecart = !!proposition_ && retenue !== proposition_;

              return (
                <TableRow key={ueId}>
                  <TableCell>
                    <div className="font-medium">{ue.code}</div>
                    <div className="text-xs text-muted-foreground">{ue.ue}</div>
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {ue.moyenne.toFixed(2).replace(".", ",")}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{ue.ects}</TableCell>
                  <TableCell>
                    {proposition_ ? (
                      <Badge variant="secondary">{proposition_}</Badge>
                    ) : (
                      <span className="text-xs text-muted-foreground">
                        aucune
                      </span>
                    )}
                    {dejaTranchee && (
                      <p className="mt-1 text-xs text-muted-foreground">
                        Déjà tranché : {ue.validation}
                      </p>
                    )}
                  </TableCell>
                  <TableCell>
                    <Select
                      value={retenue}
                      onValueChange={(valeur) =>
                        setChoix((precedent) => ({
                          ...precedent,
                          [ueId]: valeur as ValidationUE,
                        }))
                      }
                    >
                      <SelectTrigger aria-label={`Décision pour ${ue.code}`}>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {VALIDATIONS_UE.map((item) => (
                          <SelectItem key={item} value={item}>
                            {item}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {ecart && (
                      <Input
                        className="mt-2"
                        value={motifs[ueId] ?? ""}
                        onChange={(e) =>
                          setMotifs((precedent) => ({
                            ...precedent,
                            [ueId]: e.target.value,
                          }))
                        }
                        placeholder="Motif de l'écart (obligatoire)"
                        aria-label={`Motif pour ${ue.code}`}
                      />
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      {ecarts.length > 0 && (
        <p className="text-xs text-destructive">
          {ecarts.length} écart(s) avec la proposition du moteur sans motif. Le
          serveur les refuse : un verdict non motive reste inexplicable.
        </p>
      )}

      <Button
        variant="outline"
        className="w-full"
        disabled={enCours || ecarts.length > 0}
        onClick={() =>
          void onEnregistre(
            entrees.map(([ueId]) => {
              const ue = parUe[ueId];
              return {
                ue_id: ueId,
                validation: choix[ueId],
                // « À reprendre » vaut zero credit, et le serveur l'impose
                // aussi. L'ecran ne propose donc pas un total qu'il refuserait.
                credits_obtenus:
                  choix[ueId] === "À reprendre" ? 0 : (ue?.ects ?? null),
                mention: ue?.proposition_mention ?? null,
                motif: (motifs[ueId] ?? "").trim() || null,
              };
            })
          )
        }
      >
        Consigner les décisions par UE
      </Button>
    </div>
  );
};

const DecisionDialog = ({
  proposition,
  bareme,
  onClose,
  onEnregistre,
  onEnregistreUnites,
  enCours,
}: DecisionDialogProps) => {
  const [statut, setStatut] = useState<string>("Admis");
  const [mention, setMention] = useState<string>("");
  const [motif, setMotif] = useState("");

  useEffect(() => {
    if (proposition) {
      // On propose la decision du moteur comme point de depart : le jury
      // confirme ou s'ecarte, il ne repart pas de zero.
      setStatut(proposition.proposition_statut);
      setMention(proposition.proposition_mention ?? "");
      setMotif("");
    }
  }, [proposition]);

  if (!proposition) return null;

  const suggestion = mentionPour(proposition.moyenne_generale, bareme);
  const ecart =
    statut !== proposition.proposition_statut ||
    (mention || proposition.proposition_mention || "") !==
      (proposition.proposition_mention || "");
  const motifObligatoire = ecart;

  const mentionsDisponibles =
    statut === "Admis"
      ? bareme.map((entree) => entree.libelle)
      : [statut];

  return (
    <Dialog open={Boolean(proposition)} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Décision du jury</DialogTitle>
          <DialogDescription>
            {proposition.matricule} — {proposition.nom} {proposition.prenom} · moyenne{" "}
            {proposition.moyenne_generale}/20 · {proposition.ects_acquis}/
            {proposition.ects_total} ECTS
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="rounded-lg border bg-muted/30 p-3 text-sm">
            <p className="font-medium">Proposition du moteur</p>
            <p className="text-muted-foreground">
              {proposition.proposition_statut}
              {proposition.proposition_mention ? ` — ${proposition.proposition_mention}` : ""}
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="decision-statut">Décision</Label>
            <Select value={statut} onValueChange={setStatut}>
              <SelectTrigger id="decision-statut">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STATUTS.map((item) => (
                  <SelectItem key={item} value={item}>
                    {item}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {statut === "Admis" && (
            <div className="space-y-2">
              <Label htmlFor="decision-mention">Mention</Label>
              <Select value={mention} onValueChange={setMention}>
                <SelectTrigger id="decision-mention">
                  <SelectValue placeholder="Choisir une mention" />
                </SelectTrigger>
                <SelectContent>
                  {mentionsDisponibles.map((item) => (
                    <SelectItem key={item} value={item}>
                      {item}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {suggestion && suggestion !== mention && (
                <p className="text-xs text-muted-foreground">
                  Le barème situe cet étudiant à « {suggestion} ».
                </p>
              )}
            </div>
          )}

          {motifObligatoire && (
            <div className="space-y-2">
              <Label htmlFor="motif-ecart">
                Motif de l'écart <span className="text-destructive">*</span>
              </Label>
              <Textarea
                id="motif-ecart"
                value={motif}
                onChange={(e) => setMotif(e.target.value)}
                placeholder="Pourquoi le jury décide-t-il autrement que la proposition ?"
                rows={3}
              />
              <p className="text-xs text-muted-foreground">
                Sans motif, l'écart serait inexpliqué : le serveur le refuse.
              </p>
            </div>
          )}

          {/* Le sort de chaque UE, à part du verdict d'ensemble. */}
          <div className="border-t pt-4">
            <DecisionUnitesGrid
              proposition={proposition}
              onEnregistre={onEnregistreUnites}
              enCours={enCours}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Annuler
          </Button>
          <Button
            onClick={() =>
              void onEnregistre(statut, statut === "Admis" ? mention || null : statut, motif)
            }
            disabled={motifObligatoire && !motif.trim()}
          >
            Consigner la décision
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

const ChampNombre = ({
  label,
  valeur,
  onChange,
}: {
  label: string;
  valeur: string;
  onChange: (valeur: string) => void;
}) => (
  <div className="space-y-2">
    <Label>{label}</Label>
    <Input
      type="number"
      step="0.5"
      min="0"
      max="20"
      value={valeur}
      onChange={(e) => onChange(e.target.value)}
    />
  </div>
);

export default DeliberationPage;
