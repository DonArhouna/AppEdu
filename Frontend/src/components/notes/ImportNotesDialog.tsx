/**
 * Import de notes depuis un tableur.
 *
 * Le parcours est en deux temps, et l'ecran ne permet pas de le sauter :
 * choisir classe, matiere, session et coefficient -> **analyser** -> lire le
 * rapport -> **valider**. Aucune note n'est enregistree a l'analyse.
 *
 * Deux regles que cet ecran respecte :
 *
 * - la classe, la matiere et la session se choisissent **ici**, jamais dans le
 *   fichier. Un tableur de notes ne les porte pas, et les deviner reviendrait a
 *   affecter des notes a la mauvaise matiere ;
 * - le rapport est montre **en entier**, y compris les erreurs. Tronquer la
 *   liste des lignes en echec pourrait faire importer un fichier incomplet sans
 *   que l'agent le sache.
 */

import { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  FileSpreadsheet,
  Loader2,
  Upload,
  XCircle,
} from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { academicApi, extractErrorMessage, notesImportApi } from "@/services/apiClient";
import type {
  AcademicClass,
  AcademicSession,
  ModeleImportNotes,
  RapportImportNotes,
} from "@/services/apiTypes";
import { toast } from "sonner";

interface ImportNotesDialogProps {
  ouvert: boolean;
  onClose: () => void;
  onImporte: () => void;
  matieres: { id: string; code: string; nom: string }[];
  sessions: { id: string; nom: string; annee_academique: string }[];
  /** Matiere deja choisie dans l'ecran, si elle existe. */
  matiereCourante?: string;
  sessionCourante?: string;
}

