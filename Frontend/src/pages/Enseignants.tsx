import { useEffect, useMemo, useState } from "react";
import { AlertCircle, GraduationCap, Loader2, RefreshCw } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { usersApi, extractErrorMessage } from "@/services/apiClient";
import type { User } from "@/services/apiTypes";

const Enseignants = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const load = async () => { setLoading(true); setError(null); const result = await usersApi.getAll(); if (result.error) setError(result.error); else setUsers(result.data || []); setLoading(false); };
  useEffect(() => { void load(); }, []);
  const teachers = useMemo(() => users.filter((user) => user.role === "ENSEIGNANT" && `${user.prenom} ${user.nom} ${user.email}`.toLowerCase().includes(search.toLowerCase())), [users, search]);
  return <div className="space-y-6"><div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><div><h1 className="text-3xl font-bold text-foreground">Enseignants</h1><p className="mt-1 text-muted-foreground">Comptes enseignants enregistrés dans le backend.</p></div><Button variant="outline" onClick={load} disabled={loading}><RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />Actualiser</Button></div>{error && <Alert variant="destructive"><AlertCircle className="h-4 w-4" /><AlertTitle>Erreur backend</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}<Card><CardHeader><CardTitle className="flex items-center gap-2"><GraduationCap className="h-5 w-5 text-primary" />Annuaire ({teachers.length})</CardTitle><CardDescription>Les spécialités et contrats devront être ajoutés au modèle RH backend.</CardDescription></CardHeader><CardContent className="space-y-4"><Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Rechercher un enseignant" /><div className="overflow-x-auto rounded-lg border"><Table><TableHeader><TableRow><TableHead>Nom</TableHead><TableHead>Email</TableHead><TableHead>Téléphone</TableHead><TableHead>Statut</TableHead></TableRow></TableHeader><TableBody>{loading ? <TableRow><TableCell colSpan={4} className="py-10 text-center"><Loader2 className="mx-auto h-5 w-5 animate-spin" /></TableCell></TableRow> : teachers.length === 0 ? <TableRow><TableCell colSpan={4} className="py-10 text-center text-muted-foreground">Aucun compte enseignant.</TableCell></TableRow> : teachers.map((user) => <TableRow key={user.id}><TableCell className="font-medium">{user.prenom} {user.nom}</TableCell><TableCell>{user.email}</TableCell><TableCell>{user.telephone || "Non renseigné"}</TableCell><TableCell><Badge variant={user.is_active ? "default" : "secondary"}>{user.is_active ? "Actif" : "Inactif"}</Badge></TableCell></TableRow>)}</TableBody></Table></div></CardContent></Card></div>;
};

export default Enseignants;
