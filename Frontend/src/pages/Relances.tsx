/**
 * Échéances & relances : qui doit être relancé, et ce qui a déjà été fait.
 *
 * L'écran est construit autour d'une distinction que le recouvrement impose :
 *
 * - une **créance** est un fait calculé — une facture échue non soldée ;
 * - une **relance** est un **acte constaté** — quelqu'un a contacté
 *   l'étudiant, par un moyen donné, pour un montant donné.
 *
 * L'application n'envoie rien : elle n'a aucune identité de messagerie, et
 * prétendre contacter l'étudiant serait faux. Elle trace ce que le
 * secrétariat a fait, pour qu'on ne relance pas deux fois de suite, et pour
 * qu'un encaissement puisse être rattaché à la relance qui l'a provoqué.
 *
 * Le montant d'une relance est **figé** au moment où elle est consignée : si
 * la facture est soldée depuis, l'historique continue de dire ce qui avait
 * été réclamé.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  BellRing,
  CalendarClock,
  CheckCircle2,
  Clock,
  Loader2,
  Mail,
  Phone,
  Printer,
  RefreshCw,
  Search,
  Send,
} from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { KpiCard } from "@/components/ui/kpi-card";
import { useRBAC } from "@/contexts/RBACContext";
import { extractErrorMessage, relancesApi } from "@/services/apiClient";
import type { EtudiantARelancer, Relance, SyntheseRelances } from "@/services/apiTypes";
import { toast } from "sonner";

const dateFr = (iso: string | null | undefined): string => {
  if (!iso) return "—";
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? iso
    : date.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric" });
};

const montant = (valeur: number, devise: string): string =>
  `${valeur.toLocaleString("fr-FR")} ${devise || "FCFA"}`;

/** Retenu d'apres l'anciennete, avec les memes paliers que la balance agee. */
const palier = (jours: number): { libelle: string; className: string } => {
  if (jours > 60) return { libelle: "+60 jours", className: "bg-red-600 text-white" };
  if (jours > 30) return { libelle: "31–60 jours", className: "bg-amber-600 text-white" };
  return { libelle: "1–30 jours", className: "bg-amber-500/20 text-amber-700 dark:text-amber-300" };
};

