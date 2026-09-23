import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { CalendarDays, FileText, Upload, User, Clock, CheckCircle2, BookOpen } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";

export default function PortailEnseignant() {
  const [cahierTexte, setCahierTexte] = useState([
    {
      id: "1",
      date: "2026-08-28",
      heure: "08:00 - 10:00 (2h)",
      matiere: "Programmation Web React",
      classe: "L3 Informatique",
      salle: "A204",
      contenu: "Chapitre 4: Gestion d'état avancée avec TanStack Query & Context API",
      statut: "Émargé & Validé",
    },
    {
      id: "2",
      date: "2026-08-27",
      heure: "14:00 - 16:00 (2h)",
      matiere: "Développement Mobile",
      classe: "M1 Génie Logiciel",
      salle: "B105",
      contenu: "Chapitre 2: Layouts réactifs & animations",
      statut: "Émargé & Validé",
    },
  ]);

  const [nouveauCours, setNouveauCours] = useState({
    matiere: "Programmation Web React",
    classe: "L3 Informatique",
    heures: "2",
    contenu: "",
  });

  const handleEmarger = (e: React.FormEvent) => {
    e.preventDefault();
    if (!nouveauCours.contenu) {
      toast.error("Veuillez renseigner le contenu enseigné lors de la séance.");
      return;
    }

    const item = {
      id: String(Date.now()),
      date: new Date().toISOString().split("T")[0],
      heure: `10:00 - 12:00 (${nouveauCours.heures}h)`,
      matiere: nouveauCours.matiere,
      classe: nouveauCours.classe,
      salle: "A204",
      contenu: nouveauCours.contenu,
      statut: "Émargé & Validé",
    };

    setCahierTexte([item, ...cahierTexte]);
    toast.success("Émargement et Cahier de texte enregistrés avec succès !");
    setNouveauCours({ ...nouveauCours, contenu: "" });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Portail Enseignant</h1>
          <p className="text-muted-foreground">Espace personnel et suivi des heures de cours</p>
        </div>
        <div className="flex items-center gap-3 bg-card p-2 px-4 rounded-xl border">
          <User className="h-5 w-5 text-primary" />
          <div className="text-right">
            <div className="font-semibold text-sm">Mamadou Diallo</div>
            <div className="text-xs text-muted-foreground">Professeur Vacataire • 24h/mois</div>
          </div>
        </div>
      </div>

      <Tabs defaultValue="cahier-texte" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="cahier-texte">
            <BookOpen className="h-4 w-4 mr-2" /> Cahier de Texte & Émargement
          </TabsTrigger>
          <TabsTrigger value="emploi-temps">
            <CalendarDays className="h-4 w-4 mr-2" /> Emploi du Temps
          </TabsTrigger>
          <TabsTrigger value="notes">
            <FileText className="h-4 w-4 mr-2" /> Saisie des Notes
          </TabsTrigger>
          <TabsTrigger value="ressources">
            <Upload className="h-4 w-4 mr-2" /> Ressources Péda.
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Cahier de Texte & Émargement */}
        <TabsContent value="cahier-texte" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5 text-emerald-500" />
                Émargement de Séance & Cahier de Texte
              </CardTitle>
              <CardDescription>
                Déclarez le contenu du cours dispensé pour validation des heures vacataires
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleEmarger} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label>Matière</Label>
                    <Input value={nouveauCours.matiere} disabled />
                  </div>
                  <div className="space-y-2">
                    <Label>Classe / Promotion</Label>
                    <Input value={nouveauCours.classe} disabled />
                  </div>
                  <div className="space-y-2">
                    <Label>Volume Horaire Effectué</Label>
                    <Input
                      value={`${nouveauCours.heures} Heures`}
                      onChange={(e) => setNouveauCours({ ...nouveauCours, heures: e.target.value })}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="contenu">Contenu & Thème Abordé *</Label>
                  <Input
                    id="contenu"
                    required
                    placeholder="Ex: Chapitre 3 - Modélisation des entités et clés étrangères PostgreSQL..."
                    value={nouveauCours.contenu}
                    onChange={(e) => setNouveauCours({ ...nouveauCours, contenu: e.target.value })}
                  />
                </div>

                <Button type="submit" className="bg-emerald-600 hover:bg-emerald-700 text-white">
                  <CheckCircle2 className="h-4 w-4 mr-2" /> Valider mon Émargement (2 Heures)
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* History */}
          <Card>
            <CardHeader>
              <CardTitle>Historique des Émargements de la Session</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {cahierTexte.map((item) => (
                <div key={item.id} className="p-4 rounded-xl border bg-muted/30 flex flex-col sm:flex-row justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm text-foreground">{item.matiere}</span>
                      <Badge variant="outline">{item.classe}</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">{item.contenu}</p>
                    <p className="text-[11px] text-muted-foreground font-mono">
                      Date: {item.date} • Horaires: {item.heure} • Salle: {item.salle}
                    </p>
                  </div>
                  <Badge className="bg-emerald-600 text-white h-6 self-start">{item.statut}</Badge>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 2: Emploi du Temps */}
        <TabsContent value="emploi-temps" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Mon Emploi du Temps</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"].map((jour) => (
                  <div key={jour} className="p-3 bg-muted/40 rounded-lg flex justify-between items-center text-xs">
                    <span className="font-bold">{jour}</span>
                    <span>Programmation Web - L3 Info (08h-10h) • Salle A204</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 3: Notes */}
        <TabsContent value="notes" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Saisie des Notes</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">Accès direct aux grilles d'évaluation de vos cours.</p>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 4: Ressources */}
        <TabsContent value="ressources" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Ressources Pédagogiques</CardTitle>
            </CardHeader>
            <CardContent>
              <Button className="w-full">
                <Upload className="h-4 w-4 mr-2" /> Déposer un Support de Cours PDF
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