const ImportNotesDialog = ({
  ouvert,
  onClose,
  onImporte,
  matieres,
  sessions,
  matiereCourante,
  sessionCourante,
}: ImportNotesDialogProps) => {
  const [classes, setClasses] = useState<AcademicClass[]>([]);
  const [modele, setModele] = useState<ModeleImportNotes | null>(null);
  const [classeId, setClasseId] = useState("");
  const [matiereId, setMatiereId] = useState(matiereCourante ?? "");
  const [sessionId, setSessionId] = useState(sessionCourante ?? "");
  const [fichier, setFichier] = useState<File | null>(null);
  const [rapport, setRapport] = useState<RapportImportNotes | null>(null);
  const [analyse, setAnalyse] = useState(false);
  const [validation, setValidation] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  const reinitialiser = useCallback(() => {
    setRapport(null);
    setFichier(null);
    setErreur(null);
  }, []);

  useEffect(() => {
    if (!ouvert) return;
    reinitialiser();
    setMatiereId(matiereCourante ?? "");
    setSessionId(sessionCourante ?? "");
    void notesImportApi.modele().then((resultat) => {
      if (resultat.data) setModele(resultat.data);
    });
    void academicApi.getClasses().then((resultat) => {
      if (resultat.data) setClasses(resultat.data);
    });
  }, [ouvert, reinitialiser, matiereCourante, sessionCourante]);

  const choisirFichier = (evenement: React.ChangeEvent<HTMLInputElement>) => {
    setFichier(evenement.target.files?.[0] ?? null);
    // Changer de fichier invalide le rapport : l'ancien porte sur l'ancien
    // fichier, et le valider reviendrait a ecrire autre chose que ce qui est
    // affiche.
    setRapport(null);
    setErreur(null);
  };

  const lancerAnalyse = async () => {
    if (!fichier) {
      setErreur("Choisissez un fichier .csv ou .xlsx.");
      return;
    }
    if (!classeId || !matiereId || !sessionId) {
      setErreur(
        "Classe, matière et session sont obligatoires : sans elles, les notes "
          + "iraient à la mauvaise place."
      );
      return;
    }
    setAnalyse(true);
    setErreur(null);
    const resultat = await notesImportApi.analyser({
      fichier,
      classeId,
      matiereId,
      sessionId,
    });
    setAnalyse(false);
    if (resultat.error || !resultat.data) {
      setErreur(extractErrorMessage(resultat.error, "Analyse impossible."));
      return;
    }
    setRapport(resultat.data);
  };

  const valider = async () => {
    if (!rapport) return;
    setValidation(true);
    const resultat = await notesImportApi.valider(rapport);
    setValidation(false);
    if (resultat.error || !resultat.data) {
      setErreur(extractErrorMessage(resultat.error, "Import refusé."));
      return;
    }
    const bilan = resultat.data;
    toast.success(
      `${bilan.creees + bilan.modifiees} note(s) enregistrée(s) — `
        + `${bilan.creees} créée(s), ${bilan.modifiees} mise(s) à jour.`
    );
    onImporte();
    onClose();
  };

  const resume = rapport?.resume;

  return (
    <Dialog open={ouvert} onOpenChange={(ouvert) => !ouvert && onClose()}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle>Importer des notes</DialogTitle>
          <DialogDescription>
            Une ligne par étudiant, une colonne par évaluation. L&apos;analyse
            n&apos;écrit rien : elle montre ce qui serait enregistré.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {erreur && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Import impossible</AlertTitle>
              <AlertDescription>{erreur}</AlertDescription>
            </Alert>
          )}

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="import-classe">Classe *</Label>
              <Select value={classeId} onValueChange={setClasseId}>
                <SelectTrigger id="import-classe">
                  <SelectValue placeholder="Sélectionner la classe" />
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
              <Label htmlFor="import-matiere">Matière *</Label>
              <Select value={matiereId} onValueChange={setMatiereId}>
                <SelectTrigger id="import-matiere">
                  <SelectValue placeholder="Sélectionner la matière" />
                </SelectTrigger>
                <SelectContent>
                  {matieres.map((matiere) => (
                    <SelectItem key={matiere.id} value={matiere.id}>
                      {matiere.nom}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="import-session">Session *</Label>
              <Select value={sessionId} onValueChange={setSessionId}>
                <SelectTrigger id="import-session">
                  <SelectValue placeholder="Sélectionner la session" />
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

            <div className="rounded-lg border bg-muted/30 p-3 text-xs text-muted-foreground">
              Le poids de chaque évaluation est celui de la matière, pris sur sa
              fiche. Un en-tête peut porter le sien : « Examen:2 ».
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="import-fichier">Fichier (.csv ou .xlsx)</Label>
            <Input
              id="import-fichier"
              type="file"
              accept=".csv,.xlsx,.xlsm"
              onChange={choisirFichier}
            />
            {modele && (
              <p className="text-xs text-muted-foreground">
                Colonnes attendues :{" "}
                <span className="font-mono">
                  {modele.exemple_entetes.join(", ")}
                </span>
              </p>
            )}
          </div>

          {!rapport && (
            <Button onClick={() => void lancerAnalyse()} disabled={analyse || !fichier}>
              {analyse ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Upload className="mr-2 h-4 w-4" />
              )}
              Analyser le fichier
            </Button>
          )}

          {rapport && (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary">
                  {rapport.evaluations.length} évaluation(s)
                </Badge>
                <Badge variant="secondary">{resume?.lignes ?? 0} ligne(s)</Badge>
                <Badge>
                  {resume?.total_notes ?? 0} note(s) à enregistrer
                </Badge>
                {(resume?.notes_modifiees ?? 0) > 0 && (
                  <Badge className="bg-amber-600 text-white">
                    dont {resume?.notes_modifiees} mise(s) à jour
                  </Badge>
                )}
                {(resume?.lignes_en_erreur ?? 0) > 0 && (
                  <Badge className="bg-red-600 text-white">
                    {resume?.lignes_en_erreur} ligne(s) en erreur
                  </Badge>
                )}
              </div>

              <div className="flex flex-wrap gap-1.5">
                {rapport.evaluations.map((evaluation) => (
                  <Badge key={evaluation.nom} variant="outline" className="font-mono">
                    {evaluation.nom} · coef {evaluation.coefficient} ·{" "}
                    {evaluation.type}
                    {evaluation.nouvelle ? " · nouvelle" : ""}
                  </Badge>
                ))}
              </div>

              <div className="max-h-72 overflow-y-auto rounded-lg border">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/40">
                      <TableHead className="w-12">Ligne</TableHead>
                      <TableHead>Étudiant</TableHead>
                      <TableHead className="text-right">Créer</TableHead>
                      <TableHead className="text-right">Modifier</TableHead>
                      <TableHead>Diagnostic</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rapport.lignes.map((ligne, index) => (
                      <TableRow
                        key={`${ligne.numero}-${index}`}
                        className={ligne.erreurs.length ? "bg-destructive/5" : undefined}
                      >
                        <TableCell className="font-mono text-xs">
                          {ligne.numero || "—"}
                        </TableCell>
                        <TableCell>
                          <p className="font-medium">
                            {ligne.nom_complet || "—"}
                          </p>
                          {ligne.matricule && (
                            <p className="font-mono text-xs text-muted-foreground">
                              {ligne.matricule}
                            </p>
                          )}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {ligne.a_creer || "—"}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {ligne.a_modifier || "—"}
                        </TableCell>
                        <TableCell className="text-sm">
                          {ligne.ignoree ? (
                            <span className="text-muted-foreground">
                              Ignorée (aucune note)
                            </span>
                          ) : ligne.erreurs.length ? (
                            <ul className="space-y-0.5">
                              {ligne.erreurs.map((message) => (
                                <li
                                  key={message}
                                  className="flex items-start gap-1.5 text-destructive"
                                >
                                  <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                                  {message}
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <span className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
                              <CheckCircle2 className="h-3.5 w-3.5" />
                              Prête
                            </span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {(resume?.lignes_en_erreur ?? 0) > 0 && (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>Certaines lignes seront ignorées</AlertTitle>
                  <AlertDescription>
                    Les lignes en erreur ne bloquent pas les autres : l&apos;import
                    enregistrera les {resume?.total_notes ?? 0} note(s) des lignes
                    valides. Corrigez le fichier et relancez si vous préférez tout
                    importer.
                  </AlertDescription>
                </Alert>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Fermer
          </Button>
          {rapport && (
            <>
              <Button variant="outline" onClick={reinitialiser} disabled={validation}>
                Recommencer
              </Button>
              <Button
                onClick={() => void valider()}
                disabled={validation || !rapport.importable}
              >
                {validation ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <FileSpreadsheet className="mr-2 h-4 w-4" />
                )}
                Enregistrer {resume?.total_notes ?? 0} note(s)
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ImportNotesDialog;
