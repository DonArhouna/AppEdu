/**
 * Configuration institutionnelle : identité imprimable, logo, historique.
 *
 * Cette carte remplace l'affichage en lecture seule qui occupait la place
 * dans l'écran de paramétrage. Tant que l'établissement n'a rien modifié, la
 * configuration reste en version 0 : elle est celle du Setup Wizard, et
 * l'historique est vide — c'est un état normal, pas une absence de données.
 *
 * Deux régimes, et non un écran gris pour tout le monde :
 *
 * - avec `institution.settings`, les champs sont modifiables et le logo
 *   televersable ;
 * - sans elle, la même identité est lue, ce qui est nécessaire : un
 *   secrétaire doit voir l'identité qui figurera sur les documents qu'il
 *   émet, même s'il ne peut pas la modifier.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  Building2,
  History,
  ImageIcon,
  Loader2,
  RefreshCw,
  Save,
  Trash2,
  Upload,
} from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  extractErrorMessage,
  institutionApi,
  PERMISSION_INSTITUTION_SETTINGS,
} from "@/services/apiClient";
import type {
  ChampModifie,
  ConfigurationVersion,
  InstitutionConfig,
} from "@/services/apiTypes";
import { toast } from "sonner";

/** Libellés lisibles des champs, pour l'historique. */
const LIBELLES: Record<string, string> = {
  nom: "Nom",
  sigle: "Sigle",
  adresse: "Adresse",
  telephone: "Téléphone",
  email: "Courriel",
  pays: "Pays",
  devise: "Devise",
  logo: "Logo",
};

interface ChampsEditables {
  nom: string;
  sigle: string;
  adresse: string;
  telephone: string;
  email: string;
  pays: string;
  devise: string;
}

const VIDES: ChampsEditables = {
  nom: "",
  sigle: "",
  adresse: "",
  telephone: "",
  email: "",
  pays: "",
  devise: "",
};

const versChamps = (config: InstitutionConfig): ChampsEditables => ({
  nom: config.nom,
  sigle: config.sigle,
  adresse: config.adresse ?? "",
  telephone: config.telephone ?? "",
  email: config.email,
  pays: config.pays ?? "",
  devise: config.devise,
});

/** Décrit un changement en français lisible, y compris un champ effacé. */
function decrire(champ: string, valeur: ChampModifie): string {
  const libelle = LIBELLES[champ] ?? champ;
  const avant = valeur.avant === "" || valeur.avant === null ? "(vide)" : valeur.avant;
  const apres = valeur.apres === "" || valeur.apres === null ? "(vide)" : valeur.apres;
  if (champ === "logo") return `${libelle} : ${avant} → ${apres}`;
  return `${libelle} : « ${avant} » → « ${apres} »`;
}

const dateFr = (iso: string): string => {
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? iso
    : date.toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
};

/**
 * Charge le logo comme URL d'objet.
 *
 * Une ``<img src>`` ne peut pas porter le jeton Bearer : sur un endpoint
 * protege, l'image ne se chargerait jamais et l'ecran afficherait un cadre
 * vide apres un envoi pourtant reussi. On recupere les octets par le client,
 * qui est authentifie, puis on attache l'URL d'objet au DOM.
 *
 * L'URL d'objet est revoquee au changement et au demontage : une URL
 * d'objet conserve les octets en memoire jusqu'a sa revocation.
 */
function useLogoAuthentifie(present: boolean, version: number): string | null {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!present) {
      setUrl(null);
      return;
    }
    let annule = false;
    let objectUrl: string | null = null;

    void institutionApi.getLogo().then((resultat) => {
      if (annule || !resultat.data) {
        // Un 404 ici signifie « plus de logo » : c'est un etat normal, il ne
        // doit pas declencher une alerte d'erreur.
        if (!annule && resultat.status !== 404) {
          toast.error("Le logo n'a pas pu être chargé.");
        }
        return;
      }
      objectUrl = URL.createObjectURL(resultat.data);
      setUrl(objectUrl);
    });

    return () => {
      annule = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [present, version]);

  return url;
}

