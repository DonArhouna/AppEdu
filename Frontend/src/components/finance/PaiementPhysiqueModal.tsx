import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  AlertTriangle,
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  CreditCard,
  DollarSign,
  History,
  Loader2,
  Lock,
  UserCheck,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAuth } from "@/contexts/AuthContext";
import { extractErrorMessage, financesApi, setupApi, etudiantsApi, sessionsApi } from "@/services/apiClient";
import type { AcademicSession, FeeGrid, Payment, SessionPeriod } from "@/services/apiTypes";
import { ReceiptModal, type ReceiptData } from "./ReceiptModal";

interface StudentRecord {
  id: string;
  matricule: string;
  nom: string;
  prenom: string;
  email?: string | null;
  telephone?: string | null;
  filiere: string;
  niveau: string;
  session_id?: string | null;
}

interface PeriodRecord {
  id: string;
  nom: string;
  mois: string;
  date_echeance?: string | null;
  montant_estime?: number | null;
  pourcentage?: number | null;
  ordre: number;
}

interface SessionRecord {
  id: string;
  nom: string;
  code: string;
  annee_academique: string;
  date_debut: string;
  date_fin: string;
  periodes: PeriodRecord[];
}

interface InstitutionInfo {
  nom: string;
  code: string;
  devise: string;
}

export interface PaiementPhysiqueModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onPaymentSuccess?: (paymentRecord: unknown) => void;
  initialMatricule?: string;
}

const mapSession = (session: AcademicSession): SessionRecord => ({
  id: session.id,
  nom: session.nom,
  code: session.code,
  annee_academique: session.annee_academique,
  date_debut: session.date_debut,
  date_fin: session.date_fin,
  periodes: (session.periodes || []).map((period: SessionPeriod) => ({
    id: period.id,
    nom: period.nom,
    mois: period.mois,
    date_echeance: period.date_echeance,
    montant_estime: period.montant_estime,
    pourcentage: period.pourcentage,
    ordre: period.ordre,
  })),
});

