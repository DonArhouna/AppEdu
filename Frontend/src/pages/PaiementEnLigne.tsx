/**
 * Paiement en ligne — page publique de la famille (lot 4b).
 *
 * Accessible sans compte, gardée par le jeton du lien : ce que la page
 * montre est exactement le résumé que le serveur accepte de livrer à un
 * porteur de lien — établissement, élève, facture, reste à payer. Aucune
 * navigation, aucun accès au reste de l'application : la famille paie,
 * lit son reçu, et ferme l'onglet.
 */

import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { CheckCircle2, Clock, Landmark, Loader2, ShieldCheck, XCircle } from "lucide-react";
import { toast } from "sonner";
import { financesApi, extractErrorMessage } from "@/services/apiClient";
import type { ConfirmationPaiement, ResumeFamille } from "@/services/apiTypes";

type Etat =
  | { kind: "chargement" }
  | { kind: "resume"; resume: ResumeFamille }
  | { kind: "confirme"; confirmation: ConfirmationPaiement; resume: ResumeFamille }
  | { kind: "morte"; message: string };

const PaiementEnLigne = () => {
  const { token } = useParams<{ token: string }>();
  const [etat, setEtat] = useState<Etat>({ kind: "chargement" });
  const [enCours, setEnCours] = useState(false);

  const charger = useCallback(async () => {
    if (!token) {
      setEtat({ kind: "morte", message: "Lien inconnu." });
      return;
    }
    const resultat = await financesApi.lireLienPaiement(token);
    if (resultat.error || !resultat.data) {
      setEtat({ kind: "morte", message: extractErrorMessage(resultat.error, "Lien inconnu.") });
      return;
    }
    setEtat({ kind: "resume", resume: resultat.data });
  }, [token]);

  useEffect(() => {
    void charger();
  }, [charger]);

  const confirmer = async () => {
    if (!token || !("resume" in etat)) return;
    setEnCours(true);
    const resultat = await financesApi.confirmerLienPaiement(token, {});
    if (resultat.error || !resultat.data) {
      setEnCours(false);
      const message = extractErrorMessage(resultat.error, "Le paiement n'a pas pu être confirmé.");
      // Un lien devenu mort bascule l'écran, pas seulement un toast : la
      // famille doit comprendre que le lien est terminé, pas « retenter ».
      if (resultat.status === 410) {
        setEtat({ kind: "morte", message });
        return;
      }
      toast.error(message);
      return;
    }
    setEtat({ kind: "confirme", confirmation: resultat.data, resume: (etat as { resume: ResumeFamille }).resume });
    setEnCours(false);
  };

  const montant = (valeur: number | null | undefined) =>
    valeur == null ? "—" : `${valeur.toLocaleString("fr-FR")} ${"resume" in etat ? etat.resume.devise : ""}`;

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 p-4">
      <div className="w-full max-w-lg space-y-6">
        <div className="flex items-center justify-center gap-2 text-center">
          <Landmark className="h-6 w-6 text-primary" />
          <span className="text-lg font-semibold tracking-tight">Paiement des frais de scolarité</span>
        </div>

        {etat.kind === "chargement" && (
          <Card>
            <CardContent className="space-y-3 p-6">
              <Skeleton className="h-6 w-40" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-10 w-full" />
            </CardContent>
          </Card>
        )}

        {etat.kind === "morte" && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-destructive">
                <XCircle className="h-5 w-5" />
                Lien indisponible
              </CardTitle>
              <CardDescription>{etat.message}</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Contactez le secrétariat de l'établissement pour obtenir un nouveau lien de paiement.
              </p>
            </CardContent>
          </Card>
        )}

        {etat.kind === "resume" && (
          <Card>
            <CardHeader>
              <CardTitle>{etat.resume.etablissement}</CardTitle>
              <CardDescription>
                Paiement pour <strong>{etat.resume.etudiant}</strong>
                {etat.resume.matricule ? ` (${etat.resume.matricule})` : ""}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {etat.resume.facture && (
                <div className="rounded-lg border p-4 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">Facture {etat.resume.facture.numero}</span>
                    <Badge variant="outline">
                      <Clock className="mr-1 h-3 w-3" />
                      expire le {new Date(etat.resume.expire_le).toLocaleDateString("fr-FR")}
                    </Badge>
                  </div>
                  <Separator className="my-3" />
                  <dl className="space-y-1.5">
                    <div className="flex justify-between">
                      <dt className="text-muted-foreground">Montant total</dt>
                      <dd>{montant(etat.resume.facture.montant_total)}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-muted-foreground">Déjà réglé</dt>
                      <dd>{montant(etat.resume.facture.montant_paye)}</dd>
                    </div>
                    <div className="flex justify-between font-medium">
                      <dt>Reste à payer</dt>
                      <dd>{montant(etat.resume.facture.reste_a_payer)}</dd>
                    </div>
                  </dl>
                </div>
              )}

              <div className="flex items-center justify-between rounded-lg bg-primary/5 p-4">
                <div>
                  <p className="text-sm text-muted-foreground">Montant à payer</p>
                  <p className="text-xl font-bold text-primary">{montant(etat.resume.montant_demande)}</p>
                </div>
                <Badge variant="secondary">{etat.resume.provider === "simulation" ? "Mode démonstration" : etat.resume.provider}</Badge>
              </div>

              <Button className="w-full" size="lg" onClick={() => void confirmer()} disabled={enCours}>
                {enCours ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Confirmation en cours...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="mr-2 h-4 w-4" /> Payer {montant(etat.resume.montant_demande)}
                  </>
                )}
              </Button>
              <p className="flex items-center justify-center gap-1.5 text-xs text-muted-foreground">
                <ShieldCheck className="h-3.5 w-3.5" />
                Un reçu numéroté vous sera délivré dès la confirmation.
              </p>
            </CardContent>
          </Card>
        )}

        {etat.kind === "confirme" && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-emerald-600">
                <CheckCircle2 className="h-6 w-6" />
                Paiement confirmé
              </CardTitle>
              <CardDescription>
                {etat.resume.etablissement} a bien reçu votre paiement.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-lg border p-4 text-sm">
                <dl className="space-y-1.5">
                  <div className="flex justify-between">
                    <dt className="text-muted-foreground">Montant payé</dt>
                    <dd className="font-semibold">{montant(etat.confirmation.montant)}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-muted-foreground">Numéro de reçu</dt>
                    <dd className="font-mono font-semibold">{etat.confirmation.numero_recu}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-muted-foreground">Mode</dt>
                    <dd>{etat.confirmation.mode_paiement}</dd>
                  </div>
                </dl>
              </div>
              <Alert>
                <CheckCircle2 className="h-4 w-4" />
                <AlertTitle>Conservez ce numéro de reçu</AlertTitle>
                <AlertDescription>
                  Il atteste votre paiement auprès du secrétariat. Un reçu imprimable est
                  disponible sur demande.
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default PaiementEnLigne;
