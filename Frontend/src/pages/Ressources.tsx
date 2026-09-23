import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Search, FileText, Video, File, Download, Eye } from "lucide-react";
import { toast } from "sonner";

export default function Ressources() {
  const [searchTerm, setSearchTerm] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");

  const ressources = [
    {
      id: "1",
      titre: "Cours Programmation Web - Chapitre 1",
      type: "pdf",
      matiere: "Programmation Web",
      enseignant: "M. Diallo",
      date: "2024-01-15",
      taille: "2.5 MB",
    },
    {
      id: "2",
      titre: "TD Base de données avancées",
      type: "pdf",
      matiere: "Base de données",
      enseignant: "Mme Ndiaye",
      date: "2024-01-20",
      taille: "1.8 MB",
    },
    {
      id: "3",
      titre: "Vidéo - Introduction React",
      type: "video",
      matiere: "Programmation Web",
      enseignant: "M. Diallo",
      date: "2024-01-22",
      taille: "125 MB",
    },
    {
      id: "4",
      titre: "TP Algorithmique - Tri et Recherche",
      type: "document",
      matiere: "Algorithmique",
      enseignant: "M. Sow",
      date: "2024-01-25",
      taille: "850 KB",
    },
  ];

  const filteredRessources = ressources.filter((r) => {
    const matchesSearch =
      r.titre.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.matiere.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = typeFilter === "all" || r.type === typeFilter;
    return matchesSearch && matchesType;
  });

  const getTypeIcon = (type: string) => {
    if (type === "pdf") return <FileText className="h-5 w-5 text-destructive" />;
    if (type === "video") return <Video className="h-5 w-5 text-primary" />;
    return <File className="h-5 w-5 text-secondary" />;
  };

  const getTypeBadge = (type: string) => {
    if (type === "pdf") return <Badge className="bg-destructive/10 text-destructive">PDF</Badge>;
    if (type === "video") return <Badge className="bg-primary/10 text-primary">Vidéo</Badge>;
    return <Badge className="bg-secondary/10 text-secondary">Document</Badge>;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Ressources Pédagogiques</h1>
          <p className="text-muted-foreground">Espace de partage de cours, TD et TP</p>
        </div>
        <Button onClick={() => toast.success("Upload à venir")} className="bg-primary hover:bg-primary-hover">
          <Plus className="mr-2 h-4 w-4" />
          Déposer Ressource
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filtres</CardTitle>
          <CardDescription>Rechercher et filtrer les ressources</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col md:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Rechercher par titre ou matière..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-full md:w-[200px]">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous les types</SelectItem>
                <SelectItem value="pdf">PDF</SelectItem>
                <SelectItem value="video">Vidéo</SelectItem>
                <SelectItem value="document">Document</SelectItem>
              </SelectContent>
            </Select>
            <Select defaultValue="all">
              <SelectTrigger className="w-full md:w-[200px]">
                <SelectValue placeholder="Matière" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Toutes les matières</SelectItem>
                <SelectItem value="prog">Programmation Web</SelectItem>
                <SelectItem value="bdd">Base de données</SelectItem>
                <SelectItem value="algo">Algorithmique</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Ressources Disponibles ({filteredRessources.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredRessources.map((r) => (
              <Card key={r.id} className="hover:shadow-lg transition-shadow border-border">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between mb-3">
                    {getTypeIcon(r.type)}
                    {getTypeBadge(r.type)}
                  </div>
                  <h3 className="font-semibold text-foreground mb-2">{r.titre}</h3>
                  <div className="space-y-1 text-sm text-muted-foreground mb-4">
                    <div>{r.matiere}</div>
                    <div>{r.enseignant}</div>
                    <div className="flex items-center justify-between">
                      <span>{new Date(r.date).toLocaleDateString("fr-FR")}</span>
                      <span className="text-xs">{r.taille}</span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      onClick={() => toast.success("Prévisualisation")}
                    >
                      <Eye className="mr-2 h-4 w-4" />
                      Voir
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      onClick={() => toast.success("Téléchargement démarré")}
                    >
                      <Download className="mr-2 h-4 w-4" />
                      Télécharger
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
