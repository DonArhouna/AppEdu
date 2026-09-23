import { useState, useEffect, useMemo } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
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
import { Checkbox } from "@/components/ui/checkbox";
import {
  CreditCard,
  DollarSign,
  Calculator,
  Lock,
  UserCheck,
  AlertCircle,
  CalendarDays,
  CheckCircle2,
  History,
  AlertTriangle,
  ArrowRight
} from "lucide-react";
import { toast } from "sonner";
import { ReceiptModal } from "./ReceiptModal";
import {
  getStudentsRegistry,
  getAcademicSessions,
  getAcademicSessionById,
  updateStudentSession,
  recordPaymentForStudent,
  AcademicSession,
  PaymentPeriod,
  StudentSessionProfile,
} from "@/services/academicSessionService";

export interface PaiementPhysiqueModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onPaymentSuccess?: (paymentRecord: any) => void;
  initialMatricule?: string;
}

// Configured Fee Rates per Filiere / Level
const configuredTarifs: Record<string, { inscription: number; mensuel: number }> = {
  "Licence 1": { inscription: 150000, mensuel: 60000 },
  "Licence 2": { inscription: 150000, mensuel: 60000 },
  "Licence 3": { inscription: 150000, mensuel: 65000 },
  "Master 1": { inscription: 200000, mensuel: 85000 },
  "Master 2": { inscription: 200000, mensuel: 95000 },
};

