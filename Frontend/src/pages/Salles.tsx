import { useEffect, useMemo, useState } from "react";
import { AlertCircle, DoorOpen, Edit, MapPin, Plus, RefreshCw, Search, Trash2, UsersRound } from "lucide-react";
import { toast } from "sonner";

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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import SalleDialog, { type SalleEditee } from "@/components/salles/SalleDialog";
import { extractErrorMessage, structureApi } from "@/services/apiClient";
import type { Campus, Salle } from "@/services/apiTypes";

const Salles = () => {
  const [salles, setSalles] = useState<Salle[]>([]);
  const [campus, setCampus] = useState<Campus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [campusFilter, setCampusFilter] = useState("all");
  const [disponibiliteFilter, setDisponibiliteFilter] = useState("all");

  const [dialogOpen, setDialogOpen] = useState(false);
  const [salleEditee, setSalleEditee] = useState<SalleEditee>();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [salleASupprimer, setSalleASupprimer] = useState<Salle | null>(null);

  const loadSalles = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sallesResult, campusResult] = await Promise.all([
        structureApi.getSalles(),
        structureApi.getCampuses(),
      ]);
      if (sallesResult.error || campusResult.error) {
        setError(extractErrorMessage(sallesResult.error || campusResult.error, "Impossible de charger les salles."));
        setSalles([]);
      } else {
        setSalles((sallesResult.data || []) as unknown as Salle[]);
        setCampus((campusResult.data || []) as unknown as Campus[]);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erreur de connexion au serveur backend.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadSalles();
  }, []);

  const sallesFiltrees = useMemo(() => {
    const query = search.trim().toLocaleLowerCase("fr");
    return salles.filter((salle) => {
      const matchesCampus = campusFilter === "all" || (salle.campus_id || "none") === campusFilter;
      const matchesDisponibilite =
        disponibiliteFilter === "all" ||
        (disponibiliteFilter === "disponible" ? salle.disponible : !salle.disponible);
      const matchesSearch =
        !query ||
        `${salle.nom} ${salle.code} ${salle.batiment || ""} ${salle.type_salle} ${salle.equipements || ""}`
          .toLocaleLowerCase("fr")
          .includes(query);
      return matchesCampus && matchesDisponibilite && matchesSearch;
    });
  }, [salles, search, campusFilter, disponibiliteFilter]);

  const campusParId = useMemo(() => new Map(campus.map((item) => [item.id, item.nom])), [campus]);

  const handleSave = async (salle: SalleEditee): Promise<boolean> => {
    const payload = {
      nom: salle.nom,
      code: salle.code,
      type_salle: salle.type_salle,
      capacite: salle.capacite ?? null,
      campus_id: salle.campus_id || null,
      batiment: salle.batiment || null,
      etage: salle.etage || null,
      equipements: salle.equipements || null,
      disponible: salle.disponible,
    };
    const result = salle.id
      ? await structureApi.updateSalle(salle.id, payload)
      : await structureApi.createSalle(payload);
    if (result.error) {
      toast.error(extractErrorMessage(result.error, "La salle n'a pas pu être enregistrée."));
      return false;
    }
    toast.success(salle.id ? "Salle mise à jour." : "Salle enregistrée.");
    setSalleEditee(undefined);
    await loadSalles();
    return true;
  };

  const handleDelete = async () => {
    if (!salleASupprimer) return;
    const result = await structureApi.deleteSalle(salleASupprimer.id);
    if (result.error) {
      toast.error(extractErrorMessage(result.error, "La salle n'a pas pu être supprimée."));
      return;
    }
    toast.success("Salle supprimée.");
    setDeleteDialogOpen(false);
    setSalleASupprimer(null);
    await loadSalles();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Salles de cours</h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            Inventaire des lieux : la détection de conflits d'emploi du temps s'appuie sur le nom de ces salles.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => void loadSalles()} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Actualiser
          </Button>
          <Button size="sm" onClick={() => { setSalleEditee(undefined); setDialogOpen(true); }}>
            <Plus className="mr-2 h-4 w-4" />
            Nouvelle salle
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          <div className="flex items-center gap-2"><AlertCircle className="h-4 w-4" /><span>{error}</span></div>
        </div>
      )}

      <Card>
        <CardContent className="grid gap-3 p-4 md:grid-cols-3">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Rechercher par nom, code, bâtiment..."
              className="pl-9"
              aria-label="Rechercher une salle"
            />
          </div>
          <Select value={campusFilter} onValueChange={setCampusFilter}>
            <SelectTrigger aria-label="Filtrer par campus"><SelectValue placeholder="Tous les campus" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous les campus</SelectItem>
              {campus.map((item) => <SelectItem key={item.id} value={item.id}>{item.nom}</SelectItem>)}
              <SelectItem value="none">Sans campus</SelectItem>
            </SelectContent>
          </Select>
          <Select value={disponibiliteFilter} onValueChange={setDisponibiliteFilter}>
            <SelectTrigger aria-label="Filtrer par disponibilité"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Toutes</SelectItem>
              <SelectItem value="disponible">Disponibles</SelectItem>
              <SelectItem value="indisponible">Indisponibles</SelectItem>
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {loading ? (
        <Card><CardContent className="flex min-h-56 flex-col items-center justify-center gap-3 text-sm text-muted-foreground"><RefreshCw className="h-7 w-7 animate-spin text-primary" />Chargement des salles...</CardContent></Card>
      ) : sallesFiltrees.length === 0 ? (
        <Card>
          <CardContent className="flex min-h-64 flex-col items-center justify-center gap-3 text-center">
            <DoorOpen className="h-10 w-10 text-muted-foreground/50" />
            <p className="font-semibold text-foreground">
              {salles.length === 0 ? "Aucune salle enregistrée" : "Aucune salle ne correspond aux filtres"}
            </p>
            <p className="max-w-sm text-sm text-muted-foreground">
              Créez vos salles pour que l'emploi du temps détecte les conflits de lieu et d'enseignant.
            </p>
            {salles.length === 0 && (
              <Button onClick={() => { setSalleEditee(undefined); setDialogOpen(true); }}>
                <Plus className="mr-2 h-4 w-4" />Créer une salle
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {sallesFiltrees.map((salle) => (
            <Card key={salle.id} className="flex flex-col">
              <CardContent className="flex flex-1 flex-col gap-3 p-5">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex min-w-0 items-start gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                      <DoorOpen className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="truncate text-base font-semibold text-foreground">{salle.nom}</h3>
                      <p className="font-mono text-xs text-muted-foreground">{salle.code}</p>
                    </div>
                  </div>
                  <Badge variant={salle.disponible ? "secondary" : "destructive"} className="shrink-0">
                    {salle.disponible ? "Disponible" : "Indisponible"}
                  </Badge>
                </div>
                <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                  <Badge variant="outline" className="font-normal">{salle.type_salle}</Badge>
                  {salle.capacite != null && (
                    <span className="flex items-center gap-1"><UsersRound className="h-3.5 w-3.5" />{salle.capacite} places</span>
                  )}
                  {salle.batiment && (
                    <span className="flex items-center gap-1"><MapPin className="h-3.5 w-3.5" />{salle.batiment}{salle.etage ? ` · ${salle.etage}` : ""}</span>
                  )}
                  {salle.campus_id && campusParId.get(salle.campus_id) && (
                    <span>{campusParId.get(salle.campus_id)}</span>
                  )}
                </div>
                {salle.equipements && (
                  <p className="line-clamp-2 text-xs text-muted-foreground">{salle.equipements}</p>
                )}
                <div className="mt-auto flex items-center gap-2 border-t border-border/60 pt-3">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => { setSalleEditee(salle); setDialogOpen(true); }}
                  >
                    <Edit className="mr-1.5 h-3.5 w-3.5" />Modifier
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                    onClick={() => { setSalleASupprimer(salle); setDeleteDialogOpen(true); }}
                    aria-label={`Supprimer ${salle.nom}`}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <SalleDialog open={dialogOpen} onOpenChange={setDialogOpen} salle={salleEditee} campus={campus} onSave={handleSave} />

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Supprimer la salle « {salleASupprimer?.nom} » ?</AlertDialogTitle>
            <AlertDialogDescription>
              La suppression sera refusée si des cours planifiés citent cette salle. Pour la retirer de la
              planification sans la supprimer, marquez-la comme indisponible.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction onClick={() => void handleDelete()} className="bg-destructive text-destructive-foreground">
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default Salles;
