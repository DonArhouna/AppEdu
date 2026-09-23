import { useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ArrowLeft, BookOpen, Clock, Award, Users } from "lucide-react";

export default function MatiereDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const matiere = {
    id: id || "1",
    code: "INF301",
    nom: "Programmation Web",
    type: "UE",
    credits: 6,
    coefficient: 3,
    heures: 45,
    filiere: "Informatique",
    niveau: "L3",
    semestre: "S5",
    enseignant: "Mamadou Diallo",
    description: "Ce cours couvre les technologies web modernes incluant HTML5, CSS3, JavaScript et les frameworks populaires.",
    prerequis: ["Algorithmique", "Programmation orientée objet"],
    objectifs: [
      "Maîtriser les langages web fondamentaux",
      "Développer des applications web interactives",
      "Comprendre les architectures client-serveur",
    ],
    etudiants: 35,
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/matieres")}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-foreground">{matiere.nom}</h1>
            <Badge className="bg-primary text-primary-foreground">{matiere.type}</Badge>
          </div>
          <p className="text-muted-foreground">
            {matiere.code} • {matiere.filiere} - {matiere.niveau} - {matiere.semestre}
          </p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <Card className="md:col-span-1">
          <CardHeader>
            <CardTitle>Informations</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="text-sm font-medium text-muted-foreground">Code</div>
              <div className="text-lg font-mono">{matiere.code}</div>
            </div>
            <Separator />
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-2">Crédits</div>
              <div className="flex items-center gap-2">
                <Award className="h-4 w-4 text-primary" />
                <span className="text-lg font-semibold">{matiere.credits} ECTS</span>
              </div>
            </div>
            <Separator />
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-2">Coefficient</div>
              <div className="text-lg font-semibold">{matiere.coefficient}</div>
            </div>
            <Separator />
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-2">Volume horaire</div>
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-secondary" />
                <span className="text-lg font-semibold">{matiere.heures}h</span>
              </div>
            </div>
            <Separator />
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-2">Enseignant</div>
              <div className="flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-muted-foreground" />
                <span>{matiere.enseignant}</span>
              </div>
            </div>
            <Separator />
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-2">Étudiants inscrits</div>
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4 text-muted-foreground" />
                <span className="text-lg font-semibold">{matiere.etudiants}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Description du cours</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <h3 className="font-semibold mb-2">Présentation</h3>
              <p className="text-muted-foreground">{matiere.description}</p>
            </div>

            <Separator />

            <div>
              <h3 className="font-semibold mb-3">Prérequis</h3>
              <ul className="space-y-2">
                {matiere.prerequis.map((prerequis, index) => (
                  <li key={index} className="flex items-center gap-2">
                    <div className="h-1.5 w-1.5 rounded-full bg-primary" />
                    <span className="text-muted-foreground">{prerequis}</span>
                  </li>
                ))}
              </ul>
            </div>

            <Separator />

            <div>
              <h3 className="font-semibold mb-3">Objectifs pédagogiques</h3>
              <ul className="space-y-2">
                {matiere.objectifs.map((objectif, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <div className="h-1.5 w-1.5 rounded-full bg-secondary mt-2" />
                    <span className="text-muted-foreground">{objectif}</span>
                  </li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
