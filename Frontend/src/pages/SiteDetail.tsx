import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Users, MapPin, Building2, Edit } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export default function SiteDetail() {
  const { id } = useParams();

  const mockSite = {
    id: id,
    nom: "Site Principal A",
    campus: "Campus Principal",
    adresse: "123 Rue de l'Université, Ville",
    superficie: "5000 m²",
    capacite: 500,
    effectifActuel: 480,
    batiments: [
      { nom: "Bâtiment A", etages: 4, salles: 20, capacite: 200 },
      { nom: "Bâtiment B", etages: 3, salles: 15, capacite: 180 },
      { nom: "Bâtiment C", etages: 2, salles: 10, capacite: 120 },
    ],
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link to="/sites">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold">{mockSite.nom}</h1>
            <p className="text-muted-foreground">
              <MapPin className="h-4 w-4 inline mr-1" />
              {mockSite.adresse}
            </p>
          </div>
        </div>
        <Button>
          <Edit className="h-4 w-4 mr-2" />
          Modifier
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Capacité</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockSite.capacite}</div>
            <p className="text-xs text-muted-foreground">Places disponibles</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Effectif Actuel</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockSite.effectifActuel}</div>
            <p className="text-xs text-muted-foreground">
              {Math.round((mockSite.effectifActuel / mockSite.capacite) * 100)}% occupé
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Superficie</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockSite.superficie}</div>
            <p className="text-xs text-muted-foreground">Surface totale</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Bâtiments</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockSite.batiments.length}</div>
            <p className="text-xs text-muted-foreground">Sur le site</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="batiments" className="space-y-4">
        <TabsList>
          <TabsTrigger value="batiments">Bâtiments</TabsTrigger>
          <TabsTrigger value="info">Informations</TabsTrigger>
        </TabsList>

        <TabsContent value="batiments" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Liste des bâtiments</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Nom</TableHead>
                    <TableHead>Étages</TableHead>
                    <TableHead>Salles</TableHead>
                    <TableHead>Capacité</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {mockSite.batiments.map((batiment, index) => (
                    <TableRow key={index}>
                      <TableCell className="font-medium">{batiment.nom}</TableCell>
                      <TableCell>{batiment.etages}</TableCell>
                      <TableCell>{batiment.salles}</TableCell>
                      <TableCell>
                        <Badge variant="secondary">{batiment.capacite} places</Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="info" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Informations générales</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h3 className="font-semibold mb-2">Campus</h3>
                <Badge>{mockSite.campus}</Badge>
              </div>
              <div>
                <h3 className="font-semibold mb-2">Adresse complète</h3>
                <p className="text-muted-foreground">{mockSite.adresse}</p>
              </div>
              <div>
                <h3 className="font-semibold mb-2">Taux d'occupation</h3>
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-secondary h-2 rounded-full overflow-hidden">
                    <div 
                      className="bg-primary h-full"
                      style={{ width: `${(mockSite.effectifActuel / mockSite.capacite) * 100}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium">
                    {Math.round((mockSite.effectifActuel / mockSite.capacite) * 100)}%
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
