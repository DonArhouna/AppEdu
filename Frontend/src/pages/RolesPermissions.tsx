import { useEffect, useMemo, useState } from "react";
import { LoaderCircle, ServerOff, ShieldCheck } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { usersApi } from "@/services/apiClient";
import type { User } from "@/services/apiTypes";

const roleDescriptions: Record<string, string> = {
  ADMIN: "Administration complète",
  DIRECTEUR_ETUDES: "Pilotage académique",
  SECRETARIAT: "Scolarité et inscriptions",
  COMPTABILITE: "Finances et encaissements",
  ENSEIGNANT: "Pédagogie et notation",
  ETUDIANT: "Portail et consultation personnelle",
};

const RolesPermissions = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => { void usersApi.getAll().then((result) => { setUsers(result.data || []); setLoading(false); }); }, []);
  const roles = useMemo(() => Array.from(new Set(users.map((user) => user.role))), [users]);
  return <div className="space-y-6"><div><h1 className="text-3xl font-bold text-foreground">Rôles & permissions</h1><p className="mt-1 text-muted-foreground">Rôles réellement utilisés par les comptes du backend.</p></div><Alert><ShieldCheck className="h-4 w-4" /><AlertTitle>Matrice personnalisable non activée</AlertTitle><AlertDescription>Les permissions sont actuellement vérifiées par les dépendances RBAC du backend. Les cases affichées dans l'ancienne interface n'étaient pas persistées.</AlertDescription></Alert><Card><CardHeader><CardTitle>Rôles observés</CardTitle><CardDescription>Ce tableau est reconstruit depuis les comptes, sans utilisateur fictif.</CardDescription></CardHeader><CardContent className="p-0"><Table><TableHeader><TableRow><TableHead>Rôle</TableHead><TableHead>Description</TableHead><TableHead>Comptes</TableHead><TableHead>État</TableHead></TableRow></TableHeader><TableBody>{loading ? <TableRow><TableCell colSpan={4} className="py-10 text-center"><LoaderCircle className="mx-auto h-5 w-5 animate-spin" /></TableCell></TableRow> : roles.length === 0 ? <TableRow><TableCell colSpan={4} className="py-10 text-center text-muted-foreground">Aucun compte.</TableCell></TableRow> : roles.map((role) => <TableRow key={role}><TableCell><Badge variant="outline">{role}</Badge></TableCell><TableCell>{roleDescriptions[role] || "Rôle défini par le backend"}</TableCell><TableCell>{users.filter((user) => user.role === role).length}</TableCell><TableCell><Badge variant="secondary">Actif côté RBAC</Badge></TableCell></TableRow>)}</TableBody></Table></CardContent></Card><div className="flex items-center gap-2 text-xs text-muted-foreground"><ServerOff className="h-4 w-4" />La création de rôles personnalisés nécessite une migration RBAC dédiée.</div></div>;
};

export default RolesPermissions;