interface InstitutionConfigCardProps {
  /** Le compte courant peut-il modifier la configuration ? */
  canEdit: boolean;
  /** Rafraichit l'ecran apres une ecriture (nom, devise affiches ailleurs). */
  onSaved?: () => void;
}

const InstitutionConfigCard = ({ canEdit, onSaved }: InstitutionConfigCardProps) => {
  const [config, setConfig] = useState<InstitutionConfig | null>(null);
  const [champs, setChamps] = useState<ChampsEditables>(VIDES);
  const [versions, setVersions] = useState<ConfigurationVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [removingLogo, setRemovingLogo] = useState(false);
  const [erreursChamps, setErreursChamps] = useState<Record<string, string>>({});
  const inputFichier = useRef<HTMLInputElement>(null);

  const charger = useCallback(async () => {
    setLoading(true);
    setError(null);
    const [configResult, versionsResult] = await Promise.all([
      institutionApi.getConfig(),
      institutionApi.getVersions(),
    ]);
    if (configResult.error || !configResult.data) {
      setError(
        extractErrorMessage(
          configResult.error,
          "La configuration de l'établissement n'a pas pu être chargée."
        )
      );
      setConfig(null);
    } else {
      setConfig(configResult.data);
      setChamps(versChamps(configResult.data));
    }
    setVersions(versionsResult.data ?? []);
    setLoading(false);
  }, []);

  useEffect(() => {
    void charger();
  }, [charger]);

  // Le logo est rechargement a chaque version : un logo remplace ou retire ne
  // peut pas resister dans le cache du navigateur.
  const urlLogo = useLogoAuthentifie(
    Boolean(config?.logo_present),
    config?.version ?? 0
  );

  const valider = (): boolean => {
    const erreurs: Record<string, string> = {};
    if (champs.nom.trim().length < 2) erreurs.nom = "Le nom doit comporter au moins 2 caractères.";
    if (champs.sigle.trim().length < 2) erreurs.sigle = "Le sigle doit comporter au moins 2 caractères.";
    if (champs.devise.trim().length < 3) erreurs.devise = "La devise doit comporter au moins 3 lettres.";
    if (champs.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(champs.email.trim())) {
      erreurs.email = "Adresse électronique invalide.";
    }
    setErreursChamps(erreurs);
    return Object.keys(erreurs).length === 0;
  };

  const enregistrer = async () => {
    if (!valider()) {
      toast.error("Corrigez les champs signalés avant d'enregistrer.");
      return;
    }
    setSaving(true);
    const resultat = await institutionApi.updateConfig({
      nom: champs.nom.trim(),
      sigle: champs.sigle.trim(),
      // Une chaine vide efface le champ cote serveur : c'est la seule façon
      // de vider une coordonnee, et le serveur le trace comme tel.
      adresse: champs.adresse.trim(),
      telephone: champs.telephone.trim(),
      email: champs.email.trim(),
      pays: champs.pays.trim(),
      devise: champs.devise.trim().toUpperCase(),
    });
    setSaving(false);

    if (resultat.error || !resultat.data) {
      toast.error(
        extractErrorMessage(resultat.error, "La configuration n'a pas pu être enregistrée.")
      );
      return;
    }
    if (Object.keys(resultat.data.modifications).length === 0) {
      toast.info("Aucun changement : la configuration est déjà à jour.");
    } else {
      toast.success(`Configuration enregistrée (version ${resultat.data.version}).`);
    }
    await charger();
    onSaved?.();
  };

  const televerserLogo = async (fichier: File) => {
    setUploading(true);
    const resultat = await institutionApi.uploadLogo(fichier);
    setUploading(false);
    if (inputFichier.current) inputFichier.current.value = "";

    if (resultat.error || !resultat.data) {
      toast.error(
        extractErrorMessage(resultat.error, "Le logo n'a pas pu être enregistré.")
      );
      return;
    }
    toast.success(`Logo enregistré (version ${resultat.data.version}).`);
    await charger();
  };

  const retirerLogo = async () => {
    setRemovingLogo(true);
    const resultat = await institutionApi.removeLogo();
    setRemovingLogo(false);
    if (resultat.error || !resultat.data) {
      toast.error(extractErrorMessage(resultat.error, "Le logo n'a pas pu être retiré."));
      return;
    }
    toast.success(`Logo retiré (version ${resultat.data.version}).`);
    await charger();
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="h-4 w-4" /> Identité de l'établissement
          </CardTitle>
          <CardDescription>Chargement de la configuration…</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} className="h-16 w-full" />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (error || !config) {
    return (
      <Card className="border-destructive/40">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="h-4 w-4" /> Identité de l'établissement
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Configuration indisponible</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
          <Button variant="outline" onClick={charger}>
            <RefreshCw className="mr-2 h-4 w-4" /> Réessayer
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="h-4 w-4" /> Identité de l'établissement
              </CardTitle>
              <CardDescription>
                Ces informations figurent sur les documents officiels (certificat,
                relevé, quitus). Chaque modification est conservée et versionnée.
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="secondary">Version {config.version}</Badge>
              <Button
                variant="outline"
                size="sm"
                onClick={charger}
                disabled={loading || saving || uploading}
              >
                <RefreshCw className="mr-2 h-4 w-4" /> Actualiser
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-6">
          {!canEdit && (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Lecture seule</AlertTitle>
              <AlertDescription>
                Vous consultez l'identité de l'établissement. Sa modification exige
                la permission <code className="font-mono">{PERMISSION_INSTITUTION_SETTINGS}</code>.
              </AlertDescription>
            </Alert>
          )}

          <div className="grid gap-4 md:grid-cols-3">
            <Champ
              label="Nom"
              value={champs.nom}
              onChange={(valeur) => setChamps((c) => ({ ...c, nom: valeur }))}
              disabled={!canEdit}
              erreur={erreursChamps.nom}
              requis
            />
            <Champ
              label="Sigle"
              value={champs.sigle}
              onChange={(valeur) => setChamps((c) => ({ ...c, sigle: valeur }))}
              disabled={!canEdit}
              erreur={erreursChamps.sigle}
              requis
            />
            <Champ
              label="Devise"
              value={champs.devise}
              onChange={(valeur) => setChamps((c) => ({ ...c, devise: valeur }))}
              disabled={!canEdit}
              erreur={erreursChamps.devise}
              requis
              aide="Code de la devise, par exemple FCFA ou EUR."
            />
            <Champ
              label="Adresse"
              value={champs.adresse}
              onChange={(valeur) => setChamps((c) => ({ ...c, adresse: valeur }))}
              disabled={!canEdit}
            />
            <Champ
              label="Téléphone"
              value={champs.telephone}
              onChange={(valeur) => setChamps((c) => ({ ...c, telephone: valeur }))}
              disabled={!canEdit}
            />
            <Champ
              label="Pays"
              value={champs.pays}
              onChange={(valeur) => setChamps((c) => ({ ...c, pays: valeur }))}
              disabled={!canEdit}
            />
            <Champ
              label="Courriel"
              type="email"
              value={champs.email}
              onChange={(valeur) => setChamps((c) => ({ ...c, email: valeur }))}
              disabled={!canEdit}
              erreur={erreursChamps.email}
            />
          </div>

          {canEdit && (
            <div className="flex justify-end">
              <Button onClick={enregistrer} disabled={saving || uploading}>
                {saving ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Save className="mr-2 h-4 w-4" />
                )}
                Enregistrer l'identité
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ImageIcon className="h-4 w-4" /> Logo de l'établissement
          </CardTitle>
          <CardDescription>
            Placé en tête des documents officiels. PNG ou JPEG, 512 Ko maximum ;
            le format est vérifié sur le contenu réel du fichier, pas sur son nom.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {urlLogo ? (
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
              <div className="flex h-28 w-44 items-center justify-center rounded-lg border bg-white p-3">
                <img
                  src={urlLogo}
                  alt={`Logo de ${config.nom}`}
                  className="max-h-full max-w-full object-contain"
                />
              </div>
              <div className="flex-1 space-y-3">
                <p className="text-sm text-muted-foreground">
                  Un logo est enregistré et utilisé sur les nouveaux documents.
                  Les documents déjà délivrés conservent l'identité sous laquelle
                  ils ont été émis.
                </p>
                {canEdit && (
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => inputFichier.current?.click()}
                      disabled={uploading || removingLogo}
                    >
                      {uploading ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : (
                        <Upload className="mr-2 h-4 w-4" />
                      )}
                      Remplacer
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="border-destructive/30 text-destructive hover:text-destructive"
                      onClick={retirerLogo}
                      disabled={uploading || removingLogo}
                    >
                      {removingLogo ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : (
                        <Trash2 className="mr-2 h-4 w-4" />
                      )}
                      Retirer
                    </Button>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed py-10 text-center">
              <ImageIcon className="h-8 w-8 text-muted-foreground" />
              <div>
                <p className="font-medium">Aucun logo enregistré</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Les documents officiels sont émis sans branding. Le nom, le
                  sigle et les coordonnées restent imprimés.
                </p>
              </div>
              {canEdit && (
                <>
                  <Button
                    variant="outline"
                    onClick={() => inputFichier.current?.click()}
                    disabled={uploading}
                  >
                    {uploading ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Upload className="mr-2 h-4 w-4" />
                    )}
                    Téléverser un logo
                  </Button>
                  <p className="text-xs text-muted-foreground">PNG ou JPEG, 512 Ko maximum.</p>
                </>
              )}
            </div>
          )}

          {/* Le champ reste monte pour ne pas perdre la selection apres un refus. */}
          <input
            ref={inputFichier}
            type="file"
            accept="image/png,image/jpeg"
            className="hidden"
            onChange={(evenement) => {
              const fichier = evenement.target.files?.[0];
              if (fichier) void televerserLogo(fichier);
            }}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <History className="h-4 w-4" /> Historique des versions
          </CardTitle>
          <CardDescription>
            Chaque modification de l'identité ou du logo est conservée avec son
            auteur et sa date. Un document officiel déjà délivré n'est jamais
            réémis : son instantané d'émission fait foi.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {versions.length === 0 ? (
            <div className="rounded-lg border border-dashed py-10 text-center">
              <History className="mx-auto h-8 w-8 text-muted-foreground" />
              <p className="mt-3 font-medium">Aucune modification enregistrée</p>
              <p className="mt-1 text-sm text-muted-foreground">
                L'identité en vigueur est celle définie à l'installation. La
                première modification créera la version 1.
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-20">Version</TableHead>
                  <TableHead>Modifications</TableHead>
                  <TableHead className="w-44">Auteur</TableHead>
                  <TableHead className="w-44">Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {versions.map((version) => (
                  <TableRow key={version.version}>
                    <TableCell>
                      <Badge variant={version.version === config.version ? "default" : "secondary"}>
                        v{version.version}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <ul className="space-y-1 text-sm">
                        {Object.entries(version.modifications).map(([champ, valeur]) => (
                          <li key={champ} className="text-muted-foreground">
                            {decrire(champ, valeur)}
                          </li>
                        ))}
                      </ul>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {version.modifie_par_email ?? "—"}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {dateFr(version.created_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

/* -------------------------------------------------------------------------- */
/* Champ de formulaire                                                        */
/* -------------------------------------------------------------------------- */
interface ChampProps {
  label: string;
  value: string;
  onChange: (valeur: string) => void;
  disabled: boolean;
  type?: string;
  erreur?: string;
  aide?: string;
  requis?: boolean;
}

const Champ = ({
  label,
  value,
  onChange,
  disabled,
  type = "text",
  erreur,
  aide,
  requis,
}: ChampProps) => (
  <div className="space-y-2">
    <Label htmlFor={`champ-${label}`}>
      {label}
      {requis && <span className="ml-1 text-destructive">*</span>}
    </Label>
    <Input
      id={`champ-${label}`}
      type={type}
      value={value}
      onChange={(evenement) => onChange(evenement.target.value)}
      disabled={disabled}
      readOnly={disabled}
      aria-invalid={Boolean(erreur)}
      className={erreur ? "border-destructive" : undefined}
    />
    {erreur ? (
      <p className="text-xs text-destructive">{erreur}</p>
    ) : aide ? (
      <p className="text-xs text-muted-foreground">{aide}</p>
    ) : null}
  </div>
);

export default InstitutionConfigCard;
