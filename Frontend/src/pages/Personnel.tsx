import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { PersonnelDialog } from "@/components/personnel/PersonnelDialog";
import { RoleSelectionDialog, PersonnelRole } from "@/components/personnel/RoleSelectionDialog";
import { Plus, Search, Eye, Pencil, Trash2, Mail, Phone } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

interface Personnel {
  id: string;
  nom: string;
  prenom: string;
  email: string;
  telephone: string;
  role: PersonnelRole;
  departement: string;
  specialite?: string;
  dateEmbauche: string;
  statut: "actif" | "conge" | "inactif";
  grade?: string;
  departementGere?: string;
  service?: string;
  poste?: string;
}

const mockPersonnel: Personnel[] = [
  {
    id: "1",
    nom: "Diallo",
    prenom: "Mamadou",
    email: "m.diallo@ecole.sn",
    telephone: "+221 77 123 4567",
    role: "responsable",
    departement: "Informatique",
    departementGere: "Informatique",
    dateEmbauche: "2020-09-01",
    statut: "actif",
  },
  {
    id: "2",
    nom: "Ndiaye",
    prenom: "Fatou",
    email: "f.ndiaye@ecole.sn",
    telephone: "+221 76 234 5678",
    role: "professeur",
    departement: "Informatique",
    specialite: "Développement Web",
    grade: "Maître de Conférences",
    dateEmbauche: "2021-01-15",
    statut: "actif",
  },
  {
    id: "3",
    nom: "Sow",
    prenom: "Aminata",
    email: "a.sow@ecole.sn",
    telephone: "+221 78 345 6789",
    role: "assistant",
    departement: "Gestion",
    poste: "Assistant pédagogique",
    dateEmbauche: "2022-03-10",
    statut: "actif",
  },
  {
    id: "4",
    nom: "Ba",
    prenom: "Ousmane",
    email: "o.ba@ecole.sn",
    telephone: "+221 77 456 7890",
    role: "administratif",
    departement: "",
    service: "Scolarité",
    poste: "Secrétaire",
    dateEmbauche: "2019-06-15",
    statut: "actif",
  },
];

