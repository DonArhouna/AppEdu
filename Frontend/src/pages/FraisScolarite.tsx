import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Plus, Edit, Trash2, DollarSign, Settings, Layers, Lock } from "lucide-react";
import { toast } from "sonner";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";

interface TarificationConfig {
  id: string;
  filiere: string;
  niveau: string;
  droitsInscription: number;
  scolariteMensuelle: number;
  nbMois: number;
  totalAnnuel: number;
}

const FraisScolarite = () => {
  const [configs, setConfigs] = useState<TarificationConfig[]>([
    {
      id: "1",
      filiere: "Génie Informatique",
      niveau: "Licence 1",
      droitsInscription: 150000,
      scolariteMensuelle: 60000,
      nbMois: 9,
      totalAnnuel: 690000,
    },
    {
      id: "2",
      filiere: "Génie Informatique",
      niveau: "Licence 3",
      droitsInscription: 150000,
      scolariteMensuelle: 65000,
      nbMois: 9,
      totalAnnuel: 735000,
    },
    {
      id: "3",
      filiere: "Gestion & Finance",
      niveau: "Master 1",
      droitsInscription: 200000,
      scolariteMensuelle: 85000,
      nbMois: 9,
      totalAnnuel: 965000,
    },
  ]);

  const [showForm, setShowForm] = useState(false);
  const [editingConfig, setEditingConfig] = useState<TarificationConfig | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    filiere: "Génie Informatique",
    niveau: "Licence 1",
    droitsInscription: "150000",
    scolariteMensuelle: "60000",
    nbMois: "9",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const dInscr = parseFloat(formData.droitsInscription) || 0;
    const sMens = parseFloat(formData.scolariteMensuelle) || 0;
    const nMois = parseInt(formData.nbMois) || 9;
    const tot = dInscr + sMens * nMois;

    if (editingConfig) {
      setConfigs(
        configs.map((c) =>
          c.id === editingConfig.id
            ? {
                ...c,
                filiere: formData.filiere,
                niveau: formData.niveau,
                droitsInscription: dInscr,
                scolariteMensuelle: sMens,
                nbMois: nMois,
                totalAnnuel: tot,
              }
            : c
        )
      );
      toast.success("Grille tarifaire mise à jour.");
    } else {
      const newC: TarificationConfig = {
        id: String(Date.now()),
        filiere: formData.filiere,
        niveau: formData.niveau,
        droitsInscription: dInscr,
        scolariteMensuelle: sMens,
        nbMois: nMois,
        totalAnnuel: tot,
      };
      setConfigs([...configs, newC]);
      toast.success("Nouvelle grille tarifaire configurée.");
    }

    setShowForm(false);
    setEditingConfig(null);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Configuration des Tarifs & Frais</h1>
          <p className="text-muted-foreground mt-1">
            Définition des droits d'inscription et échéanciers de scolarité par filière et classe
          </p>
        </div>
        <Button onClick={() => setShowForm(!showForm)} className="shadow-md">
          <Plus className="mr-2 h-4 w-4" /> Nouvelle Grille Tarifaire
        </Button>
      </div>

      {/* Uniform KPI Cards Standard */}
      <div className="grid gap-5 md:grid-cols-3">
        <Card className="card-base relative overflow-hidden">
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-primary" />
          <CardHeader className="flex flex-row items-center justify-between pb-2 pl-5">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Grilles Configurées
            </CardTitle>
            <div className="p-2 rounded-xl bg-primary/10 text-primary">
              <Settings className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="pl-5">
            <div className="text-2xl font-bold text-foreground">{configs.length}</div>
            <p className="text-xs text-muted-foreground mt-1">Niveaux d'études paramétrés</p>
          </CardContent>
        </Card>

        <Card className="card-base relative overflow-hidden">
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-emerald-500" />
          <CardHeader className="flex flex-row items-center justify-between pb-2 pl-5">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Moyenne Droits d'Inscription
            </CardTitle>
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-500">
              <Lock className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="pl-5">
            <div className="text-2xl font-bold text-emerald-600 font-mono">
              {(
                configs.reduce((acc, c) => acc + c.droitsInscription, 0) / (configs.length || 1)
              ).toLocaleString()}{" "}
              FCFA
            </div>
            <p className="text-xs text-muted-foreground mt-1">Verrouillé au guichet</p>
          </CardContent>
        </Card>

        <Card className="card-base relative overflow-hidden">
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-purple-500" />
          <CardHeader className="flex flex-row items-center justify-between pb-2 pl-5">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Scolarité Mensuelle Moyenne
            </CardTitle>
            <div className="p-2 rounded-xl bg-purple-500/10 text-purple-500">
              <DollarSign className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="pl-5">
            <div className="text-2xl font-bold text-purple-600 font-mono">
              {(
                configs.reduce((acc, c) => acc + c.scolariteMensuelle, 0) / (configs.length || 1)
              ).toLocaleString()}{" "}
              FCFA
            </div>
            <p className="text-xs text-muted-foreground mt-1">Tarif mensuel standard</p>
          </CardContent>
        </Card>
      </div>

      {showForm && (
        <Card className="card-base">
          <CardHeader>
            <CardTitle>{editingConfig ? "Modifier" : "Créer"} une Grille Tarifaire</CardTitle>
            <CardDescription>
              Fixez les montants qui seront automatiquement appliqués lors des encaissements au guichet
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="filiere">Filière</Label>
                  <Select
                    value={formData.filiere}
                    onValueChange={(val) => setFormData({ ...formData, filiere: val })}
                  >
                    <SelectTrigger id="filiere">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Génie Informatique">Génie Informatique</SelectItem>
                      <SelectItem value="Gestion & Finance">Gestion & Finance</SelectItem>
                      <SelectItem value="Commerce & Marketing">Commerce & Marketing</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="niveau">Niveau / Classe</Label>
                  <Select
                    value={formData.niveau}
                    onValueChange={(val) => setFormData({ ...formData, niveau: val })}
                  >
                    <SelectTrigger id="niveau">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Licence 1">Licence 1</SelectItem>
                      <SelectItem value="Licence 2">Licence 2</SelectItem>
                      <SelectItem value="Licence 3">Licence 3</SelectItem>
                      <SelectItem value="Master 1">Master 1</SelectItem>
                      <SelectItem value="Master 2">Master 2</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="dInscr">Droits d'Inscription (FCFA)</Label>
                  <Input
                    id="dInscr"
                    type="number"
                    value={formData.droitsInscription}
                    onChange={(e) => setFormData({ ...formData, droitsInscription: e.target.value })}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="sMens">Frais de Scolarité Mensuels (FCFA)</Label>
                  <Input
                    id="sMens"
                    type="number"
                    value={formData.scolariteMensuelle}
                    onChange={(e) => setFormData({ ...formData, scolariteMensuelle: e.target.value })}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="nMois">Nombre de Mois d'Échéance</Label>
                  <Input
                    id="nMois"
                    type="number"
                    value={formData.nbMois}
                    onChange={(e) => setFormData({ ...formData, nbMois: e.target.value })}
                  />
                </div>
              </div>

              <div className="flex gap-2 justify-end pt-2">
                <Button type="button" variant="outline" onClick={() => setShowForm(false)}>
                  Annuler
                </Button>
                <Button type="submit">Enregistrer la Grille</Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Configurations Table */}
      <Card className="card-base">
        <CardHeader className="p-5">
          <CardTitle className="text-lg">Tarifs & Droits Configurés</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="border-t overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/40">
                  <TableHead>Filière</TableHead>
                  <TableHead>Niveau</TableHead>
                  <TableHead>Droits d'Inscription</TableHead>
                  <TableHead>Scolarité Mensuelle</TableHead>
                  <TableHead>Mois / An</TableHead>
                  <TableHead>Total Annuel Attendu</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {configs.map((c) => (
                  <TableRow key={c.id} className="hover:bg-muted/30">
                    <TableCell className="font-semibold text-sm">{c.filiere}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{c.niveau}</Badge>
                    </TableCell>
                    <TableCell className="font-mono font-bold text-foreground">
                      {c.droitsInscription.toLocaleString()} FCFA
                    </TableCell>
                    <TableCell className="font-mono font-semibold text-foreground">
                      {c.scolariteMensuelle.toLocaleString()} FCFA / mois
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">{c.nbMois} mois</TableCell>
                    <TableCell className="font-mono font-bold text-emerald-600">
                      {c.totalAnnuel.toLocaleString()} FCFA
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => {
                          setEditingConfig(c);
                          setFormData({
                            filiere: c.filiere,
                            niveau: c.niveau,
                            droitsInscription: String(c.droitsInscription),
                            scolariteMensuelle: String(c.scolariteMensuelle),
                            nbMois: String(c.nbMois),
                          });
                          setShowForm(true);
                        }}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => {
                          setConfigs(configs.filter((item) => item.id !== c.id));
                          toast.success("Grille tarifaire supprimée.");
                        }}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default FraisScolarite;
