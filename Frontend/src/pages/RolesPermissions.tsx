import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { AlertCircle, KeyRound, LoaderCircle, Plus, RefreshCw, Search, ShieldCheck, Trash2, UserPlus, Users } from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { KpiCard } from "@/components/ui/kpi-card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { extractErrorMessage, rbacApi } from "@/services/apiClient";
import type { RbacPermission, RbacRole, RbacUserAccess } from "@/services/apiTypes";

interface RoleForm {
  code: string;
  libelle: string;
  description: string;
  ordre: string;
  actif: boolean;
}

const emptyRoleForm: RoleForm = {
  code: "",
  libelle: "",
  description: "",
  ordre: "100",
  actif: true,
};

const RolesPermissions = () => {
  const [roles, setRoles] = useState<RbacRole[]>([]);
  const [permissions, setPermissions] = useState<RbacPermission[]>([]);
  const [users, setUsers] = useState<RbacUserAccess[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const [roleDialogOpen, setRoleDialogOpen] = useState(false);
  const [editingRole, setEditingRole] = useState<RbacRole | null>(null);
  const [roleForm, setRoleForm] = useState<RoleForm>(emptyRoleForm);
  const [savingRole, setSavingRole] = useState(false);

  const [deleteRole, setDeleteRole] = useState<RbacRole | null>(null);
  const [deletingRole, setDeletingRole] = useState(false);

  const [permissionRole, setPermissionRole] = useState<RbacRole | null>(null);
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>([]);
  const [savingPermissions, setSavingPermissions] = useState(false);

  const [assignmentRole, setAssignmentRole] = useState<RbacRole | null>(null);
  const [selectedUsers, setSelectedUsers] = useState<number[]>([]);
  const [savingAssignment, setSavingAssignment] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const [rolesResult, permissionsResult, usersResult] = await Promise.all([
      rbacApi.getRoles(),
      rbacApi.getPermissions(),
      rbacApi.getUsers(),
    ]);
    const firstError = rolesResult.error || permissionsResult.error || usersResult.error;
    if (firstError) {
      setError(extractErrorMessage(firstError, "Le RBAC est indisponible."));
      setRoles([]);
      setPermissions([]);
      setUsers([]);
    } else {
      setRoles(rolesResult.data || []);
      setPermissions(permissionsResult.data || []);
      setUsers(usersResult.data || []);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filteredRoles = useMemo(() => {
    const query = search.trim().toLocaleLowerCase("fr");
    if (!query) return roles;
    return roles.filter((role) => `${role.code} ${role.libelle} ${role.description || ""}`.toLocaleLowerCase("fr").includes(query));
  }, [roles, search]);

  const permissionsByDomain = useMemo(() => {
    const groups = new Map<string, RbacPermission[]>();
    permissions.filter((permission) => permission.actif).forEach((permission) => {
      const group = groups.get(permission.domaine) || [];
      group.push(permission);
      groups.set(permission.domaine, group);
    });
    return Array.from(groups.entries()).sort(([left], [right]) => left.localeCompare(right));
  }, [permissions]);

  const openCreateRole = () => {
    setEditingRole(null);
    setRoleForm(emptyRoleForm);
    setRoleDialogOpen(true);
  };

  const openEditRole = (role: RbacRole) => {
    setEditingRole(role);
    setRoleForm({
      code: role.code,
      libelle: role.libelle,
      description: role.description || "",
      ordre: String(role.ordre),
      actif: role.actif,
    });
    setRoleDialogOpen(true);
  };

  const saveRole = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!roleForm.code.trim() || !roleForm.libelle.trim()) {
      toast.error("Le code et le libellé sont obligatoires.");
      return;
    }
    setSavingRole(true);
    const result = editingRole
      ? await rbacApi.updateRole(editingRole.code, {
          libelle: roleForm.libelle.trim(),
          description: roleForm.description.trim() || null,
          ordre: Number(roleForm.ordre) || 0,
          actif: roleForm.actif,
        })
      : await rbacApi.createRole({
          code: roleForm.code.trim().toUpperCase(),
          libelle: roleForm.libelle.trim(),
          description: roleForm.description.trim() || null,
          ordre: Number(roleForm.ordre) || 0,
          actif: roleForm.actif,
        });
    setSavingRole(false);
    if (result.error) {
      toast.error(extractErrorMessage(result.error, "Le rôle n'a pas pu être enregistré."));
      return;
    }
    toast.success(editingRole ? "Rôle mis à jour." : "Rôle créé.");
    setRoleDialogOpen(false);
    await load();
  };

  const confirmDeleteRole = async () => {
    if (!deleteRole) return;
    setDeletingRole(true);
    const result = await rbacApi.deleteRole(deleteRole.code);
    setDeletingRole(false);
    if (result.error) {
      toast.error(extractErrorMessage(result.error, "Le rôle n'a pas pu être supprimé."));
      return;
    }
    toast.success("Rôle supprimé.");
    setDeleteRole(null);
    await load();
  };

  const openPermissions = async (role: RbacRole) => {
    setPermissionRole(role);
    const result = await rbacApi.getRolePermissions(role.code);
    if (result.error) {
      setPermissionRole(null);
      toast.error(extractErrorMessage(result.error, "Les permissions du rôle sont indisponibles."));
      return;
    }
    setSelectedPermissions((result.data || []).filter((permission) => permission.actif).map((permission) => permission.code));
  };

  const togglePermission = (code: string, checked: boolean) => {
    setSelectedPermissions((current) => checked ? [...new Set([...current, code])] : current.filter((item) => item !== code));
  };

  const savePermissions = async () => {
    if (!permissionRole) return;
    setSavingPermissions(true);
    const result = await rbacApi.replaceRolePermissions(permissionRole.code, { permissions: selectedPermissions });
    setSavingPermissions(false);
    if (result.error) {
      toast.error(extractErrorMessage(result.error, "Les permissions n'ont pas pu être enregistrées."));
      return;
    }
    toast.success("Permissions du rôle enregistrées.");
    setPermissionRole(null);
    await load();
  };

  const openAssignment = (role: RbacRole) => {
    setAssignmentRole(role);
    setSelectedUsers(users.filter((user) => user.roles.includes(role.code)).map((user) => user.id));
  };

  const toggleUser = (userId: number, checked: boolean) => {
    setSelectedUsers((current) => checked ? [...new Set([...current, userId])] : current.filter((id) => id !== userId));
  };

  const saveAssignment = async () => {
    if (!assignmentRole) return;
    setSavingAssignment(true);
    const current = users.filter((user) => user.roles.includes(assignmentRole.code)).map((user) => user.id);
    const toAdd = selectedUsers.filter((id) => !current.includes(id));
    const toRemove = current.filter((id) => !selectedUsers.includes(id));
    const addResult = toAdd.length ? await rbacApi.assignRole(assignmentRole.code, { user_ids: toAdd }) : null;
    if (addResult?.error) {
      setSavingAssignment(false);
      toast.error(extractErrorMessage(addResult.error, "L'affectation des comptes a échoué."));
      return;
    }
    for (const userId of toRemove) {
      const removeResult = await rbacApi.unassignRole(assignmentRole.code, userId);
      if (removeResult.error) {
        setSavingAssignment(false);
        toast.error(extractErrorMessage(removeResult.error, "Le retrait d'un compte a échoué."));
        return;
      }
    }
    setSavingAssignment(false);
    toast.success("Affectations du rôle enregistrées.");
    setAssignmentRole(null);
    await load();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Rôles & permissions</h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">Créez les rôles de l'institut, attribuez leurs permissions et affectez-les aux comptes. Les changements sont persistés côté serveur.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline" size="sm"><Link to="/utilisateurs"><Users className="mr-2 h-4 w-4" />Comptes utilisateurs</Link></Button>
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}><RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />Actualiser</Button>
          <Button size="sm" onClick={openCreateRole}><Plus className="mr-2 h-4 w-4" />Nouveau rôle</Button>
        </div>
      </div>

      {error && <Alert variant="destructive"><AlertCircle className="h-4 w-4" /><AlertTitle>RBAC indisponible</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard title="Rôles" value={roles.length} icon={ShieldCheck} subtitle="Rôles enregistrés" colorVariant="primary" />
        <KpiCard title="Rôles personnalisés" value={roles.filter((role) => !role.systeme).length} icon={UserPlus} subtitle="Créés par l'institut" colorVariant="purple" />
        <KpiCard title="Permissions catalogue" value={permissions.length} icon={KeyRound} subtitle="Permissions techniques" colorVariant="sky" />
        <KpiCard title="Comptes concernés" value={users.length} icon={Users} subtitle="Comptes de l'institut" colorVariant="emerald" />
      </div>

      <Card>
        <CardHeader className="gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div><CardTitle className="flex items-center gap-2"><ShieldCheck className="h-5 w-5 text-primary" />Catalogue des rôles</CardTitle><CardDescription>Les rôles système sont protégés ; les rôles personnalisés peuvent être modifiés ou supprimés.</CardDescription></div>
          <div className="relative sm:w-72"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" /><Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Rechercher un rôle" className="pl-9" aria-label="Rechercher un rôle" /></div>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? <div className="flex min-h-56 items-center justify-center gap-2 text-sm text-muted-foreground"><LoaderCircle className="h-5 w-5 animate-spin" />Chargement du RBAC...</div> : filteredRoles.length === 0 ? <div className="flex min-h-56 flex-col items-center justify-center gap-2 text-sm text-muted-foreground"><ShieldCheck className="h-8 w-8 text-muted-foreground/50" /><p>Aucun rôle ne correspond.</p></div> : <Table><TableHeader><TableRow><TableHead>Role</TableHead><TableHead>Type</TableHead><TableHead>Permissions</TableHead><TableHead>Comptes</TableHead><TableHead>État</TableHead><TableHead className="text-right">Actions</TableHead></TableRow></TableHeader><TableBody>{filteredRoles.map((role) => <TableRow key={role.code}><TableCell><p className="font-medium">{role.libelle}</p><p className="font-mono text-xs text-muted-foreground">{role.code}</p>{role.description && <p className="mt-1 text-xs text-muted-foreground">{role.description}</p>}</TableCell><TableCell><Badge variant={role.systeme ? "secondary" : "outline"}>{role.systeme ? "Système" : "Personnalisé"}</Badge></TableCell><TableCell><button type="button" className="inline-flex items-center gap-1 text-sm text-primary hover:underline" onClick={() => void openPermissions(role)}><KeyRound className="h-3.5 w-3.5" />{role.permissions.length}</button></TableCell><TableCell>{role.utilisateurs}</TableCell><TableCell><Badge variant={role.actif ? "default" : "secondary"}>{role.actif ? "Actif" : "Inactif"}</Badge></TableCell><TableCell className="text-right"><div className="flex justify-end gap-1"><Button variant="ghost" size="sm" onClick={() => void openPermissions(role)}>Permissions</Button><Button variant="ghost" size="sm" onClick={() => openAssignment(role)}><UserPlus className="mr-1 h-3.5 w-3.5" />Affecter</Button><Button variant="ghost" size="icon" onClick={() => openEditRole(role)} aria-label={`Modifier ${role.libelle}`}><KeyRound className="h-4 w-4" /></Button>{!role.systeme && <Button variant="ghost" size="icon" className="text-destructive hover:bg-destructive/10" onClick={() => setDeleteRole(role)} aria-label={`Supprimer ${role.libelle}`}><Trash2 className="h-4 w-4" /></Button>}</div></TableCell></TableRow>)}</TableBody></Table>}
        </CardContent>
      </Card>

      <Dialog open={roleDialogOpen} onOpenChange={setRoleDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader><DialogTitle>{editingRole ? "Modifier le rôle" : "Créer un rôle"}</DialogTitle><DialogDescription>Un rôle regroupe des permissions allow-only. Le code d'un rôle système est immuable.</DialogDescription></DialogHeader>
          <form onSubmit={saveRole} className="space-y-5">
            <div className="grid gap-4 sm:grid-cols-2"><div className="space-y-2"><Label htmlFor="rbac-role-code">Code *</Label><Input id="rbac-role-code" value={roleForm.code} onChange={(event) => setRoleForm({ ...roleForm, code: event.target.value.toUpperCase() })} disabled={Boolean(editingRole)} placeholder="ROLE_CONTROLE" required /></div><div className="space-y-2"><Label htmlFor="rbac-role-order">Ordre</Label><Input id="rbac-role-order" type="number" min="0" value={roleForm.ordre} onChange={(event) => setRoleForm({ ...roleForm, ordre: event.target.value })} /></div></div>
            <div className="space-y-2"><Label htmlFor="rbac-role-label">Libellé *</Label><Input id="rbac-role-label" value={roleForm.libelle} onChange={(event) => setRoleForm({ ...roleForm, libelle: event.target.value })} required /></div>
            <div className="space-y-2"><Label htmlFor="rbac-role-description">Description</Label><Textarea id="rbac-role-description" value={roleForm.description} onChange={(event) => setRoleForm({ ...roleForm, description: event.target.value })} /></div>
            <div className="flex items-center justify-between rounded-lg border p-3"><div><Label htmlFor="rbac-role-active">Rôle actif</Label><p className="text-xs text-muted-foreground">Un rôle inactif n'accorde plus ses permissions.</p></div><Switch id="rbac-role-active" checked={roleForm.actif} onCheckedChange={(actif) => setRoleForm({ ...roleForm, actif })} /></div>
            <DialogFooter><Button type="button" variant="outline" onClick={() => setRoleDialogOpen(false)} disabled={savingRole}>Annuler</Button><Button type="submit" disabled={savingRole}>{savingRole ? "Enregistrement..." : "Enregistrer"}</Button></DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(permissionRole)} onOpenChange={(open) => !open && setPermissionRole(null)}>
        <DialogContent className="sm:max-w-3xl">
          <DialogHeader><DialogTitle>Permissions de {permissionRole?.libelle}</DialogTitle><DialogDescription>La sauvegarde remplace l'ensemble des permissions du rôle. Les permissions absentes sont retirées.</DialogDescription></DialogHeader>
          <div className="max-h-[55vh] space-y-4 overflow-y-auto pr-1">
            {permissionsByDomain.map(([domain, domainPermissions]) => <div key={domain} className="rounded-xl border p-3"><p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">{domain}</p><div className="grid gap-2 sm:grid-cols-2">{domainPermissions.map((permission) => <label key={permission.code} className="flex cursor-pointer items-start gap-2 rounded-lg p-2 hover:bg-muted/60"><Checkbox checked={selectedPermissions.includes(permission.code)} onCheckedChange={(checked) => togglePermission(permission.code, checked === true)} /><span><span className="block text-sm font-medium">{permission.libelle}</span><span className="block font-mono text-[11px] text-muted-foreground">{permission.code}</span></span></label>)}</div></div>)}
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setPermissionRole(null)} disabled={savingPermissions}>Annuler</Button><Button onClick={() => void savePermissions()} disabled={savingPermissions}>{savingPermissions ? "Enregistrement..." : "Enregistrer les permissions"}</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(assignmentRole)} onOpenChange={(open) => !open && setAssignmentRole(null)}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader><DialogTitle>Affecter le rôle {assignmentRole?.libelle}</DialogTitle><DialogDescription>Sélectionnez les comptes qui porteront ce rôle. Le rôle legacy reste inchangé.</DialogDescription></DialogHeader>
          <div className="max-h-[50vh] space-y-2 overflow-y-auto pr-1">{users.length === 0 ? <p className="text-sm text-muted-foreground">Aucun compte disponible.</p> : users.map((user) => <label key={user.id} className="flex cursor-pointer items-center gap-3 rounded-lg border p-3 hover:bg-muted/50"><Checkbox checked={selectedUsers.includes(user.id)} onCheckedChange={(checked) => toggleUser(user.id, checked === true)} /><span className="min-w-0 flex-1"><span className="block text-sm font-medium">{user.prenom} {user.nom}</span><span className="block truncate text-xs text-muted-foreground">{user.email} · {user.roles.join(", ") || "Rôle dynamique non attribué"}</span></span>{user.is_active ? <Badge variant="secondary">Actif</Badge> : <Badge variant="outline">Inactif</Badge>}</label>)}</div>
          <DialogFooter><Button variant="outline" onClick={() => setAssignmentRole(null)} disabled={savingAssignment}>Annuler</Button><Button onClick={() => void saveAssignment()} disabled={savingAssignment}>{savingAssignment ? "Enregistrement..." : "Enregistrer les affectations"}</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={Boolean(deleteRole)} onOpenChange={(open) => !open && setDeleteRole(null)}>
        <AlertDialogContent><AlertDialogHeader><AlertDialogTitle>Supprimer le rôle {deleteRole?.libelle} ?</AlertDialogTitle><AlertDialogDescription>La suppression est refusée si des permissions ou des comptes lui sont affectés. Désactivez-le plutôt si vous souhaitez conserver l'historique.</AlertDialogDescription></AlertDialogHeader><AlertDialogFooter><AlertDialogCancel>Annuler</AlertDialogCancel><AlertDialogAction onClick={() => void confirmDeleteRole()} disabled={deletingRole} className="bg-destructive text-destructive-foreground">{deletingRole ? "Suppression..." : "Supprimer"}</AlertDialogAction></AlertDialogFooter></AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default RolesPermissions;