export const PaiementPhysiqueModal = ({
  open,
  onOpenChange,
  onPaymentSuccess,
  initialMatricule,
}: PaiementPhysiqueModalProps) => {
  const [students, setStudents] = useState<StudentSessionProfile[]>([]);
  const [sessions, setSessions] = useState<AcademicSession[]>([]);
  const [selectedMatricule, setSelectedMatricule] = useState<string>("2025-INF-0042");
  const [payInscription, setPayInscription] = useState(false);
  const [selectedPeriods, setSelectedPeriods] = useState<string[]>([]);
  const [modePaiement, setModePaiement] = useState("Espèces");
  const [reference, setReference] = useState("");
  const [receiptOpen, setReceiptOpen] = useState(false);
  const [lastReceiptData, setLastReceiptData] = useState<any>(null);

  // Fallback session assignment modal/select
  const [quickAssignSessionId, setQuickAssignSessionId] = useState<string>("");

  const refreshRegistry = () => {
    const stuList = getStudentsRegistry();
    const sesList = getAcademicSessions();
    setStudents(stuList);
    setSessions(sesList);
  };

  useEffect(() => {
    refreshRegistry();
    window.addEventListener("emp_sessions_changed", refreshRegistry);
    return () => window.removeEventListener("emp_sessions_changed", refreshRegistry);
  }, [open]);

  useEffect(() => {
    if (initialMatricule) {
      setSelectedMatricule(initialMatricule);
    } else if (students.length > 0 && !students.some((s) => s.matricule === selectedMatricule)) {
      setSelectedMatricule(students[0].matricule);
    }
  }, [initialMatricule, students]);

  // Current active student
  const student = useMemo(() => {
    return students.find((s) => s.matricule === selectedMatricule) || students[0] || {
      matricule: "2025-INF-0042",
      nom: "Dupont",
      prenom: "Marie",
      filiere: "Génie Informatique",
      niveau: "Licence 3",
      sessionId: "SES-2025-MAIN",
    };
  }, [students, selectedMatricule]);

  // Academic session attached to student
  const assignedSession = useMemo(() => {
    if (!student?.sessionId) return null;
    return sessions.find((s) => s.id === student.sessionId) || null;
  }, [student, sessions]);

  // Dynamic payment periods from session
  const availablePeriods: PaymentPeriod[] = useMemo(() => {
    return assignedSession ? assignedSession.periodes : [];
  }, [assignedSession]);

  // Already paid periods across history
  const alreadyPaidPeriods = useMemo(() => {
    const history = student?.historiquePaiements || [];
    const paidSet = new Set<string>();
    history.forEach((h) => {
      (h.periodes || []).forEach((p) => paidSet.add(p));
    });
    return paidSet;
  }, [student]);

  // Reset selected periods when student or session changes
  useEffect(() => {
    setSelectedPeriods([]);
    setPayInscription(false);
  }, [selectedMatricule, student?.sessionId]);

  const tarif = configuredTarifs[student?.niveau || "Licence 1"] || { inscription: 150000, mensuel: 60000 };

  // Helper to get period cost
  const getPeriodCost = (p: PaymentPeriod) => {
    if (p.montantEstime && p.montantEstime > 0) return p.montantEstime;
    if (p.pourcentage && p.pourcentage > 0) {
      // If percentage is set on annual tuition (e.g. 9 months * mensuel)
      return Math.round(((tarif.mensuel * 9) * p.pourcentage) / 100);
    }
    return tarif.mensuel;
  };

  // Automatic Calculation (No manual amount entry!)
  const montantInscription = payInscription ? tarif.inscription : 0;
  const montantPeriodesTotal = selectedPeriods.reduce((acc, pId) => {
    const periodObj = availablePeriods.find((p) => p.id === pId);
    return acc + (periodObj ? getPeriodCost(periodObj) : tarif.mensuel);
  }, 0);
  const totalACalculer = montantInscription + montantPeriodesTotal;

  const togglePeriod = (periodId: string) => {
    if (alreadyPaidPeriods.has(periodId)) return;
    setSelectedPeriods((prev) =>
      prev.includes(periodId) ? prev.filter((id) => id !== periodId) : [...prev, periodId]
    );
  };

  const handleSelectAllPeriods = () => {
    const payablePeriods = availablePeriods.filter(
      (p) => !alreadyPaidPeriods.has(p.nom) && !alreadyPaidPeriods.has(p.id)
    );
    if (selectedPeriods.length === payablePeriods.length) {
      setSelectedPeriods([]);
    } else {
      setSelectedPeriods(payablePeriods.map((p) => p.id));
    }
  };

  const handleAssignSessionNow = () => {
    if (!quickAssignSessionId) {
      toast.error("Veuillez choisir une session académique valide.");
      return;
    }
    updateStudentSession(student.matricule, quickAssignSessionId);
    toast.success(`Session assignée avec succès à ${student.prenom} ${student.nom}.`);
    setQuickAssignSessionId("");
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!assignedSession) {
      toast.error("Action impossible : L'étudiant doit d'abord être rattaché à une session académique.");
      return;
    }

    if (totalACalculer <= 0) {
      toast.error("Veuillez sélectionner au moins les droits d'inscription ou une tranche de scolarité.");
      return;
    }

    const periodesText: string[] = [];
    if (payInscription) periodesText.push("Droits d'Inscription");
    selectedPeriods.forEach((pId) => {
      const pObj = availablePeriods.find((p) => p.id === pId);
      if (pObj) periodesText.push(pObj.nom);
    });

    const receipt = {
      numRecu: `REC-${Math.floor(100000 + Math.random() * 900000)}`,
      datePaiement: new Date().toLocaleDateString("fr-FR"),
      sessionId: assignedSession.id,
      sessionNom: assignedSession.nom,
      etudiant: student,
      modePaiement,
      referencePaiement: reference || `Ticket Caisse #${Math.floor(100 + Math.random() * 900)}`,
      periodesPayees: periodesText,
      montantDetail: {
        total: totalACalculer,
        paye: totalACalculer,
        reste: 0,
      },
      caissier: "Mme Clarisse N'Guessan (Caisse Centrale)",
    };

    // Persist in student's financial record
    recordPaymentForStudent(student.matricule, {
      numRecu: receipt.numRecu,
      datePaiement: receipt.datePaiement,
      sessionId: assignedSession.id,
      periodes: periodesText,
      montant: totalACalculer,
    });

    setLastReceiptData(receipt);
    if (onPaymentSuccess) onPaymentSuccess(receipt);

    toast.success(`Paiement de ${totalACalculer.toLocaleString()} FCFA enregistré avec succès.`);
    onOpenChange(false);
    setReceiptOpen(true);
  };

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-[700px] max-h-[92vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-xl">
              <DollarSign className="h-6 w-6 text-emerald-500" />
              Nouveau Paiement Physique (Guichet Caisse)
            </DialogTitle>
            <DialogDescription>
              Enregistrement des règlements sur place avec calcul dynamique des tranches selon la session académique
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-5 py-2">
            {/* ── 1. Student Selection ── */}
            <div className="space-y-2">
              <Label htmlFor="student-select" className="text-xs font-bold">
                Sélectionner l'Étudiant *
              </Label>
              <Select value={selectedMatricule} onValueChange={setSelectedMatricule}>
                <SelectTrigger id="student-select" className="h-10">
                  <SelectValue placeholder="Sélectionner l'étudiant par nom ou matricule" />
                </SelectTrigger>
                <SelectContent>
                  {students.map((s) => {
                    const hasSession = !!s.sessionId;
                    return (
                      <SelectItem key={s.matricule} value={s.matricule}>
                        {s.prenom} {s.nom} ({s.matricule}) - {s.filiere} ({s.niveau})
                        {!hasSession ? " ⚠️ [Sans Session]" : ""}
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
            </div>

            {/* ── 2. Session Context or Warning Alert ── */}
            {assignedSession ? (
              <div className="rounded-xl border border-primary/20 bg-primary/5 p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-3">
                  <div className="h-9 w-9 rounded-lg bg-primary/10 text-primary font-bold flex items-center justify-center shrink-0">
                    <CalendarDays className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="font-bold text-foreground">{assignedSession.nom}</p>
                      <Badge variant="outline" className="font-mono text-[10px] bg-background text-primary">
                        {assignedSession.code}
                      </Badge>
                    </div>
                    <p className="text-muted-foreground text-[11px] mt-0.5">
                      Période : {assignedSession.dateDebut} au {assignedSession.dateFin} •{" "}
                      <span className="font-semibold text-foreground">
                        {assignedSession.periodes.length} tranches configurées
                      </span>
                    </p>
                  </div>
                </div>

                <Badge variant="outline" className="bg-background text-emerald-600 border-emerald-300 font-semibold text-[10px] self-start sm:self-auto">
                  <CheckCircle2 className="h-3 w-3 mr-1" />
                  Session Active
                </Badge>
              </div>
            ) : (
              /* CAS LIMITE : Étudiant sans session assignée */
              <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 space-y-3">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-bold text-sm text-destructive">
                      Aucune Session Académique Rattachée
                    </h4>
                    <p className="text-xs text-muted-foreground mt-1">
                      Cet étudiant ({student?.prenom} {student?.nom}) n'est rattaché à aucun calendrier académique.
                      Le système ne peut pas déterminer les tranches d'échéances pour ce profil.
                    </p>
                  </div>
                </div>

                {/* Quick Fix: Assign Session Inline */}
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 pt-1 border-t border-destructive/20">
                  <div className="flex-1">
                    <Select value={quickAssignSessionId} onValueChange={setQuickAssignSessionId}>
                      <SelectTrigger className="h-8 text-xs bg-background">
                        <SelectValue placeholder="Choisir une session pour débloquer..." />
                      </SelectTrigger>
                      <SelectContent>
                        {sessions.map((ses) => (
                          <SelectItem key={ses.id} value={ses.id}>
                            {ses.nom} ({ses.periodes.length} tranches)
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <Button
                    type="button"
                    size="sm"
                    className="h-8 text-xs gap-1.5"
                    onClick={handleAssignSessionNow}
                  >
                    Rattacher & Débloquer
                    <ArrowRight className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            )}

            {/* Configured Rate Info Box */}
            <div className="rounded-xl border bg-muted/40 p-3 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2.5">
                <div className="h-8 w-8 rounded-lg bg-primary/10 text-primary font-bold flex items-center justify-center">
                  <Lock className="h-3.5 w-3.5" />
                </div>
                <div>
                  <p className="font-bold text-foreground">Tarif Grille Officielle ({student.niveau})</p>
                  <p className="text-muted-foreground text-[11px]">
                    Inscription : <span className="font-semibold text-foreground">{tarif.inscription.toLocaleString()} FCFA</span> • Base mensuelle : <span className="font-semibold text-foreground">{tarif.mensuel.toLocaleString()} FCFA</span>
                  </p>
                </div>
              </div>
              <Badge variant="outline" className="bg-background text-primary font-mono text-[10px]">
                Calcul Automatique
              </Badge>
            </div>

            {/* ── 3. Items to Pay Selection (Dynamic Periods) ── */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-xs font-bold text-foreground">
                    Tranches Définies pour cette Session :
                  </Label>
                  <span className="text-[11px] text-muted-foreground block">
                    Seules les périodes de la session rattachée ({assignedSession?.nom || "Non assignée"}) sont présentées.
                  </span>
                </div>
                {assignedSession && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={handleSelectAllPeriods}
                    className="h-6 text-[11px] text-primary hover:bg-primary/10"
                  >
                    {selectedPeriods.length > 0 ? "Tout décocher" : "Sélect. Toutes les tranches"}
                  </Button>
                )}
              </div>

              {/* Registration Fee Checkbox */}
              <div className="flex items-center space-x-3 p-3 rounded-xl border bg-card hover:bg-accent/40 transition-colors">
                <Checkbox
                  id="reg-fee"
                  checked={payInscription}
                  onCheckedChange={(checked) => setPayInscription(!!checked)}
                />
                <label htmlFor="reg-fee" className="text-xs font-semibold cursor-pointer flex-1 flex justify-between">
                  <span>Droits d'Inscription Annuelle ({student.niveau})</span>
                  <span className="font-mono text-primary font-bold">{tarif.inscription.toLocaleString()} FCFA</span>
                </label>
              </div>

              {/* Dynamic Session Periods Grid */}
              {assignedSession ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {availablePeriods.map((p) => {
                    const isPaid = alreadyPaidPeriods.has(p.nom) || alreadyPaidPeriods.has(p.id);
                    const isChecked = selectedPeriods.includes(p.id);
                    const cost = getPeriodCost(p);

                    return (
                      <div
                        key={p.id}
                        onClick={() => !isPaid && togglePeriod(p.id)}
                        className={`p-3 rounded-xl border text-xs transition-all flex flex-col justify-between ${
                          isPaid
                            ? "bg-muted/60 border-border opacity-70 cursor-not-allowed"
                            : isChecked
                            ? "bg-primary/10 border-primary font-semibold text-primary shadow-xs cursor-pointer"
                            : "border-border hover:bg-accent/30 text-muted-foreground cursor-pointer"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <span className="font-bold text-foreground text-xs block">{p.nom}</span>
                            <span className="text-[10px] text-muted-foreground">
                              Mois : {p.mois} {p.dateEcheance ? `• Échéance : ${p.dateEcheance}` : ""}
                            </span>
                          </div>
                          {isPaid ? (
                            <Badge variant="outline" className="text-[9px] bg-emerald-500/10 text-emerald-700 border-emerald-300 font-semibold shrink-0">
                              Déjà Réglé
                            </Badge>
                          ) : (
                            <Checkbox checked={isChecked} readOnly className="pointer-events-none mt-0.5" />
                          )}
                        </div>

                        <div className="mt-2 pt-2 border-t border-border/50 flex items-center justify-between">
                          <span className="text-[10px] text-muted-foreground">Montant dû :</span>
                          <span className="font-mono text-xs text-foreground font-bold">
                            {cost.toLocaleString()} FCFA
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="p-6 text-center border rounded-xl border-dashed bg-muted/20 text-muted-foreground text-xs">
                  Veuillez assigner une session académique pour afficher le calendrier des tranches.
                </div>
              )}
            </div>

            {/* Payment History Notice if Student changed session */}
            {student.historiquePaiements && student.historiquePaiements.length > 0 && (
              <div className="p-2.5 rounded-xl bg-muted/40 border text-xs flex items-center justify-between text-muted-foreground">
                <span className="flex items-center gap-1.5 font-medium">
                  <History className="h-3.5 w-3.5 text-primary" />
                  Historique financier conservé : {student.historiquePaiements.length} règlement(s) antérieur(s)
                </span>
                <span className="text-[10px] font-mono">
                  Dernier reçu : {student.historiquePaiements[0].numRecu}
                </span>
              </div>
            )}

            {/* ── 4. Payment Method & Ref ── */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="mode-pay" className="text-xs font-bold">
                  Mode de Paiement Physique *
                </Label>
                <Select value={modePaiement} onValueChange={setModePaiement}>
                  <SelectTrigger id="mode-pay">
                    <SelectValue placeholder="Mode" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Espèces">Espèces (Comptant)</SelectItem>
                    <SelectItem value="Chèque Bancaire">Chèque Bancaire</SelectItem>
                    <SelectItem value="Carte Bancaire TPE">Carte Bancaire (TPE)</SelectItem>
                    <SelectItem value="Virement Bancaire">Virement Bancaire</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="ref" className="text-xs font-bold">
                  N° Référence / Chèque / Quittance
                </Label>
                <Input
                  id="ref"
                  placeholder="Ex: CHQ-849201"
                  value={reference}
                  onChange={(e) => setReference(e.target.value)}
                />
              </div>
            </div>

            {/* ── 5. Total Calculation Box & Submission ── */}
            <div className="rounded-xl border bg-muted/60 p-4 space-y-3">
              <div className="flex justify-between items-center text-xs">
                <span className="text-muted-foreground">Droits d'inscription :</span>
                <span className="font-mono">{montantInscription.toLocaleString()} FCFA</span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-muted-foreground">
                  Tranches sélectionnées ({selectedPeriods.length}) :
                </span>
                <span className="font-mono">{montantPeriodesTotal.toLocaleString()} FCFA</span>
              </div>
              <div className="border-t pt-2 flex justify-between items-center">
                <span className="font-bold text-sm text-foreground">TOTAL À ENCAISSER :</span>
                <span className="font-mono font-black text-lg text-primary">
                  {totalACalculer.toLocaleString()} FCFA
                </span>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Annuler
              </Button>
              <Button
                type="submit"
                disabled={totalACalculer <= 0 || !assignedSession}
                className="bg-emerald-600 hover:bg-emerald-700 text-white gap-2 font-bold shadow-sm"
              >
                <DollarSign className="h-4 w-4" />
                Valider & Émettre le Reçu ({totalACalculer.toLocaleString()} FCFA)
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Printable / Downloadable Receipt Modal */}
      <ReceiptModal
        open={receiptOpen}
        onOpenChange={setReceiptOpen}
        receiptData={lastReceiptData}
      />
    </>
  );
};

export default PaiementPhysiqueModal;
