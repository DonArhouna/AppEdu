import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Users, Calendar, Edit } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function PromotionDetail() {
  const { id } = useParams();

  const mockPromotion = {
    id: id,
    nom: "Promotion 2024-2025",
    annee: "2024-2025",
    dateDebut: "2024-09-01",
    dateFin: "2025-06-30",
    statut: "active",
    effectif: 250,
    filieres: [
      { nom: "Génie Logiciel", effectif: 80 },
      { nom: "Réseau & Télécom", effectif: 70 },
      { nom: "Informatique de Gestion", effectif: 100 },
    ],
  };

  const getStatutBadge = (statut: string) => {
    const variants: Record<string, "default" | "secondary" | "outline"> = {
      active: "default",
      terminee: "secondary",
      "a-venir": "outline",
    };
    return variants[statut] || "secondary";
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link to="/promotions">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold">{mockPromotion.nom}</h1>
            <p className="text-muted-foreground">Année académique {mockPromotion.annee}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Badge variant={getStatutBadge(mockPromotion.statut)}>
            {mockPromotion.statut === "active" ? "Active" : 
             mockPromotion.statut === "terminee" ? "Terminée" : "À venir"}
          </Badge>
          <Button>
            <Edit className="h-4 w-4 mr-2" />
            Modifier
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Effectif Total</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockPromotion.effectif}</div>
            <p className="text-xs text-muted-foreground">Étudiants inscrits</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Date de début</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{new Date(mockPromotion.dateDebut).toLocaleDateString()}</div>
            <p className="text-xs text-muted-foreground">Début année académique</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Date de fin</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{new Date(mockPromotion.dateFin).toLocaleDateString()}</div>
            <p className="text-xs text-muted-foreground">Fin année académique</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="filieres" className="space-y-4">
        <TabsList>
          <TabsTrigger value="filieres">Filières</TabsTrigger>
          <TabsTrigger value="statistiques">Statistiques</TabsTrigger>
        </TabsList>

        <TabsContent value="filieres" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Filières de la promotion</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {mockPromotion.filieres.map((filiere, index) => (
                  <div key={index} className="flex justify-between items-center p-4 border rounded-lg">
                    <div>
                      <p className="font-semibold">{filiere.nom}</p>
                      <p className="text-sm text-muted-foreground">{filiere.effectif} étudiants</p>
                    </div>
                    <Button variant="outline" size="sm">Voir les détails</Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="statistiques" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Statistiques de la promotion</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between items-center p-4 border rounded-lg">
                  <span className="font-semibold">Taux de présence</span>
                  <Badge>92%</Badge>
                </div>
                <div className="flex justify-between items-center p-4 border rounded-lg">
                  <span className="font-semibold">Moyenne générale</span>
                  <Badge>14.5/20</Badge>
                </div>
                <div className="flex justify-between items-center p-4 border rounded-lg">
                  <span className="font-semibold">Taux de réussite</span>
                  <Badge>88%</Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
