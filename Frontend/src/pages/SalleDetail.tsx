import { useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArrowLeft, Edit, Users, Monitor, Calendar, MapPin, Building, Wifi, Projector } from "lucide-react";

const SalleDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();

  const mockSalle = {
    id: id,
    nom: "Salle A101",
    type: "Amphithéâtre",
    capacite: 150,
    surface: 200,
    batiment: "Bâtiment A",
    etage: "1er étage",
    site: "Campus Principal",
    statut: "Disponible",
    equipements: [
      { nom: "Vidéoprojecteur", quantite: 2, etat: "Bon" },
      { nom: "Tableau blanc", quantite: 3, etat: "Bon" },
      { nom: "Système audio", quantite: 1, etat: "Bon" },
      { nom: "Climatisation", quantite: 4, etat: "Bon" },
      { nom: "Wifi", quantite: 1, etat: "Bon" },
      { nom: "Prises électriques", quantite: 50, etat: "Bon" },
    ],
    planning: [
      { id: "1", jour: "Lundi", heureDebut: "08:00", heureFin: "10:00", cours: "Algorithmique L2", enseignant: "Dr. Martin" },
      { id: "2", jour: "Lundi", heureDebut: "14:00", heureFin: "16:00", cours: "Base de données L3", enseignant: "Prof. Bernard" },
      { id: "3", jour: "Mardi", heureDebut: "10:00", heureFin: "12:00", cours: "Programmation M1", enseignant: "Dr. Dupont" },
      { id: "4", jour: "Mercredi", heureDebut: "08:00", heureFin: "10:00", cours: "Réseaux L3", enseignant: "Prof. Leblanc" },
    ],
    reservations: [
      { id: "1", date: "2024-02-15", heureDebut: "14:00", heureFin: "18:00", evenement: "Conférence IA", organisateur: "Club Info" },
      { id: "2", date: "2024-02-20", heureDebut: "09:00", heureFin: "12:00", evenement: "Examen Final", organisateur: "Administration" },
    ],
  };

  const getStatutBadge = (statut: string) => {
    switch (statut) {
      case "Disponible":
        return <Badge className="bg-green-500">Disponible</Badge>;
      case "Occupée":
        return <Badge className="bg-red-500">Occupée</Badge>;
      case "Maintenance":
        return <Badge className="bg-yellow-500">En maintenance</Badge>;
      default:
        return <Badge variant="outline">{statut}</Badge>;
    }
  };

  const getTypeBadge = (type: string) => {
    switch (type) {
      case "Amphithéâtre":
        return <Badge variant="secondary">Amphithéâtre</Badge>;
      case "Salle TD":
        return <Badge variant="secondary">Salle TD</Badge>;
      case "Laboratoire":
        return <Badge variant="secondary">Laboratoire</Badge>;
      case "Salle informatique":
        return <Badge variant="secondary">Salle informatique</Badge>;
      default:
        return <Badge variant="outline">{type}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate("/salles")}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-foreground">{mockSalle.nom}</h1>
              {getTypeBadge(mockSalle.type)}
              {getStatutBadge(mockSalle.statut)}
            </div>
            <p className="text-muted-foreground">{mockSalle.batiment} - {mockSalle.etage}</p>
          </div>
        </div>
        <Button>
          <Edit className="mr-2 h-4 w-4" />
          Modifier
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Capacité</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockSalle.capacite} places</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Surface</CardTitle>
            <Building className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockSalle.surface} m²</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Équipements</CardTitle>
            <Monitor className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockSalle.equipements.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Site</CardTitle>
            <MapPin className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold">{mockSalle.site}</div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="equipements" className="space-y-4">
        <TabsList>
          <TabsTrigger value="equipements">Équipements</TabsTrigger>
          <TabsTrigger value="planning">Planning Hebdomadaire</TabsTrigger>
          <TabsTrigger value="reservations">Réservations</TabsTrigger>
        </TabsList>

        <TabsContent value="equipements" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Liste des équipements</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                {mockSalle.equipements.map((equip, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between rounded-lg border p-4"
                  >
                    <div className="flex items-center gap-3">
                      {equip.nom === "Vidéoprojecteur" && <Projector className="h-5 w-5 text-muted-foreground" />}
                      {equip.nom === "Wifi" && <Wifi className="h-5 w-5 text-muted-foreground" />}
                      {!["Vidéoprojecteur", "Wifi"].includes(equip.nom) && <Monitor className="h-5 w-5 text-muted-foreground" />}
                      <div>
                        <p className="font-medium">{equip.nom}</p>
                        <p className="text-sm text-muted-foreground">Quantité: {equip.quantite}</p>
                      </div>
                    </div>
                    <Badge variant={equip.etat === "Bon" ? "default" : "destructive"}>{equip.etat}</Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="planning" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                Planning de la semaine
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {mockSalle.planning.map((seance) => (
                  <div
                    key={seance.id}
                    className="flex items-center justify-between rounded-lg border p-4"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">{seance.jour}</Badge>
                        <span className="text-sm text-muted-foreground">
                          {seance.heureDebut} - {seance.heureFin}
                        </span>
                      </div>
                      <p className="font-medium mt-1">{seance.cours}</p>
                      <p className="text-sm text-muted-foreground">{seance.enseignant}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="reservations" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Réservations à venir</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {mockSalle.reservations.map((reservation) => (
                  <div
                    key={reservation.id}
                    className="flex items-center justify-between rounded-lg border p-4"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary">{new Date(reservation.date).toLocaleDateString('fr-FR')}</Badge>
                        <span className="text-sm text-muted-foreground">
                          {reservation.heureDebut} - {reservation.heureFin}
                        </span>
                      </div>
                      <p className="font-medium mt-1">{reservation.evenement}</p>
                      <p className="text-sm text-muted-foreground">Organisateur: {reservation.organisateur}</p>
                    </div>
                    <Button variant="outline" size="sm">Annuler</Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default SalleDetail;
