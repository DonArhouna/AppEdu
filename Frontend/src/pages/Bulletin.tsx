/**
 * Bulletin d'un étudiant, semestre par semestre.
 *
 * L'écran se lit **avant** d'imprimer. C'est la raison d'être du double appel
 * côté serveur : `bulletinsApi.lire` renvoie le contenu, `bulletinsApi.pdf`
 * rend le document, et les deux sortent du même calcul. Lire d'abord permet de
 * vérifier ce que le papier affirmera — distribuer un bulletin sans l'avoir relu
 * est la seule façon d'imprimer une erreur officielle.
 *
 * L'écran ne propose donc le téléchargement que lorsque le contenu a été lu.
 * Un bouton actif alors que la lecture a échoué donnerait un document que
 * personne n'a vérifié.
 */

import { useCallback, useEffect, useState } from "react";
import { AlertCircle, Download, FileText, FolderArchive, Loader2, Printer } from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
import {
  bulletinsApi,
  academicApi,
  etudiantsApi,
  extractErrorMessage,
  sessionsApi,
  semestresApi,
} from "@/services/apiClient";
import type {
  AcademicClass,
  Bulletin,
  RattrapageEtudiant,
  Semestre,
  Student,
} from "@/services/apiTypes";

/** Deux decimales, separateur francais : c'est ainsi que le bulletin imprime. */
const nombre = (valeur: number | null | undefined, decimales = 2): string =>
  valeur == null ? "n. c." : valeur.toFixed(decimales).replace(".", ",");

