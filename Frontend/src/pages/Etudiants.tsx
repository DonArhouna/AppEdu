import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { KpiCard } from "@/components/ui/kpi-card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
  Search,
  Eye,
  Edit,
  Trash2,
  Plus,
  Filter,
  Users,
  GraduationCap,
  RefreshCw,
  Award,
  BookOpen,
  Calendar,
  AlertCircle
} from "lucide-react";
import { StudentDialog, Student } from "@/components/students/StudentDialog";
import type { AcademicSession, Filiere, Student as StudentApi } from "@/services/apiTypes";
import { toast } from "sonner";
import { etudiantsApi, sessionsApi, structureApi } from "@/services/apiClient";

const Etudiants = () => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState("");
  const [filterFiliere, setFilterFiliere] = useState("all");
  const [filterNiveau, setFilterNiveau] = useState("all");
  const [filterCycle, setFilterCycle] = useState("all");
  const [filterSession, setFilterSession] = useState("all");

  const [sessions, setSessions] = useState<AcademicSession[]>([]);
  const [filieresList, setFilieresList] = useState<Filiere[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [studentToDelete, setStudentToDelete] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [etudiantsRes, sessionsRes, filieresRes] = await Promise.all([
        etudiantsApi.getAll(),
        sessionsApi.getAll(),
        structureApi.getFilieres(),
      ]);

      if (etudiantsRes.error) {
        setError(etudiantsRes.error);
        setStudents([]);
      } else {
        const raw = etudiantsRes.data || [];
        setStudents(
          raw.map((s: StudentApi) => ({
            id: s.id,
            matricule: s.matricule,
            nom: s.nom,
            prenom: s.prenom,
            email: s.email || "",
            telephone: s.telephone || "",
            dateNaissance: s.date_naissance || "",
            lieuNaissance: s.lieu_naissance || "",
            promotion: "",
            filiere: s.filiere || "",
            niveau: s.niveau || "",
            cycle: s.niveau?.startsWith("Master") ? "Master" : s.niveau?.startsWith("Licence") ? "Licence" : "",
            statut: s.statut || "",
            creditsValides: undefined,
            sessionId: s.session_id || "",
          }))
        );
      }

      if (sessionsRes.data) {
        setSessions(sessionsRes.data);
      }
      if (filieresRes.data) {
        setFilieresList(filieresRes.data);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erreur de connexion au serveur backend.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filteredStudents = students.filter((student) => {
    const matchesSearch =
      student.nom.toLowerCase().includes(searchTerm.toLowerCase()) ||
      student.prenom.toLowerCase().includes(searchTerm.toLowerCase()) ||
      student.matricule.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFiliere = filterFiliere === "all" || student.filiere === filterFiliere;
    const matchesNiveau = filterNiveau === "all" || student.niveau === filterNiveau;
    const matchesCycle = filterCycle === "all" || student.cycle === filterCycle;
    const matchesSession =
      filterSession === "all" ||
      (filterSession === "none" ? !student.sessionId : student.sessionId === filterSession);

    return matchesSearch && matchesFiliere && matchesNiveau && matchesCycle && matchesSession;
  });

  const availableCycles = Array.from(new Set(students.map((student) => student.cycle).filter(Boolean)));
  const availableNiveaux = Array.from(new Set(students.map((student) => student.niveau).filter(Boolean)));

  const handleSaveStudent = async (student: Student) => {
    const payload = {
      nom: student.nom,
      prenom: student.prenom,
      email: student.email,
      telephone: student.telephone,
      filiere: student.filiere,
      niveau: student.niveau,
      session_id: student.sessionId || undefined,
      statut: student.statut,
    };

    if (selectedStudent?.id) {
      const res = await etudiantsApi.update(selectedStudent.id, payload);
      if (res.error) {
        toast.error(`Erreur : ${res.error}`);
        return;
      }
      toast.success("Dossier étudiant mis à jour.");
    } else {
      const res = await etudiantsApi.create(payload);
      if (res.error) {
        toast.error(`Erreur : ${res.error}`);
        return;
      }
      toast.success("Nouvel étudiant inscrit avec succès.");
    }

    setDialogOpen(false);
    setSelectedStudent(null);
    await loadData();
  };

  const handleEditStudent = (student: Student) => {
    setSelectedStudent(student);
    setDialogOpen(true);
  };

  const handleDeleteStudent = (id: string) => {
    setStudentToDelete(id);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (studentToDelete) {
      const res = await etudiantsApi.delete(studentToDelete);
      if (res.error) {
        toast.error(`Erreur : ${res.error}`);
      } else {
        toast.success("Dossier étudiant supprimé.");
        await loadData();
      }
      setDeleteDialogOpen(false);
      setStudentToDelete(null);
    }
  };

  const handleAddNew = () => {
    setSelectedStudent(null);
    setDialogOpen(true);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Gestion & Suivi des Étudiants</h1>
          <p className="text-muted-foreground mt-1">
            Suivi longitudinal des étudiants à travers les cycles LMD via l'API
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={loadData} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-1.5 ${loading ? "animate-spin" : ""}`} />
            Actualiser
          </Button>
          <Button onClick={handleAddNew} className="bg-primary text-primary-foreground">
            <Plus className="h-4 w-4 mr-2" />
            Nouvel Étudiant
          </Button>
        </div>
      </div>

      {/* Erreur API sans repli factice */}
      {error && (
        <Card className="border-destructive/40 bg-destructive/5 p-4 rounded-xl">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-destructive shrink-0" />
            <div className="flex-1 text-sm text-destructive">
              <strong>Erreur backend :</strong> {error}
            </div>
            <Button variant="outline" size="sm" onClick={loadData} className="border-destructive/30">
              Réessayer
            </Button>
          </div>
        </Card>
      )}

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          title="Total Inscrits"
          value={students.length}
          icon={Users}
          trendLabel="Dossiers enregistrés"
          colorVariant="primary"
        />
        <KpiCard
          title="Cycle Licence"
          value={students.filter((s) => s.cycle === "Licence").length}
          icon={BookOpen}
          trendLabel="Niveaux L1 à L3"
          colorVariant="emerald"
        />
        <KpiCard
          title="Cycle Master"
          value={students.filter((s) => s.cycle === "Master").length}
          icon={GraduationCap}
          trendLabel="Niveaux M1 et M2"
          colorVariant="purple"
        />
        <KpiCard
          title="Actifs / Régularisés"
          value={students.filter((s) => s.statut === "actif").length}
          icon={RefreshCw}
          trendLabel="Statut actif"
          colorVariant="amber"
        />
      </div>

      {/* Main Table Card */}
      <Card className="card-base">
        <CardHeader className="p-5">
          <div className="flex flex-col gap-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Rechercher par nom, prénom ou matricule..."
                  className="pl-10"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
            </div>
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex items-center gap-2 flex-1">
                <Filter className="h-4 w-4 text-muted-foreground" />
                <Select value={filterCycle} onValueChange={setFilterCycle}>
                  <SelectTrigger>
                    <SelectValue placeholder="Cycle Académique" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Tous les cycles</SelectItem>
                    {availableCycles.map((cycle) => (
                      <SelectItem key={cycle} value={cycle}>{cycle}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <Select value={filterFiliere} onValueChange={setFilterFiliere}>
                <SelectTrigger className="flex-1">
                  <SelectValue placeholder="Filière" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Toutes les filières</SelectItem>
                  {filieresList.map((f) => (
                    <SelectItem key={f.id} value={f.nom}>
                      {f.nom}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={filterNiveau} onValueChange={setFilterNiveau}>
                <SelectTrigger className="flex-1">
                  <SelectValue placeholder="Niveau" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tous les niveaux</SelectItem>
                  {availableNiveaux.map((niveau) => (
                    <SelectItem key={niveau} value={niveau}>{niveau}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {/* Filtre par Session Académique */}
              <Select value={filterSession} onValueChange={setFilterSession}>
                <SelectTrigger className="flex-1">
                  <SelectValue placeholder="Session Académique" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Toutes les sessions</SelectItem>
                  <SelectItem value="none">Sans session assignée</SelectItem>
                  {sessions.map((s) => (
                    <SelectItem key={s.id} value={s.id}>
                      {s.nom}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          <div className="border-t overflow-x-auto">
            {loading ? (
              <div className="p-12 text-center text-sm text-muted-foreground space-y-2">
                <RefreshCw className="h-6 w-6 animate-spin mx-auto text-primary" />
                <p>Chargement des étudiants depuis le serveur...</p>
              </div>
            ) : filteredStudents.length === 0 ? (
              <div className="p-12 text-center text-sm text-muted-foreground space-y-3">
                <Users className="h-10 w-10 mx-auto text-muted-foreground/50" />
                <p className="font-semibold text-foreground">Aucun étudiant trouvé</p>
                <p className="text-xs">Aucun étudiant n'est enregistré ou ne correspond aux filtres sélectionnés.</p>
                <Button size="sm" onClick={handleAddNew} className="mt-2">
                  <Plus className="h-4 w-4 mr-1.5" /> Inscrire un premier étudiant
                </Button>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/40">
                    <TableHead className="w-[140px]">Matricule</TableHead>
                    <TableHead>Étudiant</TableHead>
                    <TableHead>Cycle & Filière</TableHead>
                    <TableHead>Niveau</TableHead>
                    <TableHead>Session Académique</TableHead>
                    <TableHead>Crédits validés</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredStudents.map((student) => {
                    const studentSession = sessions.find((s) => s.id === student.sessionId);
                    return (
                      <TableRow key={student.id} className="hover:bg-muted/30">
                        <TableCell className="font-mono font-bold text-xs text-primary">
                          {student.matricule}
                        </TableCell>
                        <TableCell>
                          <div>
                            <div className="font-semibold text-sm text-foreground">
                              {student.prenom} {student.nom}
                            </div>
                            <div className="text-xs text-muted-foreground">{student.email}</div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="text-xs">
                            <span className="font-semibold">{student.filiere}</span>
                            <p className="text-[11px] text-muted-foreground">{student.cycle}</p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className="font-semibold text-xs">
                            {student.niveau}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {studentSession ? (
                            <Badge variant="outline" className="bg-primary/5 text-primary border-primary/25 font-semibold text-xs">
                              {studentSession.nom}
                            </Badge>
                          ) : (
                            <Badge variant="destructive" className="bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-400/30 text-xs font-semibold">
                              Non rattaché
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          <span className="font-mono text-sm">{student.creditsValides ?? "Non calculé"}</span>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => navigate(`/etudiants/${student.id}`)}
                              title="Fiche détaillée"
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleEditStudent(student)}
                              title="Modifier dossier"
                            >
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="text-destructive hover:text-destructive"
                              onClick={() => handleDeleteStudent(student.id)}
                              title="Supprimer"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </div>
        </CardContent>
      </Card>

      <StudentDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        student={selectedStudent}
        onSave={handleSaveStudent}
      />

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Supprimer ce dossier étudiant ?</AlertDialogTitle>
            <AlertDialogDescription>
              Cette action est irréversible. L'étudiant ainsi que son historique académique et financier seront supprimés de la base de données.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} className="bg-destructive text-destructive-foreground">
              Supprimer définitivement
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default Etudiants;
