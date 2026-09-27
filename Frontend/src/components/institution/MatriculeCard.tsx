/**
 * Nomenclature de matricule : la regle qui numerote les prochains dossiers.
 *
 * L'ecran montre systematiquement un **apercu** du matricule produit. Sans
 * lui, un modele mal saisi n'est decouvert qu'a la creation du dossier suivant
 * — c'est-a-dire sur un etudiant reel, avec un matricule erronee qu'il faudra
 * corriger a la main.
 *
 * Le libelle dit explicitement que la regle ne s'applique qu'aux **prochains**
 * dossiers. C'est la lecture naturelle, et la mauvaise : l'institut croirait
 * renommer des dossiers deja livres.
 */

import { useCallback, useEffect, useState } from "react";
import { AlertCircle, Hash, Loader2, RotateCcw, Save } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { extractErrorMessage, matriculeApi } from "@/services/apiClient";
import type { JetonMatricule, MatriculeParametres } from "@/services/apiTypes";
import { toast } from "sonner";

interface MatriculeCardProps {
  canEdit: boolean;
}

const MatriculeCard = ({ canEdit }: MatriculeCardProps) => {
  const [regle, setRegle] = useState<MatriculeParametres | null>(null);
  const [jetons, setJetons] = useState<JetonMatricule[]>([]);
  const [modele, setModele] = useState("");
  const [largeur, setLargeur] = useState("4");
  const [demarrage, setDemarrage] = useState("1");
  const [saving, setSaving] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  const charger = useCallback(async () => {
    setErreur(null);
    const [regleResult, jetonsResult] = await Promise.all([
      matriculeApi.get(),
      matriculeApi.getJetons(),
    ]);
    if (regleResult.error || !regleResult.data) {
      setErreur(extractErrorMessage(regleResult.error, "Nomenclature illisible."));
      return;
    }
    setRegle(regleResult.data);
    setModele(regleResult.data.modele);
    setLargeur(String(regleResult.data.largeur_numero));
    setDemarrage(String(regleResult.data.demarrage));
    setJetons(jetonsResult.data?.jetons ?? []);
  }, []);

  useEffect(() => {
    void charger();
  }, [charger]);

  const enregistrer = async () => {
    setSaving(true);
    const resultat = await matriculeApi.update({
      modele,
      largeur_numero: Number(largeur),
      demarrage: Number(demarrage),
    });
    setSaving(false);

    if (resultat.error || !resultat.data) {
      // Le refus est montre **dans la carte** : un toast disparait, et une
      // regle non enregistree sans raison visible laisse l'institut croire
      // qu'il a enregistre.
      setErreur(extractErrorMessage(resultat.error, "Nomenclature non enregistrée."));
      return;
    }
    setErreur(null);
    setRegle(resultat.data);
    setModele(resultat.data.modele);
    setLargeur(String(resultat.data.largeur_numero));
    setDemarrage(String(resultat.data.demarrage));
    toast.success(
      `Nomenclature enregistrée. Le prochain dossier portera ${resultat.data.exemple}.`
    );
  };

  const revenirAuDepart = async () => {
    if (!regle) return;
    setSaving(true);
    const resultat = await matriculeApi.update({
      modele: regle.modele_depart,
      largeur_numero: 4,
      demarrage: 1,
    });
    setSaving(false);
    if (resultat.error || !resultat.data) {
      setErreur(extractErrorMessage(resultat.error, "Retour impossible."));
      return;
    }
    setErreur(null);
    setRegle(resultat.data);
    setModele(resultat.data.modele);
    setLargeur(String(resultat.data.largeur_numero));
    setDemarrage(String(resultat.data.demarrage));
    toast.success("Nomenclature revenues au format par défaut.");
  };

  if (!regle) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Hash className="h-4 w-4" /> Nomenclature de matricule
          </CardTitle>
        </CardHeader>
        <CardContent>
          {erreur ? (
            <p className="text-sm text-destructive">{erreur}</p>
          ) : (
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Chargement...
            </p>
          )}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Hash className="h-4 w-4" /> Nomenclature de matricule
        </CardTitle>
        <CardDescription>
          Format des matricules attribués aux prochains dossiers.{" "}
          <strong className="text-foreground">
            Les matricules déjà attribués ne sont jamais modifiés
          </strong>{" "}
          : les familles ont reçu les leurs, et un certificat délivré doit rester
          rattaché à l'identifiant de l'époque.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {erreur && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Nomenclature refusée</AlertTitle>
            <AlertDescription>{erreur}</AlertDescription>
          </Alert>
        )}

        <div className="grid gap-4 sm:grid-cols-[2fr_1fr_1fr]">
          <div className="space-y-2">
            <Label htmlFor="matricule-modele">Modèle</Label>
            <Input
              id="matricule-modele"
              value={modele}
              onChange={(evenement) => setModele(evenement.target.value)}
              disabled={!canEdit}
              className="font-mono"
            />
            {jetons.length > 0 && (
              <p className="text-xs text-muted-foreground">
                Jetons acceptés :{" "}
                {jetons.map((jeton) => (
                  <span key={jeton.jeton} className="mr-2 font-mono">
                    {jeton.jeton}
                  </span>
                ))}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="matricule-largeur">Chiffres du compteur</Label>
            <Input
              id="matricule-largeur"
              type="number"
              min={1}
              max={8}
              value={largeur}
              onChange={(evenement) => setLargeur(evenement.target.value)}
              disabled={!canEdit}
            />
            <p className="text-xs text-muted-foreground">4 donne 0001</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="matricule-demarrage">Premier numéro</Label>
            <Input
              id="matricule-demarrage"
              type="number"
              min={1}
              value={demarrage}
              onChange={(evenement) => setDemarrage(evenement.target.value)}
              disabled={!canEdit}
            />
            <p className="text-xs text-muted-foreground">1 donne 0001</p>
          </div>
        </div>

        <div className="rounded-lg border bg-muted/30 p-3 text-sm">
          {modifie(regle, modele, largeur, demarrage) ? (
            <>
              <p className="text-muted-foreground">
                Apercu indicatif — le serveur le confirmera a l'enregistrement
              </p>
              <p
                className="mt-1 font-mono text-lg font-semibold text-muted-foreground"
                data-testid="matricule-apercu"
              >
                {modele
                  .replace("{annee}", "2026")
                  .replace("{filiere}", "GL")
                  .replace(
                    "{numero}",
                    String(Number(demarrage) || 1).padStart(
                      Number(largeur) || 1,
                      "0"
                    )
                  )}
              </p>
            </>
          ) : (
            <>
              <p className="text-muted-foreground">
                Aperçu — le prochain dossier portera
              </p>
              <p
                className="mt-1 font-mono text-lg font-semibold"
                data-testid="matricule-apercu"
              >
                {regle.exemple}
              </p>
            </>
          )}
        </div>

        {regle.personnalisee && (
          <p className="text-xs text-muted-foreground">
            Nomenclature personnalisée. Le format par défaut de l'application est{" "}
            <span className="font-mono">{regle.modele_depart}</span>.
          </p>
        )}

        {canEdit && (
          <div className="flex flex-wrap gap-2">
            <Button onClick={enregistrer} disabled={saving}>
              {saving ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Save className="mr-2 h-4 w-4" />
              )}
              Enregistrer la nomenclature
            </Button>
            {regle.personnalisee && (
              <Button
                variant="outline"
                onClick={revenirAuDepart}
                disabled={saving}
              >
                <RotateCcw className="mr-2 h-4 w-4" /> Revenir au format par défaut
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

/** Le formulaire est-il different de la regle enregistree ? */
const modifie = (
  regle: MatriculeParametres,
  modele: string,
  largeur: string,
  demarrage: string
): boolean =>
  regle.modele !== modele ||
  String(regle.largeur_numero) !== largeur ||
  String(regle.demarrage) !== demarrage;

export default MatriculeCard;
