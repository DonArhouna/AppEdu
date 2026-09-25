import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { KpiCard } from "@/components/ui/kpi-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { CreditCard, DollarSign, AlertCircle, Send, Zap, Plus, Building2, Printer, CalendarDays, RefreshCw } from "lucide-react";
import { PaymentGatewayModal } from "@/components/finance/PaymentGatewayModal";
import { PaiementPhysiqueModal } from "@/components/finance/PaiementPhysiqueModal";
import { ReceiptModal, type ReceiptData } from "@/components/finance/ReceiptModal";
import type { Invoice, Payment as PaymentApi, Student } from "@/services/apiTypes";
import { financesApi, etudiantsApi, extractErrorMessage, setupApi } from "@/services/apiClient";
import { toast } from "sonner";

interface ReceiptPayload {
  numero_recu?: string;
  date_emission?: string;
  etablissement?: { nom?: string; code?: string; devise?: string };
  etudiant?: { matricule?: string; nom?: string; prenom?: string; filiere?: string; niveau?: string };
  details_paiement?: { mode_paiement?: string; reference?: string; periode?: string; montant?: number; encaisse_par?: string };
  facture?: { solde_restant?: number };
}

interface Paiement {
  id: string;
  etudiant: string;
  matricule: string;
  montant: number;
  datePaiement: string;
  modePaiement: string;
  reference: string;
  statut: string;
}

interface ImpayeRow {
  id: string;
  factureRef: string;
  etudiant: string;
  matricule: string;
  montantDu: number;
  dateEcheance: string;
  joursRetard: number;
}

