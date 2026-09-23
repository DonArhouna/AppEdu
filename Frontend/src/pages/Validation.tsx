import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Check,
  X,
  Eye,
  Clock,
  Settings2,
  Sparkles,
  UserCheck,
  AlertTriangle,
  Send,
  Plus,
  Kanban,
  ListFilter,
} from "lucide-react";
import { KpiCard } from "@/components/ui/kpi-card";
import { AdmissionsKanban, type CandidatureItem } from "@/components/admissions/AdmissionsKanban";
import { NotificationTemplateEditor } from "@/components/admissions/NotificationTemplateEditor";
import { notificationService } from "@/services/notificationService";
import { toast } from "sonner";

const initialCandidatures: CandidatureItem[] = [
  {
    id: "APP001",
    nom: "Kouassi",
    prenom: "Ange",
    email: "ange.kouassi@email.com",
    telephone: "+225 07 08 12 34 56",
    filiere: "Génie Informatique (L3)",
    cycle: "Licence",
    dateDepot: "15 Janv. 2026",
    statut: "recue",
    moyenneDernierDiplome: 14.5,
  },
  {
    id: "APP002",
    nom: "Yao",
    prenom: "Michel",
    email: "michel.yao@email.com",
    telephone: "+225 05 06 78 90 12",
    filiere: "Gestion & Finance (M1)",
    cycle: "Master",
    dateDepot: "16 Janv. 2026",
    statut: "pieces_manquantes",
    piecesManquantes: ["Relevé de notes officiel Bac", "Photocopie CNI certifiée"],
  },
  {
    id: "APP003",
    nom: "Kouame",
    prenom: "Esther",
    email: "esther.kouame@email.com",
    telephone: "+225 01 02 34 56 78",
    filiere: "Commerce & Marketing (L2)",
    cycle: "Licence",
    dateDepot: "14 Janv. 2026",
    statut: "examen",
  },
  {
    id: "APP004",
    nom: "Diallo",
    prenom: "Mamadou",
    email: "mamadou.diallo@email.com",
    telephone: "+225 07 45 67 89 01",
    filiere: "Génie Informatique (M2)",
    cycle: "Master",
    dateDepot: "12 Janv. 2026",
    statut: "admis",
  },
  {
    id: "APP005",
    nom: "Traoré",
    prenom: "Aïcha",
    email: "aicha.traore@email.com",
    telephone: "+225 05 12 34 99 00",
    filiere: "Réseaux & Télécoms (L3)",
    cycle: "Licence",
    dateDepot: "10 Janv. 2026",
    statut: "inscrit",
  },
  {
    id: "APP006",
    nom: "Sow",
    prenom: "Ibrahima",
    email: "ibrahima.sow@email.com",
    telephone: "+225 07 99 88 77 66",
    filiere: "Génie Informatique (L1)",
    cycle: "Licence",
    dateDepot: "18 Janv. 2026",
    statut: "recue",
  },
];