export default function Personnel() {
  const navigate = useNavigate();
  const [personnel, setPersonnel] = useState<Personnel[]>(mockPersonnel);
  const [searchTerm, setSearchTerm] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("all");
  const [roleSelectionOpen, setRoleSelectionOpen] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedRole, setSelectedRole] = useState<PersonnelRole | undefined>();
  const [selectedPersonnel, setSelectedPersonnel] = useState<Personnel | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [personnelToDelete, setPersonnelToDelete] = useState<string | null>(null);

  const filteredPersonnel = personnel.filter((p) => {
    const matchesSearch =
      p.nom.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.prenom.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.email.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesRole = roleFilter === "all" || p.role === roleFilter;
    return matchesSearch && matchesRole;
  });

  const handleSavePersonnel = (data: Partial<Personnel>) => {
    if (selectedPersonnel) {
      setPersonnel(personnel.map((p) => (p.id === selectedPersonnel.id ? { ...p, ...data } : p)));
      toast.success("Personnel modifié avec succès");
    } else {
      const newPersonnel: Personnel = {
        id: (personnel.length + 1).toString(),
        ...data,
      } as Personnel;
      setPersonnel([...personnel, newPersonnel]);
      toast.success("Personnel ajouté avec succès");
    }
    setDialogOpen(false);
    setSelectedPersonnel(null);
    setSelectedRole(undefined);
  };

  const handleAddClick = () => {
    setSelectedPersonnel(null);
    setRoleSelectionOpen(true);
  };

  const handleRoleSelected = (role: PersonnelRole) => {
    setSelectedRole(role);
    setRoleSelectionOpen(false);
    setDialogOpen(true);
  };

  const handleEdit = (p: Personnel) => {
    setSelectedPersonnel(p);
    setSelectedRole(p.role);
    setDialogOpen(true);
  };

  const handleDelete = (id: string) => {
    setPersonnelToDelete(id);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = () => {
    if (personnelToDelete) {
      setPersonnel(personnel.filter((p) => p.id !== personnelToDelete));
      toast.success("Personnel supprimé avec succès");
      setDeleteDialogOpen(false);
      setPersonnelToDelete(null);
    }
  };

  const getRoleBadge = (role: string) => {
    const variants: Record<string, string> = {
      responsable: "bg-primary text-primary-foreground",
      professeur: "bg-secondary text-secondary-foreground",
      assistant: "bg-accent text-accent-foreground",
      administratif: "bg-muted text-muted-foreground",
    };
    const labels: Record<string, string> = {
      responsable: "Responsable",
      professeur: "Professeur",
      assistant: "Assistant(e)",
      administratif: "Administratif",
    };
    return (
      <Badge className={variants[role] || "bg-muted text-muted-foreground"}>
        {labels[role] || role}
      </Badge>
    );
  };

  const getStatutBadge = (statut: string) => {
    const variants = {
      actif: "bg-success text-success-foreground",
      conge: "bg-warning text-warning-foreground",
      inactif: "bg-muted text-muted-foreground",
    };
    const labels = {
      actif: "Actif",
      conge: "En congé",
      inactif: "Inactif",
    };
    return (
      <Badge className={variants[statut as keyof typeof variants]}>
        {labels[statut as keyof typeof labels]}
      </Badge>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Corps Administratif</h1>
          <p className="text-muted-foreground">Gestion du personnel enseignant et administratif</p>
        </div>
        <Button onClick={handleAddClick} className="bg-primary hover:bg-primary-hover">
          <Plus className="mr-2 h-4 w-4" />
          Ajouter Personnel
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filtres</CardTitle>
          <CardDescription>Rechercher et filtrer le personnel</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col md:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Rechercher par nom, prénom ou email..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={roleFilter} onValueChange={setRoleFilter}>
              <SelectTrigger className="w-full md:w-[200px]">
                <SelectValue placeholder="Rôle" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous les rôles</SelectItem>
                <SelectItem value="responsable">Responsables</SelectItem>
                <SelectItem value="professeur">Professeurs</SelectItem>
                <SelectItem value="assistant">Assistants</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Liste du Personnel ({filteredPersonnel.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border border-border">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/50">
                  <TableHead>Nom & Prénom</TableHead>
                  <TableHead>Rôle</TableHead>
                  <TableHead>Département</TableHead>
                  <TableHead>Contact</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredPersonnel.map((p) => (
                  <TableRow key={p.id} className="hover:bg-accent/50">
                    <TableCell className="font-medium">
                      {p.prenom} {p.nom}
                      {p.specialite && (
                        <div className="text-sm text-muted-foreground">{p.specialite}</div>
                      )}
                    </TableCell>
                    <TableCell>{getRoleBadge(p.role)}</TableCell>
                    <TableCell>{p.departement}</TableCell>
                    <TableCell>
                      <div className="flex flex-col gap-1">
                        <div className="flex items-center gap-1 text-sm">
                          <Mail className="h-3 w-3 text-muted-foreground" />
                          <span className="text-muted-foreground">{p.email}</span>
                        </div>
                        <div className="flex items-center gap-1 text-sm">
                          <Phone className="h-3 w-3 text-muted-foreground" />
                          <span className="text-muted-foreground">{p.telephone}</span>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>{getStatutBadge(p.statut)}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => navigate(`/personnel/${p.id}`)}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => handleEdit(p)}>
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDelete(p.id)}
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

      <RoleSelectionDialog
        open={roleSelectionOpen}
        onOpenChange={setRoleSelectionOpen}
        onSelectRole={handleRoleSelected}
      />

      <PersonnelDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onSave={handleSavePersonnel}
        personnel={selectedPersonnel}
        selectedRole={selectedRole}
      />

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmer la suppression</AlertDialogTitle>
            <AlertDialogDescription>
              Êtes-vous sûr de vouloir supprimer ce membre du personnel ? Cette action est
              irréversible.
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
