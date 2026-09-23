import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Clock,
  CheckCircle2,
  AlertTriangle,
  Send,
  MoreVertical,
  History,
  FileCheck,
  User,
  Phone,
  Mail,
  Calendar,
  Layers,
} from "lucide-react";
import { notificationService, type NotificationLog } from "@/services/notificationService";
import { toast } from "sonner";

export interface CandidatureItem {
  id: string;
  nom: string;
  prenom: string;
  email: string;
  telephone: string;
  filiere: string;
  cycle: string;
  dateDepot: string;
  statut: "recue" | "examen" | "pieces_manquantes" | "admis" | "inscrit";
  piecesManquantes?: string[];
  documentsFournis?: string[];
  moyenneDernierDiplome?: number;
}

const KANBAN_COLUMNS: {
  id: CandidatureItem["statut"];
  title: string;
  colorClass: string;
  borderClass: string;
  badgeBg: string;
}[] = [
  {
    id: "recue",
    title: "1. Reçue",
    colorClass: "text-blue-600 dark:text-blue-400",
    borderClass: "border-blue-500/30",
    badgeBg: "bg-blue-500/15 text-blue-700 dark:text-blue-300",
  },
  {
    id: "examen",
    title: "2. En examen",
    colorClass: "text-purple-600 dark:text-purple-400",
    borderClass: "border-purple-500/30",
    badgeBg: "bg-purple-500/15 text-purple-700 dark:text-purple-300",
  },
  {
    id: "pieces_manquantes",
    title: "3. Pièces manquantes",
    colorClass: "text-amber-600 dark:text-amber-400",
    borderClass: "border-amber-500/30",
    badgeBg: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
  },
  {
    id: "admis",
    title: "4. Admis",
    colorClass: "text-emerald-600 dark:text-emerald-400",
    borderClass: "border-emerald-500/30",
    badgeBg: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  },
  {
    id: "inscrit",
    title: "5. Inscrit",
    colorClass: "text-teal-600 dark:text-teal-400",
    borderClass: "border-teal-500/30",
    badgeBg: "bg-teal-500/15 text-teal-700 dark:text-teal-300",
  },
];

interface AdmissionsKanbanProps {
  candidatures: CandidatureItem[];
  onStatusChange: (candidatId: string, newStatus: CandidatureItem["statut"]) => void;
}

