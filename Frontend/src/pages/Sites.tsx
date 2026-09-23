import { useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Building, MapPin, Users, Plus, ChevronDown, ChevronUp, Edit, Trash2, Eye } from "lucide-react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { SiteDialog } from "@/components/sites/SiteDialog";
import { toast } from "sonner";

const mockSites = [
  {
    id: "SITE001",
    nom: "Site A - Bâtiment Principal",
    campus: "Campus Principal",
    adresse: "123 Avenue de l'Université, Abidjan",
    superficie: "5000 m²",
    capacite: 400,
    effectifActuel: 356,
    batiments: [
      { nom: "Bâtiment A", etages: 3, salles: 12 },
      { nom: "Bâtiment B", etages: 2, salles: 8 },
    ],
    couleur: "bg-primary",
  },
  {
    id: "SITE002",
    nom: "Site B - Annexe",
    campus: "Campus Principal",
    adresse: "456 Rue des Sciences, Abidjan",
    superficie: "3500 m²",
    capacite: 250,
    effectifActuel: 234,
    batiments: [
      { nom: "Annexe 1", etages: 2, salles: 10 },
    ],
    couleur: "bg-primary",
  },
  {
    id: "SITE003",
    nom: "Site C - Laboratoires",
    campus: "Campus Principal",
    adresse: "789 Boulevard Technique, Abidjan",
    superficie: "2000 m²",
    capacite: 150,
    effectifActuel: 145,
    batiments: [
      { nom: "Labo Tech", etages: 1, salles: 6 },
    ],
    couleur: "bg-primary",
  },
  {
    id: "SITE004",
    nom: "Site Nord 1",
    campus: "Campus Nord",
    adresse: "12 Avenue du Nord, Abidjan",
    superficie: "4200 m²",
    capacite: 300,
    effectifActuel: 278,
    batiments: [
      { nom: "Bâtiment Nord A", etages: 3, salles: 15 },
    ],
    couleur: "bg-secondary",
  },
  {
    id: "SITE005",
    nom: "Site Nord 2",
    campus: "Campus Nord",
    adresse: "34 Rue Technologique, Abidjan",
    superficie: "3000 m²",
    capacite: 200,
    effectifActuel: 145,
    batiments: [
      { nom: "Bâtiment Nord B", etages: 2, salles: 10 },
    ],
    couleur: "bg-secondary",
  },
];

const Sites = () => {
  const [sites, setSites] = useState(mockSites);
  const [openSites, setOpenSites] = useState<string[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedSite, setSelectedSite] = useState<typeof mockSites[0] | undefined>();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [siteToDelete, setSiteToDelete] = useState<string | null>(null);

  const toggleSite = (siteId: string) => {
    setOpenSites((prev) =>
      prev.includes(siteId)
        ? prev.filter((id) => id !== siteId)
        : [...prev, siteId]
    );
  };

  const campusGroups = sites.reduce((acc, site) => {
    if (!acc[site.campus]) {
      acc[site.campus] = [];
    }
    acc[site.campus].push(site);
    return acc;
  }, {} as Record<string, typeof sites>);

  const handleSave = (site: typeof mockSites[0]) => {
    if (selectedSite) {
      setSites(sites.map(s => s.id === site.id ? site : s));
    } else {
      setSites([...sites, site]);
    }
    setSelectedSite(undefined);
  };

  const handleEdit = (site: typeof mockSites[0]) => {
    setSelectedSite(site);
    setDialogOpen(true);
  };

  const handleDelete = (id: string) => {
    setSites(sites.filter(s => s.id !== id));
    setDeleteDialogOpen(false);
    setSiteToDelete(null);
    toast.success("Site supprimé");
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Sites</h1>
          <p className="text-muted-foreground mt-2">
            Gérez les sites de chaque campus
          </p>
        </div>
        <Button onClick={() => { setSelectedSite(undefined); setDialogOpen(true); }}>
          <Plus className="h-4 w-4 mr-2" />
          Nouveau Site
        </Button>
      </div>

      <div className="space-y-6">
        {Object.entries(campusGroups).map(([campusNom, sites]) => (
          <Card key={campusNom}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MapPin className="h-5 w-5 text-primary" />
                {campusNom}
                <Badge variant="secondary" className="ml-2">
                  {sites.length} {sites.length > 1 ? "sites" : "site"}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {sites.map((site) => (
                <Collapsible
                  key={site.id}
                  open={openSites.includes(site.id)}
                  onOpenChange={() => toggleSite(site.id)}
                >
                  <Card className="border-2">
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-4 flex-1">
                          <div className={`rounded-lg ${site.couleur} p-3`}>
                            <Building className="h-6 w-6 text-white" />
                          </div>
                          <div className="flex-1">
                            <CardTitle className="text-lg">{site.nom}</CardTitle>
                            <p className="text-sm text-muted-foreground mt-1">
                              {site.adresse}
                            </p>
                            <div className="flex flex-wrap gap-4 mt-3 text-sm">
                              <div className="flex items-center gap-2 text-muted-foreground">
                                <Users className="h-4 w-4" />
                                <span>{site.effectifActuel} / {site.capacite} étudiants</span>
                              </div>
                              <div className="text-muted-foreground">
                                Superficie : {site.superficie}
                              </div>
                            </div>
                          </div>
                        </div>
                        <CollapsibleTrigger asChild>
                          <Button variant="ghost" size="sm">
                            {openSites.includes(site.id) ? (
                              <ChevronUp className="h-4 w-4" />
                            ) : (
                              <ChevronDown className="h-4 w-4" />
                            )}
                          </Button>
                        </CollapsibleTrigger>
                      </div>
                    </CardHeader>

                    <CollapsibleContent>
                      <CardContent className="pt-0">
                        <div className="space-y-3">
                          <h4 className="text-sm font-semibold text-foreground">
                            Bâtiments ({site.batiments.length})
                          </h4>
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead>Bâtiment</TableHead>
                                <TableHead>Étages</TableHead>
                                <TableHead>Salles</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {site.batiments.map((batiment) => (
                                <TableRow key={batiment.nom}>
                                  <TableCell className="font-medium">
                                    {batiment.nom}
                                  </TableCell>
                                  <TableCell>{batiment.etages}</TableCell>
                                  <TableCell>{batiment.salles}</TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>

                          <div className="pt-2 flex gap-2">
                            <Link to={`/sites/${site.id}`}>
                              <Button variant="outline" size="sm">
                                <Eye className="h-4 w-4 mr-2" />
                                Voir
                              </Button>
                            </Link>
                            <Button variant="outline" size="sm" onClick={() => handleEdit(site)}>
                              <Edit className="h-4 w-4 mr-2" />
                              Modifier
                            </Button>
                            <Button variant="outline" size="sm" onClick={() => { setSiteToDelete(site.id); setDeleteDialogOpen(true); }}>
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </CollapsibleContent>
                  </Card>
                </Collapsible>
              ))}
            </CardContent>
          </Card>
        ))}
      </div>

      <SiteDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        site={selectedSite}
        onSave={handleSave}
      />

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmer la suppression</AlertDialogTitle>
            <AlertDialogDescription>
              Êtes-vous sûr de vouloir supprimer ce site ? Cette action est irréversible.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction onClick={() => siteToDelete && handleDelete(siteToDelete)}>
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default Sites;
