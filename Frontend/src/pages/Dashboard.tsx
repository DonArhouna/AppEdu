import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Users, UserCheck, CreditCard, GraduationCap, RefreshCw, AlertCircle, ArrowRight } from "lucide-react";
import { KpiCard } from "@/components/ui/kpi-card";
import { Button } from "@/components/ui/button";
import { etudiantsApi, structureApi, financesApi, sessionsApi, setupApi } from "@/services/apiClient";
import type { Payment, Student } from "@/services/apiTypes";
import { Link } from "react-router-dom";

interface DashboardData {
  totalEtudiants: number;
  etudiantsActifs: number;
  totalFilieres: number;
  totalEncaisse: number;
  activeSessionNom: string;
  recentPayments: Array<{
    id: string;
    montant: number;
    etudiantNom?: string;
    date: string;
    mode: string;
  }>;
}

const Dashboard = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currency, setCurrency] = useState("");

  const loadDashboard = async () => {
    setLoading(true);
    setError(null);

    try {
      const [etudiantsRes, filieresRes, paiementsRes, sessionRes, statusResult] = await Promise.all([
        etudiantsApi.getAll(),
        structureApi.getFilieres(),
        financesApi.getPaiements(),
        sessionsApi.getActive(),
        setupApi.getStatus(),
      ]);

      if (etudiantsRes.error || filieresRes.error || paiementsRes.error || sessionRes.error || statusResult.error) {
        const firstErr = etudiantsRes.error || filieresRes.error || paiementsRes.error || sessionRes.error || statusResult.error;
        setError(firstErr || "Impossible de charger les données du tableau de bord.");
        setLoading(false);
        return;
      }

      const students = etudiantsRes.data || [];
      const filieres = filieresRes.data || [];
      const paiements = paiementsRes.data || [];
      const activeSession = sessionRes.data;
      setCurrency(statusResult.data?.devise || "");

      const totalEncaisse = paiements.reduce((acc: number, p: Payment) => acc + (Number(p.montant) || 0), 0);
      const actifs = students.filter((s: Student) => s.statut === "actif" || s.statut === "valide").length;

      const recentPayments = paiements.slice(0, 5).map((p: Payment) => ({
        id: p.id,
        montant: p.montant,
        etudiantNom: (() => {
          const student = students.find((item) => item.id === p.etudiant_id);
          return student ? `${student.prenom || ""} ${student.nom || ""}`.trim() : p.etudiant_id;
        })(),
        date: p.date_paiement,
        mode: p.mode_paiement,
      }));

      setData({
        totalEtudiants: students.length,
        etudiantsActifs: actifs,
        totalFilieres: filieres.length,
        totalEncaisse,
        activeSessionNom: activeSession?.nom || "Non définie",
        recentPayments,
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erreur de connexion au serveur backend.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground tracking-tight">Tableau de Bord Global</h1>
          <p className="text-muted-foreground mt-1 text-sm">
            Vue d'ensemble en temps réel de la scolarité, des encaissements et du suivi académique
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={loadDashboard}
          disabled={loading}
          className="gap-2 self-start sm:self-auto"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          Actualiser
        </Button>
      </div>

      {/* Erreur backend affichée sans données de remplacement */}
      {error && (
        <Card className="border-destructive/40 bg-destructive/5 p-4 rounded-xl">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-destructive shrink-0" />
            <div className="flex-1 text-sm text-destructive">
              <strong>Erreur de synchronisation backend :</strong> {error}
            </div>
            <Button variant="outline" size="sm" onClick={loadDashboard} className="border-destructive/30">
              Réessayer
            </Button>
          </div>
        </Card>
      )}

      {/* État de chargement */}
      {loading && !data && (
        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i} className="p-6 space-y-3 animate-pulse bg-muted/40">
              <div className="h-4 w-24 bg-muted rounded" />
              <div className="h-8 w-16 bg-muted rounded" />
            </Card>
          ))}
        </div>
      )}

      {/* KPI Cards Standard branchées sur l'API */}
      {data && (
        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4">
          <KpiCard
            title="Total Étudiants"
            value={data.totalEtudiants.toLocaleString("fr-FR")}
            icon={Users}
            trendLabel="Effectif total inscrit"
            colorVariant="primary"
          />
          <KpiCard
            title="Inscriptions Actives"
            value={data.etudiantsActifs.toLocaleString("fr-FR")}
            icon={UserCheck}
            trendLabel="Dossiers régularisés"
            colorVariant="emerald"
          />
          <KpiCard
            title="Filières enregistrées"
            value={data.totalFilieres.toString()}
            icon={GraduationCap}
            trendLabel="Offre de formation"
            colorVariant="purple"
          />
          <KpiCard
            title="Total Encaissé"
            value={`${data.totalEncaisse.toLocaleString("fr-FR")} ${currency || "devise de l'établissement"}`}
            icon={CreditCard}
            trendLabel="Encaissements validés"
            colorVariant="amber"
          />
        </div>
      )}

      {/* Activité Récente & Raccourcis Rapides */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card className="card-base">
          <CardHeader className="p-5 flex flex-row items-center justify-between">
            <CardTitle className="text-lg">Derniers Encaissements</CardTitle>
            <Link to="/paiements" className="text-xs text-primary hover:underline flex items-center gap-1 font-medium">
              Voir tout <ArrowRight className="h-3 w-3" />
            </Link>
          </CardHeader>
          <CardContent className="p-5 pt-0">
            {data?.recentPayments && data.recentPayments.length > 0 ? (
              <div className="space-y-4">
                {data.recentPayments.map((p) => (
                  <div key={p.id} className="flex items-center justify-between border-b border-border/40 pb-3 last:border-0 last:pb-0">
                    <div>
                      <p className="text-sm font-semibold text-foreground">
                        {Number(p.montant).toLocaleString("fr-FR")} {currency || "devise de l'établissement"} ({p.mode})
                      </p>
                      <p className="text-xs text-muted-foreground">{p.etudiantNom}</p>
                    </div>
                    <span className="text-xs text-muted-foreground font-mono">{p.date}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-sm text-muted-foreground">
                Aucun encaissement enregistré pour le moment.
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="card-base">
          <CardHeader className="p-5">
            <CardTitle className="text-lg">Statut & Sessions Actives</CardTitle>
          </CardHeader>
          <CardContent className="p-5 pt-0 space-y-3">
            <div className="p-3 rounded-xl border border-border/50 bg-muted/30 text-xs flex items-center justify-between">
              <div>
                <p className="font-semibold text-foreground">Session Académique Courante</p>
                <p className="text-muted-foreground">{data?.activeSessionNom || "Chargement..."}</p>
              </div>
              <span className={`text-xs font-bold px-2 py-0.5 rounded border ${data?.activeSessionNom && data.activeSessionNom !== "Non définie" ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/20" : "bg-muted text-muted-foreground border-border"}`}>
                {data?.activeSessionNom && data.activeSessionNom !== "Non définie" ? "Active" : "Non définie"}
              </span>
            </div>

            <div className="p-3 rounded-xl border border-border/50 bg-muted/30 text-xs flex items-center justify-between">
              <div>
                <p className="font-semibold text-foreground">Moteur de Délibération LMD/ECTS</p>
                <p className="text-muted-foreground">Compensation, seuils d'ajournement et mentions</p>
              </div>
              <span className="text-xs font-bold px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                Opérationnel
              </span>
            </div>

            <div className="p-3 rounded-xl border border-border/50 bg-muted/30 text-xs flex items-center justify-between">
              <div>
                <p className="font-semibold text-foreground">Génération Automatique de Matricules</p>
                <p className="text-muted-foreground">Format standardisé : AAAA-FILIÈRE-NUMÉRO</p>
              </div>
              <span className="text-xs font-bold px-2 py-0.5 rounded bg-purple-500/10 text-purple-600 border border-purple-500/20">
                Automatique
              </span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Dashboard;
