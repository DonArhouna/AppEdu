import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Settings, Calendar, BookOpen, Plus, Edit, Trash2 } from "lucide-react";

const Parametrage = () => {
  const anneesUniversitaires = [
    { id: 1, annee: "2023-2024", dateDebut: "2023-09-01", dateFin: "2024-06-30", statut: "Terminée" },
    { id: 2, annee: "2024-2025", dateDebut: "2024-09-01", dateFin: "2025-06-30", statut: "En cours" },
    { id: 3, annee: "2025-2026", dateDebut: "2025-09-01", dateFin: "2026-06-30", statut: "Planifiée" },
  ];

  const semestres = [
    { id: 1, nom: "Semestre 1", annee: "2024-2025", dateDebut: "2024-09-01", dateFin: "2025-01-15", statut: "Terminé" },
    { id: 2, nom: "Semestre 2", annee: "2024-2025", dateDebut: "2025-01-20", dateFin: "2025-06-30", statut: "En cours" },
    { id: 3, nom: "Semestre 1", annee: "2025-2026", dateDebut: "2025-09-01", dateFin: "2026-01-15", statut: "Planifié" },
  ];

  const sessionsExamen = [
    { id: 1, nom: "Session Normale - Semestre 1", date: "2025-01-10 - 2025-01-20", type: "Normale", statut: "Terminée" },
    { id: 2, nom: "Session Rattrapage - Semestre 1", date: "2025-02-01 - 2025-02-10", type: "Rattrapage", statut: "Terminée" },
    { id: 3, nom: "Session Normale - Semestre 2", date: "2025-06-15 - 2025-06-25", type: "Normale", statut: "Planifiée" },
    { id: 4, nom: "Session Rattrapage - Semestre 2", date: "2025-07-05 - 2025-07-15", type: "Rattrapage", statut: "Planifiée" },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Paramétrage Général</h1>
        <p className="text-muted-foreground mt-2">
          Configuration des paramètres de l'établissement
        </p>
      </div>

      <Tabs defaultValue="etablissement" className="space-y-4">
        <TabsList>
          <TabsTrigger value="etablissement">
            <Settings className="h-4 w-4 mr-2" />
            Établissement
          </TabsTrigger>
          <TabsTrigger value="annees">
            <Calendar className="h-4 w-4 mr-2" />
            Années Universitaires
          </TabsTrigger>
          <TabsTrigger value="semestres">
            <BookOpen className="h-4 w-4 mr-2" />
            Semestres
          </TabsTrigger>
          <TabsTrigger value="examens">
            <BookOpen className="h-4 w-4 mr-2" />
            Sessions d'Examen
          </TabsTrigger>
        </TabsList>

        <TabsContent value="etablissement" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Informations Générales</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="nom-etablissement">Nom de l'Établissement</Label>
                  <Input
                    id="nom-etablissement"
                    defaultValue="Institut Supérieur de Technologie"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="sigle">Sigle</Label>
                  <Input id="sigle" defaultValue="IST" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email Institutionnel</Label>
                  <Input id="email" type="email" defaultValue="contact@ist.edu" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="telephone">Téléphone</Label>
                  <Input id="telephone" defaultValue="+225 XX XX XX XX XX" />
                </div>
                <div className="space-y-2 md:col-span-2">
                  <Label htmlFor="adresse">Adresse Complète</Label>
                  <Input
                    id="adresse"
                    defaultValue="Boulevard de la République, Abidjan, Côte d'Ivoire"
                  />
                </div>
              </div>
              <Button>Enregistrer les Modifications</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Paramètres Académiques</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="note-passage">Note de Passage (sur 20)</Label>
                  <Input id="note-passage" type="number" defaultValue="10" min="0" max="20" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="taux-presence">Taux de Présence Minimum (%)</Label>
                  <Input id="taux-presence" type="number" defaultValue="75" min="0" max="100" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="credits-validation">Crédits pour Validation</Label>
                  <Input id="credits-validation" type="number" defaultValue="60" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="systeme-notation">Système de Notation</Label>
                  <Select defaultValue="20">
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="20">Sur 20</SelectItem>
                      <SelectItem value="100">Sur 100</SelectItem>
                      <SelectItem value="letter">Lettres (A-F)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <Button>Enregistrer les Paramètres</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Nomenclature par Défaut (Matricule)</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="format-matricule">Format de Génération (Si non défini par la filière)</Label>
                <div className="flex gap-2">
                  <Input id="format-matricule" defaultValue="{ANNEE}-{FILIERE}-{SEQ}" />
                  <Button variant="secondary">Tester</Button>
                </div>
                <p className="text-sm text-muted-foreground mt-2">
                  Chaque filière peut avoir sa propre nomenclature dans le menu <b>Filières</b>.
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="seq-actuelle">Séquence Actuelle par défaut</Label>
                <Input id="seq-actuelle" type="number" defaultValue="1" className="max-w-[200px]" />
              </div>
              <Button>Sauvegarder la Nomenclature</Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="annees" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Années Universitaires</CardTitle>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Nouvelle Année
              </Button>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Année</TableHead>
                    <TableHead>Date de Début</TableHead>
                    <TableHead>Date de Fin</TableHead>
                    <TableHead>Statut</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {anneesUniversitaires.map((annee) => (
                    <TableRow key={annee.id}>
                      <TableCell className="font-medium">{annee.annee}</TableCell>
                      <TableCell>
                        {new Date(annee.dateDebut).toLocaleDateString("fr-FR")}
                      </TableCell>
                      <TableCell>
                        {new Date(annee.dateFin).toLocaleDateString("fr-FR")}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            annee.statut === "En cours"
                              ? "default"
                              : annee.statut === "Terminée"
                              ? "secondary"
                              : "outline"
                          }
                        >
                          {annee.statut}
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
        </TabsContent>

        <TabsContent value="semestres" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Semestres</CardTitle>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Nouveau Semestre
              </Button>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Semestre</TableHead>
                    <TableHead>Année Universitaire</TableHead>
                    <TableHead>Date de Début</TableHead>
                    <TableHead>Date de Fin</TableHead>
                    <TableHead>Statut</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {semestres.map((semestre) => (
                    <TableRow key={semestre.id}>
                      <TableCell className="font-medium">{semestre.nom}</TableCell>
                      <TableCell>{semestre.annee}</TableCell>
                      <TableCell>
                        {new Date(semestre.dateDebut).toLocaleDateString("fr-FR")}
                      </TableCell>
                      <TableCell>
                        {new Date(semestre.dateFin).toLocaleDateString("fr-FR")}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            semestre.statut === "En cours"
                              ? "default"
                              : semestre.statut === "Terminé"
                              ? "secondary"
                              : "outline"
                          }
                        >
                          {semestre.statut}
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
        </TabsContent>

        <TabsContent value="examens" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Sessions d'Examen</CardTitle>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Nouvelle Session
              </Button>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Nom de la Session</TableHead>
                    <TableHead>Période</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Statut</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sessionsExamen.map((session) => (
                    <TableRow key={session.id}>
                      <TableCell className="font-medium">{session.nom}</TableCell>
                      <TableCell>{session.date}</TableCell>
                      <TableCell>
                        <Badge variant={session.type === "Normale" ? "default" : "secondary"}>
                          {session.type}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            session.statut === "Terminée" ? "secondary" : "outline"
                          }
                        >
                          {session.statut}
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
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Parametrage;