const Validation = () => {
  const [candidatures, setCandidatures] = useState<CandidatureItem[]>(initialCandidatures);
  const [templateEditorOpen, setTemplateEditorOpen] = useState(false);

  const handleStatusChange = (candidatId: string, newStatus: CandidatureItem["statut"]) => {
    setCandidatures((prev) =>
      prev.map((c) => (c.id === candidatId ? { ...c, statut: newStatus } : c))
    );
  };

  const handleValidateFromTable = (id: string) => {
    const candidat = candidatures.find((c) => c.id === id);
    if (!candidat) return;
    handleStatusChange(id, "admis");
    notificationService.sendNotification(candidat, "admis");
    toast.success(`Dossier de ${candidat.prenom} ${candidat.nom} validé (Admis) ! Notification envoyée.`);
  };

  const handleRequestMissingDocs = (id: string) => {
    const candidat = candidatures.find((c) => c.id === id);
    if (!candidat) return;
    const updated = {
      ...candidat,
      statut: "pieces_manquantes" as const,
      piecesManquantes: ["Relevé de notes N-1", "2 photos d'identité"],
    };
    setCandidatures((prev) => prev.map((c) => (c.id === id ? updated : c)));
    notificationService.sendNotification(updated, "pieces_manquantes");
    toast.warning(`Alerte pièces manquantes transmise à ${candidat.prenom} par SMS et Email.`);
  };

  // KPIs
  const totalRecues = candidatures.length;
  const totalEnExamen = candidatures.filter((c) => c.statut === "examen" || c.statut === "recue").length;
  const totalPiecesManquantes = candidatures.filter((c) => c.statut === "pieces_manquantes").length;
  const totalAdmis = candidatures.filter((c) => c.statut === "admis" || c.statut === "inscrit").length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground">
            Validation des Dossiers & Admissions
          </h1>
          <p className="text-muted-foreground mt-1">
            Tableau Kanban interactif des candidatures et déclenchement automatique des notifications
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => setTemplateEditorOpen(true)}
            className="rounded-xl shadow-xs"
          >
            <Settings2 className="h-4 w-4 mr-2 text-primary" />
            Modèles Notifications (SMS / Email)
          </Button>
        </div>
      </div>

      {/* Uniform KPI Cards Standard */}
      <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          title="Total Candidatures"
          value={totalRecues}
          icon={UserCheck}
          subtitle="Campagne 2025-2026"
          trend="+18%"
          trendDirection="up"
          trendLabel="vs session N-1"
          colorVariant="primary"
        />
        <KpiCard
          title="En Instruction"
          value={totalEnExamen}
          icon={Clock}
          subtitle="Comité pédagogique"
          colorVariant="purple"
        />
        <KpiCard
          title="Pièces Manquantes"
          value={totalPiecesManquantes}
          icon={AlertTriangle}
          subtitle="Relances en cours"
          trend="Action requise"
          trendDirection="down"
          trendLabel="sous 72h"
          colorVariant="amber"
        />
        <KpiCard
          title="Admis & Inscrits"
          value={totalAdmis}
          icon={Check}
          subtitle="Taux d'admission : 82%"
          trend="+8%"
          trendDirection="up"
          colorVariant="emerald"
        />
      </div>

      {/* Tabs View: Kanban vs Table */}
      <Tabs defaultValue="kanban" className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <TabsList className="rounded-xl p-1 bg-muted">
            <TabsTrigger value="kanban" className="flex items-center gap-1.5 rounded-lg text-xs font-semibold">
              <Kanban className="h-4 w-4" />
              Vue Kanban (Glisser-Déposer)
            </TabsTrigger>
            <TabsTrigger value="table" className="flex items-center gap-1.5 rounded-lg text-xs font-semibold">
              <ListFilter className="h-4 w-4" />
              Vue Tableau & Décision
            </TabsTrigger>
          </TabsList>

          <span className="text-xs text-muted-foreground hidden sm:inline">
            💡 Glissez une carte d'une colonne à l'autre pour déclencher automatiquement l'email et le SMS correspondant.
          </span>
        </div>

        {/* Tab 1: Kanban Board */}
        <TabsContent value="kanban" className="space-y-4">
          <AdmissionsKanban
            candidatures={candidatures}
            onStatusChange={handleStatusChange}
          />
        </TabsContent>

        {/* Tab 2: Table View */}
        <TabsContent value="table">
          <Card className="card-base overflow-hidden">
            <CardHeader className="p-4 border-b bg-muted/20">
              <CardTitle className="text-sm font-semibold">
                Registre des Candidatures en Instance
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto scrollbar-thin">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/40">
                      <TableHead className="font-bold text-[11px] uppercase">ID</TableHead>
                      <TableHead className="font-bold text-[11px] uppercase">Candidat</TableHead>
                      <TableHead className="font-bold text-[11px] uppercase">Filière</TableHead>
                      <TableHead className="font-bold text-[11px] uppercase">Date Dépôt</TableHead>
                      <TableHead className="font-bold text-[11px] uppercase">Statut Actuel</TableHead>
                      <TableHead className="text-right font-bold text-[11px] uppercase pr-5">Actions Décisionnelles</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {candidatures.map((c) => (
                      <TableRow key={c.id} className="hover:bg-muted/30 transition-colors">
                        <TableCell className="font-mono text-xs font-semibold text-primary">{c.id}</TableCell>
                        <TableCell>
                          <div className="flex flex-col">
                            <span className="font-semibold text-xs text-foreground">{c.prenom} {c.nom}</span>
                            <span className="text-[10px] text-muted-foreground">{c.email} • {c.telephone}</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-xs">{c.filiere}</TableCell>
                        <TableCell className="text-xs text-muted-foreground">{c.dateDepot}</TableCell>
                        <TableCell>
                          <Badge
                            className={`text-[10px] font-semibold ${
                              c.statut === "admis" || c.statut === "inscrit"
                                ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30"
                                : c.statut === "pieces_manquantes"
                                ? "bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30"
                                : "bg-primary/15 text-primary border-primary/30"
                            }`}
                          >
                            {c.statut.replace("_", " ").toUpperCase()}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right pr-5">
                          <div className="flex items-center justify-end gap-1.5">
                            {c.statut !== "admis" && c.statut !== "inscrit" && (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleValidateFromTable(c.id)}
                                className="h-7 text-xs rounded-lg text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50"
                              >
                                <Check className="h-3.5 w-3.5 mr-1" /> Valider
                              </Button>
                            )}
                            {c.statut !== "pieces_manquantes" && (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleRequestMissingDocs(c.id)}
                                className="h-7 text-xs rounded-lg text-amber-600 hover:text-amber-700 hover:bg-amber-50"
                              >
                                <AlertTriangle className="h-3.5 w-3.5 mr-1" /> Pièces manquantes
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Notification Template Editor Dialog */}
      <NotificationTemplateEditor
        open={templateEditorOpen}
        onOpenChange={setTemplateEditorOpen}
      />
    </div>
  );
};

export default Validation;
