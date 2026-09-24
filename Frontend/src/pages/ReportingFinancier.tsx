import { useEffect, useMemo, useState } from "react";
import { AlertCircle, DollarSign, Loader2, RefreshCw, TrendingUp, Users } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { financesApi, setupApi, extractErrorMessage } from "@/services/apiClient";
import type { Invoice, Payment } from "@/services/apiTypes";

const ReportingFinancier = () => {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [currency, setCurrency] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const load = async () => { setLoading(true); setError(null); const [p, f, s] = await Promise.all([financesApi.getPaiements(), financesApi.getFactures(), setupApi.getStatus()]); if (p.error || f.error) setError(extractErrorMessage(p.error || f.error)); setPayments(p.data || []); setInvoices(f.data || []); setCurrency(s.data?.devise || ""); setLoading(false); };
  useEffect(() => { void load(); }, []);
  const totalPaid = payments.reduce((sum, item) => sum + Number(item.montant || 0), 0);
  const totalInvoiced = invoices.reduce((sum, item) => sum + Number(item.montant_total || 0), 0);
  const outstanding = invoices.reduce((sum, item) => sum + Number(item.reste_a_payer ?? (item.montant_total - item.montant_paye)), 0);
  const recovery = totalInvoiced ? Math.round((totalPaid / totalInvoiced) * 100) : 0;
  const byMonth = useMemo(() => { const map = new Map<string, number>(); payments.forEach((payment) => { const month = String(payment.date_paiement || "").slice(0, 7); if (month) map.set(month, (map.get(month) || 0) + Number(payment.montant || 0)); }); return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b)).map(([month, amount]) => ({ month, amount })); }, [payments]);
  const currencyLabel = currency || "devise de l'établissement";
  return <div className="space-y-6"><div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><div><h1 className="text-3xl font-bold tracking-tight">Reporting financier</h1><p className="mt-1 text-muted-foreground">Agrégats calculés depuis les factures et paiements de l'API.</p></div><Button variant="outline" onClick={load} disabled={loading}><RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />Actualiser</Button></div>{error && <Alert variant="destructive"><AlertCircle className="h-4 w-4" /><AlertTitle>Erreur backend</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}{loading ? <div className="flex items-center justify-center gap-2 p-16 text-sm text-muted-foreground"><Loader2 className="h-5 w-5 animate-spin" />Calcul...</div> : <><div className="grid gap-4 md:grid-cols-4"><Card><CardHeader><CardTitle className="text-sm text-muted-foreground">Encaissé</CardTitle><DollarSign className="h-4 w-4 text-amber-600" /></CardHeader><CardContent><p className="text-2xl font-bold">{totalPaid.toLocaleString("fr-FR")} {currencyLabel}</p></CardContent></Card><Card><CardHeader><CardTitle className="text-sm text-muted-foreground">Facturé</CardTitle><TrendingUp className="h-4 w-4 text-primary" /></CardHeader><CardContent><p className="text-2xl font-bold">{totalInvoiced.toLocaleString("fr-FR")} {currencyLabel}</p></CardContent></Card><Card><CardHeader><CardTitle className="text-sm text-muted-foreground">Reste à recouvrer</CardTitle><AlertCircle className="h-4 w-4 text-destructive" /></CardHeader><CardContent><p className="text-2xl font-bold text-destructive">{outstanding.toLocaleString("fr-FR")} {currencyLabel}</p></CardContent></Card><Card><CardHeader><CardTitle className="text-sm text-muted-foreground">Taux de recouvrement</CardTitle><TrendingUp className="h-4 w-4 text-emerald-600" /></CardHeader><CardContent><p className="text-2xl font-bold">{recovery}%</p></CardContent></Card></div><Card><CardHeader><CardTitle>Paiements par mois</CardTitle><CardDescription>Les montants proviennent de la date enregistrée côté serveur.</CardDescription></CardHeader><CardContent className="p-0"><Table><TableHeader><TableRow><TableHead>Mois</TableHead><TableHead>Montant</TableHead></TableRow></TableHeader><TableBody>{byMonth.length === 0 ? <TableRow><TableCell colSpan={2} className="py-8 text-center text-muted-foreground">Aucun paiement.</TableCell></TableRow> : byMonth.map((item) => <TableRow key={item.month}><TableCell>{item.month}</TableCell><TableCell className="font-mono">{item.amount.toLocaleString("fr-FR")} {currencyLabel}</TableCell></TableRow>)}</TableBody></Table></CardContent></Card><p className="text-xs text-muted-foreground">Les projections, coûts et ventilation par type de frais ne sont pas simulés : elles nécessitent un module de reporting backend.</p></>}</div>;
};

export default ReportingFinancier;
