import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  CalendarDays,
  Plus,
  Edit,
  Trash2,
  Users,
  CreditCard,
  Clock,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Calendar,
  Layers,
  ArrowUpDown,
  Sliders
} from "lucide-react";
import { toast } from "sonner";
import {
  AcademicSession,
  PaymentPeriod,
  getAcademicSessions,
  saveAcademicSession,
  deleteAcademicSession,
  getStudentCountForSession,
} from "@/services/academicSessionService";

const MOIS_LIST = [
  "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
  "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
];

export const SessionsConfig = () => {
  const [sessions, setSessions] = useState<AcademicSession[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingSession, setEditingSession] = useState<AcademicSession | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [sessionToDelete, setSessionToDelete] = useState<AcademicSession | null>(null);

  // Form states
  const [nom, setNom] = useState("");
  const [code, setCode] = useState("");
  const [anneeAcademique, setAnneeAcademique] = useState("2025-2026");
  const [dateDebut, setDateDebut] = useState("2025-09-01");
  const [dateFin, setDateFin] = useState("2026-06-30");
  const [statut, setStatut] = useState<"active" | "planifiee" | "cloturee">("active");
  const [description, setDescription] = useState("");
  const [periodes, setPeriodes] = useState<PaymentPeriod[]>([]);

  const loadData = () => {
    setSessions(getAcademicSessions());
  };

  useEffect(() => {
    loadData();
    const handleUpdate = () => loadData();
    window.addEventListener("emp_sessions_changed", handleUpdate);
    return () => window.removeEventListener("emp_sessions_changed", handleUpdate);
  }, []);

  const openCreateDialog = () => {
    setEditingSession(null);
    setNom("");
    setCode(`SES-${new Date().getFullYear().toString().slice(-2)}-${Math.floor(10 + Math.random() * 90)}`);
    setAnneeAcademique("2025-2026");
    setDateDebut("2025-09-01");
    setDateFin("2026-06-30");
    setStatut("active");
    setDescription("");
    // Default 3 Tranches template
    setPeriodes([
      { id: `per-${Date.now()}-1`, nom: "Tranche 1 (Octobre)", mois: "Octobre", dateEcheance: "2025-10-15", pourcentage: 40, ordre: 1 },
      { id: `per-${Date.now()}-2`, nom: "Tranche 2 (Janvier)", mois: "Janvier", dateEcheance: "2026-01-15", pourcentage: 30, ordre: 2 },
      { id: `per-${Date.now()}-3`, nom: "Tranche 3 (Avril)", mois: "Avril", dateEcheance: "2026-04-15", pourcentage: 30, ordre: 3 },
    ]);
    setDialogOpen(true);
  };

  const openEditDialog = (session: AcademicSession) => {
    setEditingSession(session);
    setNom(session.nom);
    setCode(session.code);
    setAnneeAcademique(session.anneeAcademique);
    setDateDebut(session.dateDebut);
    setDateFin(session.dateFin);
    setStatut(session.statut);
    setDescription(session.description || "");
    setPeriodes(session.periodes || []);
    setDialogOpen(true);
  };

  const handleApplyPreset = (presetType: "3tranches" | "4tranches" | "10mensuel" | "2semestres") => {
    const ts = Date.now();
    if (presetType === "3tranches") {
      setPeriodes([
        { id: `per-${ts}-1`, nom: "Tranche 1 (Octobre)", mois: "Octobre", dateEcheance: "2025-10-15", pourcentage: 40, ordre: 1 },
        { id: `per-${ts}-2`, nom: "Tranche 2 (Janvier)", mois: "Janvier", dateEcheance: "2026-01-15", pourcentage: 30, ordre: 2 },
        { id: `per-${ts}-3`, nom: "Tranche 3 (Avril)", mois: "Avril", dateEcheance: "2026-04-15", pourcentage: 30, ordre: 3 },
      ]);
      toast.success("Modèle 3 Tranches appliqué.");
    } else if (presetType === "4tranches") {
      setPeriodes([
        { id: `per-${ts}-1`, nom: "Tranche 1 (Février)", mois: "Février", dateEcheance: "2026-02-15", pourcentage: 30, ordre: 1 },
        { id: `per-${ts}-2`, nom: "Tranche 2 (Avril)", mois: "Avril", dateEcheance: "2026-04-15", pourcentage: 25, ordre: 2 },
        { id: `per-${ts}-3`, nom: "Tranche 3 (Juin)", mois: "Juin", dateEcheance: "2026-06-15", pourcentage: 25, ordre: 3 },
        { id: `per-${ts}-4`, nom: "Tranche 4 (Août)", mois: "Août", dateEcheance: "2026-08-15", pourcentage: 20, ordre: 4 },
      ]);
      toast.success("Modèle 4 Tranches appliqué.");
    } else if (presetType === "2semestres") {
      setPeriodes([
        { id: `per-${ts}-1`, nom: "Semestre 1 (Octobre)", mois: "Octobre", dateEcheance: "2025-10-20", pourcentage: 50, ordre: 1 },
        { id: `per-${ts}-2`, nom: "Semestre 2 (Février)", mois: "Février", dateEcheance: "2026-02-20", pourcentage: 50, ordre: 2 },
      ]);
      toast.success("Modèle 2 Semestres appliqué.");
    } else if (presetType === "10mensuel") {
      const months = ["Septembre", "Octobre", "Novembre", "Décembre", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin"];
      setPeriodes(
        months.map((m, idx) => ({
          id: `per-${ts}-${idx}`,
          nom: `Mensualité ${m}`,
          mois: m,
          dateEcheance: `2025-${String(idx + 9 > 12 ? idx - 3 : idx + 9).padStart(2, "0")}-10`,
          pourcentage: 10,
          ordre: idx + 1,
        }))
      );
      toast.success("Modèle 10 Mensualités appliqué.");
    }
  };

  const handleAddPeriod = () => {
    const nextOrdre = periodes.length + 1;
    const newPeriod: PaymentPeriod = {
      id: `per-${Date.now()}`,
      nom: `Tranche ${nextOrdre}`,
      mois: "Octobre",
      dateEcheance: new Date().toISOString().split("T")[0],
      pourcentage: 0,
      ordre: nextOrdre,
    };
    setPeriodes([...periodes, newPeriod]);
  };

  const handleUpdatePeriod = (id: string, field: keyof PaymentPeriod, value: any) => {
    setPeriodes(
      periodes.map((p) => {
        if (p.id === id) {
          const updated = { ...p, [field]: value };
          if (field === "mois" && !p.nom.startsWith("Tranche personnalisée")) {
            // Auto update name if simple
            updated.nom = `Tranche ${p.ordre} (${value})`;
          }
          return updated;
        }
        return p;
      })
    );
  };

  const handleDeletePeriod = (id: string) => {
    setPeriodes(periodes.filter((p) => p.id !== id).map((p, idx) => ({ ...p, ordre: idx + 1 })));
  };

  const handleSaveSession = (e: React.FormEvent) => {
    e.preventDefault();

    if (!nom.trim()) {
      toast.error("Veuillez saisir un nom pour la session.");
      return;
    }

    if (periodes.length === 0) {
      toast.error("Veuillez configurer au moins une période de paiement pour cette session.");
      return;
    }

    const sessionData: AcademicSession = {
      id: editingSession ? editingSession.id : `SES-${Date.now()}`,
      nom: nom.trim(),
      code: code.trim() || `SES-${Date.now()}`,
      anneeAcademique,
      dateDebut,
      dateFin,
      statut,
      description: description.trim(),
      periodes,
    };

    saveAcademicSession(sessionData);
    toast.success(editingSession ? "Session académique mise à jour avec succès !" : "Nouvelle session académique créée !");
    setDialogOpen(false);
  };

  const handleConfirmDelete = () => {
    if (!sessionToDelete) return;
    const attachedCount = getStudentCountForSession(sessionToDelete.id);
    if (attachedCount > 0) {
      toast.warning(`Attention : ${attachedCount} étudiant(s) sont encore rattachés à cette session. Ils devront être réassignés.`);
    }
    deleteAcademicSession(sessionToDelete.id);
    toast.success(`La session "${sessionToDelete.nom}" a été supprimée.`);
    setDeleteDialogOpen(false);
    setSessionToDelete(null);
  };

  const totalActiveSessions = sessions.filter((s) => s.statut === "active").length;
  const totalStudents = sessions.reduce((acc, s) => acc + getStudentCountForSession(s.id), 0);
  const totalPeriods = sessions.reduce((acc, s) => acc + s.periodes.length, 0);

  return (
    <div className="space-y-6">
      {/* ── Page Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="h-10 w-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
              <CalendarDays className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
                Sessions Académiques & Échéanciers
              </h1>
              <p className="text-muted-foreground text-xs sm:text-sm">
                Configuration des calendriers universitaires et découpage dynamique des tranches de paiement
              </p>
            </div>
          </div>
        </div>

        <Button onClick={openCreateDialog} className="rounded-xl shadow-sm gap-2">
          <Plus className="h-4 w-4" />
          Nouvelle Session
        </Button>
      </div>

      {/* ── Top Summary KPIs ── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="rounded-2xl border-border/70 shadow-xs">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Sessions Actives</p>
              <p className="text-2xl font-bold text-foreground mt-1">{totalActiveSessions} / {sessions.length}</p>
            </div>
            <div className="h-10 w-10 rounded-xl bg-emerald-500/10 text-emerald-600 flex items-center justify-center">
              <CheckCircle2 className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-2xl border-border/70 shadow-xs">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Étudiants Rattachés</p>
              <p className="text-2xl font-bold text-foreground mt-1">{totalStudents}</p>
            </div>
            <div className="h-10 w-10 rounded-xl bg-blue-500/10 text-blue-600 flex items-center justify-center">
              <Users className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-2xl border-border/70 shadow-xs">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Périodes Financières</p>
              <p className="text-2xl font-bold text-foreground mt-1">{totalPeriods} tranches</p>
            </div>
            <div className="h-10 w-10 rounded-xl bg-amber-500/10 text-amber-600 flex items-center justify-center">
              <CreditCard className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── Sessions List Cards ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {sessions.map((session) => {
          const studentCount = getStudentCountForSession(session.id);
          const isActif = session.statut === "active";

          return (
            <Card
              key={session.id}
              className={`rounded-2xl border transition-all ${
                isActif ? "border-primary/30 shadow-xs bg-card" : "border-border/60 bg-muted/5 opacity-90"
              }`}
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <CardTitle className="text-lg font-bold">{session.nom}</CardTitle>
                      <Badge
                        variant={isActif ? "default" : session.statut === "planifiee" ? "outline" : "secondary"}
                        className={isActif ? "bg-emerald-600 text-white hover:bg-emerald-700" : ""}
                      >
                        {session.statut === "active" ? "Active" : session.statut === "planifiee" ? "Planifiée" : "Clôturée"}
                      </Badge>
                    </div>
                    <CardDescription className="text-xs flex items-center gap-2">
                      <span className="font-mono font-medium text-foreground">{session.code}</span>
                      <span>•</span>
                      <span>Année : {session.anneeAcademique}</span>
                    </CardDescription>
                  </div>

                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 rounded-lg"
                      onClick={() => openEditDialog(session)}
                      title="Modifier la session"
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 rounded-lg text-destructive hover:bg-destructive/10"
                      onClick={() => {
                        setSessionToDelete(session);
                        setDeleteDialogOpen(true);
                      }}
                      title="Supprimer"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>

              <CardContent className="space-y-4 pt-0">
                {session.description && (
                  <p className="text-xs text-muted-foreground italic">{session.description}</p>
                )}

                <div className="grid grid-cols-2 gap-3 text-xs p-3 rounded-xl bg-muted/40 border border-border/50">
                  <div className="flex items-center gap-2">
                    <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
                    <span>
                      <strong className="text-foreground">Début :</strong> {session.dateDebut}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
                    <span>
                      <strong className="text-foreground">Fin :</strong> {session.dateFin}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 col-span-2">
                    <Users className="h-3.5 w-3.5 text-primary" />
                    <span>
                      <strong className="text-foreground">{studentCount}</strong> étudiant(s) rattaché(s) à cette session
                    </span>
                  </div>
                </div>

                {/* Attached Payment Periods */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold flex items-center gap-1.5 text-foreground">
                      <CreditCard className="h-3.5 w-3.5 text-primary" />
                      Échéancier Financier ({session.periodes.length} périodes)
                    </span>
                    <span className="text-[11px] text-muted-foreground">Appliqué en fenêtre de paiement</span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {session.periodes.map((p) => (
                      <div
                        key={p.id}
                        className="p-2.5 rounded-xl border border-border/70 bg-background/60 flex items-center justify-between text-xs"
                      >
                        <div className="flex flex-col">
                          <span className="font-semibold text-foreground truncate">{p.nom}</span>
                          <span className="text-[10px] text-muted-foreground">
                            Mois : {p.mois} {p.dateEcheance ? `• Échéance : ${p.dateEcheance}` : ""}
                          </span>
                        </div>
                        {p.pourcentage ? (
                          <Badge variant="outline" className="text-[10px] font-mono shrink-0 ml-2">
                            {p.pourcentage}%
                          </Badge>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* ── Modal Create / Edit Session ── */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-xl">
              <CalendarDays className="h-5 w-5 text-primary" />
              {editingSession ? "Modifier la Session Académique" : "Nouvelle Session Académique"}
            </DialogTitle>
            <DialogDescription>
              Définissez les paramètres de la session et configurez les périodes de paiement correspondantes.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSaveSession} className="space-y-5 py-2">
            {/* Session details */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="session-nom" className="text-xs font-bold">Nom de la Session *</Label>
                <Input
                  id="session-nom"
                  value={nom}
                  onChange={(e) => setNom(e.target.value)}
                  placeholder="Ex : Session Principale 2025-2026, Session Septembre..."
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="session-code" className="text-xs font-bold">Code / Identifiant *</Label>
                <Input
                  id="session-code"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="Ex : SES-25-26-A"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="session-annee" className="text-xs font-bold">Année Académique</Label>
                <Select value={anneeAcademique} onValueChange={setAnneeAcademique}>
                  <SelectTrigger id="session-annee">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="2024-2025">2024-2025</SelectItem>
                    <SelectItem value="2025-2026">2025-2026</SelectItem>
                    <SelectItem value="2026-2027">2026-2027</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="session-debut" className="text-xs font-bold">Date de Début *</Label>
                <Input
                  id="session-debut"
                  type="date"
                  value={dateDebut}
                  onChange={(e) => setDateDebut(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="session-fin" className="text-xs font-bold">Date de Fin *</Label>
                <Input
                  id="session-fin"
                  type="date"
                  value={dateFin}
                  onChange={(e) => setDateFin(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="session-statut" className="text-xs font-bold">Statut de la session</Label>
                <Select value={statut} onValueChange={(val: any) => setStatut(val)}>
                  <SelectTrigger id="session-statut">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">Active (En cours d'inscription et de règlement)</SelectItem>
                    <SelectItem value="planifiee">Planifiée (Ouverture future)</SelectItem>
                    <SelectItem value="cloturee">Clôturée (Terminée)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="session-desc" className="text-xs font-bold">Description / Observations</Label>
                <Textarea
                  id="session-desc"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={2}
                  placeholder="Précisions sur cette session (ex: cohortes concernées, calendrier financier)..."
                />
              </div>
            </div>

            {/* Payment periods config */}
            <div className="space-y-3 pt-3 border-t">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <div>
                  <h4 className="text-sm font-bold text-foreground flex items-center gap-2">
                    <CreditCard className="h-4 w-4 text-primary" />
                    Périodes de Paiement Rattachées
                  </h4>
                  <p className="text-xs text-muted-foreground">
                    Ces tranches seront calculées dynamiquement pour tout étudiant rattaché à cette session.
                  </p>
                </div>

                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleAddPeriod}
                  className="rounded-xl h-8 gap-1.5 text-xs text-primary"
                >
                  <Plus className="h-3.5 w-3.5" />
                  Ajouter une Tranche
                </Button>
              </div>

              {/* Quick Presets */}
              <div className="flex flex-wrap items-center gap-1.5 p-2.5 rounded-xl bg-muted/40 border text-xs">
                <span className="font-semibold text-muted-foreground mr-1 text-[11px] flex items-center gap-1">
                  <Sparkles className="h-3 w-3 text-amber-500" />
                  Modèles :
                </span>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  className="h-6 text-[11px] px-2"
                  onClick={() => handleApplyPreset("3tranches")}
                >
                  3 Tranches (Oct, Jan, Avr)
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  className="h-6 text-[11px] px-2"
                  onClick={() => handleApplyPreset("4tranches")}
                >
                  4 Tranches Décalées
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  className="h-6 text-[11px] px-2"
                  onClick={() => handleApplyPreset("2semestres")}
                >
                  2 Semestres
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  className="h-6 text-[11px] px-2"
                  onClick={() => handleApplyPreset("10mensuel")}
                >
                  10 Mensualités (Sept-Juin)
                </Button>
              </div>

              {/* Periods editable list */}
              <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                {periodes.map((p, idx) => (
                  <div
                    key={p.id}
                    className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 p-2.5 rounded-xl border bg-card"
                  >
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="h-6 w-6 rounded-full bg-primary/10 text-primary font-bold text-xs flex items-center justify-center">
                        {p.ordre}
                      </span>
                    </div>

                    <div className="flex-1 grid grid-cols-1 sm:grid-cols-3 gap-2">
                      <Input
                        value={p.nom}
                        onChange={(e) => handleUpdatePeriod(p.id, "nom", e.target.value)}
                        placeholder="Libellé de la tranche"
                        className="h-8 text-xs"
                      />

                      <Select
                        value={p.mois}
                        onValueChange={(val) => handleUpdatePeriod(p.id, "mois", val)}
                      >
                        <SelectTrigger className="h-8 text-xs">
                          <SelectValue placeholder="Mois" />
                        </SelectTrigger>
                        <SelectContent>
                          {MOIS_LIST.map((m) => (
                            <SelectItem key={m} value={m}>
                              {m}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>

                      <Input
                        type="date"
                        value={p.dateEcheance}
                        onChange={(e) => handleUpdatePeriod(p.id, "dateEcheance", e.target.value)}
                        className="h-8 text-xs font-mono"
                        title="Date limite d'échéance"
                      />
                    </div>

                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDeletePeriod(p.id)}
                      className="h-8 w-8 text-destructive hover:bg-destructive/10 shrink-0 self-end sm:self-center"
                      title="Retirer cette période"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>

            <DialogFooter className="gap-2 sm:gap-0 pt-2 border-t">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Annuler
              </Button>
              <Button type="submit" className="gap-2">
                <CheckCircle2 className="h-4 w-4" />
                {editingSession ? "Enregistrer les modifications" : "Créer la Session"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ── Alert Delete Dialog ── */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="text-destructive flex items-center gap-2">
              <AlertCircle className="h-5 w-5" />
              Supprimer la session académique ?
            </AlertDialogTitle>
            <AlertDialogDescription>
              Êtes-vous sûr de vouloir supprimer la session <strong>"{sessionToDelete?.nom}"</strong> ?
              Cette action supprimera également son calendrier d'échéances pour les nouveaux paiements.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmDelete} className="bg-destructive hover:bg-destructive/90 text-white">
              Supprimer définitivement
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default SessionsConfig;