export const PaiementPhysiqueModal = ({
  open,
  onOpenChange,
  onPaymentSuccess,
  initialMatricule,
}: PaiementPhysiqueModalProps) => {
  const { user } = useAuth();
  const [students, setStudents] = useState<StudentRecord[]>([]);
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [feeGrids, setFeeGrids] = useState<FeeGrid[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [institution, setInstitution] = useState<InstitutionInfo>({ nom: "", code: "", devise: "" });
  const [selectedMatricule, setSelectedMatricule] = useState("");
  const [selectedPeriods, setSelectedPeriods] = useState<string[]>([]);
  const [payInscription, setPayInscription] = useState(false);
  const [modePaiement, setModePaiement] = useState("Espèces");
  const [reference, setReference] = useState("");
  const [quickAssignSessionId, setQuickAssignSessionId] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [receiptOpen, setReceiptOpen] = useState(false);
  const [lastReceiptData, setLastReceiptData] = useState<ReceiptData | null>(null);

  const loadRegistry = async () => {
    setLoading(true);
    const [studentsResult, sessionsResult, feesResult, statusResult] = await Promise.all([
      etudiantsApi.getAll(),
      sessionsApi.getAll(),
      financesApi.getGrillesTarifaires({ actif: true }),
      setupApi.getStatus(),
    ]);

    if (studentsResult.error || sessionsResult.error || feesResult.error) {
      toast.error(
        extractErrorMessage(
          studentsResult.error || sessionsResult.error || feesResult.error,
          "Impossible de charger les données de paiement."
        )
      );
      setStudents([]);
      setSessions([]);
      setFeeGrids([]);
    } else {
      setStudents((studentsResult.data || []) as StudentRecord[]);
      setSessions((sessionsResult.data || []).map(mapSession));
      setFeeGrids(feesResult.data || []);
    }

    if (statusResult.data) {
      setInstitution({
        nom: statusResult.data.etablissement_nom || "",
        code: statusResult.data.etablissement_code || "",
        devise: statusResult.data.devise || "",
      });
    }
    setLoading(false);
  };

  useEffect(() => {
    if (open) void loadRegistry();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    setSelectedMatricule((current) => {
      if (initialMatricule && students.some((student) => student.matricule === initialMatricule)) {
        return initialMatricule;
      }
      if (current && students.some((student) => student.matricule === current)) return current;
      return students[0]?.matricule || "";
    });
  }, [open, initialMatricule, students]);

  const student = useMemo(
    () => students.find((item) => item.matricule === selectedMatricule) || null,
    [students, selectedMatricule]
  );

  const assignedSession = useMemo(
    () => sessions.find((session) => session.id === student?.session_id) || null,
    [sessions, student?.session_id]
  );

  const tarif = useMemo(() => {
    if (!student) return null;
    return (
      feeGrids.find(
        (grid) => grid.filiere === student.filiere && grid.niveau === student.niveau
      ) || null
    );
  }, [feeGrids, student]);

  const currencyLabel = institution.devise || "devise de l'établissement";

  const paidPeriodAmounts = useMemo(() => {
    const totals = new Map<string, number>();
    payments.forEach((payment) => {
      if (!payment.periode_id) return;
      totals.set(
        payment.periode_id,
        (totals.get(payment.periode_id) || 0) + Number(payment.montant || 0)
      );
    });
    return totals;
  }, [payments]);
  const registrationPaid = useMemo(
    () => payments.some((payment) => !payment.periode_id),
    [payments]
  );

  useEffect(() => {
    setSelectedPeriods([]);
    setPayInscription(false);
    if (!student) {
      setPayments([]);
      return;
    }
    const loadPayments = async () => {
      const result = await financesApi.getPaiements({ etudiant_id: student.id });
      if (result.error) {
        toast.error(extractErrorMessage(result.error, "Historique de paiement indisponible."));
        return;
      }
      setPayments(result.data || []);
    };
    void loadPayments();
  }, [student]);

  const getPeriodCost = (period: PeriodRecord) => {
    if (period.montant_estime && period.montant_estime > 0) return period.montant_estime;
    if (period.pourcentage && period.pourcentage > 0 && tarif) {
      return Math.round(
        (tarif.scolarite_mensuelle * tarif.nombre_mois * period.pourcentage) / 100
      );
    }
    return tarif?.scolarite_mensuelle || 0;
  };

  const getRemainingPeriodCost = (period: PeriodRecord) => {
    const expected = getPeriodCost(period);
    const paid = paidPeriodAmounts.get(period.id) || 0;
    return Math.max(0, expected - paid);
  };

  const isPeriodSettled = (period: PeriodRecord) => {
    const expected = getPeriodCost(period);
    return expected > 0 && (paidPeriodAmounts.get(period.id) || 0) >= expected;
  };

  const selectedPeriodObjects = assignedSession
    ? assignedSession.periodes.filter((period) => selectedPeriods.includes(period.id))
    : [];
  const totalACalculer =
    (payInscription && tarif ? tarif.droits_inscription : 0) +
    selectedPeriodObjects.reduce((sum, period) => sum + getRemainingPeriodCost(period), 0);

  const togglePeriod = (period: PeriodRecord) => {
    if (isPeriodSettled(period)) return;
    setSelectedPeriods((current) =>
      current.includes(period.id)
        ? current.filter((id) => id !== period.id)
        : [...current, period.id]
    );
  };

  const handleSelectAllPeriods = () => {
    if (!assignedSession) return;
    const payable = assignedSession.periodes.filter((period) => !isPeriodSettled(period));
    setSelectedPeriods((current) =>
      current.length === payable.length ? [] : payable.map((period) => period.id)
    );
  };

  const handleAssignSessionNow = async () => {
    if (!student || !quickAssignSessionId) {
      toast.error("Sélectionnez une session académique.");
      return;
    }
    setAssigning(true);
    const result = await etudiantsApi.update(student.id, { session_id: quickAssignSessionId });
    setAssigning(false);
    if (result.error) {
      toast.error(extractErrorMessage(result.error));
      return;
    }
    setStudents((current) =>
      current.map((item) =>
        item.id === student.id ? { ...item, session_id: quickAssignSessionId } : item
      )
    );
    setQuickAssignSessionId("");
    toast.success("Session académique enregistrée.");
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!student || !assignedSession) {
      toast.error("Sélectionnez un étudiant rattaché à une session académique.");
      return;
    }

    const items: Array<{ montant: number; periode_id: string | null; label: string }> = [];
    if (payInscription && tarif) {
      items.push({
        montant: tarif.droits_inscription,
        periode_id: null,
        label: "Droits d'inscription",
      });
    }
    selectedPeriodObjects.forEach((period) => {
      const montant = getRemainingPeriodCost(period);
      if (montant > 0) {
        items.push({ montant, periode_id: period.id, label: period.nom });
      }
    });

    if (items.length === 0 || items.every((item) => item.montant <= 0)) {
      toast.error("Sélectionnez un montant à encaisser.");
      return;
    }

    setSubmitting(true);
    const createdPayments: Payment[] = [];
    for (const item of items) {
      const result = await financesApi.enregistrerPaiement({
        etudiant_id: student.id,
        session_id: assignedSession.id,
        periode_id: item.periode_id,
        montant: item.montant,
        mode_paiement: modePaiement,
        reference: reference.trim() || undefined,
      });
      if (result.error || !result.data) {
        setSubmitting(false);
        toast.error(extractErrorMessage(result.error, "Le paiement n'a pas pu être enregistré."));
        return;
      }
      createdPayments.push(result.data);
    }

    const receiptNumbers: string[] = [];
    for (const payment of createdPayments) {
      const receipt = await financesApi.getRecuByPaiement(payment.id);
      if (receipt.data?.numero_recu) receiptNumbers.push(receipt.data.numero_recu);
    }

    setSubmitting(false);
    setSelectedPeriods([]);
    setPayInscription(false);
    setReference("");
    setLastReceiptData({
      numRecu: receiptNumbers.join(" / ") || createdPayments.map((payment) => payment.reference).join(" / "),
      datePaiement: new Date().toLocaleDateString("fr-FR"),
      sessionId: assignedSession.id,
      sessionNom: assignedSession.nom,
      etudiant: {
        matricule: student.matricule,
        nom: student.nom,
        prenom: student.prenom,
        filiere: student.filiere,
        niveau: student.niveau,
      },
      etablissement: institution,
      devise: institution.devise,
      modePaiement,
      referencePaiement: reference.trim() || createdPayments[0]?.reference,
      periodesPayees: items.map((item) => item.label),
      montantDetail: {
        total: totalACalculer,
        paye: totalACalculer,
        reste: 0,
      },
      caissier: user ? `${user.prenom} ${user.nom}` : "Compte authentifié",
    });
    onPaymentSuccess?.(createdPayments);
    onOpenChange(false);
    setReceiptOpen(true);
  };

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-h-[92vh] max-w-[760px] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-xl">
              <DollarSign className="h-6 w-6 text-emerald-600" />
              Nouveau paiement au guichet
            </DialogTitle>
            <DialogDescription>
              Les règlements sont enregistrés par l'API et génèrent un reçu côté serveur.
            </DialogDescription>
          </DialogHeader>

          {loading ? (
            <div className="flex items-center justify-center gap-2 py-12 text-sm text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" /> Chargement des données...
            </div>
          ) : students.length === 0 ? (
            <div className="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground">
              Aucun étudiant n'est disponible dans le backend.
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5 py-2">
              <div className="space-y-2">
                <Label htmlFor="payment-student" className="text-xs font-semibold">Étudiant *</Label>
                <Select value={selectedMatricule} onValueChange={setSelectedMatricule}>
                  <SelectTrigger id="payment-student">
                    <SelectValue placeholder="Sélectionner un étudiant" />
                  </SelectTrigger>
                  <SelectContent>
                    {students.map((item) => (
                      <SelectItem key={item.id} value={item.matricule}>
                        {item.prenom} {item.nom} ({item.matricule}) — {item.filiere} / {item.niveau}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {assignedSession ? (
                <div className="flex flex-col gap-3 rounded-xl border border-primary/20 bg-primary/5 p-3.5 text-xs sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-3">
                    <CalendarDays className="h-5 w-5 text-primary" />
                    <div>
                      <p className="font-semibold">{assignedSession.nom}</p>
                      <p className="text-muted-foreground">
                        {assignedSession.date_debut} au {assignedSession.date_fin} · {assignedSession.periodes.length} période(s)
                      </p>
                    </div>
                  </div>
                  <Badge variant="outline" className="bg-background text-emerald-600">
                    <CheckCircle2 className="mr-1 h-3 w-3" /> Rattachée
                  </Badge>
                </div>
              ) : (
                <div className="space-y-3 rounded-xl border border-destructive/30 bg-destructive/5 p-4">
                  <div className="flex gap-3">
                    <AlertTriangle className="h-5 w-5 shrink-0 text-destructive" />
                    <div>
                      <p className="font-semibold text-destructive">Session non renseignée</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Rattachez l'étudiant à une session avant d'enregistrer un règlement.
                      </p>
                    </div>
                  </div>
                  <div className="flex flex-col gap-2 border-t border-destructive/20 pt-3 sm:flex-row">
                    <Select value={quickAssignSessionId} onValueChange={setQuickAssignSessionId}>
                      <SelectTrigger className="h-9 bg-background">
                        <SelectValue placeholder="Choisir une session" />
                      </SelectTrigger>
                      <SelectContent>
                        {sessions.map((session) => (
                          <SelectItem key={session.id} value={session.id}>
                            {session.nom} ({session.periodes.length} période(s))
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button type="button" variant="outline" onClick={handleAssignSessionNow} disabled={assigning}>
                      {assigning && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      Rattacher <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}

              {tarif ? (
                <div className="flex flex-col gap-2 rounded-xl border bg-muted/30 p-3 text-xs sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-2">
                    <Lock className="h-4 w-4 text-primary" />
                    <div>
                      <p className="font-semibold">Grille officielle : {tarif.filiere} / {tarif.niveau}</p>
                      <p className="text-muted-foreground">
                        Inscription {tarif.droits_inscription.toLocaleString("fr-FR")} {currencyLabel} · Mensualité {tarif.scolarite_mensuelle.toLocaleString("fr-FR")} {currencyLabel}
                      </p>
                    </div>
                  </div>
                  <Badge variant="outline" className="bg-background">API</Badge>
                </div>
              ) : (
                <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-3 text-xs text-amber-700 dark:text-amber-300">
                  Aucune grille tarifaire active ne correspond à cet étudiant. Configurez-la dans Frais de scolarité avant de calculer un règlement.
                </div>
              )}

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold">Éléments à encaisser</p>
                    <p className="text-xs text-muted-foreground">Les périodes entièrement réglées sont désactivées ; les acomptes affichent le solde restant.</p>
                  </div>
                  {assignedSession && assignedSession.periodes.length > 0 && (
                    <Button type="button" variant="ghost" size="sm" onClick={handleSelectAllPeriods}>
                      {selectedPeriods.length > 0 ? "Tout décocher" : "Tout sélectionner"}
                    </Button>
                  )}
                </div>

                {tarif && (
                  <div className="flex items-center gap-3 rounded-xl border bg-card p-3 text-xs">
                    <Checkbox
                      id="registration-fee"
                      checked={payInscription}
                      disabled={registrationPaid}
                      onCheckedChange={(checked) => setPayInscription(Boolean(checked))}
                    />
                    <label htmlFor="registration-fee" className="flex flex-1 cursor-pointer items-center justify-between gap-3">
                      <span>Droits d'inscription</span>
                      <span className="font-mono font-semibold">{tarif.droits_inscription.toLocaleString("fr-FR")} {currencyLabel}</span>
                    </label>
                    {registrationPaid && <Badge variant="outline">Déjà enregistré</Badge>}
                  </div>
                )}

                {assignedSession?.periodes.length ? (
                  <div className="grid gap-2 sm:grid-cols-2">
                    {assignedSession.periodes.map((period) => {
                      const paidAmount = paidPeriodAmounts.get(period.id) || 0;
                       const paid = isPeriodSettled(period);
                      const checked = selectedPeriods.includes(period.id);
                      const cost = getRemainingPeriodCost(period);
                      return (
                        <button
                          type="button"
                          key={period.id}
                          disabled={paid || cost <= 0}
                          onClick={() => togglePeriod(period)}
                          className={`rounded-xl border p-3 text-left text-xs transition-colors ${paid || cost <= 0 ? "cursor-not-allowed bg-muted/50 opacity-60" : checked ? "border-primary bg-primary/5" : "hover:bg-accent/40"}`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <p className="font-semibold">{period.nom}</p>
                              <p className="text-muted-foreground">{period.mois} {period.date_echeance ? `· ${period.date_echeance}` : ""}</p>
                            </div>
                            {paid ? <Badge variant="outline">Réglée</Badge> : paidAmount > 0 ? <Badge variant="outline">Partiellement réglée</Badge> : <Checkbox checked={checked} className="pointer-events-none" />}
                          </div>
                          <p className="mt-2 text-right font-mono font-semibold">{cost.toLocaleString("fr-FR")} {currencyLabel}</p>
                        </button>
                      );
                    })}
                  </div>
                ) : (
                  <div className="rounded-xl border border-dashed p-6 text-center text-xs text-muted-foreground">
                    Aucune période de paiement n'est configurée pour cette session.
                  </div>
                )}
              </div>

              {payments.length > 0 && (
                <div className="flex items-center gap-2 rounded-xl border bg-muted/30 p-2.5 text-xs text-muted-foreground">
                  <History className="h-4 w-4 text-primary" />
                  {payments.length} règlement(s) déjà enregistré(s) pour cet étudiant.
                </div>
              )}

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="payment-mode">Mode de paiement *</Label>
                  <Select value={modePaiement} onValueChange={setModePaiement}>
                    <SelectTrigger id="payment-mode"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Espèces">Espèces</SelectItem>
                      <SelectItem value="Chèque">Chèque</SelectItem>
                      <SelectItem value="Virement">Virement</SelectItem>
                      <SelectItem value="Mobile Money">Mobile Money</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="payment-reference">Référence (optionnelle)</Label>
                  <Input id="payment-reference" value={reference} onChange={(event) => setReference(event.target.value)} placeholder="Saisie du guichet" />
                </div>
              </div>

              <div className="flex items-center justify-between rounded-xl border border-primary/20 bg-primary/5 p-4">
                <div className="flex items-center gap-2">
                  <CreditCard className="h-5 w-5 text-primary" />
                  <span className="text-sm font-semibold">Total à encaisser</span>
                </div>
                <span className="text-xl font-bold text-primary">{totalACalculer.toLocaleString("fr-FR")} {currencyLabel}</span>
              </div>

              <div className="flex justify-end gap-2 border-t pt-4">
                <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Annuler</Button>
                <Button type="submit" disabled={submitting || !assignedSession || totalACalculer <= 0}>
                  {submitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <UserCheck className="mr-2 h-4 w-4" />}
                  Enregistrer le paiement
                </Button>
              </div>
            </form>
          )}
        </DialogContent>
      </Dialog>

      <ReceiptModal
        open={receiptOpen}
        onOpenChange={setReceiptOpen}
        receiptData={lastReceiptData}
      />
    </>
  );
};

export default PaiementPhysiqueModal;
