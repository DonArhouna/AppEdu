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
  Users,
  UserCheck,
  UserX,
  Plus,
  Search,
  MoreVertical,
  KeyRound,
  Edit,
  Trash2,
  ShieldCheck,
  Mail,
  Download,
  Filter
} from "lucide-react";
import { UserDialog } from "@/components/utilisateurs/UserDialog";
import { toast } from "sonner";

interface User {
  id: string;
  nom: string;
  prenom: string;
  email: string;
  telephone: string;
  role: "Administrateur" | "Secrétariat" | "Enseignant" | "Comptable" | "Étudiant";
  departement: string;
  statut: "Actif" | "Inactif" | "En attente";
  derniereConnexion: string;
}

const mockUsers: User[] = [
  {
    id: "USR-001",
    nom: "Dupont",
    prenom: "Marie",
    email: "m.dupont@univ-edumanage.com",
    telephone: "+33 6 12 34 56 78",
    role: "Administrateur",
    departement: "Direction",
    statut: "Actif",
    derniereConnexion: "Aujourd'hui à 10:15",
  },
  {
    id: "USR-002",
    nom: "Kouassi",
    prenom: "Jean-Philippe",
    email: "jp.kouassi@univ-edumanage.com",
    telephone: "+225 07 08 09 10 11",
    role: "Enseignant",
    departement: "Informatique",
    statut: "Actif",
    derniereConnexion: "Hier à 16:40",
  },
  {
    id: "USR-003",
    nom: "Bernard",
    prenom: "Sophie",
    email: "s.bernard@univ-edumanage.com",
    telephone: "+33 6 98 76 54 32",
    role: "Secrétariat",
    departement: "Gestion",
    statut: "Actif",
    derniereConnexion: "Il y a 2h",
  },
  {
    id: "USR-004",
    nom: "Diallo",
    prenom: "Amadou",
    email: "a.diallo@univ-edumanage.com",
    telephone: "+221 77 123 45 67",
    role: "Comptable",
    departement: "Finance",
    statut: "Actif",
    derniereConnexion: "Il y a 3 jours",
  },
  {
    id: "USR-005",
    nom: "Martin",
    prenom: "Lucas",
    email: "l.martin@etudiant.edumanage.com",
    telephone: "+33 7 11 22 33 44",
    role: "Étudiant",
    departement: "Informatique",
    statut: "En attente",
    derniereConnexion: "Jamais",
  },
  {
    id: "USR-006",
    nom: "Traoré",
    prenom: "Fatou",
    email: "f.traore@univ-edumanage.com",
    telephone: "+223 66 55 44 33",
    role: "Enseignant",
    departement: "Commerce",
    statut: "Inactif",
    derniereConnexion: "Il y a 2 semaines",
  },
];