const Paiements = () => {
  const navigate = useNavigate();
  const [physiqueModalOpen, setPhysiqueModalOpen] = useState(false);
  const [receiptModalOpen, setReceiptModalOpen] = useState(false);
  const [selectedReceipt, setSelectedReceipt] = useState<ReceiptData | null>(null);

  const [selectedPayTarget, setSelectedPayTarget] = useState<{
    montant: string;
    factureRef: string;
    etudiantNom: string;
  } | null>(null);

  const [paiements, setPaiements] = useState<Paiement[]>([]);
  const [impayes, setImpayes] = useState<ImpayeRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currency, setCurrency] = useState("");

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [pList, fList, studentsResult, statusResult] = await Promise.all([
        financesApi.getPaiements(),
        financesApi.getFactures(),
        etudiantsApi.getSummary(),
        setupApi.getStatus(),
      ]);

      if (pList.error || fList.error || studentsResult.error) {
        throw new Error(pList.error || fList.error || studentsResult.error || "Impossible de charger les paiements.");
      }
      const students = studentsResult.data || [];
      setCurrency(statusResult.data?.devise || "");

      const formattedPaiements = (pList.data || []).map((p: PaymentApi) => {
        const student = students.find((item) => item.id === p.etudiant_id);
        return {
          id: p.id,
          etudiant: student ? `${student.prenom || ""} ${student.nom || ""}`.trim() : p.etudiant_id,
          matricule: student?.matricule || "",
          montant: Number(p.montant || 0),
          datePaiement: p.date_paiement || "",
          modePaiement: p.mode_paiement || "",
          reference: p.reference || p.id,
          statut: p.statut || "",
          raw: p,
        };
      });
      setPaiements(formattedPaiements);

      const now = new Date();
      const unpaidInvoices = (fList.data || [])
        .filter((f: Invoice) => f.statut !== "payee" && (f.reste_a_payer > 0 || f.montant_total > f.montant_paye))
        .map((f: Invoice) => {
          const student = students.find((item) => item.id === f.etudiant_id);
          const reste = Number(f.reste_a_payer ?? (f.montant_total - f.montant_paye));
          const ech = f.date_echeance ? new Date(f.date_echeance) : null;
          const diffDays = ech ? Math.max(0, Math.floor((now.getTime() - ech.getTime()) / (1000 * 60 * 60 * 24))) : 0;
          return {
            id: f.id,
            factureRef: f.numero_facture || f.id,
            etudiant: student ? `${student.prenom || ""} ${student.nom || ""}`.trim() : f.etudiant_id,
            matricule: student?.matricule || "",
            montantDu: reste,
            dateEcheance: f.date_echeance || "",
            joursRetard: diffDays,
          };
        });
      setImpayes(unpaidInvoices);
    } catch (err: unknown) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const openReceipt = async (paymentId: string) => {
    const result = await financesApi.getRecuByPaiement(paymentId);
    if (result.error || !result.data) {
      toast.error(extractErrorMessage(result.error, "Reçu indisponible."));
      return;
    }
    const data = (result.data.donnees_json || {}) as ReceiptPayload;
    const etudiant = data.etudiant || {};
    setSelectedReceipt({
      numRecu: data.numero_recu || result.data.numero_recu,
      datePaiement: data.date_emission || result.data.date_emission,
      etudiant: {
        matricule: etudiant.matricule || "",
        nom: etudiant.nom || "",
        prenom: etudiant.prenom || "",
        filiere: etudiant.filiere || "",
        niveau: etudiant.niveau || "",
      },
      etablissement: data.etablissement,
      devise: data.etablissement?.devise,
      modePaiement: data.details_paiement?.mode_paiement || "",
      referencePaiement: data.details_paiement?.reference,
      periodesPayees: data.details_paiement?.periode ? [data.details_paiement.periode] : [],
      montantDetail: { total: data.details_paiement?.montant || 0, paye: data.details_paiement?.montant || 0, reste: data.facture?.solde_restant || 0 },
      caissier: data.details_paiement?.encaisse_par,
    });
    setReceiptModalOpen(true);
  };

  const handlePhysiqueSuccess = (_receiptRecord: unknown) => {
    void fetchData();
  };

  const handleOnlinePaymentSuccess = () => {
    fetchData();
    setSelectedPayTarget(null);
  };

  const totalEncaisse = paiements.reduce((acc, p) => acc + (p.montant || 0), 0);
  const totalImpayes = impayes.reduce((acc, i) => acc + (i.montantDu || 0), 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Caisse & Suivi des Paiements</h1>
          <p className="text-muted-foreground mt-1">
            Enregistrement des règlements au guichet (espèces/chèques) et transactions en ligne
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <Button
            variant="outline"
            onClick={() => navigate("/sessions")}
            className="rounded-xl border-border/80 text-foreground font-semibold text-xs h-9 shadow-2xs gap-1.5"
          >
            <CalendarDays className="h-4 w-4 text-primary" />
            Sessions & Périodes
          </Button>

          <Button
            onClick={() => setPhysiqueModalOpen(true)}
            className="rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs h-9 shadow-sm gap-1.5"
          >
            <Plus className="h-4 w-4" />
            Nouveau Paiement Guichet (Caisse)
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Erreur de communication avec le serveur</AlertTitle>
          <AlertDescription className="mt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <p>{error}</p>
            <Button variant="outline" size="sm" onClick={fetchData}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Réessayer
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Uniform KPI Cards Standard */}
      <div className="grid gap-4 md:grid-cols-3">
        <KpiCard title="Total encaissé" value={`${totalEncaisse.toLocaleString()} ${currency || "devise de l'établissement"}`} icon={DollarSign} subtitle={`${paiements.length} règlement(s) validé(s)`} colorVariant="emerald" />
        <KpiCard title="Impayés en attente" value={`${totalImpayes.toLocaleString()} ${currency || "devise de l'établissement"}`} icon={AlertCircle} subtitle={`${impayes.length} dossier(s) en retard`} colorVariant="rose" />
        <KpiCard title="Taux de recouvrement" value={`${((totalEncaisse / (totalEncaisse + totalImpayes)) * 100).toFixed(1)}%`} icon={CreditCard} subtitle="Sur l'ensemble des frais dus" colorVariant="primary" />
      </div>

      <Tabs defaultValue="paiements" className="space-y-4">
        <TabsList className="bg-muted p-1 rounded-xl">
          <TabsTrigger value="paiements" className="rounded-lg">Historique des Règlements</TabsTrigger>
          <TabsTrigger value="impayes" className="rounded-lg">Impayés & Relances</TabsTrigger>
          <TabsTrigger value="gateways" className="rounded-lg">Passerelles Mobile Money / Carte</TabsTrigger>
        </TabsList>

        <TabsContent value="paiements" className="space-y-4">
          <Card className="card-base">
            <CardHeader className="p-5">
              <CardTitle className="text-lg">Historique des Encaissements</CardTitle>
              <CardDescription>
                Paiements enregistrés par les caissiers au guichet et passerelles automatiques
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <div className="border-t overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/40">
                      <TableHead>Matricule</TableHead>
                      <TableHead>Étudiant</TableHead>
                      <TableHead>Montant Encaissé</TableHead>
                      <TableHead>Date</TableHead>
                      <TableHead>Mode de Règlement</TableHead>
                      <TableHead>N° Reçu / Réf</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {loading ? (
                      [1, 2, 3].map((i) => (
                        <TableRow key={i}>
                          <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                          <TableCell><Skeleton className="h-4 w-32" /></TableCell>
                          <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                          <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                          <TableCell><Skeleton className="h-4 w-28" /></TableCell>
                          <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                          <TableCell className="text-right"><Skeleton className="h-8 w-16 ml-auto" /></TableCell>
                        </TableRow>
                      ))
                    ) : paiements.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                          Aucun encaissement enregistré dans la base de données.
                        </TableCell>
                      </TableRow>
                    ) : (
                      paiements.map((paiement) => (
                        <TableRow key={paiement.id} className="hover:bg-muted/30">
                          <TableCell className="font-mono font-bold text-xs text-primary">
                            {paiement.matricule}
                          </TableCell>
                          <TableCell className="font-semibold text-sm">{paiement.etudiant}</TableCell>
                          <TableCell className="font-mono font-bold text-emerald-600">
                            {paiement.montant.toLocaleString()} {currency || "devise de l'établissement"}
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground">
                            {new Date(paiement.datePaiement).toLocaleDateString("fr-FR")}
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className="font-semibold text-xs bg-card">
                              {paiement.modePaiement}
                            </Badge>
                          </TableCell>
                          <TableCell className="font-mono text-xs text-foreground font-semibold">
                            {paiement.reference}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => void openReceipt(paiement.id)}
                              className="text-xs gap-1"
                            >
                              <Printer className="h-3.5 w-3.5" /> Reçu
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="impayes" className="space-y-4">
          <Card className="card-base">
            <CardHeader className="p-5">
              <CardTitle className="text-lg">Impayés et Relances Automatisées</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="border-t overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/40">
                      <TableHead>Matricule</TableHead>
                      <TableHead>Étudiant</TableHead>
                      <TableHead>Montant Dû</TableHead>
                      <TableHead>Date Échéance</TableHead>
                      <TableHead>Retard</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {loading ? (
                      [1, 2].map((i) => (
                        <TableRow key={i}>
                          <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                          <TableCell><Skeleton className="h-4 w-32" /></TableCell>
                          <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                          <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                          <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                          <TableCell className="text-right"><Skeleton className="h-8 w-28 ml-auto" /></TableCell>
                        </TableRow>
                      ))
                    ) : impayes.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center py-8 text-emerald-600 font-medium">
                          Aucun impayé en attente ! Toutes les échéances sont réglées.
                        </TableCell>
                      </TableRow>
                    ) : (
                      impayes.map((impaye) => (
                        <TableRow key={impaye.id}>
                          <TableCell className="font-mono font-bold text-xs">{impaye.matricule}</TableCell>
                          <TableCell className="font-semibold text-sm">{impaye.etudiant}</TableCell>
                          <TableCell className="font-mono font-bold text-destructive">
                            {impaye.montantDu.toLocaleString()} {currency || "devise de l'établissement"}
                          </TableCell>
                          <TableCell className="text-xs">{impaye.dateEcheance}</TableCell>
                          <TableCell>
                            <Badge variant="destructive">{impaye.joursRetard} jours</Badge>
                          </TableCell>
                          <TableCell className="text-right space-x-2">
                            <Button
                              size="sm"
                              onClick={() =>
                                setSelectedPayTarget({
                                  montant: `${impaye.montantDu.toLocaleString()} ${currency || "devise de l'établissement"}`,
                                  factureRef: impaye.factureRef || "Non renseignée",
                                  etudiantNom: impaye.etudiant,
                                })
                              }
                              className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs"
                            >
                              <Zap className="mr-1 h-3.5 w-3.5" /> Régler en Ligne
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Cashier In-Person Physical Payment Modal */}
      <PaiementPhysiqueModal
        open={physiqueModalOpen}
        onOpenChange={setPhysiqueModalOpen}
        onPaymentSuccess={handlePhysiqueSuccess}
      />

      {/* Online Gateway Modal */}
      {selectedPayTarget && (
        <PaymentGatewayModal
          open={!!selectedPayTarget}
          onOpenChange={(open) => {
            if (!open) setSelectedPayTarget(null);
          }}
          montant={selectedPayTarget.montant}
          factureRef={selectedPayTarget.factureRef}
          etudiantNom={selectedPayTarget.etudiantNom}
          onSuccess={handleOnlinePaymentSuccess}
        />
      )}

      {/* Printable Receipt Modal */}
      <ReceiptModal
        open={receiptModalOpen}
        onOpenChange={setReceiptModalOpen}
        receiptData={selectedReceipt}
      />
    </div>
  );
};

export default Paiements;
