import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2 } from "lucide-react";
import { semestresApi, sessionsApi } from "@/services/apiClient";
import type { Semestre } from "@/services/apiTypes";

/** Valeur du select quand l'UE n'est rattachee a aucun semestre. */
const HORS_SEMESTRE = "__hors_semestre__";

interface UE {
  id: string;
  code: string;
  nom: string;
  type: "UE";
  credits: number;
  coefficient: number;
  heures: number;
  filiere: string;
  niveau: string;
  /** Libelle d'affichage, renseigne avec le semestre choisi. */
  semestre: string;
  /** Rattachement structurel : c'est lui que le moteur de moyennes lit. */
  semestre_id?: string | null;
  /**
   * `semestrielle` (defaut) ou `annuelle`. Un enseignement annuel figure sur
   * tous les semestres et se donne sur chacun : il n'a pas de semestre unique.
   */
  regime?: "semestrielle" | "annuelle";
  responsable?: string;
  description?: string;
}

/**
 * Ce que l'agent doit voir avant de choisir un semestre. Les trois etats sont
 * distincts et aucun n'est une liste vide : un select sans option se lit comme
 * « rien a choisir », alors qu'il peut signifier « le chargement a echoue ».
 */
type Chargement =
  | { etat: "chargement" }
  | { etat: "echec"; message: string }
  | { etat: "sans_session"; message: string }
  | { etat: "pret"; semestres: Semestre[] };

interface UEDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (data: Partial<UE>) => void;
  ue: UE | null;
  filieres: { id: string; nom: string }[];
}

