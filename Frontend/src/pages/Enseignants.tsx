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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  GraduationCap,
  Plus,
  Search,
  MoreVertical,
  Edit,
  Trash2,
  Calendar,
  Clock,
  BookOpen,
  DollarSign,
  Filter
} from "lucide-react";
import { EnseignantDialog } from "@/components/personnel/EnseignantDialog";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";

interface Enseignant {
  id: string;
  nom: string;
  prenom: string;
  email: string;
  telephone: string;
  specialite: string;
  statut: "Vacataire" | "Permanent" | "Professeur Invité";
  tarifHoraire: string;
  heuresHebdo: number;
  departement: string;
}

const mockEnseignants: Enseignant[] = [
  {
    id: "ENS-1001",
    nom: "Diallo",
    prenom: "Mamadou",
    email: "m.diallo@univ-edumanage.com",
    telephone: "+225 07 12 34 56 78",
    specialite: "Programmation Web & React",
    statut: "Vacataire",
    tarifHoraire: "15 000 FCFA/h",
    heuresHebdo: 12,
    departement: "Génie Informatique",
  },
  {
    id: "ENS-1002",
    nom: "Ndiaye",
    prenom: "Sophie",
    email: "s.ndiaye@univ-edumanage.com",
    telephone: "+221 77 987 65 43",
    specialite: "Base de données & PostgreSQL",
    statut: "Permanent",
    tarifHoraire: "Plein temps",
    heuresHebdo: 18,
    departement: "Génie Informatique",
  },
  {
    id: "ENS-1003",
    nom: "Sow",
    prenom: "Jean-Philippe",
    email: "jp.sow@univ-edumanage.com",
    telephone: "+33 6 44 55 66 77",
    specialite: "Algorithmique & Structures",
    statut: "Vacataire",
    tarifHoraire: "20 000 FCFA/h",
    heuresHebdo: 8,
    departement: "Génie Informatique",
  },
  {
    id: "ENS-1004",
    nom: "Traoré",
    prenom: "Fatou",
    email: "f.traore@univ-edumanage.com",
    telephone: "+223 66 11 22 33",
    specialite: "Gestion de Projet & Finance",
    statut: "Permanent",
    tarifHoraire: "Plein temps",
    heuresHebdo: 16,
    departement: "Gestion & Finance",
  },
];

