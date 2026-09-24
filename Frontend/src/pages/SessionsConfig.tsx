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
import { etudiantsApi, extractErrorMessage, sessionsApi } from "@/services/apiClient";
import type { AcademicSession as ApiSession, SessionPeriod } from "@/services/apiTypes";
import type { AcademicSession, PaymentPeriod } from "@/services/academicSessionService";

const getCurrentAcademicYear = () => {
  const now = new Date();
  const startYear = now.getMonth() >= 7 ? now.getFullYear() : now.getFullYear() - 1;
  return `${startYear}-${startYear + 1}`;
};

const normalizeSessionStatus = (value: string): AcademicSession["statut"] =>
  value === "planifiee" || value === "cloturee" ? value : "active";

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
  const [studentCounts, setStudentCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);

  // Form states
  const [nom, setNom] = useState("");
  const [code, setCode] = useState("");
  const [anneeAcademique, setAnneeAcademique] = useState(getCurrentAcademicYear());
  const [dateDebut, setDateDebut] = useState("");
  const [dateFin, setDateFin] = useState("");
  const [statut, setStatut] = useState<"active" | "planifiee" | "cloturee">("active");
  const [description, setDescription] = useState("");
  const [periodes, setPeriodes] = useState<PaymentPeriod[]>([]);
  const [saving, setSaving] = useState(false);

  const loadData = async () => {
    setLoading(true);
    const [sessionsResult, studentsResult] = await Promise.all([
      sessionsApi.getAll(),
      etudiantsApi.getAll(),
    ]);
    if (sessionsResult.error || studentsResult.error || !sessionsResult.data) {
      toast.error(
        extractErrorMessage(
          sessionsResult.error || studentsResult.error,
          "Impossible de charger les sessions académiques."
        )
      );
      setLoading(false);
      return;
    }

    const mappedSessions: AcademicSession[] = sessionsResult.data.map((session: ApiSession) => ({
      id: session.id,
      nom: session.nom,
      code: session.code,
      anneeAcademique: session.annee_academique,
      dateDebut: session.date_debut,
      dateFin: session.date_fin,
      statut: normalizeSessionStatus(session.statut),
      description: session.description || "",
      periodes: (session.periodes || []).map((period: SessionPeriod) => ({
        id: period.id,
        nom: period.nom,
        mois: period.mois,
        dateEcheance: period.date_echeance || "",
        montantEstime: period.montant_estime,
        pourcentage: period.pourcentage,
        ordre: period.ordre,
      })),
    }));
    setSessions(mappedSessions);

    const counts: Record<string, number> = {};
    for (const student of studentsResult.data || []) {
      if (student.session_id) {
        counts[student.session_id] = (counts[student.session_id] || 0) + 1;
      }
    }
    setStudentCounts(counts);
    setLoading(false);
  };

  useEffect(() => {
    void loadData();
  }, []);

  const openCreateDialog = () => {
    setEditingSession(null);
    setNom("");
    setCode("");
    setAnneeAcademique(getCurrentAcademicYear());
    setDateDebut("");
    setDateFin("");
    setStatut("active");
    setDescription("");
    setPeriodes([]);
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

  const handleAddPeriod = () => {
    const nextOrdre = periodes.length + 1;
    const newPeriod: PaymentPeriod = {
      id: crypto.randomUUID(),
      nom: "",
      mois: "",
      dateEcheance: "",
      pourcentage: 0,
      ordre: nextOrdre,
    };
    setPeriodes([...periodes, newPeriod]);
  };

  const handleUpdatePeriod = (id: string, field: keyof PaymentPeriod, value: string | number) => {
    setPeriodes(
      periodes.map((p) => {
        if (p.id === id) {
          return { ...p, [field]: value };
        }
        return p;
      })
    );
  };

  const handleDeletePeriod = (id: string) => {
    setPeriodes(periodes.filter((p) => p.id !== id).map((p, idx) => ({ ...p, ordre: idx + 1 })));
  };

  const handleSaveSession = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!nom.trim() || !code.trim() || !anneeAcademique.trim() || !dateDebut || !dateFin) {
      toast.error("Nom, code, année et dates sont obligatoires.");
      return;
    }
    if (periodes.length === 0) {
      toast.error("Ajoutez au moins une période de paiement.");
      return;
    }
    if (periodes.some((period) => !period.nom || !period.mois || !period.dateEcheance)) {
      toast.error("Chaque période doit avoir un libellé, un mois et une date d'échéance.");
      return;
    }

    const payload = {
      nom: nom.trim(),
      code: code.trim().toUpperCase(),
      annee_academique: anneeAcademique.trim(),
      date_debut: dateDebut,
      date_fin: dateFin,
      statut,
      description: description.trim(),
      periodes: periodes.map((period) => ({
        id: period.id,
        nom: period.nom.trim(),
        mois: period.mois,
        date_echeance: period.dateEcheance,
        montant_estime: period.montantEstime ?? null,
        pourcentage: period.pourcentage ?? null,
        ordre: period.ordre,
      })),
    };

    setSaving(true);
    const result = editingSession
      ? await sessionsApi.update(editingSession.id, payload)
      : await sessionsApi.create(payload);
    setSaving(false);
    if (result.error) {
      toast.error(extractErrorMessage(result.error));
      return;
    }

    toast.success(editingSession ? "Session académique mise à jour." : "Session académique créée.");
    setDialogOpen(false);
    await loadData();
  };

  const handleConfirmDelete = async () => {
    if (!sessionToDelete) return;
    const result = await sessionsApi.delete(sessionToDelete.id);
    if (result.error) {
      toast.error(extractErrorMessage(result.error));
      return;
    }
    toast.success("Session académique supprimée.");
    setDeleteDialogOpen(false);
    setSessionToDelete(null);
    await loadData();
  };

  const totalActiveSessions = sessions.filter((s) => s.statut === "active").length;
  const totalStudents = sessions.reduce(
    (total, session) => total + (studentCounts[session.id] || 0),
    0
  );
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
        {loading ? (
          <Card className="col-span-full">
            <CardContent className="py-12 text-center text-sm text-muted-foreground">
              Chargement des sessions depuis l'API...
            </CardContent>
          </Card>
        ) : sessions.length === 0 ? (
          <Card className="col-span-full border-dashed">
            <CardContent className="py-12 text-center">
              <CalendarDays className="mx-auto mb-3 h-8 w-8 text-muted-foreground/50" />
              <p className="font-medium">Aucune session enregistrée</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Créez la première session depuis cette page.
              </p>
            </CardContent>
          </Card>
        ) : sessions.map((session) => {
          const studentCount = studentCounts[session.id] || 0;
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
                  placeholder="Nom de la session"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="session-code" className="text-xs font-bold">Code / Identifiant *</Label>
                <Input
                  id="session-code"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="Code unique de la session"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="session-annee" className="text-xs font-bold">Année Académique *</Label>
                <Input
                  id="session-annee"
                  value={anneeAcademique}
                  onChange={(e) => setAnneeAcademique(e.target.value)}
                  placeholder="AAAA-AAAA"
                  required
                />
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
                <Select value={statut} onValueChange={(value) => setStatut(value as typeof statut)}>
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
                        onValueChange={(value) => handleUpdatePeriod(p.id, "mois", value)}
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
