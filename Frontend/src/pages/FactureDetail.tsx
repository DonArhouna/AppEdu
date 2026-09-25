import { useCallback, useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { KpiCard } from "@/components/ui/kpi-card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  ArrowLeft,
  Download,
  Printer,
  FileText,
  CreditCard,
  Calendar,
  User,
  AlertCircle,
  RefreshCw,
  Clock,
  CheckCircle2,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { financesApi, extractErrorMessage, setupApi } from "@/services/apiClient";
import type { Invoice, Payment } from "@/services/apiTypes";

const FactureDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [facture, setFacture] = useState<Invoice | null>(null);
  const [paiements, setPaiements] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currency, setCurrency] = useState("");

  const fetchFactureData = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const factureResult = await financesApi.getFactureById(id);
      if (factureResult.error || !factureResult.data) {
        throw new Error(factureResult.error || "Facture introuvable.");
      }

      const factureData = factureResult.data;
      const statusResult = await setupApi.getStatus();
      setCurrency(statusResult.data?.devise || "");
      setFacture(factureData);
      if (factureData.etudiant_id) {
        const paiementsResult = await financesApi.getPaiements({ etudiant_id: factureData.etudiant_id });
        if (paiementsResult.error) throw new Error(paiementsResult.error);
        setPaiements((paiementsResult.data || []).filter((payment) => payment.facture_id === id));
      }
    } catch (err: unknown) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void fetchFactureData();
  }, [fetchFactureData]);

  const getStatutBadge = (statut: string) => {
    const s = statut?.toLowerCase();
    switch (s) {
      case "payee":
      case "payée":
        return <Badge className="bg-emerald-600 text-white hover:bg-emerald-700">Payée</Badge>;
      case "partielle":
      case "partiellement payée":
        return <Badge className="bg-amber-500 text-white hover:bg-amber-600">Partielle</Badge>;
      case "emise":
      case "en attente":
        return <Badge className="bg-blue-600 text-white hover:bg-blue-700">Émise</Badge>;
      case "echue":
      case "en retard":
        return <Badge variant="destructive">Échue</Badge>;
      default:
        return <Badge variant="outline">{statut || "Non défini"}</Badge>;
    }
  };

  const handleDownload = () => {
    toast({
      title: "Téléchargement en cours",
      description: `Facture ${facture?.numero_facture || id} générée au format PDF.`,
    });
  };

  const handlePrint = () => {
    window.print();
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10 rounded" />
          <div className="space-y-2">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-32" />
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-64 rounded-xl" />
      </div>
    );
  }

  if (error || !facture) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" size="icon" onClick={() => navigate("/factures")}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Erreur lors du chargement de la facture</AlertTitle>
          <AlertDescription className="mt-2 flex flex-col gap-4">
            <p>{error || "Facture introuvable ou inaccessible sur le serveur."}</p>
            <Button variant="outline" className="w-fit" onClick={fetchFactureData}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Réessayer
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const montantTotal = Number(facture.montant_total || 0);
  const montantPaye = Number(facture.montant_paye || 0);
  const resteAPayer = Number(facture.reste_a_payer ?? Math.max(0, montantTotal - montantPaye));
  const etudiantNom = facture.etudiant
    ? `${facture.etudiant.nom || ""} ${facture.etudiant.prenom || ""}`.trim()
    : "Étudiant #" + facture.etudiant_id;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate("/factures")}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-foreground">
                {facture.numero_facture || facture.id}
              </h1>
              {getStatutBadge(facture.statut)}
            </div>
            <p className="text-muted-foreground">Facture émise pour {etudiantNom}</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={handleDownload}>
            <Download className="mr-2 h-4 w-4" />
            Télécharger
          </Button>
          <Button variant="outline" onClick={handlePrint}>
            <Printer className="mr-2 h-4 w-4" />
            Imprimer
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <KpiCard title="Montant total" value={`${montantTotal.toLocaleString("fr-FR")} ${currency || "devise de l'établissement"}`} icon={FileText} subtitle="Échéance définie" colorVariant="primary" />
        <KpiCard title="Montant encaissé" value={`${montantPaye.toLocaleString("fr-FR")} ${currency || "devise de l'établissement"}`} icon={CheckCircle2} subtitle={`${montantTotal > 0 ? Math.round((montantPaye / montantTotal) * 100) : 0}% réglé`} colorVariant="emerald" />
        <KpiCard title="Reste à payer" value={`${resteAPayer.toLocaleString("fr-FR")} ${currency || "devise de l'établissement"}`} icon={CreditCard} subtitle="Solde débiteur" colorVariant="amber" />
        <KpiCard title="Date d'échéance" value={facture.date_echeance ? new Date(facture.date_echeance).toLocaleDateString("fr-FR") : "Non fixée"} icon={Calendar} subtitle={facture.date_emission ? `Émise le ${new Date(facture.date_emission).toLocaleDateString("fr-FR")}` : "Émission non renseignée"} colorVariant="sky" />
      </div>

      {/* Tabs */}
      <Tabs defaultValue="details" className="space-y-4">
        <TabsList className="bg-muted">
          <TabsTrigger value="details">Détails Facture</TabsTrigger>
          <TabsTrigger value="etudiant">Étudiant</TabsTrigger>
          <TabsTrigger value="paiements">
            Historique Paiements ({paiements.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="details" className="space-y-4">
          <Card className="border-border bg-card">
            <CardHeader>
              <CardTitle className="text-lg">Informations de facturation</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between rounded-lg border border-border p-4 bg-background">
                  <div>
                    <p className="font-semibold text-foreground">
                      {facture.description || "Aucune description fournie"}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Session académique : {facture.session?.nom || facture.session_id}
                    </p>
                  </div>
                  <span className="text-lg font-bold text-foreground">
                    {montantTotal.toLocaleString("fr-FR")} {currency || "devise de l'établissement"}
                  </span>
                </div>

                <div className="flex items-center justify-between rounded-lg bg-muted/60 p-4">
                  <p className="font-bold text-foreground">Total Facturé</p>
                  <span className="text-xl font-extrabold text-foreground">
                    {montantTotal.toLocaleString("fr-FR")} {currency || "devise de l'établissement"}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="etudiant" className="space-y-4">
          <Card className="border-border bg-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <User className="h-5 w-5 text-primary" />
                Informations de l'Étudiant
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-lg border border-border p-3">
                  <p className="text-xs text-muted-foreground">Nom complet</p>
                  <p className="font-semibold text-foreground">{etudiantNom}</p>
                </div>
                <div className="rounded-lg border border-border p-3">
                  <p className="text-xs text-muted-foreground">Matricule</p>
                  <p className="font-semibold text-foreground">
                    {facture.etudiant?.matricule || "Non renseigné"}
                  </p>
                </div>
                <div className="rounded-lg border border-border p-3">
                  <p className="text-xs text-muted-foreground">Email</p>
                  <p className="font-semibold text-foreground">
                    {facture.etudiant?.email || "Non renseigné"}
                  </p>
                </div>
                <div className="rounded-lg border border-border p-3">
                  <p className="text-xs text-muted-foreground">Filière</p>
                  <p className="font-semibold text-foreground">
                    {facture.etudiant?.filiere || "Non renseigné"}
                  </p>
                </div>
              </div>

              {facture.etudiant_id && (
                <Button
                  variant="outline"
                  className="mt-4"
                  onClick={() => navigate(`/etudiants/${facture.etudiant_id}`)}
                >
                  Voir le dossier complet de l'étudiant
                </Button>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="paiements" className="space-y-4">
          <Card className="border-border bg-card">
            <CardHeader>
              <CardTitle className="text-lg">Historique des encaissements</CardTitle>
            </CardHeader>
            <CardContent>
              {paiements.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Clock className="mx-auto h-8 w-8 mb-2 opacity-50" />
                  <p>Aucun paiement n'a encore été enregistré pour cette facture.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {paiements.map((p) => (
                    <div
                      key={p.id}
                      className="flex items-center justify-between rounded-lg border border-border p-4 bg-background hover:bg-muted/30 transition-colors"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="font-semibold text-foreground">
                            {p.mode_paiement || "Paiement"}
                          </p>
                          <Badge variant="outline" className="text-xs">
                            {p.statut || "valide"}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {p.date_paiement
                            ? new Date(p.date_paiement).toLocaleDateString("fr-FR")
                            : "Date inconnue"}{" "}
                          — Réf: {p.reference || p.id}
                        </p>
                      </div>
                      <span className="text-lg font-bold text-emerald-600 dark:text-emerald-400">
                        +{Number(p.montant).toLocaleString("fr-FR")} {currency || "devise de l'établissement"}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default FactureDetail;
