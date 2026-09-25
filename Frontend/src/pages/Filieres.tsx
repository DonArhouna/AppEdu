import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AlertCircle, Building2, Edit, Eye, GraduationCap, Layers3, Plus, RefreshCw, Search, Trash2 } from "lucide-react";
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
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FiliereDialog, type Filiere } from "@/components/filieres/FiliereDialog";
import { extractErrorMessage, structureApi } from "@/services/apiClient";

interface DepartementOption {
  id: string;
  nom: string;
}

interface FiliereGroup {
  id: string;
  nom: string;
  filieres: Filiere[];
}

const Filieres = () => {
  const [filieres, setFilieres] = useState<Filiere[]>([]);
  const [departements, setDepartements] = useState<DepartementOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("all");

  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedFiliere, setSelectedFiliere] = useState<Filiere>();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [filiereToDelete, setFiliereToDelete] = useState<string | null>(null);

  const loadFilieres = async () => {
    setLoading(true);
    setError(null);
    try {
      const [filieresResult, departementsResult] = await Promise.all([
        structureApi.getFilieres(),
        structureApi.getDepartements(),
      ]);
      if (filieresResult.error || departementsResult.error) {
        setError(extractErrorMessage(filieresResult.error || departementsResult.error, "Impossible de charger les filières."));
        setFilieres([]);
        setDepartements([]);
      } else {
        setFilieres((filieresResult.data || []) as unknown as Filiere[]);
        setDepartements((departementsResult.data || []).map((item) => ({ id: item.id, nom: item.nom })));
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erreur de connexion au serveur backend.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadFilieres();
  }, []);

  const filteredFilieres = useMemo(() => {
    const query = search.trim().toLocaleLowerCase("fr");
    return filieres.filter((filiere) => {
      const matchesDepartment = departmentFilter === "all" || (filiere.departement_id || "unassigned") === departmentFilter;
      const matchesSearch = !query || `${filiere.nom} ${filiere.code} ${filiere.description || ""}`.toLocaleLowerCase("fr").includes(query);
      return matchesDepartment && matchesSearch;
    });
  }, [departmentFilter, filieres, search]);

  const groups = useMemo<FiliereGroup[]>(() => {
    const byDepartment = new Map<string, FiliereGroup>();
    departements.forEach((department) => byDepartment.set(department.id, { id: department.id, nom: department.nom, filieres: [] }));
    byDepartment.set("unassigned", { id: "unassigned", nom: "Filières non rattachées", filieres: [] });
    filteredFilieres.forEach((filiere) => {
      const key = filiere.departement_id || "unassigned";
      const group = byDepartment.get(key) || { id: key, nom: "Département inconnu", filieres: [] };
      group.filieres.push(filiere);
      byDepartment.set(key, group);
    });
    return Array.from(byDepartment.values()).filter((group) => group.filieres.length > 0);
  }, [departements, filteredFilieres]);

  const handleSave = async (filiereData: Filiere) => {
    const payload = {
      nom: filiereData.nom,
      code: filiereData.code,
      description: filiereData.description || "",
      diplome: filiereData.diplome,
      duree: Number(filiereData.duree),
      departement_id: filiereData.departement_id || undefined,
    };

    const result = selectedFiliere
      ? await structureApi.updateFiliere(selectedFiliere.id, payload)
      : await structureApi.createFiliere(payload);
    if (result.error) {
      toast.error(extractErrorMessage(result.error, "La filière n'a pas pu être enregistrée."));
      return false;
    }
    toast.success(selectedFiliere ? "Filière mise à jour." : "Filière enregistrée.");
    setSelectedFiliere(undefined);
    await loadFilieres();
    return true;
  };

  const handleEdit = (filiere: Filiere) => {
    setSelectedFiliere(filiere);
    setDialogOpen(true);
  };

  const handleDelete = async () => {
    if (!filiereToDelete) return;
    const result = await structureApi.deleteFiliere(filiereToDelete);
    if (result.error) {
      toast.error(extractErrorMessage(result.error, "La filière n'a pas pu être supprimée."));
      return;
    }
    toast.success("Filière supprimée.");
    setDeleteDialogOpen(false);
    setFiliereToDelete(null);
    await loadFilieres();
  };

  const openCreateDialog = () => {
    setSelectedFiliere(undefined);
    setDialogOpen(true);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Filières & offre de formation</h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            Regroupez les filières par département pour retrouver rapidement un programme et le rattacher à ses classes.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button asChild variant="outline" size="sm">
            <Link to="/academic-structure"><GraduationCap className="mr-2 h-4 w-4" />Gérer les classes</Link>
          </Button>
          <Button variant="outline" size="sm" onClick={() => void loadFilieres()} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Actualiser
          </Button>
          <Button size="sm" onClick={openCreateDialog}>
            <Plus className="mr-2 h-4 w-4" />
            Nouvelle filière
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Filières indisponibles</AlertTitle>
          <AlertDescription className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <span>{error}</span>
            <Button variant="outline" size="sm" onClick={() => void loadFilieres()}>Réessayer</Button>
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardContent className="p-4 sm:p-5">
          <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_280px]">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Rechercher une filière par nom, code ou description"
                className="pl-9"
                aria-label="Rechercher une filière"
              />
            </div>
            <Select value={departmentFilter} onValueChange={setDepartmentFilter}>
              <SelectTrigger aria-label="Filtrer par département">
                <SelectValue placeholder="Tous les départements" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous les départements</SelectItem>
                {departements.map((department) => (
                  <SelectItem key={department.id} value={department.id}>{department.nom}</SelectItem>
                ))}
                {filieres.some((filiere) => !filiere.departement_id) && (
                  <SelectItem value="unassigned">Non rattachées</SelectItem>
                )}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {loading ? (
        <Card><CardContent className="flex min-h-56 flex-col items-center justify-center gap-3 text-sm text-muted-foreground"><RefreshCw className="h-7 w-7 animate-spin text-primary" />Chargement des filières...</CardContent></Card>
      ) : filieres.length === 0 ? (
        <Card><CardContent className="flex min-h-64 flex-col items-center justify-center gap-3 text-center"><GraduationCap className="h-10 w-10 text-muted-foreground/50" /><p className="font-semibold text-foreground">Aucune filière enregistrée</p><p className="max-w-sm text-sm text-muted-foreground">Créez une filière et rattachez-la à un département pour structurer l'offre de formation.</p><Button onClick={openCreateDialog}><Plus className="mr-2 h-4 w-4" />Créer une filière</Button></CardContent></Card>
      ) : groups.length === 0 ? (
        <Card><CardContent className="flex min-h-48 flex-col items-center justify-center gap-2 text-center"><Search className="h-8 w-8 text-muted-foreground/50" /><p className="font-semibold">Aucune filière ne correspond aux filtres</p><p className="text-sm text-muted-foreground">Modifiez la recherche ou le département sélectionné.</p></CardContent></Card>
      ) : (
        <div className="space-y-8">
          {groups.map((group) => (
            <section key={group.id} className="space-y-3" aria-labelledby={`department-${group.id}`}>
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  {group.id === "unassigned" ? <Layers3 className="h-4 w-4" /> : <Building2 className="h-4 w-4" />}
                </div>
                <div>
                  <h2 id={`department-${group.id}`} className="text-lg font-semibold tracking-tight">{group.nom}</h2>
                  <p className="text-xs text-muted-foreground">{group.filieres.length} filière(s) dans ce regroupement</p>
                </div>
              </div>

              <div className="space-y-3">
                {group.filieres.map((filiere) => (
                  <Card key={filiere.id} className="overflow-hidden transition-shadow hover:shadow-md">
                    <CardContent className="p-0">
                      <div className="flex flex-col gap-5 p-4 sm:p-5 xl:flex-row xl:items-center xl:justify-between">
                        <div className="flex min-w-0 flex-1 items-start gap-4">
                          <div className="hidden h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary sm:flex">
                            <GraduationCap className="h-5 w-5" />
                          </div>
                          <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                              <h3 className="truncate text-base font-semibold text-foreground">{filiere.nom}</h3>
                              <Badge variant="outline" className="font-mono text-[10px]">{filiere.code}</Badge>
                            </div>
                            <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{filiere.description || "Aucune description fournie"}</p>
                            <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                              <Badge variant="secondary" className="font-normal">{filiere.diplome || "Diplôme non renseigné"}</Badge>
                              <span>Durée : <strong className="text-foreground">{filiere.duree ?? "non renseignée"}</strong>{filiere.duree ? " an(s)" : ""}</span>
                              <span>•</span>
                              <span>UEs : <strong className="text-foreground">{filiere.unites_enseignement?.length ?? 0}</strong></span>
                            </div>
                          </div>
                        </div>

                        <div className="flex flex-wrap items-center gap-2 border-t border-border/60 pt-4 xl:justify-end xl:border-0 xl:pt-0">
                          <Button asChild variant="outline" size="sm">
                            <Link to={`/filieres/${filiere.id}`}><Eye className="mr-1.5 h-3.5 w-3.5" />Voir</Link>
                          </Button>
                          <Button asChild variant="outline" size="sm">
                            <Link to={`/academic-structure?filiere=${filiere.id}`}><GraduationCap className="mr-1.5 h-3.5 w-3.5" />Classes</Link>
                          </Button>
                          <Button variant="outline" size="sm" onClick={() => handleEdit(filiere)}><Edit className="mr-1.5 h-3.5 w-3.5" />Modifier</Button>
                          <Button variant="ghost" size="icon" className="text-destructive hover:bg-destructive/10 hover:text-destructive" onClick={() => { setFiliereToDelete(filiere.id); setDeleteDialogOpen(true); }} aria-label={`Supprimer ${filiere.nom}`}>
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}

      <FiliereDialog open={dialogOpen} onOpenChange={setDialogOpen} filiere={selectedFiliere} departements={departements} onSave={handleSave} />

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Supprimer cette filière ?</AlertDialogTitle>
            <AlertDialogDescription>Les UEs, classes et données qui lui sont rattachées peuvent empêcher cette suppression. L'opération sera refusée si une dépendance existe.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction onClick={() => void handleDelete()} className="bg-destructive text-destructive-foreground">Supprimer</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default Filieres;