const Enseignants = () => {
  const navigate = useNavigate();
  const [enseignants, setEnseignants] = useState<Enseignant[]>(mockEnseignants);
  const [search, setSearch] = useState("");
  const [statutFilter, setStatutFilter] = useState("ALL");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingEnseignant, setEditingEnseignant] = useState<Enseignant | undefined>(undefined);

  const filteredEnseignants = enseignants.filter((e) => {
    const matchesSearch =
      e.nom.toLowerCase().includes(search.toLowerCase()) ||
      e.prenom.toLowerCase().includes(search.toLowerCase()) ||
      e.email.toLowerCase().includes(search.toLowerCase()) ||
      e.specialite.toLowerCase().includes(search.toLowerCase());

    const matchesStatut = statutFilter === "ALL" || e.statut === statutFilter;

    return matchesSearch && matchesStatut;
  });

  const handleSaveEnseignant = (data: Enseignant) => {
    setEnseignants((prev) => {
      const exists = prev.some((e) => e.id === data.id);
      if (exists) {
        return prev.map((e) => (e.id === data.id ? data : e));
      }
      return [data, ...prev];
    });
  };

  const handleDeleteEnseignant = (id: string) => {
    setEnseignants((prev) => prev.filter((e) => e.id !== id));
    toast.success("L'enseignant a été retiré de l'établissement.");
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground flex items-center gap-3">
            <GraduationCap className="h-8 w-8 text-primary" />
            Gestion des Enseignants & Intervenants
          </h1>
          <p className="text-muted-foreground mt-1">
            Gestion du corps professoral, vacataires, volume horaire et suivi des rémunérations
          </p>
        </div>

        <Button
          onClick={() => {
            setEditingEnseignant(undefined);
            setDialogOpen(true);
          }}
          className="shadow-md"
        >
          <Plus className="h-4 w-4 mr-2" />
          Nouveau Professeur
        </Button>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-6 md:grid-cols-4">
        <Card className="relative overflow-hidden">
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-primary" />
          <CardHeader className="flex flex-row items-center justify-between pb-2 pl-5">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Enseignants
            </CardTitle>
            <GraduationCap className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent className="pl-5">
            <div className="text-2xl font-bold">{enseignants.length}</div>
            <p className="text-xs text-muted-foreground mt-1">Corps professoral actif</p>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden">
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-emerald-500" />
          <CardHeader className="flex flex-row items-center justify-between pb-2 pl-5">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Permanents
            </CardTitle>
            <BookOpen className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent className="pl-5">
            <div className="text-2xl font-bold">
              {enseignants.filter((e) => e.statut === "Permanent").length}
            </div>
            <p className="text-xs text-emerald-600 font-medium mt-1">Plein temps</p>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden">
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-amber-500" />
          <CardHeader className="flex flex-row items-center justify-between pb-2 pl-5">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Vacataires
            </CardTitle>
            <Clock className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent className="pl-5">
            <div className="text-2xl font-bold">
              {enseignants.filter((e) => e.statut === "Vacataire").length}
            </div>
            <p className="text-xs text-amber-600 font-medium mt-1">Paiement au volume d'heures</p>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden">
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-purple-500" />
          <CardHeader className="flex flex-row items-center justify-between pb-2 pl-5">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Volume Heures / Sem.
            </CardTitle>
            <DollarSign className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent className="pl-5">
            <div className="text-2xl font-bold">
              {enseignants.reduce((acc, e) => acc + e.heuresHebdo, 0)} h
            </div>
            <p className="text-xs text-muted-foreground mt-1">Enseignées cette semaine</p>
          </CardContent>
        </Card>
      </div>

      {/* Table & Filters */}
      <Card>
        <CardContent className="p-4 sm:p-6 space-y-4">
          <div className="flex flex-col md:flex-row gap-4 justify-between items-center">
            <div className="relative w-full md:w-80">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Rechercher par nom, spécialité, email..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 text-sm"
              />
            </div>

            <div className="flex items-center gap-3 w-full md:w-auto">
              <Select value={statutFilter} onValueChange={setStatutFilter}>
                <SelectTrigger className="w-[180px] text-xs">
                  <Filter className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
                  <SelectValue placeholder="Statut Contractuel" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">Tous les statuts</SelectItem>
                  <SelectItem value="Vacataire">Vacataire</SelectItem>
                  <SelectItem value="Permanent">Permanent</SelectItem>
                  <SelectItem value="Professeur Invité">Professeur Invité</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="rounded-lg border overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/50">
                  <TableHead>Enseignant</TableHead>
                  <TableHead>Spécialité & Matières</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead>Département</TableHead>
                  <TableHead>Tarif Horaire</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredEnseignants.map((ens) => (
                  <TableRow key={ens.id} className="hover:bg-muted/30">
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="h-9 w-9 rounded-full bg-primary/10 text-primary font-bold flex items-center justify-center text-xs">
                          {ens.prenom[0]}
                          {ens.nom[0]}
                        </div>
                        <div className="flex flex-col">
                          <span className="font-semibold text-sm">
                            {ens.prenom} {ens.nom}
                          </span>
                          <span className="text-xs text-muted-foreground">{ens.email}</span>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="font-medium text-xs text-foreground">
                      {ens.specialite}
                    </TableCell>
                    <TableCell>
                      <Badge
                        className={
                          ens.statut === "Permanent"
                            ? "bg-emerald-500/15 text-emerald-700 border-emerald-300"
                            : "bg-amber-500/15 text-amber-700 border-amber-300"
                        }
                      >
                        {ens.statut}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {ens.departement}
                    </TableCell>
                    <TableCell className="font-mono text-xs font-semibold text-foreground">
                      {ens.tarifHoraire}
                    </TableCell>
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-48">
                          <DropdownMenuLabel>Actions</DropdownMenuLabel>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            onClick={() => {
                              setEditingEnseignant(ens);
                              setDialogOpen(true);
                            }}
                          >
                            <Edit className="h-4 w-4 mr-2 text-blue-500" />
                            Modifier la fiche
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => navigate("/emplois-du-temps")}>
                            <Calendar className="h-4 w-4 mr-2 text-emerald-500" />
                            Voir Emploi du Temps
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-destructive"
                            onClick={() => handleDeleteEnseignant(ens.id)}
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Supprimer
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Enseignant Dialog */}
      <EnseignantDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        enseignantToEdit={editingEnseignant}
        onSave={handleSaveEnseignant}
      />
    </div>
  );
};

export default Enseignants;