export const AdmissionsKanban = ({
  candidatures,
  onStatusChange,
}: AdmissionsKanbanProps) => {
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [selectedCandidatForLogs, setSelectedCandidatForLogs] = useState<CandidatureItem | null>(null);
  const [logsDialogOpen, setLogsDialogOpen] = useState(false);

  // Drag & Drop Handlers
  const handleDragStart = (id: string) => {
    setDraggedId(id);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (targetColId: CandidatureItem["statut"]) => {
    if (!draggedId) return;

    const candidat = candidatures.find((c) => c.id === draggedId);
    if (!candidat || candidat.statut === targetColId) {
      setDraggedId(null);
      return;
    }

    // Move status
    onStatusChange(draggedId, targetColId);

    // Automatic notification trigger
    const sent = notificationService.sendNotification(candidat, targetColId);
    toast.success(
      `Candidature déplacée vers "${targetColId.replace("_", " ").toUpperCase()}". Notification envoyée à ${candidat.prenom} !`,
      {
        description: `SMS: "${sent.smsSent.slice(0, 75)}..."`,
        duration: 4000,
      }
    );

    setDraggedId(null);
  };

  const handleManualMove = (candidat: CandidatureItem, targetColId: CandidatureItem["statut"]) => {
    if (candidat.statut === targetColId) return;
    onStatusChange(candidat.id, targetColId);
    const sent = notificationService.sendNotification(candidat, targetColId);
    toast.success(
      `Statut mis à jour pour ${candidat.prenom} ${candidat.nom}. Notification automatique déclenchée !`,
      {
        description: `SMS transmis : "${sent.smsSent.slice(0, 75)}..."`,
      }
    );
  };

  const openCandidateLogs = (candidat: CandidatureItem) => {
    setSelectedCandidatForLogs(candidat);
    setLogsDialogOpen(true);
  };

  const currentLogs: NotificationLog[] = selectedCandidatForLogs
    ? notificationService.getLogsForCandidat(selectedCandidatForLogs.id)
    : [];

  return (
    <div className="space-y-4">
      {/* 5-Column Responsive Board */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-3.5 items-start">
        {KANBAN_COLUMNS.map((col) => {
          const itemsInCol = candidatures.filter((c) => c.statut === col.id);

          return (
            <div
              key={col.id}
              onDragOver={handleDragOver}
              onDrop={() => handleDrop(col.id)}
              className={`rounded-2xl p-3 border transition-colors bg-card/60 backdrop-blur-xs min-h-[480px] flex flex-col ${col.borderClass}`}
            >
              {/* Column Header */}
              <div className="flex items-center justify-between pb-3 border-b border-border/60 mb-3">
                <span className={`text-xs font-bold uppercase tracking-wider ${col.colorClass}`}>
                  {col.title}
                </span>
                <Badge className={`h-5 px-1.5 text-[10px] font-bold border-none ${col.badgeBg}`}>
                  {itemsInCol.length}
                </Badge>
              </div>

              {/* Cards list */}
              <div className="space-y-2.5 flex-1">
                {itemsInCol.length === 0 ? (
                  <div className="h-28 rounded-xl border border-dashed border-border/80 flex items-center justify-center text-xs text-muted-foreground/60 text-center p-2">
                    Glissez un dossier ici
                  </div>
                ) : (
                  itemsInCol.map((candidat) => (
                    <div
                      key={candidat.id}
                      draggable
                      onDragStart={() => handleDragStart(candidat.id)}
                      className={`p-3 rounded-xl border bg-background hover:shadow-md transition-all cursor-grab active:cursor-grabbing group relative ${
                        draggedId === candidat.id ? "opacity-40 border-primary" : "border-border/80"
                      }`}
                    >
                      {/* Card Header: Name & Action menu */}
                      <div className="flex items-start justify-between gap-1">
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-bold text-foreground truncate group-hover:text-primary transition-colors">
                            {candidat.prenom} {candidat.nom}
                          </p>
                          <p className="text-[10px] text-muted-foreground truncate">{candidat.filiere}</p>
                        </div>

                        {/* Quick action menu */}
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-6 w-6 rounded-lg text-muted-foreground hover:text-foreground"
                            >
                              <MoreVertical className="h-3.5 w-3.5" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="w-52 rounded-xl text-xs">
                            <DropdownMenuLabel className="text-[10px] uppercase font-bold text-muted-foreground">
                              Changer de statut
                            </DropdownMenuLabel>
                            {KANBAN_COLUMNS.map((target) => (
                              <DropdownMenuItem
                                key={target.id}
                                disabled={target.id === candidat.statut}
                                onClick={() => handleManualMove(candidat, target.id)}
                                className="cursor-pointer"
                              >
                                Vers {target.title}
                              </DropdownMenuItem>
                            ))}
                            <DropdownMenuItem
                              onClick={() => openCandidateLogs(candidat)}
                              className="cursor-pointer text-primary"
                            >
                              <History className="h-3.5 w-3.5 mr-1.5" /> Voir les notifications
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>

                      {/* Missing Docs or Badge */}
                      {col.id === "pieces_manquantes" && candidat.piecesManquantes && (
                        <div className="mt-2 p-1.5 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200/60 dark:border-amber-900/40 text-[10px] text-amber-800 dark:text-amber-200 space-y-0.5">
                          <span className="font-semibold flex items-center gap-1">
                            <AlertTriangle className="h-2.5 w-2.5" /> Manquants :
                          </span>
                          <span className="line-clamp-2">{candidat.piecesManquantes.join(", ")}</span>
                        </div>
                      )}

                      {/* Footer: Date & Quick History Button */}
                      <div className="flex items-center justify-between text-[10px] text-muted-foreground mt-2.5 pt-2 border-t border-border/50">
                        <span className="flex items-center gap-1">
                          <Calendar className="h-2.5 w-2.5" /> {candidat.dateDepot}
                        </span>

                        <button
                          type="button"
                          onClick={() => openCandidateLogs(candidat)}
                          title="Historique des notifications"
                          className="flex items-center gap-1 hover:text-primary transition-colors font-medium text-[9px] bg-muted/60 px-1.5 py-0.5 rounded-md"
                        >
                          <Send className="h-2.5 w-2.5 text-primary" /> Notifs
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* History Dialog */}
      <Dialog open={logsDialogOpen} onOpenChange={setLogsDialogOpen}>
        <DialogContent className="sm:max-w-[560px] rounded-2xl">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold flex items-center gap-2">
              <History className="h-5 w-5 text-primary" />
              Historique des Notifications — {selectedCandidatForLogs?.prenom} {selectedCandidatForLogs?.nom}
            </DialogTitle>
            <DialogDescription>
              Traçabilité des e-mails et SMS transactionnels envoyés pour cette candidature.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2 max-h-[360px] overflow-y-auto scrollbar-thin">
            {currentLogs.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center py-8">
                Aucune notification envoyée pour le moment.
              </p>
            ) : (
              currentLogs.map((log) => (
                <div key={log.id} className="p-3 rounded-xl border border-border/80 bg-muted/20 space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-foreground uppercase tracking-wider text-[10px]">
                      Étape : {log.statut.replace("_", " ")}
                    </span>
                    <span className="text-[10px] text-muted-foreground">{log.timestamp}</span>
                  </div>
                  <p className="text-xs text-muted-foreground font-mono bg-background p-2 rounded-lg border">
                    {log.messagePreview}
                  </p>
                  <div className="flex items-center gap-2 pt-1 text-[10px] text-emerald-600 font-medium">
                    <CheckCircle2 className="h-3 w-3" /> Transmis par SMS ({selectedCandidatForLogs?.telephone}) et Email ({selectedCandidatForLogs?.email})
                  </div>
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};
