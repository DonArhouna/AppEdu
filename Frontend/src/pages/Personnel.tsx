import { useEffect, useMemo, useState } from "react";
import { AlertCircle, Loader2, RefreshCw, ShieldCheck, Users } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { usersApi, extractErrorMessage } from "@/services/apiClient";
import type { User } from "@/services/apiTypes";

const Personnel = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [search, setSearch] = useState("");
  const [role, setRole] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true); setError(null);
    const result = await usersApi.getAll();
    if (result.error) setError(result.error); else setUsers(result.data || []);
    setLoading(false);
  };
  useEffect(() => { void load(); }, []);

  const staff = useMemo(() => users.filter((user) => !["ETUDIANT", "ADMIN"].includes(user.role)), [users]);
  const roles = useMemo(() => Array.from(new Set(staff.map((user) => user.role))), [staff]);
  const filtered = staff.filter((user) => {
    const query = search.toLowerCase();
    return (!query || `${user.prenom} ${user.nom} ${user.email}`.toLowerCase().includes(query)) && (role === "all" || user.role === role);
  });

  return <div className="space-y-6">
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><div><h1 className="text-3xl font-bold text-foreground">Personnel & utilisateurs professionnels</h1><p className="mt-1 text-muted-foreground">Les comptes professionnels proviennent de l'API utilisateurs.</p></div><Button variant="outline" onClick={load} disabled={loading}><RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />Actualiser</Button></div>
    {error && <Alert variant="destructive"><AlertCircle className="h-4 w-4" /><AlertTitle>Erreur backend</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}
    <Alert><ShieldCheck className="h-4 w-4" /><AlertTitle>Informations RH à venir</AlertTitle><AlertDescription>Le modèle Utilisateur ne contient pas encore les attributs RH (poste, département, date d'embauche). Ces champs ne sont pas simulés ici.</AlertDescription></Alert>
    <Card><CardContent className="space-y-4 p-4 sm:p-6"><div className="flex flex-col gap-3 md:flex-row"><Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Rechercher un compte" /><Select value={role} onValueChange={setRole}><SelectTrigger className="md:w-64"><SelectValue placeholder="Rôle" /></SelectTrigger><SelectContent><SelectItem value="all">Tous les rôles</SelectItem>{roles.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent></Select></div><div className="overflow-x-auto rounded-lg border"><Table><TableHeader><TableRow><TableHead>Nom</TableHead><TableHead>Email</TableHead><TableHead>Rôle</TableHead><TableHead>Téléphone</TableHead><TableHead>Statut</TableHead></TableRow></TableHeader><TableBody>{loading ? <TableRow><TableCell colSpan={5} className="py-10 text-center"><Loader2 className="mx-auto h-5 w-5 animate-spin" /></TableCell></TableRow> : filtered.length === 0 ? <TableRow><TableCell colSpan={5} className="py-10 text-center text-muted-foreground">Aucun compte professionnel.</TableCell></TableRow> : filtered.map((user) => <TableRow key={user.id}><TableCell className="font-medium">{user.prenom} {user.nom}</TableCell><TableCell>{user.email}</TableCell><TableCell><Badge variant="outline">{user.role}</Badge></TableCell><TableCell>{user.telephone || "Non renseigné"}</TableCell><TableCell><Badge variant={user.is_active ? "default" : "secondary"}>{user.is_active ? "Actif" : "Inactif"}</Badge></TableCell></TableRow>)}</TableBody></Table></div></CardContent></Card>
    <p className="text-xs text-muted-foreground">Pour gérer les rôles et statuts, utilisez la page Comptes utilisateurs.</p>
  </div>;
};

export default Personnel;
