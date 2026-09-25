import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FileText, Eye, DollarSign, CheckCircle2, Clock, AlertTriangle, RefreshCw, AlertCircle, Search } from "lucide-react";
import { toast } from "sonner";
import { KpiCard } from "@/components/ui/kpi-card";
import { BalanceAgee } from "@/components/finance/BalanceAgee";
import { financesApi, etudiantsApi, setupApi } from "@/services/apiClient";
import type { Invoice } from "@/services/apiTypes";

interface Facture {
  id: string;
  numeroFacture: string;
  etudiantId: string;
  etudiantNom: string;
  matricule: string;
  montantTotal: number;
  montantPaye: number;
  soldeRestant: number;
  dateEmission: string;
  dateEcheance: string;
  statut: string;
  description?: string;
}

const Factures = () => {
  const [factures, setFactures] = useState<Facture[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterStatut, setFilterStatut] = useState<string>("tous");
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [currency, setCurrency] = useState("");

  const loadFactures = async () => {
    setLoading(true);
    setError(null);
    try {
      const [res, studentsResult, setupResult] = await Promise.all([
        financesApi.getFactures(),
        etudiantsApi.getSummary(),
        setupApi.getStatus(),
      ]);
      if (res.error || studentsResult.error) {
        setError(res.error || studentsResult.error || "Impossible de charger les factures.");
        setFactures([]);
      } else {
        const students = studentsResult.data || [];
        setFactures(
          (res.data || []).map((f: Invoice) => {
            const student = students.find((item) => item.id === f.etudiant_id);
            return {
              id: f.id,
              numeroFacture: f.numero_facture || f.id,
              etudiantId: f.etudiant_id,
              etudiantNom: student ? `${student.prenom || ""} ${student.nom || ""}`.trim() : "Étudiant introuvable",
              matricule: student?.matricule || "",
              montantTotal: Number(f.montant_total) || 0,
              montantPaye: Number(f.montant_paye) || 0,
              soldeRestant: Number(f.reste_a_payer ?? (f.montant_total - f.montant_paye)) || 0,
              dateEmission: f.date_emission || "",
              dateEcheance: f.date_echeance || "",
              statut: f.statut || "",
              description: f.description,
            };
          })
        );
        setCurrency(setupResult.data?.devise || "");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erreur de connexion.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFactures();
  }, []);

  const totalFacture = factures.reduce((acc, f) => acc + f.montantTotal, 0);
  const totalPaye = factures.reduce((acc, f) => acc + f.montantPaye, 0);
  const totalImpaye = factures.reduce((acc, f) => acc + f.soldeRestant, 0);

  const filteredFactures = factures.filter((f) => {
    const matchStatut = filterStatut === "tous" || f.statut === filterStatut;
    const matchSearch =
      f.numeroFacture.toLowerCase().includes(searchTerm.toLowerCase()) ||
      f.etudiantId.toLowerCase().includes(searchTerm.toLowerCase()) ||
      f.etudiantNom.toLowerCase().includes(searchTerm.toLowerCase()) ||
      f.matricule.toLowerCase().includes(searchTerm.toLowerCase());
    return matchStatut && matchSearch;
  });

  const getBadgeVariant = (statut: string) => {
    switch (statut) {
      case "payee":
        return <Badge className="bg-emerald-600 text-white">Payée</Badge>;
      case "partielle":
        return <Badge className="bg-amber-600 text-white">Partielle</Badge>;
      case "en_attente":
        return <Badge variant="outline" className="text-amber-600 border-amber-600">En attente</Badge>;
      case "echue":
        return <Badge className="bg-red-600 text-white">Échue</Badge>;
      default:
        return <Badge variant="secondary">{statut}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Facturation & Échéanciers</h1>
          <p className="text-muted-foreground mt-1">
            Suivi des factures scolaires, échéances et soldes restants
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={loadFactures} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-1.5 ${loading ? "animate-spin" : ""}`} />
          Actualiser
        </Button>
      </div>

      {error && (
        <Card className="border-destructive/40 bg-destructive/5 p-4 rounded-xl">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-destructive shrink-0" />
            <div className="flex-1 text-sm text-destructive">
              <strong>Erreur backend :</strong> {error}
            </div>
            <Button variant="outline" size="sm" onClick={loadFactures} className="border-destructive/30">
              Réessayer
            </Button>
          </div>
        </Card>
      )}

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <KpiCard
          title="Total Facturé"
          value={`${totalFacture.toLocaleString("fr-FR")} ${currency || "devise de l'établissement"}`}
          icon={DollarSign}
          subtitle={`${factures.length} factures générées`}
          colorVariant="primary"
        />
        <KpiCard
          title="Montant Recouvré"
          value={`${totalPaye.toLocaleString("fr-FR")} ${currency || "devise de l'établissement"}`}
          icon={CheckCircle2}
          subtitle={`${totalFacture > 0 ? Math.round((totalPaye / totalFacture) * 100) : 0}% de recouvrement`}
          colorVariant="emerald"
        />
        <KpiCard
          title="Reste à Recouvrer"
          value={`${totalImpaye.toLocaleString("fr-FR")} ${currency || "devise de l'établissement"}`}
          icon={Clock}
          subtitle="Créances en cours"
          colorVariant="amber"
        />
      </div>

      <Tabs defaultValue="factures" className="space-y-4">
        <TabsList>
          <TabsTrigger value="factures">Liste des Factures ({filteredFactures.length})</TabsTrigger>
          <TabsTrigger value="balance">Balance Âgée</TabsTrigger>
        </TabsList>

        <TabsContent value="factures" className="space-y-4">
          <Card className="card-base">
            <CardHeader className="p-4">
              <div className="flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
                <div className="relative flex-1 max-w-sm">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Rechercher par N° Facture ou Étudiant..."
                    className="pl-9 text-xs"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                </div>
                <div className="flex items-center gap-2">
                  <Select value={filterStatut} onValueChange={setFilterStatut}>
                    <SelectTrigger className="w-[160px] text-xs">
                      <SelectValue placeholder="Filtrer par statut" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="tous">Tous les statuts</SelectItem>
                      <SelectItem value="payee">Payée</SelectItem>
                      <SelectItem value="partielle">Partielle</SelectItem>
                      <SelectItem value="en_attente">En attente</SelectItem>
                      <SelectItem value="echue">Échue</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="border-t overflow-x-auto">
                {loading ? (
                  <div className="p-16 text-center space-y-3">
                    <RefreshCw className="h-8 w-8 animate-spin mx-auto text-primary" />
                    <p className="text-sm text-muted-foreground">Chargement des factures...</p>
                  </div>
                ) : filteredFactures.length === 0 ? (
                  <div className="p-12 text-center text-sm text-muted-foreground space-y-2">
                    <FileText className="h-10 w-10 mx-auto text-muted-foreground/40" />
                    <p className="font-semibold text-foreground">Aucune facture trouvée</p>
                    <p className="text-xs">Aucune facture enregistrée dans le système pour le moment.</p>
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-muted/40 text-xs">
                        <TableHead>N° Facture</TableHead>
                        <TableHead>Étudiant Rattaché</TableHead>
                        <TableHead>Montant Total</TableHead>
                        <TableHead>Payé</TableHead>
                        <TableHead>Solde Restant</TableHead>
                        <TableHead>Échéance</TableHead>
                        <TableHead>Statut</TableHead>
                        <TableHead className="text-right">Action</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredFactures.map((facture) => (
                        <TableRow key={facture.id} className="text-xs hover:bg-muted/30">
                          <TableCell className="font-mono font-bold text-primary">
                            {facture.numeroFacture}
                          </TableCell>
                          <TableCell className="font-medium text-foreground">
                            <div>{facture.etudiantNom}</div>
                             {facture.matricule && <div className="font-mono text-[10px] text-muted-foreground">{facture.matricule}</div>}
                          </TableCell>
                          <TableCell className="font-semibold">
                            {facture.montantTotal.toLocaleString("fr-FR")} {currency || "devise de l'établissement"}
                          </TableCell>
                          <TableCell className="text-emerald-600 font-medium">
                            {facture.montantPaye.toLocaleString("fr-FR")} {currency || "devise de l'établissement"}
                          </TableCell>
                          <TableCell className={facture.soldeRestant > 0 ? "text-amber-600 font-bold" : "text-muted-foreground"}>
                            {facture.soldeRestant.toLocaleString("fr-FR")} {currency || "devise de l'établissement"}
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {facture.dateEcheance}
                          </TableCell>
                          <TableCell>{getBadgeVariant(facture.statut)}</TableCell>
                          <TableCell className="text-right">
                            <Link to={`/factures/${facture.id}`}>
                              <Button variant="ghost" size="icon">
                                <Eye className="h-4 w-4" />
                              </Button>
                            </Link>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="balance">
          <BalanceAgee />
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Factures;
