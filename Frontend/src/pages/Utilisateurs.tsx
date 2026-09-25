import { useEffect, useMemo, useState } from "react";
import { AlertCircle, KeyRound, Loader2, Plus, RefreshCw, Search, ShieldCheck, Trash2, UserCheck, UserX, Users } from "lucide-react";
import { toast } from "sonner";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { KpiCard } from "@/components/ui/kpi-card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { UserDialog, type UserFormData } from "@/components/utilisateurs/UserDialog";
import { extractErrorMessage, usersApi } from "@/services/apiClient";
import type { User } from "@/services/apiTypes";

interface UserRow {
  id: number;
  nom: string;
  prenom: string;
  email: string;
  telephone?: string | null;
  role: User["role"];
  is_active: boolean;
  etudiant_id?: string | null;
  last_login?: string | null;
  created_at: string;
}

const roleLabels: Record<string, string> = {
  ADMIN: "Administrateur",
  DIRECTEUR_ETUDES: "Directeur des études",
  SECRETARIAT: "Secrétariat",
  COMPTABILITE: "Comptabilité",
  ENSEIGNANT: "Enseignant",
  ETUDIANT: "Étudiant",
};

const Utilisateurs = () => {
  const [users, setUsers] = useState<UserRow[]>([]);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<UserRow | undefined>();
  const [deleteUser, setDeleteUser] = useState<UserRow | undefined>();

  const loadUsers = async () => {
    setLoading(true);
    setError(null);
    const result = await usersApi.getAll();
    if (result.error) setError(result.error);
    else setUsers((result.data || []) as UserRow[]);
    setLoading(false);
  };

  useEffect(() => { void loadUsers(); }, []);

  const availableRoles = useMemo(() => Array.from(new Set(users.map((user) => user.role))), [users]);
  const activeAdminCount = useMemo(
    () => users.filter((user) => user.role === "ADMIN" && user.is_active).length,
    [users]
  );
  const isProtectedAdmin = (user: UserRow) =>
    user.role === "ADMIN" && user.is_active && activeAdminCount === 1;
  const filteredUsers = useMemo(() => users.filter((user) => {
    const query = search.trim().toLowerCase();
    const matchesSearch = !query || `${user.prenom} ${user.nom} ${user.email}`.toLowerCase().includes(query);
    const matchesRole = roleFilter === "all" || user.role === roleFilter;
    const matchesStatus = statusFilter === "all" || (statusFilter === "active" ? user.is_active : !user.is_active);
    return matchesSearch && matchesRole && matchesStatus;
  }), [users, search, roleFilter, statusFilter]);

  const handleSave = async (data: UserFormData) => {
    const payload = {
      nom: data.nom,
      prenom: data.prenom,
      email: data.email,
      telephone: data.telephone || null,
      role: data.role,
      is_active: data.is_active,
      etudiant_id: data.role === "ETUDIANT" ? data.etudiant_id || null : null,
      ...(data.password ? { password: data.password } : {}),
    };
    const result = editingUser
      ? await usersApi.update(editingUser.id, payload)
      : await usersApi.create(payload);
    if (result.error) {
      toast.error(extractErrorMessage(result.error));
      throw new Error(result.error);
    }
    toast.success(editingUser ? "Compte mis à jour." : "Compte créé.");
    await loadUsers();
  };

  const confirmDelete = async () => {
    if (!deleteUser) return;
    if (isProtectedAdmin(deleteUser)) {
      toast.error("Le dernier administrateur actif doit être conservé.");
      setDeleteUser(undefined);
      return;
    }
    const result = await usersApi.delete(deleteUser.id);
    if (result.error) {
      toast.error(result.error);
      return;
    }
    toast.success("Compte supprimé.");
    setDeleteUser(undefined);
    await loadUsers();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div><h1 className="text-3xl font-bold text-foreground">Comptes utilisateurs</h1><p className="mt-1 text-muted-foreground">Les comptes, rôles et statuts sont gérés par le backend.</p></div>
        <div className="flex gap-2"><Button variant="outline" onClick={loadUsers} disabled={loading}><RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />Actualiser</Button><Button onClick={() => { setEditingUser(undefined); setDialogOpen(true); }}><Plus className="mr-2 h-4 w-4" />Nouvel utilisateur</Button></div>
      </div>

      {error && <Alert variant="destructive"><AlertCircle className="h-4 w-4" /><AlertTitle>Erreur backend</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard title="Total" value={users.length} icon={Users} subtitle="Comptes enregistrés" colorVariant="primary" />
        <KpiCard title="Actifs" value={users.filter((user) => user.is_active).length} icon={UserCheck} subtitle="Comptes autorisés" colorVariant="emerald" />
        <KpiCard title="Inactifs" value={users.filter((user) => !user.is_active).length} icon={UserX} subtitle="Comptes désactivés" colorVariant="rose" />
        <KpiCard title="Administrateurs" value={users.filter((user) => user.role === "ADMIN").length} icon={ShieldCheck} subtitle="Rôles d'administration" colorVariant="purple" />
      </div>

      <Card>
        <CardContent className="space-y-4 p-4 sm:p-6">
          <div className="flex flex-col gap-3 md:flex-row">
            <div className="relative flex-1"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" /><Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Rechercher un nom ou un email" className="pl-9" /></div>
            <Select value={roleFilter} onValueChange={setRoleFilter}><SelectTrigger className="w-full md:w-56"><SelectValue placeholder="Rôle" /></SelectTrigger><SelectContent><SelectItem value="all">Tous les rôles</SelectItem>{availableRoles.map((role) => <SelectItem key={role} value={role}>{roleLabels[role] || role}</SelectItem>)}</SelectContent></Select>
            <Select value={statusFilter} onValueChange={setStatusFilter}><SelectTrigger className="w-full md:w-44"><SelectValue placeholder="Statut" /></SelectTrigger><SelectContent><SelectItem value="all">Tous les statuts</SelectItem><SelectItem value="active">Actifs</SelectItem><SelectItem value="inactive">Inactifs</SelectItem></SelectContent></Select>
          </div>
          <div className="overflow-x-auto rounded-lg border">
            <Table><TableHeader><TableRow className="bg-muted/50"><TableHead>Utilisateur</TableHead><TableHead>Rôle</TableHead><TableHead>Statut</TableHead><TableHead>Dernière connexion</TableHead><TableHead className="text-right">Actions</TableHead></TableRow></TableHeader>
              <TableBody>{loading ? <TableRow><TableCell colSpan={5} className="py-10 text-center"><Loader2 className="mx-auto h-5 w-5 animate-spin" /></TableCell></TableRow> : filteredUsers.length === 0 ? <TableRow><TableCell colSpan={5} className="py-10 text-center text-muted-foreground">Aucun utilisateur trouvé.</TableCell></TableRow> : filteredUsers.map((user) => <TableRow key={user.id}>
                <TableCell><div className="flex items-center gap-3"><div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">{user.prenom?.[0]}{user.nom?.[0]}</div><div><p className="font-semibold text-sm">{user.prenom} {user.nom}</p><p className="text-xs text-muted-foreground">{user.email}</p></div></div></TableCell>
                <TableCell><Badge variant="outline">{roleLabels[user.role] || user.role}</Badge></TableCell>
                <TableCell><Badge variant={user.is_active ? "default" : "secondary"}>{user.is_active ? "Actif" : "Inactif"}</Badge></TableCell>
                <TableCell className="text-xs text-muted-foreground">{user.last_login ? new Date(user.last_login).toLocaleString("fr-FR") : "Jamais"}</TableCell>
                <TableCell className="text-right"><div className="flex justify-end gap-1"><Button variant="ghost" size="icon" onClick={() => { setEditingUser(user); setDialogOpen(true); }} aria-label="Modifier"><Users className="h-4 w-4" /></Button><Button variant="ghost" size="icon" onClick={() => { setEditingUser(user); setDialogOpen(true); }} aria-label="Modifier le mot de passe"><KeyRound className="h-4 w-4" /></Button><Button variant="ghost" size="icon" className="text-destructive" onClick={() => setDeleteUser(user)} aria-label={isProtectedAdmin(user) ? "Dernier administrateur protégé" : "Supprimer"} disabled={isProtectedAdmin(user)} title={isProtectedAdmin(user) ? "Le dernier administrateur actif ne peut pas être supprimé" : undefined}><Trash2 className="h-4 w-4" /></Button></div></TableCell>
              </TableRow>)}</TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <UserDialog open={dialogOpen} onOpenChange={setDialogOpen} userToEdit={editingUser} protectAdminAccess={Boolean(editingUser && isProtectedAdmin(editingUser))} onSave={handleSave} />
      <AlertDialog open={Boolean(deleteUser)} onOpenChange={(open) => !open && setDeleteUser(undefined)}><AlertDialogContent><AlertDialogHeader><AlertDialogTitle>Supprimer ce compte ?</AlertDialogTitle><AlertDialogDescription>Le compte {deleteUser?.email} sera supprimé. Cette action est irréversible.</AlertDialogDescription></AlertDialogHeader><AlertDialogFooter><AlertDialogCancel>Annuler</AlertDialogCancel><AlertDialogAction onClick={confirmDelete} className="bg-destructive text-destructive-foreground">Supprimer</AlertDialogAction></AlertDialogFooter></AlertDialogContent></AlertDialog>
    </div>
  );
};

export default Utilisateurs;
