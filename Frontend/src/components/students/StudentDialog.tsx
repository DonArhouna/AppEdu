import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Lock, UserCheck, RefreshCw, Sparkles, Building, Calendar } from "lucide-react";
import { toast } from "sonner";
import { etudiantsApi, sessionsApi, structureApi } from "@/services/apiClient";
import type { AcademicSession as ApiAcademicSession, Student as StudentDto } from "@/services/apiTypes";

interface AcademicSessionOption {
  id: string;
  nom: string;
  code: string;
  anneeAcademique: string;
  dateDebut: string;
  dateFin: string;
  statut: string;
  description: string;
  periodes: ApiAcademicSession["periodes"];
}

export interface Student {
  id: string;
  nom: string;
  prenom: string;
  email: string;
  telephone: string;
  dateNaissance: string;
  lieuNaissance: string;
  filiere: string;
  niveau: string;
  cycle: string; // Licence, Master, Doctorat
  promotion: string;
  statut: string;
  matricule: string;
  typeInscription?: "nouvelle" | "reinscription";
  etablissementOrigine?: string;
  creditsValide?: number;
  creditsValides?: number;
  sessionId?: string; // Rattachement Session Académique
}

interface StudentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  student?: Student | null;
  onSave: (student: Student) => void;
}

export const StudentDialog = ({
  open,
  onOpenChange,
  student,
  onSave,
}: StudentDialogProps) => {
  const [typeInscription, setTypeInscription] = useState<"nouvelle" | "reinscription">("nouvelle");
  const [autoMatricule, setAutoMatricule] = useState("");
  const [academicSessions, setAcademicSessions] = useState<AcademicSessionOption[]>([]);
  const [filieres, setFilieres] = useState<{ id: string; nom: string }[]>([]);

  useEffect(() => {
    if (!open) return;
    const loadSessions = async () => {
      const [sessionResult, filiereResult] = await Promise.all([
        sessionsApi.getAll(),
        structureApi.getFilieres(),
      ]);
      if (filiereResult.data) setFilieres(filiereResult.data as { id: string; nom: string }[]);
      if (sessionResult.error || !sessionResult.data) return;
      setAcademicSessions(
        sessionResult.data.map((session) => ({
          id: session.id,
          nom: session.nom,
          code: session.code,
          anneeAcademique: session.annee_academique,
          dateDebut: session.date_debut,
          dateFin: session.date_fin,
          statut: session.statut,
          description: session.description || "",
          periodes: session.periodes || [],
        }))
      );
    };
    void loadSessions();
  }, [open]);

  const [formData, setFormData] = useState<Student>({
    id: "",
    nom: "",
    prenom: "",
    email: "",
    telephone: "",
    dateNaissance: "",
    lieuNaissance: "",
    filiere: "",
    niveau: "",
    cycle: "",
    promotion: "",
    statut: "actif",
    matricule: "",
    typeInscription: "nouvelle",
    etablissementOrigine: "",
    creditsValide: 0,
    sessionId: "",
  });

  useEffect(() => {
    if (student) {
      setFormData({
        ...student,
        sessionId: student.sessionId || "",
      });
      setAutoMatricule(student.matricule);
      setTypeInscription(student.typeInscription || "reinscription");
    } else {
      const generated = "";
      setFormData({
        id: "",
        nom: "",
        prenom: "",
        email: "",
        telephone: "",
        dateNaissance: "",
        lieuNaissance: "",
        filiere: "",
        niveau: "",
        cycle: "",
        promotion: "",
        statut: "actif",
        matricule: generated,
        typeInscription: "nouvelle",
        etablissementOrigine: "",
        creditsValide: 0,
        sessionId: "",
      });
    }
  }, [student, open]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.nom || !formData.prenom || !formData.email) {
      toast.error("Veuillez remplir tous les champs obligatoires");
      return;
    }

    const finalStudent: Student = {
      ...formData,
      id: formData.id,
      matricule: autoMatricule,
      typeInscription,
    };

    onSave(finalStudent);
    toast.success(
      typeInscription === "reinscription"
        ? `Réinscription effectuée avec succès pour ${formData.prenom} ${formData.nom}`
        : `Nouvelle inscription enregistrée. Matricule attribué : ${autoMatricule}`
    );
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <UserCheck className="h-5 w-5 text-primary" />
            {student ? "Modifier le Dossier Étudiant" : "Inscription & Réinscription Étudiant"}
          </DialogTitle>
          <DialogDescription>
            Gestion standardisée du cycle académique, du matricule automatique et des réinscriptions.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Mode Inscription Selection */}
          {!student && (
            <div className="rounded-xl border p-4 bg-muted/40 space-y-4">
              <div>
                <Label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Type de Procédure Académique *
                </Label>
                <RadioGroup
                  value={typeInscription}
                  onValueChange={(val: string) => {
                    setTypeInscription(val === "reinscription" ? "reinscription" : "nouvelle");
                    setAutoMatricule("");
                  }}
                  className="grid grid-cols-2 gap-4 pt-2"
                >
                  <div className={`flex items-center space-x-3 p-3 rounded-lg border cursor-pointer ${typeInscription === "nouvelle" ? "bg-primary/10 border-primary font-semibold" : "bg-card"}`}>
                    <RadioGroupItem value="nouvelle" id="r-nouvelle" />
                    <label htmlFor="r-nouvelle" className="text-xs cursor-pointer">
                      <span className="font-bold block">Nouvelle Inscription</span>
                      <span className="text-[11px] text-muted-foreground">Nouveau bachelier ou transfert d'établissement</span>
                    </label>
                  </div>

                  <div className={`flex items-center space-x-3 p-3 rounded-lg border cursor-pointer ${typeInscription === "reinscription" ? "bg-primary/10 border-primary font-semibold" : "bg-card"}`}>
                    <RadioGroupItem value="reinscription" id="r-reinscription" />
                    <label htmlFor="r-reinscription" className="text-xs cursor-pointer">
                      <span className="font-bold block">Réinscription</span>
                      <span className="text-[11px] text-muted-foreground">Passage en classe supérieure (Étudiant existant)</span>
                    </label>
                  </div>
                </RadioGroup>
              </div>

              {typeInscription === "reinscription" && (
                <div className="space-y-2 pt-2 border-t border-border/50">
                  <Label htmlFor="search-matricule" className="text-xs font-bold flex items-center gap-1.5">
                    <RefreshCw className="h-3.5 w-3.5 text-primary" />
                    Rechercher le dossier existant (Saisir Matricule)
                  </Label>
                  <div className="flex gap-2">
                    <Input
                      id="search-matricule"
                      placeholder="Saisissez le matricule"
                      value={autoMatricule}
                      onChange={(e) => setAutoMatricule(e.target.value)}
                    />
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={async () => {
                        if (!autoMatricule) {
                          toast.error("Veuillez saisir un matricule.");
                          return;
                        }
                        const result = await etudiantsApi.getAll({ search: autoMatricule });
                        const found = (result.data || []).find(
                          (candidate: StudentDto) => candidate.matricule === autoMatricule
                        );
                        if (result.error || !found) {
                          toast.error("Aucun dossier trouvé pour ce matricule.");
                          return;
                        }
                        setFormData((current) => ({
                          ...current,
                          id: found.id,
                          nom: found.nom || "",
                          prenom: found.prenom || "",
                          email: found.email || "",
                          telephone: found.telephone || "",
                          filiere: found.filiere || "",
                          niveau: found.niveau || "",
                          cycle: found.niveau?.startsWith("Master") ? "Master" : "",
                          sessionId: found.session_id || "",
                        }));
                        toast.success("Dossier étudiant chargé depuis l'API.");
                      }}
                    >
                      Rechercher
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Grisé / Read-only Matricule Field for New Inscription */}
          {typeInscription === "nouvelle" && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="matricule" className="text-xs font-bold flex items-center gap-1.5">
                  <Lock className="h-3.5 w-3.5 text-muted-foreground" />
                  Matricule Étudiant (Nomenclature Configurable)
                </Label>
                <Badge variant="outline" className="text-[10px] font-mono bg-muted">
                  Généré Automatiquement
                </Badge>
              </div>
              <div className="relative">
                <Input
                  id="matricule"
                  value={autoMatricule}
                  disabled
                  className="bg-muted font-mono font-bold text-primary disabled:opacity-90"
                />
                <Sparkles className="absolute right-3 top-2.5 h-4 w-4 text-amber-500" />
              </div>
              <p className="text-[10px] text-muted-foreground">
                Format attribué selon la nomenclature établie par l'établissement (ex: 2025-FILIERE-SEQ).
              </p>
            </div>
          )}

          {/* Personal Info */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="nom">Nom *</Label>
              <Input
                id="nom"
                value={formData.nom}
                onChange={(e) => setFormData({ ...formData, nom: e.target.value })}
                placeholder="Nom"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="prenom">Prénom *</Label>
              <Input
                id="prenom"
                value={formData.prenom}
                onChange={(e) => setFormData({ ...formData, prenom: e.target.value })}
                placeholder="Prénom"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email Institutionnel / Perso *</Label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="Adresse email"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="telephone">Téléphone</Label>
              <Input
                id="telephone"
                value={formData.telephone}
                onChange={(e) => setFormData({ ...formData, telephone: e.target.value })}
                placeholder="Numéro de téléphone"
              />
            </div>
          </div>

          {/* Cycle & Academic Level */}
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="cycle">Cycle Académique *</Label>
              <Input
                id="cycle"
                value={formData.cycle}
                onChange={(e) => setFormData({ ...formData, cycle: e.target.value })}
                placeholder="Cycle"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="filiere">Filière *</Label>
              <Select
                value={formData.filiere}
                onValueChange={(value) => setFormData({ ...formData, filiere: value })}
              >
                <SelectTrigger id="filiere">
                  <SelectValue placeholder="Filière" />
                </SelectTrigger>
                <SelectContent>
                  {filieres.map((filiere) => (
                    <SelectItem key={filiere.id} value={filiere.nom}>
                      {filiere.nom}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="niveau">Niveau / Classe *</Label>
              <Input
                id="niveau"
                value={formData.niveau}
                onChange={(e) => setFormData({ ...formData, niveau: e.target.value })}
                placeholder="Niveau ou classe"
              />
            </div>
          </div>

          {/* Rattachement Session Académique */}
          <div className="space-y-2 p-3.5 rounded-xl border bg-primary/5 border-primary/20">
            <div className="flex items-center justify-between">
              <Label htmlFor="session-select" className="text-xs font-bold text-foreground flex items-center gap-1.5">
                <Calendar className="h-3.5 w-3.5 text-primary" />
                Session Académique Rattachée *
              </Label>
              <Badge variant="outline" className="text-[10px] bg-background border-primary/30 text-primary font-semibold">
                Calendrier financier dynamique
              </Badge>
            </div>
            <Select
              value={formData.sessionId || "none"}
              onValueChange={(val) => setFormData({ ...formData, sessionId: val === "none" ? "" : val })}
            >
              <SelectTrigger id="session-select" className="bg-background">
                <SelectValue placeholder="Sélectionner la session académique..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">-- Aucune session (Non rattaché - Bloque paiement) --</SelectItem>
                {academicSessions.map((ses) => (
                  <SelectItem key={ses.id} value={ses.id}>
                    {ses.nom} ({ses.periodes.length} tranches configurées)
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-[10px] text-muted-foreground">
              Les tranches et échéances proposées lors des règlements de scolarité seront calculées dynamiquement selon cette session.
            </p>
          </div>

          {/* Transfer Info if New Entrant from other school */}
          {typeInscription === "nouvelle" && (
            <div className="space-y-2 p-3 rounded-lg border border-dashed bg-muted/20">
              <Label htmlFor="orig" className="text-xs font-semibold flex items-center gap-1.5">
                <Building className="h-3.5 w-3.5 text-muted-foreground" />
                Établissement d'Origine (Si étudiant en transfert)
              </Label>
              <Input
                id="orig"
                placeholder="Établissement d'origine"
                value={formData.etablissementOrigine || ""}
                onChange={(e) => setFormData({ ...formData, etablissementOrigine: e.target.value })}
              />
            </div>
          )}

          <DialogFooter className="pt-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Annuler
            </Button>
            <Button type="submit">
              {student ? "Mettre à jour" : typeInscription === "reinscription" ? "Valider la Réinscription" : "Valider l'Inscription"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
