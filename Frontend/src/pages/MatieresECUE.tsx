import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { MatiereDialog } from "@/components/matieres/MatiereDialog";
import { Plus, Search, Eye, Pencil, Trash2, BookOpen } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

interface Matiere {
  id: string;
  code: string;
  nom: string;
  type: "ECUE";
  credits: number;
  coefficient: number;
  heures: number;
  filiere: string;
  niveau: string;
  semestre: string;
  enseignant?: string;
  ue?: string;
}

const mockMatieres: Matiere[] = [
  {
    id: "1",
    code: "INF302",
    nom: "Base de données avancées",
    type: "ECUE",
    credits: 4,
    coefficient: 2,
    heures: 30,
    filiere: "Informatique",
    niveau: "L3",
    semestre: "S5",
    enseignant: "Fatou Ndiaye",
    ue: "Systèmes d'Information",
  },
];

export default function MatieresECUE() {
  const navigate = useNavigate();
  const [matieres, setMatieres] = useState<Matiere[]>(mockMatieres);
  const [searchTerm, setSearchTerm] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedMatiere, setSelectedMatiere] = useState<Matiere | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [matiereToDelete, setMatiereToDelete] = useState<string | null>(null);

  const filteredMatieres = matieres.filter((m) =>
    m.nom.toLowerCase().includes(searchTerm.toLowerCase()) ||
    m.code.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleSaveMatiere = (data: Partial<Matiere>) => {
    if (selectedMatiere) {
      setMatieres(matieres.map((m) => (m.id === selectedMatiere.id ? { ...m, ...data } : m)));
      toast.success("Matière modifiée avec succès");
    } else {
      const newMatiere: Matiere = {
        id: (matieres.length + 1).toString(),
        type: "ECUE",
        ...data,
      } as Matiere;
      setMatieres([...matieres, newMatiere]);
      toast.success("Matière ajoutée avec succès");
    }
    setDialogOpen(false);
    setSelectedMatiere(null);
  };

  const handleEdit = (m: Matiere) => {
    setSelectedMatiere(m);
    setDialogOpen(true);
  };

  const handleDelete = (id: string) => {
    setMatiereToDelete(id);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = () => {
    if (matiereToDelete) {
      setMatieres(matieres.filter((m) => m.id !== matiereToDelete));
      toast.success("Matière supprimée avec succès");
      setDeleteDialogOpen(false);
      setMatiereToDelete(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Matières (ECUE)</h1>
          <p className="text-muted-foreground">Éléments Constitutifs d'Unités d'Enseignement</p>
        </div>
        <Button onClick={() => setDialogOpen(true)} className="bg-primary hover:bg-primary-hover">
          <Plus className="mr-2 h-4 w-4" />
          Créer Matière
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recherche</CardTitle>
          <CardDescription>Rechercher une matière</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="relative">
            <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Rechercher par nom ou code..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Liste des Matières ({filteredMatieres.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border border-border">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/50">
                  <TableHead>Code</TableHead>
                  <TableHead>Matière</TableHead>
                  <TableHead>UE Parente</TableHead>
                  <TableHead>Crédits</TableHead>
                  <TableHead>Coef.</TableHead>
                  <TableHead>Heures</TableHead>
                  <TableHead>Enseignant</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredMatieres.map((m) => (
                  <TableRow key={m.id} className="hover:bg-accent/50">
                    <TableCell className="font-mono font-medium">{m.code}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <BookOpen className="h-4 w-4 text-secondary" />
                        <div>
                          <div className="font-medium">{m.nom}</div>
                          <div className="text-sm text-muted-foreground">
                            {m.filiere} - {m.niveau} - {m.semestre}
                          </div>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {m.ue || "Non assignée"}
                    </TableCell>
                    <TableCell>{m.credits}</TableCell>
                    <TableCell>{m.coefficient}</TableCell>
                    <TableCell>{m.heures}h</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {m.enseignant || "Non assigné"}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => navigate(`/matieres/${m.id}`)}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => handleEdit(m)}>
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDelete(m.id)}
                          className="text-destructive hover:text-destructive"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <MatiereDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onSave={handleSaveMatiere}
        matiere={selectedMatiere}
        fixedType="ECUE"
      />

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmer la suppression</AlertDialogTitle>
            <AlertDialogDescription>
              Êtes-vous sûr de vouloir supprimer cette matière ? Cette action est irréversible.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
