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
import { getAcademicSessions, AcademicSession } from "@/services/academicSessionService";

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
  const [academicSessions, setAcademicSessions] = useState<AcademicSession[]>([]);

  useEffect(() => {
    setAcademicSessions(getAcademicSessions());
  }, [open]);

  const [formData, setFormData] = useState<Student>({
    id: "",
    nom: "",
    prenom: "",
    email: "",
    telephone: "",
    dateNaissance: "",
    lieuNaissance: "",
    filiere: "Génie Informatique",
    niveau: "Licence 1",
    cycle: "Licence",
    promotion: "2025-2026",
    statut: "actif",
    matricule: "",
    typeInscription: "nouvelle",
    etablissementOrigine: "",
    creditsValide: 60,
    sessionId: "SES-2025-MAIN",
  });

  useEffect(() => {
    if (student) {
      setFormData({
        ...student,
        sessionId: student.sessionId !== undefined ? student.sessionId : "SES-2025-MAIN",
      });
      setAutoMatricule(student.matricule);
      setTypeInscription(student.typeInscription || "reinscription");
    } else {
      // Generate preview matricule based on nomenclature settings
      const generated = `2025-INF-${Math.floor(1000 + Math.random() * 9000)}`;
      setAutoMatricule(generated);
      setFormData({
        id: "",
        nom: "",
        prenom: "",
        email: "",
        telephone: "",
        dateNaissance: "",
        lieuNaissance: "",
        filiere: "Génie Informatique",
        niveau: "Licence 1",
        cycle: "Licence",
        promotion: "2025-2026",
        statut: "actif",
        matricule: generated,
        typeInscription: "nouvelle",
        etablissementOrigine: "",
        creditsValide: 60,
        sessionId: "SES-2025-MAIN",
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
      id: formData.id || `ETU${Date.now()}`,
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
                  onValueChange={(val: any) => {
                    setTypeInscription(val);
                    if (val === "nouvelle") {
                      setAutoMatricule(`2025-INF-${Math.floor(1000 + Math.random() * 9000)}`);
                    } else {
                      setAutoMatricule("");
                    }
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
                      placeholder="Ex: 2024-INF-0042"
                      value={autoMatricule}
                      onChange={(e) => setAutoMatricule(e.target.value)}
                    />
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => {
                        if (autoMatricule) {
                          // Simulate API lookup
                          setFormData({
                            ...formData,
                            nom: "Dupont",
                            prenom: "Marie",
                            email: "marie.dupont@email.com",
                            telephone: "0700112233",
                            filiere: "Génie Informatique",
                            cycle: "Licence",
                            niveau: "Licence 2", // Upgraded from L1
                          });
                          toast.success("Dossier étudiant trouvé. Les informations ont été pré-remplies.");
                        } else {
                          toast.error("Veuillez saisir un matricule.");
                        }
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
                placeholder="Ex: Dupont"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="prenom">Prénom *</Label>
              <Input
                id="prenom"
                value={formData.prenom}
                onChange={(e) => setFormData({ ...formData, prenom: e.target.value })}
                placeholder="Ex: Marie"
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
                placeholder="marie.dupont@email.com"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="telephone">Téléphone</Label>
              <Input
                id="telephone"
                value={formData.telephone}
                onChange={(e) => setFormData({ ...formData, telephone: e.target.value })}
                placeholder="+225 07 00 11 22 33"
              />
            </div>
          </div>

          {/* Cycle & Academic Level */}
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="cycle">Cycle Académique *</Label>
              <Select
                value={formData.cycle}
                onValueChange={(val) => setFormData({ ...formData, cycle: val })}
              >
                <SelectTrigger id="cycle">
                  <SelectValue placeholder="Cycle" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Licence">Cycle Licence (L1, L2, L3)</SelectItem>
                  <SelectItem value="Master">Cycle Master (M1, M2)</SelectItem>
                  <SelectItem value="Doctorat">Cycle Doctorat (D1, D2, D3)</SelectItem>
                  <SelectItem value="BTS_DUT">BTS / DUT (Bac+2)</SelectItem>
                </SelectContent>
              </Select>
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
                  <SelectItem value="Génie Informatique">Génie Informatique</SelectItem>
                  <SelectItem value="Gestion & Finance">Gestion & Finance</SelectItem>
                  <SelectItem value="Commerce & Marketing">Commerce & Marketing</SelectItem>
                  <SelectItem value="Droit & Science Po">Droit & Science Po</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="niveau">Niveau / Classe *</Label>
              <Select
                value={formData.niveau}
                onValueChange={(value) => setFormData({ ...formData, niveau: value })}
              >
                <SelectTrigger id="niveau">
                  <SelectValue placeholder="Niveau" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Licence 1">Licence 1 (L1)</SelectItem>
                  <SelectItem value="Licence 2">Licence 2 (L2)</SelectItem>
                  <SelectItem value="Licence 3">Licence 3 (L3)</SelectItem>
                  <SelectItem value="Master 1">Master 1 (M1)</SelectItem>
                  <SelectItem value="Master 2">Master 2 (M2)</SelectItem>
                </SelectContent>
              </Select>
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
                placeholder="Ex: Université Félix Houphouët-Boigny"
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
