import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  ArrowLeft,
  Download,
  Printer,
  CreditCard,
  Calendar,
  User,
  FileText,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  Clock,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { financesApi, extractErrorMessage } from "@/services/apiClient";

const PaiementDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [paiement, setPaiement] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPaiement = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await financesApi.getPaiementById(id);
      setPaiement(data);
    } catch (err: any) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPaiement();
  }, [id]);

  const getStatutBadge = (statut: string) => {
    const s = statut?.toLowerCase();
    switch (s) {
      case "valide":
      case "validé":
        return <Badge className="bg-emerald-600 text-white hover:bg-emerald-700">Validé</Badge>;
      case "en_attente":
      case "en attente":
        return <Badge className="bg-amber-500 text-white hover:bg-amber-600">En attente</Badge>;
      case "echoue":
      case "rejeté":
        return <Badge variant="destructive">Rejeté</Badge>;
      default:
        return <Badge variant="outline">{statut || "Inconnu"}</Badge>;
    }
  };

  const handleDownloadRecu = () => {
    toast({
      title: "Téléchargement du reçu",
      description: `Reçu pour le paiement ${paiement?.reference || id} en cours de génération...`,
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
        <div className="grid gap-6 md:grid-cols-2">
          <Skeleton className="h-64 rounded-xl" />
          <Skeleton className="h-64 rounded-xl" />
        </div>
      </div>
    );
  }

  if (error || !paiement) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" size="icon" onClick={() => navigate("/paiements")}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Erreur lors du chargement du paiement</AlertTitle>
          <AlertDescription className="mt-2 flex flex-col gap-4">
            <p>{error || "Règlement introuvable ou inaccessible sur le serveur."}</p>
            <Button variant="outline" className="w-fit" onClick={fetchPaiement}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Réessayer
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const montant = Number(paiement.montant || 0);
  const etudiantNom = paiement.etudiant
    ? `${paiement.etudiant.nom || ""} ${paiement.etudiant.prenom || ""}`.trim()
    : "Étudiant #" + (paiement.etudiant_id || "N/A");

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate("/paiements")}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-foreground">{paiement.reference || paiement.id}</h1>
              {getStatutBadge(paiement.statut)}
            </div>
            <p className="text-muted-foreground">Règlement de {etudiantNom}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleDownloadRecu}>
            <Download className="mr-2 h-4 w-4" />
            Télécharger Reçu
          </Button>
          <Button variant="outline" onClick={handlePrint}>
            <Printer className="mr-2 h-4 w-4" />
            Imprimer
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="border-border bg-card">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Montant Encaissé</CardTitle>
            <CreditCard className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
              {montant.toLocaleString("fr-FR")} FCFA
            </div>
          </CardContent>
        </Card>

        <Card className="border-border bg-card">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Date de Paiement</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold text-foreground">
              {paiement.date_paiement
                ? new Date(paiement.date_paiement).toLocaleDateString("fr-FR")
                : "-"}
            </div>
          </CardContent>
        </Card>

        <Card className="border-border bg-card">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Mode de Paiement</CardTitle>
            <CreditCard className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold text-foreground">
              {paiement.mode_paiement || "Espèces"}
            </div>
          </CardContent>
        </Card>

        <Card className="border-border bg-card">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Statut</CardTitle>
            <CheckCircle className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold capitalize text-foreground">
              {paiement.statut || "Validé"}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Details */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Étudiant */}
        <Card className="border-border bg-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <User className="h-5 w-5 text-primary" />
              Informations Étudiant
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 grid-cols-2">
              <div className="rounded-lg border border-border p-3">
                <p className="text-xs text-muted-foreground">Nom complet</p>
                <p className="font-semibold text-foreground">{etudiantNom}</p>
              </div>
              <div className="rounded-lg border border-border p-3">
                <p className="text-xs text-muted-foreground">Matricule</p>
                <p className="font-semibold text-foreground">
                  {paiement.etudiant?.matricule || "N/A"}
                </p>
              </div>
              <div className="rounded-lg border border-border p-3">
                <p className="text-xs text-muted-foreground">Email</p>
                <p className="font-semibold text-foreground">
                  {paiement.etudiant?.email || "Non renseigné"}
                </p>
              </div>
              <div className="rounded-lg border border-border p-3">
                <p className="text-xs text-muted-foreground">Téléphone</p>
                <p className="font-semibold text-foreground">
                  {paiement.etudiant?.telephone || "Non renseigné"}
                </p>
              </div>
            </div>
            {paiement.etudiant_id && (
              <Button
                variant="outline"
                onClick={() => navigate(`/etudiants/${paiement.etudiant_id}`)}
              >
                Voir le dossier étudiant
              </Button>
            )}
          </CardContent>
        </Card>

        {/* Facture liée */}
        <Card className="border-border bg-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <FileText className="h-5 w-5 text-primary" />
              Facture Associée
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 grid-cols-2">
              <div className="rounded-lg border border-border p-3">
                <p className="text-xs text-muted-foreground">Numéro de Facture</p>
                <p className="font-semibold text-foreground">
                  {paiement.facture?.numero_facture || paiement.facture_id || "Facture standard"}
                </p>
              </div>
              <div className="rounded-lg border border-border p-3">
                <p className="text-xs text-muted-foreground">Montant Total Facture</p>
                <p className="font-semibold text-foreground">
                  {paiement.facture?.montant_total
                    ? `${Number(paiement.facture.montant_total).toLocaleString("fr-FR")} FCFA`
                    : "Non spécifié"}
                </p>
              </div>
            </div>
            {paiement.facture_id && (
              <Button
                variant="outline"
                onClick={() => navigate(`/factures/${paiement.facture_id}`)}
              >
                Voir la facture détaillée
              </Button>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Détails complémentaires */}
      <Card className="border-border bg-card">
        <CardHeader>
          <CardTitle className="text-lg">Informations de Traçabilité & Transaction</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-border p-3">
              <p className="text-xs text-muted-foreground">Référence Transaction</p>
              <p className="font-mono font-semibold text-foreground">{paiement.reference || paiement.id}</p>
            </div>
            <div className="rounded-lg border border-border p-3">
              <p className="text-xs text-muted-foreground">Session Académique</p>
              <p className="font-semibold text-foreground">{paiement.session?.nom || paiement.session_id || "Session courante"}</p>
            </div>
            <div className="rounded-lg border border-border p-3">
              <p className="text-xs text-muted-foreground">Opérateur / Caisse</p>
              <p className="font-semibold text-foreground">Caisse Centrale IMIA</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default PaiementDetail;
