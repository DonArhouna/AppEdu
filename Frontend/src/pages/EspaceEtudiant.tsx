import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Calendar, FileText, Download, BookOpen, AlertCircle } from "lucide-react";

const EspaceEtudiant = () => {
  // Mock student data
  const student = {
    name: "Sophie Martin",
    studentId: "ETU2024001",
    promotion: "Licence 3 Informatique",
    semester: "Semestre 6"
  };

  const emploiDuTemps = [
    { day: "Lundi", time: "08:00 - 10:00", subject: "Bases de Données", room: "Salle 201", teacher: "Prof. Dubois" },
    { day: "Lundi", time: "10:15 - 12:15", subject: "Programmation Web", room: "Lab Info 1", teacher: "Prof. Martin" },
    { day: "Mardi", time: "08:00 - 10:00", subject: "Réseaux", room: "Salle 105", teacher: "Prof. Bernard" },
    { day: "Mercredi", time: "14:00 - 16:00", subject: "Génie Logiciel", room: "Salle 303", teacher: "Prof. Lefebvre" },
  ];

  const notes = [
    { subject: "Bases de Données", note: 15.5, coef: 3, type: "Examen" },
    { subject: "Programmation Web", note: 16.0, coef: 2, type: "Projet" },
    { subject: "Réseaux", note: 14.0, coef: 2, type: "Examen" },
    { subject: "Génie Logiciel", note: 17.0, coef: 3, type: "Projet" },
  ];

  const moyenne = notes.reduce((acc, n) => acc + (n.note * n.coef), 0) / notes.reduce((acc, n) => acc + n.coef, 0);

  const absences = [
    { date: "2024-01-15", subject: "Bases de Données", status: "Justifiée", reason: "Certificat médical" },
    { date: "2024-01-20", subject: "Réseaux", status: "Non justifiée", reason: "-" },
    { date: "2024-02-05", subject: "Programmation Web", status: "Justifiée", reason: "Convocation administrative" },
  ];

  const factures = [
    { id: "FACT-2024-001", date: "2024-01-10", montant: 850000, statut: "Payée" },
    { id: "FACT-2024-002", date: "2024-02-10", montant: 850000, statut: "En attente" },
    { id: "FACT-2024-003", date: "2024-03-10", montant: 850000, statut: "En attente" },
  ];

  const ressources = [
    { title: "Cours - Modèle Relationnel", subject: "Bases de Données", type: "PDF", date: "2024-01-15" },
    { title: "TP - Requêtes SQL Avancées", subject: "Bases de Données", type: "PDF", date: "2024-01-20" },
    { title: "Cours - React & Redux", subject: "Programmation Web", type: "PDF", date: "2024-01-18" },
    { title: "TD - Protocoles TCP/IP", subject: "Réseaux", type: "PDF", date: "2024-01-22" },
  ];

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Espace Étudiant</h1>
          <p className="text-muted-foreground mt-2">
            Bienvenue {student.name} - {student.studentId}
          </p>
        </div>
        <div className="text-right">
          <p className="font-medium text-foreground">{student.promotion}</p>
          <p className="text-sm text-muted-foreground">{student.semester}</p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Moyenne Générale
            </CardTitle>
            <FileText className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {moyenne.toFixed(2)}/20
            </div>
            <p className="text-xs text-success mt-1">Bon résultat</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Absences
            </CardTitle>
            <AlertCircle className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {absences.length}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {absences.filter(a => a.status === "Non justifiée").length} non justifiée(s)
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Paiements
            </CardTitle>
            <FileText className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {factures.filter(f => f.statut === "Payée").length}/{factures.length}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Factures payées</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="emploi" className="space-y-4">
        <TabsList>
          <TabsTrigger value="emploi">
            <Calendar className="h-4 w-4 mr-2" />
            Emploi du Temps
          </TabsTrigger>
          <TabsTrigger value="notes">
            <FileText className="h-4 w-4 mr-2" />
            Notes
          </TabsTrigger>
          <TabsTrigger value="absences">
            <AlertCircle className="h-4 w-4 mr-2" />
            Absences
          </TabsTrigger>
          <TabsTrigger value="factures">
            <FileText className="h-4 w-4 mr-2" />
            Factures
          </TabsTrigger>
          <TabsTrigger value="ressources">
            <BookOpen className="h-4 w-4 mr-2" />
            Ressources
          </TabsTrigger>
        </TabsList>

        <TabsContent value="emploi" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Mon Emploi du Temps</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {emploiDuTemps.map((cours, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between border-b border-border pb-3 last:border-0"
                  >
                    <div>
                      <p className="font-medium text-foreground">{cours.subject}</p>
                      <p className="text-sm text-muted-foreground">
                        {cours.day} • {cours.time}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {cours.teacher} • {cours.room}
                      </p>
                    </div>
                    <Badge variant="outline">{cours.day}</Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notes" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Mes Notes</CardTitle>
              <Button variant="outline" size="sm">
                <Download className="h-4 w-4 mr-2" />
                Télécharger Bulletin
              </Button>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {notes.map((note, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between border-b border-border pb-3 last:border-0"
                  >
                    <div className="flex-1">
                      <p className="font-medium text-foreground">{note.subject}</p>
                      <p className="text-sm text-muted-foreground">
                        Coefficient {note.coef} • {note.type}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold text-foreground">{note.note}/20</p>
                    </div>
                  </div>
                ))}
                <div className="flex items-center justify-between pt-4 border-t-2 border-primary">
                  <p className="font-bold text-foreground">Moyenne Générale</p>
                  <p className="text-2xl font-bold text-primary">{moyenne.toFixed(2)}/20</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="absences" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Mes Absences</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {absences.map((absence, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between border-b border-border pb-3 last:border-0"
                  >
                    <div>
                      <p className="font-medium text-foreground">{absence.subject}</p>
                      <p className="text-sm text-muted-foreground">
                        {new Date(absence.date).toLocaleDateString("fr-FR")}
                      </p>
                      <p className="text-sm text-muted-foreground">{absence.reason}</p>
                    </div>
                    <Badge
                      variant={absence.status === "Justifiée" ? "default" : "destructive"}
                    >
                      {absence.status}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="factures" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Mes Factures</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {factures.map((facture) => (
                  <div
                    key={facture.id}
                    className="flex items-center justify-between border-b border-border pb-3 last:border-0"
                  >
                    <div>
                      <p className="font-medium text-foreground">{facture.id}</p>
                      <p className="text-sm text-muted-foreground">
                        {new Date(facture.date).toLocaleDateString("fr-FR")}
                      </p>
                      <p className="text-sm font-medium text-foreground">
                        {facture.montant.toLocaleString()} FCFA
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge
                        variant={facture.statut === "Payée" ? "default" : "secondary"}
                      >
                        {facture.statut}
                      </Badge>
                      <Button variant="outline" size="sm">
                        <Download className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="ressources" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Ressources Pédagogiques</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {ressources.map((ressource, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between border-b border-border pb-3 last:border-0"
                  >
                    <div className="flex items-start gap-3">
                      <BookOpen className="h-5 w-5 text-primary mt-1" />
                      <div>
                        <p className="font-medium text-foreground">{ressource.title}</p>
                        <p className="text-sm text-muted-foreground">
                          {ressource.subject}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {new Date(ressource.date).toLocaleDateString("fr-FR")}
                        </p>
                      </div>
                    </div>
                    <Button variant="outline" size="sm">
                      <Download className="h-4 w-4 mr-2" />
                      {ressource.type}
                    </Button>
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

export default EspaceEtudiant;
