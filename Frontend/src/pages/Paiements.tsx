import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
import { ReceiptModal } from "@/components/finance/ReceiptModal";
import { financesApi, extractErrorMessage } from "@/services/apiClient";
import { toast } from "sonner";

interface Paiement {
  id: string;
  etudiant: string;
  matricule: string;
  montant: number;
  datePaiement: string;
  modePaiement: string;
  reference: string;
  statut: "valide" | "en_attente" | "echoue";
}

const Paiements = () => {
  const navigate = useNavigate();
  const [physiqueModalOpen, setPhysiqueModalOpen] = useState(false);
  const [receiptModalOpen, setReceiptModalOpen] = useState(false);
  const [selectedReceipt, setSelectedReceipt] = useState<any>(null);

  const [selectedPayTarget, setSelectedPayTarget] = useState<{
    montant: string;
    factureRef: string;
    etudiantNom: string;
  } | null>(null);

  const [paiements, setPaiements] = useState<any[]>([]);
  const [impayes, setImpayes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [pList, fList] = await Promise.all([
        financesApi.getPaiements(),
        financesApi.getFactures(),
      ]);

      const formattedPaiements = (pList || []).map((p: any) => ({
        id: p.id,
        etudiant: p.etudiant ? `${p.etudiant.prenom || ""} ${p.etudiant.nom || ""}`.trim() : (p.etudiant_id || "Étudiant"),
        matricule: p.etudiant?.matricule || "N/A",
        montant: Number(p.montant || 0),
        datePaiement: p.date_paiement || new Date().toISOString(),
        modePaiement: p.mode_paiement || "Espèces",
        reference: p.reference || p.id,
        statut: p.statut || "valide",
        raw: p,
      }));
      setPaiements(formattedPaiements);

      const now = new Date();
      const unpaidInvoices = (fList || [])
        .filter((f: any) => f.statut !== "payee" && (f.reste_a_payer > 0 || f.montant_total > f.montant_paye))
        .map((f: any) => {
          const reste = Number(f.reste_a_payer ?? (f.montant_total - f.montant_paye));
          const ech = f.date_echeance ? new Date(f.date_echeance) : new Date();
          const diffDays = Math.max(0, Math.floor((now.getTime() - ech.getTime()) / (1000 * 60 * 60 * 24)));
          return {
            id: f.id,
            factureRef: f.numero_facture || f.id,
            etudiant: f.etudiant ? `${f.etudiant.prenom || ""} ${f.etudiant.nom || ""}`.trim() : (f.etudiant_id || "Étudiant"),
            matricule: f.etudiant?.matricule || "N/A",
            montantDu: reste,
            dateEcheance: f.date_echeance || "-",
            joursRetard: diffDays,
          };
        });
      setImpayes(unpaidInvoices);
    } catch (err: any) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handlePhysiqueSuccess = (receiptRecord: any) => {
    fetchData();
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
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <Card className="card-base relative overflow-hidden">
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-emerald-500" />
          <CardHeader className="flex flex-row items-center justify-between pb-2 pl-5">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Total Encaissé
            </CardTitle>
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-500">
              <DollarSign className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="pl-5">
            <div className="text-2xl font-bold text-emerald-600 font-mono">
              {totalEncaisse.toLocaleString()} FCFA
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {paiements.length} règlements validés en caisse
            </p>
          </CardContent>
        </Card>

        <Card className="card-base relative overflow-hidden">
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-destructive" />
          <CardHeader className="flex flex-row items-center justify-between pb-2 pl-5">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Impayés en Attente
            </CardTitle>
            <div className="p-2 rounded-xl bg-destructive/10 text-destructive">
              <AlertCircle className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="pl-5">
            <div className="text-2xl font-bold text-destructive font-mono">
              {totalImpayes.toLocaleString()} FCFA
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {impayes.length} dossiers d'étudiants en retard
            </p>
          </CardContent>
        </Card>

        <Card className="card-base relative overflow-hidden">
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-primary" />
          <CardHeader className="flex flex-row items-center justify-between pb-2 pl-5">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Taux de Recouvrement
            </CardTitle>
            <div className="p-2 rounded-xl bg-primary/10 text-primary">
              <CreditCard className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="pl-5">
            <div className="text-2xl font-bold text-foreground">
              {((totalEncaisse / (totalEncaisse + totalImpayes)) * 100).toFixed(1)}%
            </div>
            <p className="text-xs text-muted-foreground mt-1">Sur l'ensemble des frais dus</p>
          </CardContent>
        </Card>
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
                            {paiement.montant.toLocaleString()} FCFA
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
                              onClick={() => {
                                setSelectedReceipt({
                                  numRecu: paiement.reference,
                                  datePaiement: paiement.datePaiement,
                                  etudiant: {
                                    matricule: paiement.matricule,
                                    nom: paiement.etudiant.split(" ")[1] || "",
                                    prenom: paiement.etudiant.split(" ")[0] || "",
                                    filiere: "Génie Informatique",
                                    niveau: "Licence 3",
                                  },
                                  modePaiement: paiement.modePaiement,
                                  periodesPayees: ["Scolarité Régulière"],
                                  montantDetail: {
                                    total: paiement.montant,
                                    paye: paiement.montant,
                                    reste: 0,
                                  },
                                  caissier: "Caisse Centrale",
                                });
                                setReceiptModalOpen(true);
                              }}
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
                            {impaye.montantDu.toLocaleString()} FCFA
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
                                  montant: `${impaye.montantDu.toLocaleString()} FCFA`,
                                  factureRef: impaye.factureRef || `FAC-${impaye.id}`,
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
