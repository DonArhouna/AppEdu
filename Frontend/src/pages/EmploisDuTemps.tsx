import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Calendar, Clock, Plus, Printer, Edit2, Trash2, Filter, Moon } from "lucide-react";
import { EmploiDuTempsDialog } from "@/components/pedagogie/EmploiDuTempsDialog";
import { toast } from "sonner";

interface CoursSession {
  id: string;
  jour: number; // 0: Lundi, 1: Mardi, 2: Mercredi, 3: Jeudi, 4: Vendredi, 5: Samedi
  heureDebut: string; // Ex: "08:00", "14:00", "18:00"
  heureFin: string; // Ex: "11:00" (3h course), "17:00", "21:00"
  matiere: string;
  prof: string;
  salle: string;
  filiere?: string;
  niveau?: string;
  isCoursDuSoir?: boolean;
}

export default function EmploisDuTemps() {
  const jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"];

  const timeSlots = [
    { label: "08:00 - 10:00 (Matin 1)", debut: "08:00" },
    { label: "10:00 - 12:00 (Matin 2)", debut: "10:00" },
    { label: "12:00 - 14:00 (Déjeuner / Pause)", debut: "12:00" },
    { label: "14:00 - 17:00 (Après-midi 3h)", debut: "14:00" },
    { label: "16:00 - 18:00 (Après-midi 2)", debut: "16:00" },
    { label: "18:00 - 21:00 (Cours du Soir 3h)", debut: "18:00", isSoir: true },
    { label: "20:00 - 22:00 (Cours du Soir 2h)", debut: "20:00", isSoir: true },
  ];

  const [filiereFilter, setFiliereFilter] = useState("informatique");
  const [niveauFilter, setNiveauFilter] = useState("l3");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingSession, setEditingSession] = useState<CoursSession | undefined>(undefined);
  const [selectedSlot, setSelectedSlot] = useState<{ jour: number; heureDebut: string }>({ jour: 0, heureDebut: "08:00" });

  const [cours, setCours] = useState<CoursSession[]>([
    { id: "1", jour: 0, heureDebut: "08:00", heureFin: "11:00", matiere: "Programmation Web React (3h)", prof: "M. Mamadou Diallo", salle: "Salle A101" },
    { id: "2", jour: 0, heureDebut: "14:00", heureFin: "17:00", matiere: "Base de données SQL (3h)", prof: "Mme Sophie Ndiaye", salle: "Labo 1" },
    { id: "3", jour: 1, heureDebut: "10:00", heureFin: "12:00", matiere: "Algorithmique Avancée", prof: "M. Jean-Philippe Sow", salle: "Amphi A" },
    { id: "4", jour: 2, heureDebut: "18:00", heureFin: "21:00", matiere: "Sécurité & Cryptographie (Cours du Soir 3h)", prof: "Mme Fatou Traoré", salle: "Labo 2", isCoursDuSoir: true },
    { id: "5", jour: 3, heureDebut: "14:00", heureFin: "16:00", matiere: "Gestion de projet Agile", prof: "M. Mamadou Diallo", salle: "Salle A204" },
    { id: "6", jour: 4, heureDebut: "18:00", heureFin: "21:00", matiere: "Développement Mobile Flutter (Cours du Soir 3h)", prof: "Mme Sophie Ndiaye", salle: "Labo 2", isCoursDuSoir: true },
  ]);

  const handleOpenAdd = (jIndex: number, hDebut: string) => {
    setEditingSession(undefined);
    setSelectedSlot({ jour: jIndex, heureDebut: hDebut });
    setDialogOpen(true);
  };

  const handleOpenEdit = (session: CoursSession, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingSession(session);
    setDialogOpen(true);
  };

  const handleDeleteSession = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setCours((prev) => prev.filter((c) => c.id !== id));
    toast.success("Cours retiré du planning.");
  };

  const handleSaveSession = (sessionData: CoursSession) => {
    setCours((prev) => {
      const exists = prev.some((c) => c.id === sessionData.id);
      if (exists) {
        return prev.map((c) => (c.id === sessionData.id ? sessionData : c));
      }
      return [...prev, sessionData];
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Emplois du Temps & Plannings</h1>
          <p className="text-muted-foreground mt-1">
            Créneaux horaires modulables (2h, 3h) et gestion des cours du soir jusqu'à 22h
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => window.print()} className="shadow-sm">
            <Printer className="h-4 w-4 mr-2" /> Imprimer / PDF
          </Button>

          <Button
            onClick={() => {
              setEditingSession(undefined);
              setSelectedSlot({ jour: 0, heureDebut: "08:00" });
              setDialogOpen(true);
            }}
            className="shadow-md"
          >
            <Plus className="h-4 w-4 mr-2" />
            Planifier un Cours
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card className="card-base">
        <CardContent className="p-4 sm:p-5">
          <div className="flex flex-col md:flex-row gap-4 items-center">
            <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground">
              <Filter className="h-4 w-4" /> Filtres d'Affichage :
            </div>

            <Select value={filiereFilter} onValueChange={setFiliereFilter}>
              <SelectTrigger className="w-full md:w-[240px] text-xs">
                <SelectValue placeholder="Filière" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="informatique">Licence Génie Informatique</SelectItem>
                <SelectItem value="gestion">Master Gestion & Finance</SelectItem>
                <SelectItem value="commerce">DUT Commerce & Marketing</SelectItem>
              </SelectContent>
            </Select>

            <Select value={niveauFilter} onValueChange={setNiveauFilter}>
              <SelectTrigger className="w-full md:w-[180px] text-xs">
                <SelectValue placeholder="Niveau" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="l1">Licence 1</SelectItem>
                <SelectItem value="l2">Licence 2</SelectItem>
                <SelectItem value="l3">Licence 3</SelectItem>
                <SelectItem value="m1">Master 1</SelectItem>
                <SelectItem value="m2">Master 2</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Schedule Weekly Grid */}
      <Card className="card-base">
        <CardHeader className="flex flex-row items-center justify-between pb-4 p-5">
          <div>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Calendar className="h-5 w-5 text-primary" />
              Planning Hebdomadaire (Créneaux 08h00 - 22h00)
            </CardTitle>
            <CardDescription className="text-xs">
              Cliquez sur n'importe quel créneau pour ajouter un cours avec horaires modulables
            </CardDescription>
          </div>

          <Badge className="bg-emerald-600 text-white font-mono">
            {cours.length} Cours Programmés
          </Badge>
        </CardHeader>

        <CardContent className="p-0">
          <div className="overflow-x-auto border-t">
            <div className="min-w-[950px]">
              <div className="grid grid-cols-7 gap-1 bg-muted/40 p-2 border-b">
                <div className="font-semibold text-xs text-muted-foreground p-2 flex items-center justify-center">
                  Créneau Horaire
                </div>
                {jours.map((jour) => (
                  <div
                    key={jour}
                    className="font-bold text-xs text-center p-2 rounded-lg bg-sidebar text-sidebar-foreground"
                  >
                    {jour}
                  </div>
                ))}
              </div>

              <div className="divide-y divide-border">
                {timeSlots.map((slot, hIndex) => (
                  <div key={hIndex} className={`grid grid-cols-7 gap-1 p-1 min-h-[110px] ${slot.isSoir ? "bg-amber-500/5 dark:bg-amber-950/10" : ""}`}>
                    {/* Time Slot Label */}
                    <div className="font-mono text-[11px] font-semibold text-muted-foreground p-2 flex flex-col justify-center items-center bg-muted/20 rounded-lg text-center">
                      <Clock className="h-3.5 w-3.5 text-primary mb-1" />
                      <span>{slot.label}</span>
                      {slot.isSoir && (
                        <span className="text-[9px] text-amber-600 font-bold flex items-center gap-0.5 mt-0.5">
                          <Moon className="h-2.5 w-2.5" /> Soir
                        </span>
                      )}
                    </div>

                    {/* Days Columns */}
                    {jours.map((_, jIndex) => {
                      const coursDuSlot = cours.find(
                        (c) => c.jour === jIndex && c.heureDebut === slot.debut
                      );

                      return (
                        <div
                          key={`${jIndex}-${slot.debut}`}
                          onClick={() => !coursDuSlot && handleOpenAdd(jIndex, slot.debut)}
                          className={`rounded-lg p-2 transition-all border flex flex-col justify-between group ${
                            coursDuSlot
                              ? "bg-primary/10 border-primary/30 hover:shadow-md cursor-pointer"
                              : "border-dashed border-border/60 hover:bg-primary/5 hover:border-primary/40 cursor-pointer"
                          }`}
                        >
                          {coursDuSlot ? (
                            <div className="space-y-1.5 h-full flex flex-col justify-between">
                              <div>
                                <div className="flex items-start justify-between gap-1">
                                  <span className="font-bold text-xs text-foreground leading-tight">
                                    {coursDuSlot.matiere}
                                  </span>
                                  <div className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-0.5">
                                    <button
                                      onClick={(e) => handleOpenEdit(coursDuSlot, e)}
                                      className="p-1 hover:text-primary"
                                    >
                                      <Edit2 className="h-3 w-3" />
                                    </button>
                                    <button
                                      onClick={(e) => handleDeleteSession(coursDuSlot.id, e)}
                                      className="p-1 hover:text-destructive"
                                    >
                                      <Trash2 className="h-3 w-3" />
                                    </button>
                                  </div>
                                </div>
                                <p className="text-[11px] text-muted-foreground font-medium mt-0.5">
                                  {coursDuSlot.prof}
                                </p>
                              </div>

                              <div className="flex items-center justify-between gap-1 mt-1">
                                <Badge
                                  variant="secondary"
                                  className="text-[10px] font-mono bg-primary/20 text-primary border-none"
                                >
                                  {coursDuSlot.salle}
                                </Badge>
                                <span className="font-mono text-[9px] font-bold text-muted-foreground">
                                  {coursDuSlot.heureDebut}-{coursDuSlot.heureFin}
                                </span>
                              </div>
                            </div>
                          ) : (
                            <div className="h-full flex items-center justify-center text-muted-foreground/30 group-hover:text-primary/70 transition-colors">
                              <Plus className="h-5 w-5" />
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Dialog */}
      <EmploiDuTempsDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        sessionToEdit={editingSession}
        initialJour={selectedSlot.jour}
        initialHeureDebut={selectedSlot.heureDebut}
        existingSessions={cours}
        onSave={handleSaveSession}
      />
    </div>
  );
}
