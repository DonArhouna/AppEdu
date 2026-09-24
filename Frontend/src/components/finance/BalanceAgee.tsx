import { useEffect, useMemo, useState } from "react";
import { AlertCircle, Clock, Loader2, RefreshCw, Search, ShieldAlert, Wallet } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { KpiCard } from "@/components/ui/kpi-card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { financesApi, extractErrorMessage, setupApi } from "@/services/apiClient";

interface BalanceItem {
  etudiant_id: string;
  matricule: string;
  nom_complet: string;
  filiere: string;
  montant_total_du: number;
  non_echu: number;
  retard_1_30_jours: number;
  retard_31_60_jours: number;
  retard_plus_60_jours: number;
}

interface BalanceResponse {
  date_calcul: string;
  total_creances: number;
  items: BalanceItem[];
}

const EMPTY_ITEMS: BalanceItem[] = [];

type Tranche = "all" | "1_30" | "31_60" | "60_plus";
type TrancheFilter = Tranche;

const getTranche = (item: BalanceItem): Tranche => {
  if (item.retard_plus_60_jours > 0) return "60_plus";
  if (item.retard_31_60_jours > 0) return "31_60";
  if (item.retard_1_30_jours > 0) return "1_30";
  return "all";
};

export const BalanceAgee = () => {
  const [balance, setBalance] = useState<BalanceResponse | null>(null);
  const [currency, setCurrency] = useState("");
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<TrancheFilter>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadBalance = async () => {
    setLoading(true);
    setError(null);
    const [balanceResult, statusResult] = await Promise.all([
      financesApi.getBalanceAgee(),
      setupApi.getStatus(),
    ]);
    if (balanceResult.error || !balanceResult.data) {
      setError(extractErrorMessage(balanceResult.error, "Impossible de charger la balance âgée."));
      setBalance(null);
    } else {
      setBalance(balanceResult.data);
    }
    setCurrency(statusResult.data?.devise || "");
    setLoading(false);
  };

  useEffect(() => {
    void loadBalance();
  }, []);

  const items = balance?.items ?? EMPTY_ITEMS;
  const filteredItems = useMemo(() => {
    const query = search.trim().toLowerCase();
    return items.filter((item) => {
      const matchesSearch = !query || [item.nom_complet, item.matricule, item.filiere]
        .join(" ")
        .toLowerCase()
        .includes(query);
      const matchesFilter = filter === "all" || getTranche(item) === filter;
      return matchesSearch && matchesFilter;
    });
  }, [items, search, filter]);

  const totalDue = balance?.total_creances || 0;
  const critical = items.reduce((sum, item) => sum + item.retard_plus_60_jours, 0);
  const firstBucket = items.reduce((sum, item) => sum + item.retard_1_30_jours, 0);
  const currencyLabel = currency || "devise de l'établissement";

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <KpiCard title="Total des créances" value={`${totalDue.toLocaleString("fr-FR")} ${currencyLabel}`} subtitle="Solde restant dans l'API" icon={Wallet} color="rose" />
        <KpiCard title="Retard critique" value={`${critical.toLocaleString("fr-FR")} ${currencyLabel}`} subtitle="Plus de 60 jours" icon={ShieldAlert} color="rose" />
        <KpiCard title="Retard 1–30 jours" value={`${firstBucket.toLocaleString("fr-FR")} ${currencyLabel}`} subtitle="Créances sur la première échéance" icon={Clock} color="amber" />
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Erreur backend</AlertTitle>
          <AlertDescription className="flex items-center justify-between gap-3">
            <span>{error}</span>
            <Button variant="outline" size="sm" onClick={loadBalance}><RefreshCw className="mr-2 h-4 w-4" />Réessayer</Button>
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>Balance âgée des créances</CardTitle>
              <CardDescription>
                Calculée par le backend à partir des factures et des paiements enregistrés.
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={loadBalance} disabled={loading}>
              <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Actualiser
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative w-full sm:max-w-sm">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input value={search} onChange={(event) => setSearch(event.target.value)} className="pl-9" placeholder="Étudiant, matricule ou filière" />
            </div>
            <div className="flex flex-wrap gap-2">
              {([
                ["all", "Tous"],
                ["1_30", "1–30j"],
                ["31_60", "31–60j"],
                ["60_plus", "> 60j"],
              ] as const).map(([value, label]) => (
                <Button key={value} size="sm" variant={filter === value ? "default" : "outline"} onClick={() => setFilter(value)}>
                  {label}
                </Button>
              ))}
            </div>
          </div>

          <div className="overflow-x-auto rounded-xl border">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/40">
                  <TableHead>Étudiant</TableHead><TableHead>Filière</TableHead>
                  <TableHead className="text-right">Solde</TableHead><TableHead className="text-right">1–30j</TableHead>
                  <TableHead className="text-right">31–60j</TableHead><TableHead className="text-right">&gt;60j</TableHead>
                  <TableHead>Tranche</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow><TableCell colSpan={7} className="py-10 text-center"><Loader2 className="mx-auto h-5 w-5 animate-spin" /></TableCell></TableRow>
                ) : filteredItems.length === 0 ? (
                  <TableRow><TableCell colSpan={7} className="py-10 text-center text-muted-foreground">Aucune créance ne correspond au filtre.</TableCell></TableRow>
                ) : filteredItems.map((item) => {
                  const tranche = getTranche(item);
                  return (
                    <TableRow key={item.etudiant_id}>
                      <TableCell><p className="font-medium">{item.nom_complet}</p><p className="font-mono text-xs text-muted-foreground">{item.matricule}</p></TableCell>
                      <TableCell>{item.filiere || "Non renseignée"}</TableCell>
                      <TableCell className="text-right font-mono font-semibold text-destructive">{item.montant_total_du.toLocaleString("fr-FR")} {currencyLabel}</TableCell>
                      <TableCell className="text-right font-mono">{item.retard_1_30_jours.toLocaleString("fr-FR")}</TableCell>
                      <TableCell className="text-right font-mono">{item.retard_31_60_jours.toLocaleString("fr-FR")}</TableCell>
                      <TableCell className="text-right font-mono text-rose-600">{item.retard_plus_60_jours.toLocaleString("fr-FR")}</TableCell>
                      <TableCell><Badge variant={tranche === "60_plus" ? "destructive" : tranche === "all" ? "outline" : "secondary"}>{tranche === "all" ? "Non échu" : tranche === "60_plus" ? "> 60j" : tranche === "31_60" ? "31–60j" : "1–30j"}</Badge></TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
          <p className="text-xs text-muted-foreground">
            Les relances automatiques ne sont pas activées tant qu'un service de messagerie et un modèle de relance n'ont pas été configurés côté backend.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default BalanceAgee;