const RelancesPage = () => {
  const { hasPermission } = useRBAC();
  // Relancer est un acte de recouvrement, pas une consultation : lecture et
  // ecriture ne vont pas au meme profil.
  const peutRelancer = hasPermission("finance.write");

  const [synthese, setSynthese] = useState<SyntheseRelances | null>(null);
  const [historique, setHistorique] = useState<Relance[]>([]);
  const [moyens, setMoyens] = useState<string[]>([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [recherche, setRecherche] = useState("");
  const [retardMin, setRetardMin] = useState("1");
  const [actif, setActif] = useState<EtudiantARelancer | null>(null);
  const [envoi, setEnvoi] = useState(false);

  const charger = useCallback(async () => {
    setChargement(true);
    setErreur(null);
    const [suivi, histo, listeMoyens] = await Promise.all([
      relancesApi.getARelancer({ retardMinimum: Number(retardMin) || 1 }),
      relancesApi.historique(),
      relancesApi.getMoyens(),
    ]);
    if (suivi.error) {
      setErreur(extractErrorMessage(suivi.error, "Créances illisibles."));
      setSynthese(null);
    } else if (suivi.data) {
      setSynthese(suivi.data);
    }
    setHistorique(histo.data ?? []);
    setMoyens(listeMoyens.data ?? []);
    setChargement(false);
  }, [retardMin]);

  useEffect(() => {
    void charger();
  }, [charger]);

  const filtres = useMemo(() => {
    const terme = recherche.trim().toLowerCase();
    if (!terme || !synthese) return synthese?.items ?? [];
    return synthese.items.filter((item) =>
      [item.nom, item.prenom, item.matricule, item.filiere]
        .filter(Boolean)
        .some((champ) => String(champ).toLowerCase().includes(terme))
    );
  }, [recherche, synthese]);

  const consigner = async (moyen: string, message: string) => {
    if (!actif) return;
    setEnvoi(true);
    const resultat = await relancesApi.enregistrer({
      etudiant_id: actif.etudiant_id,
      moyen,
      message: message.trim() || null,
    });
    setEnvoi(false);
    setActif(null);

    if (resultat.error || !resultat.data) {
      toast.error(extractErrorMessage(resultat.error, "Relance non consignée."));
      return;
    }
    const resume = resultat.data.resume as { niveau?: number };
    toast.success(
      `${resume.niveau ?? 1}re relance consignée — ${montant(
        resultat.data.relance.montant_reclame,
        synthese?.devise ?? ""
      )} réclamés.`
    );
    await charger();
  };

  const constaterSolde = async (etudiantId: string, niveau: number) => {
    const resultat = await relancesApi.constaterSolde(etudiantId, niveau);
    if (resultat.error) {
      toast.error(extractErrorMessage(resultat.error, "Solde non constaté."));
      return;
    }
    const solde = (resultat.data?.solde_apres ?? 0) as number;
    toast.success(
      solde <= 0
        ? `Relance ${niveau} soldée : la dette est réglée.`
        : `Solde après la relance ${niveau} : ${montant(solde, synthese?.devise ?? "")}.`
    );
    await charger();
  };

  /**
   * TelCharge la lettre et la remet a l'agent.
   *
   * L'URL d'objet est revoquee aussitot apres le clic : sans cela, chaque
   * impression laisse un blob en memoire pour toute la session.
   */
  const telechargerLettre = async (relanceId: string) => {
    const resultat = await relancesApi.getLettre(relanceId);
    if (resultat.error || !resultat.data) {
      toast.error(extractErrorMessage(resultat.error, "Lettre indisponible."));
      return;
    }
    const url = URL.createObjectURL(resultat.data);
    const lien = document.createElement("a");
    lien.href = url;
    // Reference de la relance : le fichier se retrouve sans renommer a la main.
    lien.download = `relance-${relanceId.slice(0, 8)}.pdf`;
    document.body.appendChild(lien);
    lien.click();
    document.body.removeChild(lien);
    URL.revokeObjectURL(url);
    toast.success("Lettre téléchargée.");
  };

  /**
   * Envoie la lettre par email. Un 502 (« echec ») reste sur l'écran : la
   * relance est conservée, l'envoi se retente — l'application ne prétend
   * jamais avoir contacté un étudiant qu'elle n'a pas contacté.
   */
  const envoyerParEmail = async (relanceId: string) => {
    const resultat = await relancesApi.envoyerLettreEmail(relanceId);
    if (resultat.error || !resultat.data) {
      toast.error(extractErrorMessage(resultat.error, "Envoi impossible."));
      return;
    }
    const statut = resultat.data.email_statut;
    if (statut === "simule") {
      toast.warning(
        "Envoi simulé : aucun serveur SMTP n'est configuré. La relance est tracée, mais aucun email n'est parti.",
        { duration: 8000 }
      );
    } else {
      toast.success("Lettre envoyée par email.");
    }
    await charger();
  };

  if (chargement && !synthese) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-72" />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-28 w-full" />
          ))}
        </div>
        <Skeleton className="h-72 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">
            Échéances & relances
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            Les factures échues non soldées, par ancienneté de retard. L'application
            n'envoie rien : elle trace les relances que vous constatez, pour ne pas
            relancer deux fois et pour rattacher un encaissement à sa relance.
          </p>
        </div>
        <Button variant="outline" onClick={charger} disabled={chargement}>
          <RefreshCw className={`mr-2 h-4 w-4 ${chargement ? "animate-spin" : ""}`} />
          Actualiser
        </Button>
      </div>

      {erreur && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Module indisponible</AlertTitle>
          <AlertDescription>{erreur}</AlertDescription>
        </Alert>
      )}

      {synthese && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard
              title="Total à relancer"
              value={montant(synthese.total_du, synthese.devise)}
              icon={BellRing}
              subtitle={`${synthese.nb_etudiants} étudiant(s), ${synthese.nb_creances} facture(s)`}
              colorVariant="primary"
            />
            <KpiCard
              title="1 à 30 jours"
              value={montant(synthese.retard_1_30, synthese.devise)}
              icon={Clock}
              subtitle="Relance de rappel"
              colorVariant="amber"
            />
            <KpiCard
              title="31 à 60 jours"
              value={montant(synthese.retard_31_60, synthese.devise)}
              icon={CalendarClock}
              subtitle="Deuxième relance"
              colorVariant="amber"
            />
            <KpiCard
              title="Plus de 60 jours"
              value={montant(synthese.retard_plus_60, synthese.devise)}
              icon={AlertCircle}
              subtitle="Créance ancienne"
              colorVariant="rose"
            />
          </div>

          <Tabs defaultValue="a-relancer">
            <TabsList>
              <TabsTrigger value="a-relancer">
                À relancer ({synthese.nb_etudiants})
              </TabsTrigger>
              <TabsTrigger value="historique">
                Historique ({historique.length})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="a-relancer" className="space-y-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                <div className="flex-1 space-y-2">
                  <Label htmlFor="recherche-relance">Rechercher</Label>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      id="recherche-relance"
                      value={recherche}
                      onChange={(evenement) => setRecherche(evenement.target.value)}
                      placeholder="Nom, prénom, matricule ou filière"
                      className="pl-9"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="retard-minimum">Retard minimum</Label>
                  <Select value={retardMin} onValueChange={setRetardMin}>
                    <SelectTrigger id="retard-minimum" className="w-56">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0">Dès l'échéance</SelectItem>
                      <SelectItem value="1">1 jour ou plus</SelectItem>
                      <SelectItem value="15">15 jours ou plus</SelectItem>
                      <SelectItem value="30">30 jours ou plus</SelectItem>
                      <SelectItem value="60">60 jours ou plus</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {filtres.length === 0 ? (
                <div className="rounded-lg border border-dashed py-12 text-center">
                  <CheckCircle2 className="mx-auto h-8 w-8 text-muted-foreground" />
                  <p className="mt-3 font-medium">Aucune créance à relancer</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {synthese.nb_etudiants === 0
                      ? "Aucune facture échue non soldée. Rien à relancer."
                      : `Aucune créance ne correspond à « ${recherche} » avec un retard d'au moins ${retardMin} jour(s).`}
                  </p>
                </div>
              ) : (
                <div className="rounded-lg border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Étudiant</TableHead>
                        <TableHead>Contact</TableHead>
                        <TableHead className="text-right">Montant dû</TableHead>
                        <TableHead className="text-right">Retard</TableHead>
                        <TableHead>Factures</TableHead>
                        <TableHead>Relances</TableHead>
                        {peutRelancer && <TableHead />}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filtres.map((item) => {
                        const niveau = palier(item.retard_jours);
                        const derniere = item.derniere_relance;
                        // Une relance faite la veille n'a pas besoin d'être
                        // refaite aujourd'hui ; le bouton le dit plutôt que de
                        // laisser relancer à l'aveugle.
                        const tropRecent =
                          item.jours_depuis_derniere !== null &&
                          item.jours_depuis_derniere < 7;
                        return (
                          <TableRow key={item.etudiant_id}>
                            <TableCell>
                              <p className="font-medium">
                                {item.prenom} {item.nom}
                              </p>
                              <p className="font-mono text-xs text-muted-foreground">
                                {item.matricule}
                              </p>
                              {item.filiere && (
                                <p className="text-xs text-muted-foreground">{item.filiere}</p>
                              )}
                            </TableCell>
                            <TableCell className="text-sm">
                              {item.email && <p>{item.email}</p>}
                              {item.telephone && (
                                <p className="text-muted-foreground">{item.telephone}</p>
                              )}
                              {!item.email && !item.telephone && (
                                <span className="text-muted-foreground">Non renseigné</span>
                              )}
                            </TableCell>
                            <TableCell
                              data-testid="montant-du"
                              className="text-right font-mono font-semibold"
                            >
                              {montant(item.total_du, synthese.devise)}
                            </TableCell>
                            <TableCell className="text-right">
                              <Badge className={niveau.className}>
                                {item.retard_jours} j
                              </Badge>
                            </TableCell>
                            <TableCell className="text-sm text-muted-foreground">
                              {item.creances.map((creance) => (
                                <p key={creance.facture_id}>
                                  {creance.numero} — {montant(creance.reste, synthese.devise)}
                                  <span className="block text-xs">
                                    échue le {dateFr(creance.date_echeance)}
                                  </span>
                                </p>
                              ))}
                            </TableCell>
                            <TableCell className="text-sm">
                              {derniere ? (
                                <>
                                  <Badge variant="secondary">
                                    {derniere.niveau}e relance
                                  </Badge>
                                  <p className="mt-1 text-xs text-muted-foreground">
                                    {dateFr(derniere.date_relance)} · {derniere.moyen}
                                  </p>
                                  {item.jours_depuis_derniere !== null && item.jours_depuis_derniere < 7 && (
                                    <p className="text-xs text-muted-foreground">
                                      il y a {item.jours_depuis_derniere} jour(s)
                                    </p>
                                  )}
                                </>
                              ) : (
                                <span className="text-muted-foreground">Jamais relancé</span>
                              )}
                            </TableCell>
                            {peutRelancer && (
                              <TableCell>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => setActif(item)}
                                  disabled={tropRecent}
                                  title={
                                    tropRecent
                                      ? "Relance faite il y a moins de 7 jours"
                                      : undefined
                                  }
                                >
                                  <Phone className="mr-2 h-4 w-4" />
                                  {derniere ? `Relancer (${item.niveau_suivant}e)` : "Relancer"}
                                </Button>
                              </TableCell>
                            )}
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
              )}
            </TabsContent>

            <TabsContent value="historique" className="space-y-4">
              {historique.length === 0 ? (
                <div className="rounded-lg border border-dashed py-12 text-center">
                  <Printer className="mx-auto h-8 w-8 text-muted-foreground" />
                  <p className="mt-3 font-medium">Aucune relance consignée</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    L'historique se remplira dès qu'une relance sera constatée. Rien n'est
                    pré-rempli : une relance inventée nvaluerait rien.
                  </p>
                </div>
              ) : (
                <div className="rounded-lg border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Étudiant</TableHead>
                        <TableHead className="text-right">Niveau</TableHead>
                        <TableHead className="text-right">Réclamé</TableHead>
                        <TableHead>Date & moyen</TableHead>
                        <TableHead>Retard</TableHead>
                        <TableHead>Suite</TableHead>
                        {/* La lettre est une lecture : elle n'est pas reservee a
                            qui peut consigner une relance. */}
                        <TableHead className="text-right">Document</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {historique.map((relance) => (
                        <TableRow key={relance.id}>
                          <TableCell>
                            <p className="font-medium">
                              {relance.prenom} {relance.nom}
                            </p>
                            <p className="font-mono text-xs text-muted-foreground">
                              {relance.matricule}
                            </p>
                          </TableCell>
                          <TableCell className="text-right">
                            <Badge variant="secondary">{relance.niveau}e</Badge>
                          </TableCell>
                          <TableCell
                            data-testid="montant-reclame-historique"
                            className="text-right font-mono"
                          >
                            {montant(relance.montant_reclame, synthese.devise)}
                          </TableCell>
                          <TableCell className="text-sm">
                            {dateFr(relance.date_relance)}
                            <p className="text-xs text-muted-foreground">{relance.moyen}</p>
                            {relance.relance_par_email && (
                              <p className="text-xs text-muted-foreground">
                                par {relance.relance_par_email}
                              </p>
                            )}
                          </TableCell>
                          <TableCell className="text-sm">{relance.retard_jours} j</TableCell>
                          <TableCell className="text-sm">
                            {relance.solde_apres === null ? (
                              <span className="text-muted-foreground">Non constaté</span>
                            ) : relance.solde_apres <= 0 ? (
                              <span className="font-medium text-emerald-600 dark:text-emerald-400">
                                Soldee
                              </span>
                            ) : (
                              <span>
                                reste {montant(relance.solde_apres, synthese.devise)}
                              </span>
                            )}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-2">
                              {peutRelancer &&
                                relance.solde_apres === null && (
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() =>
                                      void constaterSolde(relance.etudiant_id, relance.niveau)
                                    }
                                  >
                                    <CheckCircle2 className="mr-2 h-4 w-4" />
                                    Constater le solde
                                  </Button>
                                )}
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => void telechargerLettre(relance.id)}
                              >
                                <Printer className="mr-2 h-4 w-4" />
                                Lettre
                              </Button>
                              {peutRelancer && (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => void envoyerParEmail(relance.id)}
                                  title={
                                    relance.email_statut === "envoye"
                                      ? "Lettre déjà envoyée — cliquer renvoie une copie"
                                      : relance.email_statut === "echec"
                                        ? "Dernier envoi échoué — retenter"
                                        : "Envoyer la lettre par email"
                                  }
                                >
                                  <Mail className="mr-2 h-4 w-4" />
                                  Email
                                  {relance.email_statut === "echec" && (
                                    <span className="ml-1 h-2 w-2 rounded-full bg-destructive" aria-hidden />
                                  )}
                                </Button>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </>
      )}

      <DialogRelance
        etudiant={actif}
        moyens={moyens}
        devise={synthese?.devise ?? ""}
        envoi={envoi}
        onClose={() => setActif(null)}
        onConfirmer={(moyen, message) => void consigner(moyen, message)}
      />
    </div>
  );
};

/* -------------------------------------------------------------------------- */
/* Dialogue de constat de relance                                             */
/* -------------------------------------------------------------------------- */
interface DialogRelanceProps {
  etudiant: EtudiantARelancer | null;
  moyens: string[];
  devise: string;
  envoi: boolean;
  onClose: () => void;
  onConfirmer: (moyen: string, message: string) => void;
}

const DialogRelance = ({
  etudiant,
  moyens,
  devise,
  envoi,
  onClose,
  onConfirmer,
}: DialogRelanceProps) => {
  const [moyen, setMoyen] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (etudiant) {
      // Le moyen retenu est une suggestion, pas une decision : la liste
      // vient du serveur, et l'agent choisit.
      setMoyen(moyens[0] ?? "");
      setMessage(
        `Nous vous informons que la facture ${
          etudiant.creances[0]?.numero ?? ""
        } d'un montant de ${montant(etudiant.total_du, devise)} arrive à échéance depuis ${etudiant.retard_jours} jour(s). Nous vous remercions de bien vouloir régulariser votre situation.`
      );
    }
  }, [etudiant, moyens, devise]);

  if (!etudiant) return null;

  return (
    <Dialog open={Boolean(etudiant)} onOpenChange={(ouvert) => !ouvert && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Constater une relance</DialogTitle>
          <DialogDescription>
            Vous avez contacté {etudiant.prenom} {etudiant.nom} ({etudiant.matricule}).
            L'application enregistre ce qui a été fait ; elle n'envoie rien à votre
            place.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="rounded-lg border bg-muted/30 p-3 text-sm">
            <p className="font-medium">
              {etudiant.niveau_suivant}e relance —{" "}
              <span data-testid="montant-reclame">
                {montant(etudiant.total_du, devise)}
              </span>
            </p>
            <p className="text-muted-foreground">
              {etudiant.nb_creances} facture(s) échue(s), retard de {etudiant.retard_jours} jour(s)
              {etudiant.derniere_relance
                ? ` — dernière relance le ${dateFr(etudiant.derniere_relance.date_relance)} par ${etudiant.derniere_relance.moyen}`
                : " — jamais relancé"}
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="moyen-relance">Moyen utilisé</Label>
            <Select value={moyen} onValueChange={setMoyen}>
              <SelectTrigger id="moyen-relance">
                <SelectValue placeholder="Sélectionner un moyen" />
              </SelectTrigger>
              <SelectContent>
                {moyens.map((item) => (
                  <SelectItem key={item} value={item}>
                    {item}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Liste imposée par le serveur : une saisie libre rendrait l'historique
              illisible.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="message-relance">Message transmis</Label>
            <Textarea
              id="message-relance"
              value={message}
              onChange={(evenement) => setMessage(evenement.target.value)}
              rows={4}
            />
            <p className="text-xs text-muted-foreground">
              Conservé avec la relance, pour tracer ce que l'étudiant a reçu.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Annuler
          </Button>
          <Button onClick={() => onConfirmer(moyen, message)} disabled={envoi || !moyen}>
            {envoi ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Send className="mr-2 h-4 w-4" />
            )}
            Consigner la {etudiant.niveau_suivant}e relance
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default RelancesPage;
