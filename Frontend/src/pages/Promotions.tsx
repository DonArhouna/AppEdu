import { useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { GraduationCap, Users, Calendar, Plus, Edit, Trash2, Eye } from "lucide-react";
import { PromotionDialog } from "@/components/promotions/PromotionDialog";
import { toast } from "sonner";

const mockPromotions = [
  {
    id: "PROMO001",
    nom: "Licence 1 Informatique 2024",
    annee: "2024-2025",
    effectif: 45,
    dateDebut: "2024-09-01",
    dateFin: "2025-06-30",
    statut: "actif",
  },
  {
    id: "PROMO002",
    nom: "Master 1 Gestion 2024",
    annee: "2024-2025",
    effectif: 32,
    dateDebut: "2024-09-01",
    dateFin: "2025-06-30",
    statut: "actif",
  },
  {
    id: "PROMO003",
    nom: "Licence 3 Commerce 2023",
    annee: "2023-2024",
    effectif: 38,
    dateDebut: "2023-09-01",
    dateFin: "2024-06-30",
    statut: "cloture",
  },
];

const Promotions = () => {
  const [promotions, setPromotions] = useState(mockPromotions);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedPromotion, setSelectedPromotion] = useState<typeof mockPromotions[0] | undefined>();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [promotionToDelete, setPromotionToDelete] = useState<string | null>(null);

  const handleSave = (promotion: typeof mockPromotions[0]) => {
    if (selectedPromotion) {
      setPromotions(promotions.map(p => p.id === promotion.id ? promotion : p));
    } else {
      setPromotions([...promotions, promotion]);
    }
    setSelectedPromotion(undefined);
  };

  const handleEdit = (promotion: typeof mockPromotions[0]) => {
    setSelectedPromotion(promotion);
    setDialogOpen(true);
  };

  const handleDelete = (id: string) => {
    setPromotions(promotions.filter(p => p.id !== id));
    setDeleteDialogOpen(false);
    setPromotionToDelete(null);
    toast.success("Promotion supprimée");
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Promotions</h1>
          <p className="text-muted-foreground mt-2">
            Gérez les promotions et leurs effectifs
          </p>
        </div>
        <Button onClick={() => { setSelectedPromotion(undefined); setDialogOpen(true); }}>
          <Plus className="h-4 w-4 mr-2" />
          Nouvelle Promotion
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {promotions.map((promo) => (
          <Card key={promo.id} className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <div className="rounded-lg bg-primary/10 p-2">
                    <GraduationCap className="h-5 w-5 text-primary" />
                  </div>
                  <Badge
                    variant={promo.statut === "actif" ? "default" : "secondary"}
                    className={
                      promo.statut === "actif"
                        ? "bg-success text-success-foreground"
                        : ""
                    }
                  >
                    {promo.statut}
                  </Badge>
                </div>
              </div>
              <CardTitle className="mt-4 text-lg">{promo.nom}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Calendar className="h-4 w-4" />
                <span>{promo.annee}</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Users className="h-4 w-4" />
                <span>{promo.effectif} étudiants</span>
              </div>
              <div className="pt-4 flex gap-2">
                <Link to={`/promotions/${promo.id}`} className="flex-1">
                  <Button variant="outline" size="sm" className="w-full">
                    <Eye className="h-4 w-4 mr-2" />
                    Voir
                  </Button>
                </Link>
                <Button variant="outline" size="sm" className="flex-1" onClick={() => handleEdit(promo)}>
                  <Edit className="h-4 w-4 mr-2" />
                  Modifier
                </Button>
                <Button variant="outline" size="sm" onClick={() => { setPromotionToDelete(promo.id); setDeleteDialogOpen(true); }}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <PromotionDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        promotion={selectedPromotion}
        onSave={handleSave}
      />

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmer la suppression</AlertDialogTitle>
            <AlertDialogDescription>
              Êtes-vous sûr de vouloir supprimer cette promotion ? Cette action est irréversible.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction onClick={() => promotionToDelete && handleDelete(promotionToDelete)}>
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default Promotions;