const Utilisateurs = () => {
  const [users, setUsers] = useState<User[]>(mockUsers);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("ALL");
  const [statutFilter, setStatutFilter] = useState("ALL");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | undefined>(undefined);

  const filteredUsers = users.filter((u) => {
    const matchesSearch =
      u.nom.toLowerCase().includes(search.toLowerCase()) ||
      u.prenom.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase()) ||
      u.id.toLowerCase().includes(search.toLowerCase());

    const matchesRole = roleFilter === "ALL" || u.role === roleFilter;
    const matchesStatut = statutFilter === "ALL" || u.statut === statutFilter;

    return matchesSearch && matchesRole && matchesStatut;
  });

  const handleResetPassword = (email: string) => {
    toast.success(`Un email de réinitialisation de mot de passe a été envoyé à ${email}`);
  };

  const handleToggleStatut = (id: string) => {
    setUsers((prev) =>
      prev.map((u) => {
        if (u.id === id) {
          const newStatut = u.statut === "Actif" ? "Inactif" : "Actif";
          toast.info(`Le statut de ${u.prenom} ${u.nom} est maintenant "${newStatut}".`);
          return { ...u, statut: newStatut };
        }
        return u;
      })
    );
  };

  const handleDeleteUser = (id: string) => {
    setUsers((prev) => prev.filter((u) => u.id !== id));
    toast.success("L'utilisateur a été supprimé de l'établissement.");
  };

  const getRoleBadge = (role: string) => {
    switch (role) {
      case "Administrateur":
        return <Badge className="bg-rose-500/10 text-rose-600 border-rose-200">Administrateur</Badge>;
      case "Secrétariat":
        return <Badge className="bg-blue-500/10 text-blue-600 border-blue-200">Secrétariat</Badge>;
      case "Enseignant":
        return <Badge className="bg-emerald-500/10 text-emerald-600 border-emerald-200">Enseignant</Badge>;
      case "Comptable":
        return <Badge className="bg-amber-500/10 text-amber-600 border-amber-200">Comptable</Badge>;
      default:
        return <Badge variant="outline">Étudiant</Badge>;
    }
  };

  const getStatutBadge = (statut: string) => {
    switch (statut) {
      case "Actif":
        return <Badge className="bg-emerald-500/15 text-emerald-700 border-emerald-300">Actif</Badge>;
      case "En attente":
        return <Badge className="bg-amber-500/15 text-amber-700 border-amber-300">En attente</Badge>;
      default:
        return <Badge className="bg-slate-500/15 text-slate-700 border-slate-300">Inactif</Badge>;
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Gestion des Utilisateurs</h1>
          <p className="text-muted-foreground mt-1">
            Gérez les comptes d'accès, rôles et réinitialisations de mot de passe de votre établissement
          </p>
        </div>

        <Button
          onClick={() => {
            setEditingUser(undefined);
            setDialogOpen(true);
          }}
          className="shadow-md"
        >
          <Plus className="h-4 w-4 mr-2" />
          Nouvel Utilisateur
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-6 md:grid-cols-4">
        <Card className="relative overflow-hidden">
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-primary" />
          <CardHeader className="flex flex-row items-center justify-between pb-2 pl-5">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Utilisateurs
            </CardTitle>
            <Users className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent className="pl-5">
            <div className="text-2xl font-bold">{users.length}</div>
            <p className="text-xs text-muted-foreground mt-1">Comptes enregistrés</p>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden">
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-emerald-500" />
          <CardHeader className="flex flex-row items-center justify-between pb-2 pl-5">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Comptes Actifs
            </CardTitle>
            <UserCheck className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent className="pl-5">
            <div className="text-2xl font-bold">
              {users.filter((u) => u.statut === "Actif").length}
            </div>
            <p className="text-xs text-emerald-600 font-medium mt-1">Accès autorisés</p>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden">
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-amber-500" />
          <CardHeader className="flex flex-row items-center justify-between pb-2 pl-5">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              En Attente
            </CardTitle>
            <Mail className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent className="pl-5">
            <div className="text-2xl font-bold">
              {users.filter((u) => u.statut === "En attente").length}
            </div>
            <p className="text-xs text-amber-600 font-medium mt-1">Invitations envoyées</p>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden">
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-slate-400" />
          <CardHeader className="flex flex-row items-center justify-between pb-2 pl-5">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Comptes Inactifs
            </CardTitle>
            <UserX className="h-4 w-4 text-slate-500" />
          </CardHeader>
          <CardContent className="pl-5">
            <div className="text-2xl font-bold">
              {users.filter((u) => u.statut === "Inactif").length}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Accès révoqués</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters & Actions */}
      <Card>
        <CardContent className="p-4 sm:p-6 space-y-4">
          <div className="flex flex-col md:flex-row gap-4 justify-between items-center">
            {/* Search */}
            <div className="relative w-full md:w-80">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Rechercher par nom, email..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 text-sm"
              />
            </div>

            {/* Select Filters */}
            <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
              <Select value={roleFilter} onValueChange={setRoleFilter}>
                <SelectTrigger className="w-[160px] text-xs">
                  <Filter className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
                  <SelectValue placeholder="Rôle" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">Tous les rôles</SelectItem>
                  <SelectItem value="Administrateur">Administrateur</SelectItem>
                  <SelectItem value="Secrétariat">Secrétariat</SelectItem>
                  <SelectItem value="Enseignant">Enseignant</SelectItem>
                  <SelectItem value="Comptable">Comptable</SelectItem>
                  <SelectItem value="Étudiant">Étudiant</SelectItem>
                </SelectContent>
              </Select>

              <Select value={statutFilter} onValueChange={setStatutFilter}>
                <SelectTrigger className="w-[150px] text-xs">
                  <SelectValue placeholder="Statut" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">Tous les statuts</SelectItem>
                  <SelectItem value="Actif">Actif</SelectItem>
                  <SelectItem value="En attente">En attente</SelectItem>
                  <SelectItem value="Inactif">Inactif</SelectItem>
                </SelectContent>
              </Select>

              <Button
                variant="outline"
                size="sm"
                onClick={() => toast.info("Exportation CSV de la liste des utilisateurs...")}
              >
                <Download className="h-4 w-4 mr-2" />
                Exporter
              </Button>
            </div>
          </div>

          {/* Table */}
          <div className="rounded-lg border overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/50">
                  <TableHead>Utilisateur</TableHead>
                  <TableHead>Rôle</TableHead>
                  <TableHead>Département</TableHead>
                  <TableHead>Téléphone</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead>Dernière Connexion</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredUsers.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                      Aucun utilisateur ne correspond à votre recherche.
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredUsers.map((user) => (
                    <TableRow key={user.id} className="hover:bg-muted/30">
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="h-9 w-9 rounded-full bg-primary/10 text-primary font-bold flex items-center justify-center text-xs">
                            {user.prenom[0]}
                            {user.nom[0]}
                          </div>
                          <div className="flex flex-col">
                            <span className="font-semibold text-sm">
                              {user.prenom} {user.nom}
                            </span>
                            <span className="text-xs text-muted-foreground">{user.email}</span>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>{getRoleBadge(user.role)}</TableCell>
                      <TableCell className="text-xs font-medium text-muted-foreground">
                        {user.departement}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {user.telephone}
                      </TableCell>
                      <TableCell>{getStatutBadge(user.statut)}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {user.derniereConnexion}
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
                                setEditingUser(user);
                                setDialogOpen(true);
                              }}
                            >
                              <Edit className="h-4 w-4 mr-2 text-blue-500" />
                              Modifier
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleResetPassword(user.email)}>
                              <KeyRound className="h-4 w-4 mr-2 text-amber-500" />
                              Réinitialiser Mot de passe
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleToggleStatut(user.id)}>
                              <ShieldCheck className="h-4 w-4 mr-2 text-emerald-500" />
                              {user.statut === "Actif" ? "Désactiver le compte" : "Activer le compte"}
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              className="text-destructive"
                              onClick={() => handleDeleteUser(user.id)}
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              Supprimer
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* User Dialog */}
      <UserDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        userToEdit={editingUser}
      />
    </div>
  );
};

export default Utilisateurs;
