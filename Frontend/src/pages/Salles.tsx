import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, Edit, Trash2, Building, Search } from "lucide-react";

const Salles = () => {
  const [searchTerm, setSearchTerm] = useState("");

  const salles = [
    {
      id: 1,
      nom: "Salle A101",
      campus: "Campus Principal",
      batiment: "Bâtiment A",
      capacite: 50,
      type: "Cours magistral",
      equipements: ["Projecteur", "Tableau", "Climatisation"],
      statut: "Disponible",
    },
    {
      id: 2,
      nom: "Lab Info 1",
      campus: "Campus Principal",
      batiment: "Bâtiment B",
      capacite: 30,
      type: "Laboratoire",
      equipements: ["30 PC", "Projecteur", "Réseau"],
      statut: "Occupée",
    },
    {
      id: 3,
      nom: "Salle C201",
      campus: "Campus Principal",
      batiment: "Bâtiment C",
      capacite: 80,
      type: "Amphithéâtre",
      equipements: ["Projecteur", "Sono", "Climatisation", "Wifi"],
      statut: "Disponible",
    },
    {
      id: 4,
      nom: "Salle TD 12",
      campus: "Campus Cocody",
      batiment: "Bâtiment D",
      capacite: 35,
      type: "TD",
      equipements: ["Tableau", "Climatisation"],
      statut: "Maintenance",
    },
    {
      id: 5,
      nom: "Amphi 500",
      campus: "Campus Principal",
      batiment: "Bâtiment E",
      capacite: 500,
      type: "Amphithéâtre",
      equipements: ["Double Projecteur", "Sono", "Enregistrement", "Climatisation"],
      statut: "Disponible",
    },
    {
      id: 6,
      nom: "Lab Chimie 1",
      campus: "Campus Sciences",
      batiment: "Bâtiment F",
      capacite: 25,
      type: "Laboratoire",
      equipements: ["Paillasses", "Hotte", "Douche sécurité"],
      statut: "Disponible",
    },
  ];

  const filteredSalles = salles.filter(
    (salle) =>
      salle.nom.toLowerCase().includes(searchTerm.toLowerCase()) ||
      salle.campus.toLowerCase().includes(searchTerm.toLowerCase()) ||
      salle.batiment.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const stats = [
    { label: "Total Salles", value: salles.length, color: "primary" },
    { label: "Disponibles", value: salles.filter((s) => s.statut === "Disponible").length, color: "default" },
    { label: "Occupées", value: salles.filter((s) => s.statut === "Occupée").length, color: "secondary" },
    { label: "Maintenance", value: salles.filter((s) => s.statut === "Maintenance").length, color: "destructive" },
  ];

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Gestion des Salles</h1>
          <p className="text-muted-foreground mt-2">
            Gérez les salles de classe et laboratoires
          </p>
        </div>
        <Dialog>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Nouvelle Salle
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Ajouter une nouvelle salle</DialogTitle>
              <DialogDescription>
                Renseignez les informations de la salle
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="nom">Nom de la Salle *</Label>
                  <Input id="nom" placeholder="Ex: Salle A101" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="capacite">Capacité *</Label>
                  <Input id="capacite" type="number" placeholder="50" />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="campus">Campus *</Label>
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="Sélectionner" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="principal">Campus Principal</SelectItem>
                      <SelectItem value="cocody">Campus Cocody</SelectItem>
                      <SelectItem value="sciences">Campus Sciences</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="batiment">Bâtiment *</Label>
                  <Input id="batiment" placeholder="Ex: Bâtiment A" />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="type">Type de Salle *</Label>
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="Sélectionner" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="cours">Cours magistral</SelectItem>
                      <SelectItem value="td">TD</SelectItem>
                      <SelectItem value="amphi">Amphithéâtre</SelectItem>
                      <SelectItem value="labo">Laboratoire</SelectItem>
                      <SelectItem value="bureau">Bureau</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="statut">Statut *</Label>
                  <Select defaultValue="disponible">
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="disponible">Disponible</SelectItem>
                      <SelectItem value="occupee">Occupée</SelectItem>
                      <SelectItem value="maintenance">Maintenance</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="equipements">Équipements</Label>
                <Input
                  id="equipements"
                  placeholder="Ex: Projecteur, Tableau, Climatisation (séparés par des virgules)"
                />
              </div>

              <Button className="w-full">Créer la Salle</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid gap-6 md:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <Building className="h-5 w-5 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-foreground">{stat.value}</div>
              <p className="text-sm text-muted-foreground">{stat.label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Liste des Salles</CardTitle>
            <div className="relative w-64">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Rechercher une salle..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-8"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nom</TableHead>
                <TableHead>Campus</TableHead>
                <TableHead>Bâtiment</TableHead>
                <TableHead>Capacité</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Équipements</TableHead>
                <TableHead>Statut</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredSalles.map((salle) => (
                <TableRow key={salle.id}>
                  <TableCell className="font-medium">{salle.nom}</TableCell>
                  <TableCell>{salle.campus}</TableCell>
                  <TableCell>{salle.batiment}</TableCell>
                  <TableCell>{salle.capacite} places</TableCell>
                  <TableCell>
                    <Badge variant="outline">{salle.type}</Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {salle.equipements.slice(0, 2).map((eq, idx) => (
                        <Badge key={idx} variant="secondary" className="text-xs">
                          {eq}
                        </Badge>
                      ))}
                      {salle.equipements.length > 2 && (
                        <Badge variant="secondary" className="text-xs">
                          +{salle.equipements.length - 2}
                        </Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        salle.statut === "Disponible"
                          ? "default"
                          : salle.statut === "Occupée"
                          ? "secondary"
                          : "destructive"
                      }
                    >
                      {salle.statut}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button variant="ghost" size="sm">
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="sm">
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
};

export default Salles;