export default function BulletinPage() {
  const [etudiants, setEtudiants] = useState<Student[]>([]);
  const [classes, setClasses] = useState<AcademicClass[]>([]);
  const [sessions, setSessions] = useState<{ id: string; nom: string }[]>([]);
  const [semestres, setSemestres] = useState<Semestre[]>([]);

  const [etudiantId, setEtudiantId] = useState("");
  const [classeLotId, setClasseLotId] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [semestreId, setSemestreId] = useState("");

  const [bulletin, setBulletin] = useState<Bulletin | null>(null);
  const [rattrapage, setRattrapage] = useState<RattrapageEtudiant | null>(null);
  const [chargement, setChargement] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [telechargement, setTelechargement] = useState(false);
  const [telechargementLot, setTelechargementLot] = useState(false);

  useEffect(() => {
    (async () => {
      const [liste, seances, repartitionClasses] = await Promise.all([
        etudiantsApi.getAll(),
        sessionsApi.getAll(),
        academicApi.getClasses(),
      ]);
      if (liste.error) {
        setErreur(extractErrorMessage(liste.error, "Étudiants illisibles."));
        return;
      }
      setEtudiants((liste.data ?? []) as Student[]);
      setSessions((seances.data ?? []) as { id: string; nom: string }[]);
      if (seances.data && seances.data.length > 0) {
        setSessionId(seances.data[0].id);
      }
      setClasses((repartitionClasses.data ?? []) as AcademicClass[]);
    })();
  }, []);

  // Les semestres dependent de la session. Changer de session **efface** le
  // semestre choisi : le garder afficherait des notes d'une autre session, ce
  // que le bulletin refuse ensuite — sans dire pourquoi.
  useEffect(() => {
    setSemestreId("");
    setBulletin(null);
    setRattrapage(null);
    if (!sessionId) {
      setSemestres([]);
      return;
    }
    (async () => {
      const repartition = await semestresApi.getRepartition(sessionId);
      if (repartition.error || !repartition.data) {
        setErreur(
          extractErrorMessage(
            repartition.error,
            "Semestres de la session illisibles."
          )
        );
        return;
      }
      setSemestres(repartition.data.semestres);
    })();
  }, [sessionId]);

  const charger = useCallback(async () => {
    if (!etudiantId || !semestreId) return;
    setChargement(true);
    setErreur(null);
    const [contenu, reprise] = await Promise.all([
      bulletinsApi.lire(etudiantId, semestreId),
      bulletinsApi.rattrapage(etudiantId, sessionId),
    ]);
    setChargement(false);
    if (contenu.error || !contenu.data) {
      setBulletin(null);
      setErreur(
        extractErrorMessage(contenu.error, "Bulletin illisible.")
      );
      return;
    }
    setBulletin(contenu.data);
    setRattrapage(reprise.data ?? null);
  }, [etudiantId, semestreId, sessionId]);

  const telecharger = async () => {
    if (!etudiantId || !semestreId) return;
    setTelechargement(true);
    const resultat = await bulletinsApi.pdf(etudiantId, semestreId);
    setTelechargement(false);
    if (resultat.error || !resultat.data) {
      toast.error(
        extractErrorMessage(resultat.error, "Bulletin indisponible.")
      );
      return;
    }
    const url = URL.createObjectURL(resultat.data);
    const lien = document.createElement("a");
    const nom = bulletin?.etudiant.matricule ?? "etudiant";
    lien.href = url;
    lien.download = `bulletin_${bulletin?.session.semestre_libelle ?? "S"}_${nom}.pdf`;
    lien.click();
    URL.revokeObjectURL(url);
    toast.success("Bulletin téléchargé. Il reste à le signer et à le cacheter.");
  };

  /**
   * Le lot d'une classe entiere. L'archive ne requiert pas d'avoir lu un
   * bulletin d'abord : la classe se signe en seance, sans relecture ecran
   * par etudiant. Les erreurs par etudiant figurent dans le rapport joint.
   */
  const telechargerLot = async () => {
    if (!classeLotId || !semestreId) return;
    setTelechargementLot(true);
    const resultat = await bulletinsApi.telechargerLot(classeLotId, semestreId);
    setTelechargementLot(false);
    if (resultat.error || !resultat.data) {
      toast.error(
        extractErrorMessage(resultat.error, "Archive des bulletins indisponible.")
      );
      return;
    }
    const url = URL.createObjectURL(resultat.data);
    const lien = document.createElement("a");
    const classe = classes.find((c) => c.id === classeLotId);
    const nomClasse = (classe?.code || classe?.nom || "classe")
      .replace(/[^A-Za-z0-9_-]+/g, "-");
    const semestre = semestres.find((s) => s.id === semestreId);
    lien.href = url;
    lien.download = `bulletins_${nomClasse}_${semestre?.libelle ?? "S"}.zip`;
    lien.click();
    URL.revokeObjectURL(url);
    toast.success(
      "Archive des bulletins de la classe téléchargée. Rapport des bulletins "
      + "non produits inclus le cas échéant."
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          Bulletin de notes
        </h1>
        <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
          Le contenu s'affiche ici avant toute impression. Le document
          téléchargé ne portera ni signature ni cachet : il se signe et se
          cachète à la main, une fois sorti de l'imprimante.
        </p>
      </div>

      {erreur && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Chargement impossible</AlertTitle>
          <AlertDescription>{erreur}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Choix de l'étudiant et du semestre</CardTitle>
          <CardDescription>
            Le semestre est celui de la session : un enseignement annuel figure
            sur chacun d'eux, avec sa propre note.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-3">
          <div className="space-y-2">
            <Label htmlFor="bulletin-etudiant">Étudiant</Label>
            <Select value={etudiantId} onValueChange={setEtudiantId}>
              <SelectTrigger id="bulletin-etudiant">
                <SelectValue placeholder="Choisir" />
              </SelectTrigger>
              <SelectContent>
                {etudiants.map((etudiant) => (
                  <SelectItem key={etudiant.id} value={etudiant.id}>
                    {etudiant.matricule} — {etudiant.nom} {etudiant.prenom}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="bulletin-session">Session</Label>
            <Select value={sessionId} onValueChange={setSessionId}>
              <SelectTrigger id="bulletin-session">
                <SelectValue placeholder="Choisir" />
              </SelectTrigger>
              <SelectContent>
                {sessions.map((session) => (
                  <SelectItem key={session.id} value={session.id}>
                    {session.nom}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="bulletin-semestre">Semestre</Label>
            <Select value={semestreId} onValueChange={setSemestreId}>
              <SelectTrigger id="bulletin-semestre">
                <SelectValue placeholder="Choisir" />
              </SelectTrigger>
              <SelectContent>
                {semestres.length === 0 ? (
                  <SelectItem value="__aucun__" disabled>
                    Aucun semestre sur cette session
                  </SelectItem>
                ) : (
                  semestres.map((semestre) => (
                    <SelectItem key={semestre.id} value={semestre.id}>
                      {semestre.numero}. {semestre.libelle} —{" "}
                      {semestre.nb_unites} UE
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <div className="flex flex-wrap gap-2">
        <Button
          onClick={() => void charger()}
          disabled={!etudiantId || !semestreId || chargement}
        >
          {chargement ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <FileText className="mr-2 h-4 w-4" />
          )}
          Lire le bulletin
        </Button>
        <Button
          variant="outline"
          onClick={() => void telecharger()}
          disabled={!bulletin || telechargement}
        >
          {telechargement ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Download className="mr-2 h-4 w-4" />
          )}
          Télécharger le PDF
        </Button>
      </div>

      {!bulletin && !chargement && (
        <Alert>
          <AlertTitle>Aucun bulletin affiché</AlertTitle>
          <AlertDescription>
            Choisissez un étudiant et un semestre, puis lisez le bulletin. Le
            téléchargement individuel n'est possible qu'après : un document
            officiel imprimé sans avoir été relu n'est vérifiable par personne.
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Téléchargement groupé</CardTitle>
          <CardDescription>
            Un ZIP par classe, un bulletin par étudiant inscrit. L'archive
            reprend exactement le PDF individuel ; un étudiant dont le bulletin
            échoue est signalé dans un rapport joint, sans bloquer les autres.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <div className="space-y-2">
            <Label htmlFor="bulletin-lot-classe">Classe</Label>
            <Select value={classeLotId} onValueChange={setClasseLotId}>
              <SelectTrigger id="bulletin-lot-classe" className="w-64">
                <SelectValue placeholder="Choisir" />
              </SelectTrigger>
              <SelectContent>
                {classes.length === 0 ? (
                  <SelectItem value="__aucune__" disabled>
                    Aucune classe enregistrée
                  </SelectItem>
                ) : (
                  classes.map((classe) => (
                    <SelectItem key={classe.id} value={classe.id}>
                      {classe.code}
                      {classe.nom && classe.nom !== classe.code
                        ? ` — ${classe.nom}`
                        : ""}
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          </div>
          <Button
            variant="outline"
            onClick={() => void telechargerLot()}
            disabled={!classeLotId || !semestreId || telechargementLot}
          >
            {telechargementLot ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <FolderArchive className="mr-2 h-4 w-4" />
            )}
            Télécharger les bulletins de la classe (ZIP)
          </Button>
        </CardContent>
      </Card>

      {bulletin && (
        <>
          {bulletin.observations.deliberation_absente && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Aucune délibération enregistrée</AlertTitle>
              <AlertDescription>
                Le jury ne s'est pas prononcé sur cet étudiant. Le bulletin ne
                porte que des moyennes : ni admission, ni rattrapage, ni
                crédits obtenus.
              </AlertDescription>
            </Alert>
          )}

          {rattrapage && rattrapage.etat === "a_reprendre" && (
            <Alert>
              <AlertTitle>
                {rattrapage.total_matieres} matière(s) à reprendre
              </AlertTitle>
              <AlertDescription>
                <ul className="mt-1 list-disc space-y-0.5 pl-5">
                  {rattrapage.unites.map((ue) => (
                    <li key={ue.ue_id}>
                      <span className="font-medium">{ue.ue_code}</span> —{" "}
                      {ue.matieres.map((m) => m.matiere_nom).join(", ")}
                    </li>
                  ))}
                </ul>
                Importez les notes de seconde chance en cochant « rattrapage » :
                elles remplaceront la première tentative, elles ne s'y
                ajouteront pas.
              </AlertDescription>
            </Alert>
          )}

          {rattrapage && rattrapage.etat === "rien_a_reprendre" && (
            <Alert>
              <AlertTitle>Rien à reprendre</AlertTitle>
              <AlertDescription>{rattrapage.message}</AlertDescription>
            </Alert>
          )}

          <Card>
            <CardHeader>
              <CardTitle>
                {bulletin.etudiant.nom} {bulletin.etudiant.prenom}
              </CardTitle>
              <CardDescription>
                {bulletin.etudiant.matricule} — {bulletin.etudiant.filiere} ·{" "}
                {bulletin.session.semestre_libelle} ·{" "}
                {bulletin.session.annee_academique}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {bulletin.unites.length === 0 ? (
                <Alert variant="destructive">
                  <AlertTitle>Aucune unité notée sur ce semestre</AlertTitle>
                  <AlertDescription>
                    Ce semestre ne porte aucune note. Le tableau serait vide et
                    se lirait comme un semestre sans matières.
                  </AlertDescription>
                </Alert>
              ) : (
                bulletin.unites.map((ue) => (
                  <div key={ue.code} className="space-y-1">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium">
                        {ue.code} — {ue.nom}{" "}
                        {ue.annuelle && (
                          <Badge variant="outline" className="ml-1">
                            annuel
                          </Badge>
                        )}
                      </p>
                      <span className="text-xs text-muted-foreground">
                        CUE {ue.cue}
                      </span>
                    </div>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Code</TableHead>
                          <TableHead>Intitulé</TableHead>
                          <TableHead className="text-right">Moy. contrôle</TableHead>
                          <TableHead className="text-right">Moy. examen</TableHead>
                          <TableHead className="text-right">CEC</TableHead>
                          <TableHead className="text-right">Moy. matière</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {ue.matieres.map((matiere) => (
                          <TableRow key={matiere.code}>
                            <TableCell className="text-xs">{matiere.code}</TableCell>
                            <TableCell>{matiere.nom}</TableCell>
                            <TableCell className="text-right tabular-nums">
                              {nombre(matiere.mcc)}
                            </TableCell>
                            <TableCell className="text-right tabular-nums">
                              {nombre(matiere.exam)}
                            </TableCell>
                            <TableCell className="text-right tabular-nums">
                              {nombre(matiere.cec)}
                            </TableCell>
                            <TableCell className="text-right tabular-nums font-medium">
                              {nombre(matiere.mec)}
                            </TableCell>
                          </TableRow>
                        ))}
                        <TableRow className="bg-muted/30">
                          <TableCell />
                          <TableCell className="font-medium">
                            Total UE
                            {ue.validation ? ` — ${ue.validation}` : ""}
                            {ue.validation
                              ? ""
                              : ue.proposition_validation
                                ? ` — proposition : ${ue.proposition_validation} (non tranchée)`
                                : ""}
                          </TableCell>
                          <TableCell />
                          <TableCell />
                          <TableCell className="text-right tabular-nums font-medium">
                            {ue.cue}
                          </TableCell>
                          <TableCell className="text-right tabular-nums font-medium">
                            {nombre(ue.mue)}
                          </TableCell>
                        </TableRow>
                      </TableBody>
                    </Table>
                  </div>
                ))
              )}

              <div className="grid gap-3 sm:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Total du semestre</CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm">
                    <p>
                      {bulletin.totaux.credits_prevus} crédit(s) — moyenne{" "}
                      <span className="font-medium">
                        {nombre(bulletin.totaux.moyenne)}
                      </span>
                      {bulletin.totaux.mention
                        ? ` — ${bulletin.totaux.mention}`
                        : ""}
                    </p>
                  </CardContent>
                </Card>

                {bulletin.recapitulatif.lignes.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">
                        Récapitulatif de l'année
                      </CardTitle>
                      <CardDescription>
                        Présent sur les semestres pairs : une année couvre deux
                        semestres.
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-1 text-sm">
                      {bulletin.recapitulatif.lignes.map((ligne) => (
                        <p key={ligne.libelle}>
                          {ligne.libelle} — {ligne.credits ?? "n. c."} crédit(s),
                          moyenne {nombre(ligne.moyenne)}
                        </p>
                      ))}
                      <p className="font-medium">
                        Moyenne générale {nombre(bulletin.recapitulatif.moyenne_annuelle)}
                        {bulletin.recapitulatif.mention_annuelle
                          ? ` — ${bulletin.recapitulatif.mention_annuelle}`
                          : ""}
                      </p>
                    </CardContent>
                  </Card>
                )}
              </div>

              {bulletin.observations.incompletudes.length > 0 && (
                <Alert>
                  <AlertTitle>Observations</AlertTitle>
                  <AlertDescription>
                    <ul className="list-disc space-y-0.5 pl-5">
                      {bulletin.observations.incompletudes.map((entree) => (
                        <li key={entree.code}>
                          {entree.matiere} ({entree.code}) : un {entree.manque}{" "}
                          est noté sans l'autre.
                        </li>
                      ))}
                      {bulletin.observations.annuelles_absentes.map((entree) => (
                        <li key={entree.ue_id}>
                          {entree.code} — {entree.unite} : enseignement annuel
                          sans note sur ce semestre.
                        </li>
                      ))}
                      {bulletin.observations.hors_bulletin.map((entree, index) => (
                        <li key={`${entree.code ?? "hors"}-${index}`}>
                          {entree.code} — {entree.matiere} : {entree.raison}
                        </li>
                      ))}
                    </ul>
                  </AlertDescription>
                </Alert>
              )}

              <p className="flex items-center gap-2 text-xs text-muted-foreground">
                <Printer className="h-3.5 w-3.5" />
                Le document téléchargé portera la mention « provisoire — à
                signer et à cacheter ». Ni signature ni cachet n'y sont
                imprimés.
              </p>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
