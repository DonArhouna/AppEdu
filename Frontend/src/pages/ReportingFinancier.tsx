import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { DollarSign, TrendingUp, AlertCircle, Users } from "lucide-react";

const ReportingFinancier = () => {
  // Données pour le graphique des encaissements mensuels
  const encaissementsMensuels = [
    { mois: "Jan", montant: 12500000 },
    { mois: "Fév", montant: 8900000 },
    { mois: "Mar", montant: 3200000 },
    { mois: "Avr", montant: 2100000 },
    { mois: "Mai", montant: 1800000 },
    { mois: "Juin", montant: 5600000 },
  ];

  // Données pour le graphique de répartition par type de frais
  const repartitionFrais = [
    { name: "Inscription", value: 4500000, color: "#8b5cf6" },
    { name: "Scolarité", value: 18000000, color: "#6366f1" },
    { name: "Examens", value: 3000000, color: "#3b82f6" },
    { name: "Autres", value: 900000, color: "#06b6d4" },
  ];

  // Données pour l'évolution du taux de recouvrement
  const tauxRecouvrement = [
    { mois: "Jan", taux: 95 },
    { mois: "Fév", taux: 92 },
    { mois: "Mar", taux: 88 },
    { mois: "Avr", taux: 85 },
    { mois: "Mai", taux: 82 },
    { mois: "Juin", taux: 79 },
  ];

  const totalEncaisse = 26400000;
  const totalAttendu = 33500000;
  const totalImpayes = 7100000;
  const tauxRecouvrementActuel = ((totalEncaisse / totalAttendu) * 100).toFixed(1);
  const nombreEtudiants = 156;
  const moyenneParEtudiant = Math.round(totalEncaisse / nombreEtudiants);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Reporting Financier</h1>
        <p className="text-muted-foreground mt-2">
          Analyse du chiffre d'affaires et du taux de recouvrement
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Chiffre d'Affaires</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalEncaisse.toLocaleString()} FCFA</div>
            <p className="text-xs text-muted-foreground">
              Sur {totalAttendu.toLocaleString()} FCFA attendus
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Taux de Recouvrement</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{tauxRecouvrementActuel}%</div>
            <p className="text-xs text-muted-foreground">
              -3% par rapport au mois dernier
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Impayés</CardTitle>
            <AlertCircle className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">
              {totalImpayes.toLocaleString()} FCFA
            </div>
            <p className="text-xs text-muted-foreground">
              À recouvrer
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Moyenne/Étudiant</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{moyenneParEtudiant.toLocaleString()} FCFA</div>
            <p className="text-xs text-muted-foreground">
              {nombreEtudiants} étudiants actifs
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Filtres de Période</CardTitle>
                <CardDescription>Sélectionnez la période d'analyse</CardDescription>
              </div>
              <div className="flex gap-4">
                <div className="space-y-2">
                  <Label htmlFor="annee">Année</Label>
                  <Select defaultValue="2024">
                    <SelectTrigger id="annee" className="w-32">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="2024">2024</SelectItem>
                      <SelectItem value="2023">2023</SelectItem>
                      <SelectItem value="2022">2022</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="periode">Période</Label>
                  <Select defaultValue="semestre1">
                    <SelectTrigger id="periode" className="w-40">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="annee">Année complète</SelectItem>
                      <SelectItem value="semestre1">Semestre 1</SelectItem>
                      <SelectItem value="semestre2">Semestre 2</SelectItem>
                      <SelectItem value="trimestre1">Trimestre 1</SelectItem>
                      <SelectItem value="trimestre2">Trimestre 2</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
          </CardHeader>
        </Card>
      </div>

      <Tabs defaultValue="encaissements" className="space-y-4">
        <TabsList>
          <TabsTrigger value="encaissements">Encaissements</TabsTrigger>
          <TabsTrigger value="repartition">Répartition</TabsTrigger>
          <TabsTrigger value="recouvrement">Recouvrement</TabsTrigger>
        </TabsList>

        <TabsContent value="encaissements" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Évolution des Encaissements Mensuels</CardTitle>
              <CardDescription>
                Montants encaissés par mois (en FCFA)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={encaissementsMensuels}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="mois" />
                  <YAxis />
                  <Tooltip 
                    formatter={(value: number) => `${value.toLocaleString()} FCFA`}
                  />
                  <Legend />
                  <Bar dataKey="montant" fill="#8b5cf6" name="Montant encaissé" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="repartition" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Répartition par Type de Frais</CardTitle>
              <CardDescription>
                Distribution des encaissements par catégorie
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <ResponsiveContainer width="100%" height={400}>
                  <PieChart>
                    <Pie
                      data={repartitionFrais}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                      outerRadius={120}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {repartitionFrais.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value: number) => `${value.toLocaleString()} FCFA`} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-4">
                  {repartitionFrais.map((item) => (
                    <div key={item.name} className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div
                          className="w-4 h-4 rounded"
                          style={{ backgroundColor: item.color }}
                        />
                        <span className="font-medium">{item.name}</span>
                      </div>
                      <div className="text-right">
                        <div className="font-bold">{item.value.toLocaleString()} FCFA</div>
                        <div className="text-sm text-muted-foreground">
                          {((item.value / totalEncaisse) * 100).toFixed(1)}%
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="recouvrement" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Évolution du Taux de Recouvrement</CardTitle>
              <CardDescription>
                Taux de recouvrement mensuel (en %)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={tauxRecouvrement}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="mois" />
                  <YAxis domain={[0, 100]} />
                  <Tooltip formatter={(value: number) => `${value}%`} />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="taux"
                    stroke="#8b5cf6"
                    strokeWidth={3}
                    name="Taux de recouvrement"
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default ReportingFinancier;
