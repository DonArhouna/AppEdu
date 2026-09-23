import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { Calendar, AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import { toast } from "sonner";

export default function Absences() {
  const [presences, setPresences] = useState([
    { id: "1", etudiant: "Amadou Ba", matricule: "ET2024001", present: true, justifie: false },
    { id: "2", etudiant: "Fatou Sarr", matricule: "ET2024002", present: true, justifie: false },
    { id: "3", etudiant: "Ibrahima Diop", matricule: "ET2024003", present: false, justifie: false },
    { id: "4", etudiant: "Awa Ndiaye", matricule: "ET2024004", present: true, justifie: false },
    { id: "5", etudiant: "Moussa Fall", matricule: "ET2024005", present: false, justifie: true },
  ]);

  const handlePresenceChange = (id: string, present: boolean) => {
    setPresences(presences.map((p) => (p.id === id ? { ...p, present } : p)));
  };

  const handleJustificationChange = (id: string, justifie: boolean) => {
    setPresences(presences.map((p) => (p.id === id ? { ...p, justifie } : p)));
  };

  const enregistrerPresences = () => {
    toast.success("Présences enregistrées avec succès");
  };

  const stats = {
    presents: presences.filter((p) => p.present).length,
    absents: presences.filter((p) => !p.present).length,
    justifies: presences.filter((p) => !p.present && p.justifie).length,
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Suivi des Absences</h1>
          <p className="text-muted-foreground">Gestion des présences étudiantes</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-muted-foreground">Présents</div>
                <div className="text-3xl font-bold text-success">{stats.presents}</div>
              </div>
              <CheckCircle2 className="h-10 w-10 text-success" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-muted-foreground">Absents</div>
                <div className="text-3xl font-bold text-destructive">{stats.absents}</div>
              </div>
              <XCircle className="h-10 w-10 text-destructive" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-muted-foreground">Justifiés</div>
                <div className="text-3xl font-bold text-warning">{stats.justifies}</div>
              </div>
              <AlertTriangle className="h-10 w-10 text-warning" />
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Séance</CardTitle>
          <CardDescription>Sélectionner la matière et la date</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col md:flex-row gap-4">
            <Select defaultValue="inf301">
              <SelectTrigger className="w-full md:w-[250px]">
                <SelectValue placeholder="Matière" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="inf301">INF301 - Programmation Web</SelectItem>
                <SelectItem value="inf302">INF302 - Base de données</SelectItem>
                <SelectItem value="inf303">INF303 - Algorithmique</SelectItem>
              </SelectContent>
            </Select>
            <Select defaultValue="l3">
              <SelectTrigger className="w-full md:w-[150px]">
                <SelectValue placeholder="Niveau" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="l1">L1</SelectItem>
                <SelectItem value="l2">L2</SelectItem>
                <SelectItem value="l3">L3</SelectItem>
              </SelectContent>
            </Select>
            <div className="flex items-center gap-2 px-3 py-2 border border-border rounded-md">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm">{new Date().toLocaleDateString("fr-FR")}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Liste de Présence</CardTitle>
          <CardDescription>L3 Informatique - Programmation Web</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border border-border">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/50">
                  <TableHead>Matricule</TableHead>
                  <TableHead>Étudiant</TableHead>
                  <TableHead className="text-center">Présent</TableHead>
                  <TableHead className="text-center">Absence Justifiée</TableHead>
                  <TableHead>Statut</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {presences.map((p) => (
                  <TableRow key={p.id} className="hover:bg-accent/50">
                    <TableCell className="font-mono text-sm">{p.matricule}</TableCell>
                    <TableCell className="font-medium">{p.etudiant}</TableCell>
                    <TableCell className="text-center">
                      <div className="flex justify-center">
                        <Checkbox
                          checked={p.present}
                          onCheckedChange={(checked) => handlePresenceChange(p.id, checked as boolean)}
                        />
                      </div>
                    </TableCell>
                    <TableCell className="text-center">
                      <div className="flex justify-center">
                        <Checkbox
                          checked={p.justifie}
                          disabled={p.present}
                          onCheckedChange={(checked) =>
                            handleJustificationChange(p.id, checked as boolean)
                          }
                        />
                      </div>
                    </TableCell>
                    <TableCell>
                      {p.present ? (
                        <Badge className="bg-success text-success-foreground">Présent</Badge>
                      ) : p.justifie ? (
                        <Badge className="bg-warning text-warning-foreground">Absent Justifié</Badge>
                      ) : (
                        <Badge className="bg-destructive text-destructive-foreground">Absent</Badge>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <div className="flex justify-end mt-4">
            <Button onClick={enregistrerPresences} className="bg-primary hover:bg-primary-hover">
              Enregistrer les Présences
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
