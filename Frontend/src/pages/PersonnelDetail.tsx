import { useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArrowLeft, Mail, Phone, Calendar, Building2, BookOpen, Users } from "lucide-react";

export default function PersonnelDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  // Mock data
  const personnel = {
    id: id || "1",
    nom: "Diallo",
    prenom: "Mamadou",
    email: "m.diallo@ecole.sn",
    telephone: "+221 77 123 4567",
    role: "professeur",
    departement: "Informatique",
    specialite: "Développement Web & Mobile",
    dateEmbauche: "2020-09-01",
    statut: "actif",
    adresse: "Dakar, Sénégal",
    diplomes: ["Doctorat en Informatique", "Master en Génie Logiciel"],
    matieres: ["Programmation Web", "Développement Mobile", "Base de données"],
    classes: ["L3 Informatique", "M1 Génie Logiciel"],
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/personnel")}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold text-foreground">
            {personnel.prenom} {personnel.nom}
          </h1>
          <p className="text-muted-foreground">{personnel.specialite}</p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <Card className="md:col-span-1">
          <CardHeader>
            <CardTitle>Informations Générales</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="text-sm font-medium text-muted-foreground">Rôle</div>
              <Badge className="mt-1 bg-secondary text-secondary-foreground">Professeur</Badge>
            </div>
            <Separator />
            <div>
              <div className="text-sm font-medium text-muted-foreground">Statut</div>
              <Badge className="mt-1 bg-success text-success-foreground">Actif</Badge>
            </div>
            <Separator />
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-2">Contact</div>
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm">
                  <Mail className="h-4 w-4 text-muted-foreground" />
                  <span>{personnel.email}</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <Phone className="h-4 w-4 text-muted-foreground" />
                  <span>{personnel.telephone}</span>
                </div>
              </div>
            </div>
            <Separator />
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-2">Département</div>
              <div className="flex items-center gap-2 text-sm">
                <Building2 className="h-4 w-4 text-muted-foreground" />
                <span>{personnel.departement}</span>
              </div>
            </div>
            <Separator />
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-2">Date d'embauche</div>
              <div className="flex items-center gap-2 text-sm">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <span>{new Date(personnel.dateEmbauche).toLocaleDateString("fr-FR")}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Détails du Profil</CardTitle>
            <CardDescription>Informations académiques et professionnelles</CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="diplomes" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="diplomes">Diplômes</TabsTrigger>
                <TabsTrigger value="matieres">Matières</TabsTrigger>
                <TabsTrigger value="classes">Classes</TabsTrigger>
              </TabsList>
              <TabsContent value="diplomes" className="space-y-4 mt-4">
                <div className="space-y-3">
                  {personnel.diplomes.map((diplome, index) => (
                    <Card key={index} className="border-l-4 border-l-primary">
                      <CardContent className="pt-4">
                        <div className="flex items-start gap-3">
                          <BookOpen className="h-5 w-5 text-primary mt-1" />
                          <div>
                            <div className="font-medium">{diplome}</div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </TabsContent>
              <TabsContent value="matieres" className="space-y-4 mt-4">
                <div className="grid gap-3 sm:grid-cols-2">
                  {personnel.matieres.map((matiere, index) => (
                    <Card key={index}>
                      <CardContent className="pt-4">
                        <div className="flex items-center gap-2">
                          <BookOpen className="h-4 w-4 text-secondary" />
                          <span className="font-medium">{matiere}</span>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </TabsContent>
              <TabsContent value="classes" className="space-y-4 mt-4">
                <div className="space-y-3">
                  {personnel.classes.map((classe, index) => (
                    <Card key={index}>
                      <CardContent className="pt-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Users className="h-4 w-4 text-primary" />
                            <span className="font-medium">{classe}</span>
                          </div>
                          <Badge variant="outline">35 étudiants</Badge>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