export function UEDialog({ open, onOpenChange, onSave, ue, filieres }: UEDialogProps) {
  const [formData, setFormData] = useState<Partial<UE>>({
    code: "",
    nom: "",
    type: "UE",
    credits: 0,
    coefficient: 0,
    heures: 0,
    filiere: "",
    niveau: "",
    semestre: "",
    semestre_id: null,
    responsable: "",
    description: "",
  });
  const [charge, setCharge] = useState<Chargement>({ etat: "chargement" });

  useEffect(() => {
    if (ue) {
      setFormData(ue);
    } else {
      setFormData({
        code: "",
        nom: "",
        type: "UE",
        credits: 0,
        coefficient: 0,
        heures: 0,
        filiere: "",
        niveau: "",
        semestre: "",
        semestre_id: null,
        responsable: "",
        description: "",
      });
    }
  }, [ue, open]);

  useEffect(() => {
    if (!open) return;
    let annule = false;

    (async () => {
      setCharge({ etat: "chargement" });
      // Une session active est requise : c'est elle qui porte les semestres.
      const session = await sessionsApi.getActive();
      if (annule) return;
      if (session.error || !session.data) {
        setCharge({
          etat: "sans_session",
          message:
            "Aucune session active : impossible de proposer des semestres. Créez une session depuis Paramètres ▸ Sessions.",
        });
        return;
      }
      const repartition = await semestresApi.getRepartition(session.data.id);
      if (annule) return;
      if (repartition.error || !repartition.data) {
        setCharge({
          etat: "echec",
          message:
            repartition.error ||
            "Impossible de charger les semestres de la session. Réessayez : l'UE pourra être enregistrée, mais elle restera hors des bulletins tant qu'elle n'est pas rattachée.",
        });
        return;
      }
      setCharge({ etat: "pret", semestres: repartition.data.semestres });
    })();

    return () => {
      annule = true;
    };
  }, [open]);

  /**
   * Le semestre est choisi, pas saisi. On renseigne les deux champs d'un coup —
   * l'identifiant, que le moteur lit, et le libelle, qui s'affiche — pour qu'ils
   * ne puissent pas diverger a la saisie.
   *
   * Passer une UE en regime annuel retire son semestre des deux champs : il
   * n'en designe aucun, et l'API refuse cette combinaison. Le faire ici evite
   * que l'utilisateur decouvre le refus apres avoir rempli le formulaire.
   */
  const choisirSemestre = (valeur: string) => {
    if (valeur === HORS_SEMESTRE) {
      setFormData((precedent) => ({
        ...precedent,
        semestre_id: null,
        semestre: "",
      }));
      return;
    }
    const choisi = charge.etat === "pret"
      ? charge.semestres.find((s) => s.id === valeur)
      : undefined;
    setFormData((precedent) => ({
      ...precedent,
      semestre_id: valeur,
      semestre: choisi?.libelle ?? "",
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  const annuel = formData.regime === "annuelle";
  const horsSemestre =
    formData.semestre_id == null || formData.semestre_id === "";
  const rattacheInconnu =
    !annuel &&
    formData.semestre_id != null &&
    charge.etat === "pret" &&
    !charge.semestres.some((s) => s.id === formData.semestre_id);

  /** Bascule le regime. Un annuel n'a pas de semestre : on retire les deux. */
  const choisirRegime = (valeur: string) => {
    if (valeur === "annuelle") {
      setFormData((precedent) => ({
        ...precedent,
        regime: "annuelle",
        semestre_id: null,
        semestre: "",
      }));
      return;
    }
    setFormData((precedent) => ({ ...precedent, regime: "semestrielle" }));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{ue ? "Modifier l'UE" : "Créer une UE"}</DialogTitle>
          <DialogDescription>
            {ue ? "Modifiez les informations de l'unité d'enseignement" : "Créez une nouvelle unité d'enseignement"}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="code">Code UE *</Label>
                <Input
                  id="code"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                  placeholder="Code de l'unité"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="responsable">Responsable UE</Label>
                <Input
                  id="responsable"
                  value={formData.responsable || ""}
                  onChange={(e) => setFormData({ ...formData, responsable: e.target.value })}
                  placeholder="Nom du responsable"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="nom">Nom de l'UE *</Label>
              <Input
                id="nom"
                value={formData.nom}
                onChange={(e) => setFormData({ ...formData, nom: e.target.value })}
                placeholder="Intitulé de l'unité"
                required
              />
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="credits">Crédits ECTS *</Label>
                <Input
                  id="credits"
                  type="number"
                  min="0"
                  value={formData.credits}
                  onChange={(e) => setFormData({ ...formData, credits: parseInt(e.target.value) })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="coefficient">Coefficient *</Label>
                <Input
                  id="coefficient"
                  type="number"
                  min="0"
                  value={formData.coefficient}
                  onChange={(e) => setFormData({ ...formData, coefficient: parseInt(e.target.value) })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="heures">Volume Horaire *</Label>
                <Input
                  id="heures"
                  type="number"
                  min="0"
                  value={formData.heures}
                  onChange={(e) => setFormData({ ...formData, heures: parseInt(e.target.value) })}
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="filiere">Filière *</Label>
                <Select
                  value={formData.filiere}
                  onValueChange={(value) => setFormData({ ...formData, filiere: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Sélectionner" />
                  </SelectTrigger>
                  <SelectContent>
                    {filieres.map((filiere) => (
                      <SelectItem key={filiere.id} value={filiere.id}>
                        {filiere.nom}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="regime">Régime *</Label>
                <Select
                  value={formData.regime ?? "semestrielle"}
                  onValueChange={choisirRegime}
                >
                  <SelectTrigger id="regime" aria-label="Régime de l'enseignement">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="semestrielle">
                      Semestriel — sur un seul semestre
                    </SelectItem>
                    <SelectItem value="annuelle">
                      Annuel — sur toute l'année
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="niveau">Niveau *</Label>
                <Input id="niveau" value={formData.niveau || ""} onChange={(e) => setFormData({ ...formData, niveau: e.target.value })} required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="semestre">Semestre *</Label>
                {annuel ? (
                  /* Un enseignement annuel figure sur **tous** les semestres :
                     il n'en designe aucun. Le champ disparait plutot que de
                     proposer un semestre que l'API refuserait. */
                  <div
                    id="semestre"
                    className="flex h-9 items-center rounded-md border bg-muted/40 px-3 text-sm text-muted-foreground"
                  >
                    Tous les semestres
                  </div>
                ) : charge.etat === "chargement" ? (
                  <div className="flex h-9 items-center gap-2 rounded-md border px-3 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                    Chargement des semestres…
                  </div>
                ) : (
                  <Select
                    value={formData.semestre_id ?? HORS_SEMESTRE}
                    onValueChange={choisirSemestre}
                    disabled={charge.etat !== "pret"}
                  >
                    <SelectTrigger id="semestre" aria-label="Semestre">
                      <SelectValue placeholder="Sélectionner un semestre" />
                    </SelectTrigger>
                    <SelectContent>
                      {charge.etat === "pret" &&
                        charge.semestres.map((semestre) => (
                          <SelectItem key={semestre.id} value={semestre.id}>
                            {semestre.numero}. {semestre.libelle}
                          </SelectItem>
                        ))}
                      <SelectItem value={HORS_SEMESTRE}>
                        Aucun semestre (hors bulletin)
                      </SelectItem>
                    </SelectContent>
                  </Select>
                )}
              </div>
            </div>

            {/* Les trois messages ci-dessous se distinguent volontairement : un
                select vide ne dit pas *pourquoi* il est vide. */}
            {charge.etat === "echec" && (
              <Alert variant="destructive">
                <AlertDescription>{charge.message}</AlertDescription>
              </Alert>
            )}
            {charge.etat === "sans_session" && (
              <Alert variant="destructive">
                <AlertDescription>{charge.message}</AlertDescription>
              </Alert>
            )}
            {charge.etat === "pret" && charge.semestres.length === 0 && !annuel && (
              <Alert>
                <AlertDescription>
                  Cette session n'a aucun semestre. Ajoutez-en depuis Paramètres ▸
                  Structure ▸ Semestres : sans rattachement, cette UE n'apparaîtra
                  sur aucun bulletin.
                </AlertDescription>
              </Alert>
            )}
            {annuel && (
              <Alert>
                <AlertDescription>
                  Cet enseignement est annuel : il figurera sur le bulletin de
                  **chaque** semestre, avec une note propre à chacun. Ses
                  crédits {formData.credits ?? 0} s'inscrivent dans le total de
                  chaque semestre où il apparaît — inscrivez la part de
                  l'année si votre institut les partage.
                </AlertDescription>
              </Alert>
            )}
            {rattacheInconnu && (
              <Alert variant="destructive">
                <AlertDescription>
                  Cette UE était rattachée à un semestre qui n'existe plus. Choisissez-en
                  un autre, ou laissez « Aucun semestre » pour la sortir des bulletins.
                </AlertDescription>
              </Alert>
            )}
            {charge.etat === "pret" && !rattacheInconnu && !annuel && horsSemestre && (
              <Alert>
                <AlertDescription>
                  UE sans semestre : elle n'apparaîtra sur aucun bulletin, et ses
                  notes ne compteront dans aucune moyenne de semestre.
                </AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="description">Description & Objectifs</Label>
              <Textarea
                id="description"
                value={formData.description || ""}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Objectifs pédagogiques de l'UE..."
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Annuler
            </Button>
            <Button type="submit" className="bg-primary hover:bg-primary-hover">
              {ue ? "Modifier" : "Créer"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
