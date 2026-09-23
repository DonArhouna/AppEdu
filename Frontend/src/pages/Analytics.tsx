import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import {
  TrendingUp,
  TrendingDown,
  Users,
  GraduationCap,
  DollarSign,
  Building,
  AlertTriangle,
} from "lucide-react";

import { KpiCard } from "@/components/ui/kpi-card";

const Analytics = () => {
  // KPIs data standardisés
  const kpis = [
    {
      title: "Effectifs Totaux",
      value: "1,234",
      trend: "+12%",
      trendDirection: "up" as const,
      icon: Users,
      colorVariant: "primary" as const,
    },
    {
      title: "Taux de Réussite",
      value: "87.5%",
      trend: "+3.2%",
      trendDirection: "up" as const,
      icon: GraduationCap,
      colorVariant: "emerald" as const,
    },
    {
      title: "Taux d'Abandon",
      value: "8.3%",
      trend: "-1.5%",
      trendDirection: "down" as const,
      icon: AlertTriangle,
      colorVariant: "rose" as const,
    },
    {
      title: "Chiffre d'Affaires",
      value: "850M FCFA",
      trend: "+15%",
      trendDirection: "up" as const,
      icon: DollarSign,
      colorVariant: "amber" as const,
    },
  ];

  // Success rate by program
  const tauxReussiteData = [
    { filiere: "Licence Info", taux: 92 },
    { filiere: "Master Gestion", taux: 88 },
    { filiere: "DUT Commerce", taux: 85 },
    { filiere: "Licence Compta", taux: 90 },
    { filiere: "Master RH", taux: 87 },
    { filiere: "BTS Informatique", taux: 83 },
  ];

  // Enrollment evolution
  const effectifsData = [
    { mois: "Sep", etudiants: 980 },
    { mois: "Oct", etudiants: 1020 },
    { mois: "Nov", etudiants: 1050 },
    { mois: "Dec", etudiants: 1080 },
    { mois: "Jan", etudiants: 1150 },
    { mois: "Fev", etudiants: 1200 },
    { mois: "Mar", etudiants: 1234 },
  ];

  // Distribution by program
  const distributionData = [
    { name: "Informatique", value: 420 },
    { name: "Gestion", value: 350 },
    { name: "Commerce", value: 280 },
    { name: "Comptabilité", value: 184 },
  ];

  const COLORS = ["hsl(var(--primary))", "hsl(var(--secondary))", "hsl(var(--accent))", "hsl(var(--muted))"];

  // Room occupancy
  const occupationSallesData = [
    { jour: "Lun", taux: 85 },
    { jour: "Mar", taux: 92 },
    { jour: "Mer", taux: 88 },
    { jour: "Jeu", taux: 95 },
    { jour: "Ven", taux: 78 },
    { jour: "Sam", taux: 45 },
  ];

  // Financial health
  const santeFinanciereData = [
    { mois: "Sep", recettes: 120, depenses: 85 },
    { mois: "Oct", recettes: 125, depenses: 90 },
    { mois: "Nov", recettes: 130, depenses: 88 },
    { mois: "Dec", recettes: 140, depenses: 95 },
    { mois: "Jan", recettes: 145, depenses: 92 },
    { mois: "Fev", recettes: 150, depenses: 98 },
    { mois: "Mar", recettes: 155, depenses: 100 },
  ];

  // Students at risk (for ML prediction feature)
  const etudiantsRisqueData = [
    { nom: "Jean Martin", filiere: "Licence Info", risque: 85, facteurs: "Absences élevées, notes en baisse" },
    { nom: "Marie Dubois", filiere: "Master Gestion", risque: 72, facteurs: "Retard paiements, participation faible" },
    { nom: "Ahmed Hassan", filiere: "DUT Commerce", risque: 68, facteurs: "Notes limites, absences récurrentes" },
    { nom: "Sophie Bernard", filiere: "Licence Compta", risque: 64, facteurs: "Difficultés matières clés" },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Analytics & Business Intelligence</h1>
        <p className="text-muted-foreground mt-2">
          Tableaux de bord et indicateurs de performance pour la Direction
        </p>
      </div>

      {/* Uniform KPI Cards Standard */}
      <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4">
        {kpis.map((kpi) => (
          <KpiCard
            key={kpi.title}
            title={kpi.title}
            value={kpi.value}
            icon={kpi.icon}
            trend={kpi.trend}
            trendDirection={kpi.trendDirection}
            trendLabel="vs année dernière"
            colorVariant={kpi.colorVariant}
          />
        ))}
      </div>

      {/* Charts Tabs */}
      <Tabs defaultValue="academique" className="space-y-4">
        <TabsList>
          <TabsTrigger value="academique">Académique</TabsTrigger>
          <TabsTrigger value="financier">Financier</TabsTrigger>
          <TabsTrigger value="ressources">Ressources</TabsTrigger>
          <TabsTrigger value="prediction">Prédiction (ML)</TabsTrigger>
        </TabsList>

        <TabsContent value="academique" className="space-y-4">
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Taux de Réussite par Filière</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={tauxReussiteData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="filiere" fontSize={12} />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="taux" fill="hsl(var(--primary))" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Évolution des Effectifs</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={effectifsData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="mois" />
                    <YAxis />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="etudiants"
                      stroke="hsl(var(--primary))"
                      strokeWidth={2}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Distribution par Filière</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={distributionData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={(entry) => `${entry.name}: ${entry.value}`}
                      outerRadius={80}
                      fill="hsl(var(--primary))"
                      dataKey="value"
                    >
                      {distributionData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Taux d'Occupation des Salles</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={occupationSallesData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="jour" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="taux" fill="hsl(var(--accent))" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="financier" className="space-y-4">
          <div className="grid gap-6 md:grid-cols-2">
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle>Santé Financière - Recettes vs Dépenses (en millions FCFA)</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={350}>
                  <LineChart data={santeFinanciereData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="mois" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="recettes"
                      stroke="hsl(var(--primary))"
                      strokeWidth={2}
                      name="Recettes"
                    />
                    <Line
                      type="monotone"
                      dataKey="depenses"
                      stroke="hsl(var(--destructive))"
                      strokeWidth={2}
                      name="Dépenses"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Taux de Recouvrement</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Paiements reçus</span>
                    <span className="text-2xl font-bold text-foreground">92.5%</span>
                  </div>
                  <div className="h-2 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full bg-primary transition-all"
                      style={{ width: "92.5%" }}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4 mt-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Payé</p>
                      <p className="text-xl font-bold text-success">786M FCFA</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">En attente</p>
                      <p className="text-xl font-bold text-destructive">64M FCFA</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Répartition des Revenus</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-foreground">Scolarité</span>
                    <span className="text-sm font-medium">620M (73%)</span>
                  </div>
                  <div className="h-2 rounded-full bg-muted overflow-hidden">
                    <div className="h-full bg-primary" style={{ width: "73%" }} />
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-sm text-foreground">Formations continues</span>
                    <span className="text-sm font-medium">150M (18%)</span>
                  </div>
                  <div className="h-2 rounded-full bg-muted overflow-hidden">
                    <div className="h-full bg-secondary" style={{ width: "18%" }} />
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-sm text-foreground">Services divers</span>
                    <span className="text-sm font-medium">80M (9%)</span>
                  </div>
                  <div className="h-2 rounded-full bg-muted overflow-hidden">
                    <div className="h-full bg-accent" style={{ width: "9%" }} />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="ressources" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Utilisation des Ressources</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-6 md:grid-cols-2">
                <div className="space-y-4">
                  <h3 className="font-medium text-foreground">Salles de Cours</h3>
                  <div className="space-y-3">
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm text-muted-foreground">Taux moyen d'occupation</span>
                        <span className="text-sm font-medium">82%</span>
                      </div>
                      <div className="h-2 rounded-full bg-muted overflow-hidden">
                        <div className="h-full bg-primary" style={{ width: "82%" }} />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs text-muted-foreground">Salles disponibles</p>
                        <p className="text-lg font-bold text-foreground">45</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Utilisation journalière</p>
                        <p className="text-lg font-bold text-foreground">37</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <h3 className="font-medium text-foreground">Ratio Enseignants/Étudiants</h3>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Ratio actuel</span>
                      <span className="text-2xl font-bold text-foreground">1:28</span>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs text-muted-foreground">Enseignants</p>
                        <p className="text-lg font-bold text-foreground">44</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Étudiants</p>
                        <p className="text-lg font-bold text-foreground">1,234</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="prediction" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-destructive" />
                Étudiants à Risque d'Échec (Machine Learning)
              </CardTitle>
              <p className="text-sm text-muted-foreground mt-2">
                Prédiction basée sur l'analyse des absences, notes, participation et paiements
              </p>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {etudiantsRisqueData.map((etudiant, index) => (
                  <div
                    key={index}
                    className="flex items-start justify-between border-b border-border pb-4 last:border-0"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="font-medium text-foreground">{etudiant.nom}</p>
                        <Badge
                          variant={
                            etudiant.risque > 75
                              ? "destructive"
                              : etudiant.risque > 60
                              ? "secondary"
                              : "default"
                          }
                        >
                          Risque: {etudiant.risque}%
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mb-2">{etudiant.filiere}</p>
                      <p className="text-sm text-foreground">{etudiant.facteurs}</p>
                    </div>
                    <div className="ml-4">
                      <div className="w-20 h-20 rounded-full border-4 border-primary/20 flex items-center justify-center">
                        <span className="text-xl font-bold text-destructive">
                          {etudiant.risque}%
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-6 p-4 bg-muted rounded-lg">
                <p className="text-sm text-muted-foreground">
                  <strong>Note:</strong> Cette fonctionnalité utilise un modèle de Machine Learning
                  pour prédire les étudiants à risque. Les recommandations incluent un suivi
                  personnalisé, des sessions de tutorat et un accompagnement renforcé.
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Analytics;
