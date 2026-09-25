import { useCallback, useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  ArrowLeft,
  Edit,
  FileText,
  GraduationCap,
  User,
  Mail,
  Phone,
  Calendar,
  MapPin,
  CreditCard,
  Download,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { toast } from "sonner";
import { StudentCardModal } from "@/components/students/StudentCardModal";
import { academicApi, etudiantsApi, financesApi, pedagogieApi, sessionsApi, setupApi } from "@/services/apiClient";
import type { AcademicClass, AcademicCycle, AcademicLevel, AcademicSession, Note, Payment, Student } from "@/services/apiTypes";

const StudentDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [cardModalOpen, setCardModalOpen] = useState(false);

  const [student, setStudent] = useState<Student | null>(null);
  const [session, setSession] = useState<AcademicSession | null>(null);
  const [paiements, setPaiements] = useState<Payment[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  const [academicClass, setAcademicClass] = useState<AcademicClass | null>(null);
  const [academicLevel, setAcademicLevel] = useState<AcademicLevel | null>(null);
  const [academicCycle, setAcademicCycle] = useState<AcademicCycle | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currency, setCurrency] = useState("");

  const loadStudentData = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const [stuRes, paiementsRes, notesRes, classesRes, levelsRes, cyclesRes] = await Promise.all([
        etudiantsApi.getById(id),
        financesApi.getPaiements({ etudiant_id: id }),
        pedagogieApi.getNotes({ etudiant_id: id }),
        academicApi.getClasses(),
        academicApi.getLevels(),
        academicApi.getCycles(),
      ]);

      if (stuRes.error) {
        setError(stuRes.error);
        setStudent(null);
      } else {
        const s = stuRes.data;
        const statusResult = await setupApi.getStatus();
        setCurrency(statusResult.data?.devise || "");
        setStudent(s);
        const currentClass = classesRes.data?.find((item) => item.id === s?.classe_id) || null;
        const currentLevel = levelsRes.data?.find((item) => item.id === currentClass?.niveau_id) || null;
        const currentCycle = cyclesRes.data?.find((item) => item.id === currentLevel?.cycle_id) || null;
        setAcademicClass(currentClass);
        setAcademicLevel(currentLevel);
        setAcademicCycle(currentCycle);
        if (s?.session_id) {
          const sesRes = await sessionsApi.getById(s.session_id);
          if (sesRes.data) setSession(sesRes.data);
        }
      }

      if (paiementsRes.data) {
        setPaiements(paiementsRes.data);
      }
      if (notesRes.data) {
        setNotes(notesRes.data);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Impossible de charger le dossier étudiant.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void loadStudentData();
  }, [loadStudentData]);

  const handleGenerateCertificate = () => {
    toast.info("La génération de certificats sera disponible après l'ajout du endpoint documentaire.");
  };

  if (loading) {
    return (
      <div className="p-16 text-center space-y-3">
        <RefreshCw className="h-8 w-8 animate-spin mx-auto text-primary" />
        <p className="text-sm text-muted-foreground">Chargement du dossier étudiant...</p>
      </div>
    );
  }

  if (error || !student) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" size="sm" onClick={() => navigate("/etudiants")}>
          <ArrowLeft className="h-4 w-4 mr-2" /> Retour à la liste
        </Button>
        <Card className="border-destructive/40 bg-destructive/5 p-6 rounded-xl text-center space-y-3">
          <AlertCircle className="h-8 w-8 text-destructive mx-auto" />
          <p className="font-semibold text-destructive">Étudiant introuvable ou erreur de chargement</p>
          <p className="text-xs text-muted-foreground">{error || "Le dossier demandé n'existe pas dans la base de données."}</p>
          <Button size="sm" onClick={loadStudentData} variant="outline">
            Réessayer
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate("/etudiants")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-3xl font-bold text-foreground">
                {student.prenom} {student.nom}
              </h1>
              <Badge className={student.statut === "actif" ? "bg-emerald-600 text-white" : "bg-amber-600 text-white"}>
                {student.statut || "Non renseigné"}
              </Badge>
            </div>
            <p className="text-muted-foreground text-sm font-mono">
              Matricule: {student.matricule} • {student.filiere || "Non assigné"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            onClick={() => setCardModalOpen(true)}
            className="bg-primary hover:bg-primary-hover shadow-md"
          >
            <CreditCard className="h-4 w-4 mr-2" /> Carte Étudiant (Badge)
          </Button>
        </div>
      </div>

      {/* Info Cards */}
      <div className="grid gap-6 md:grid-cols-3">
        <Card className="md:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <User className="h-5 w-5 text-primary" />
              Informations Personnelles
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="aspect-square bg-primary/10 rounded-xl flex items-center justify-center border border-primary/20">
              <div className="h-24 w-24 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold text-3xl">
                {student.prenom?.[0]}
                {student.nom?.[0]}
              </div>
            </div>
            <Separator />
            <div className="space-y-3 text-xs">
              <div className="flex items-center gap-2">
                <Mail className="h-4 w-4 text-muted-foreground" />
                <span>{student.email}</span>
              </div>
              <div className="flex items-center gap-2">
                <Phone className="h-4 w-4 text-muted-foreground" />
                <span>{student.telephone || "Non renseigné"}</span>
              </div>
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <span>Né(e) le {student.date_naissance || "Non renseigné"}</span>
              </div>
              <div className="flex items-center gap-2">
                <MapPin className="h-4 w-4 text-muted-foreground" />
                <span>Lieu: {student.lieu_naissance || "Non renseigné"}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="md:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <GraduationCap className="h-5 w-5 text-primary" />
                Parcours Académique & Inscription
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-3">
                <div>
                  <p className="text-xs text-muted-foreground">Filière</p>
                  <p className="font-semibold">{student.filiere || "Non assignée"}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Classe</p>
                  <p className="font-semibold">{academicClass ? `${academicClass.code} — ${academicClass.libelle}` : "Non affectée"}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Cycle</p>
                  <p className="font-semibold">{academicCycle?.libelle || "Non résolu"}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Niveau</p>
                  <p className="font-semibold">{academicLevel?.libelle || student.niveau || "Non renseigné"}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Session Académique</p>
                  <p className="font-semibold">{session?.nom || "Non rattachée"}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Crédits ECTS Validés</p>
                  <p className="font-semibold text-primary">{student.credits_valides !== undefined ? student.credits_valides : "Non calculé"}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Tabs defaultValue="finances" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="finances">Historique Paiements ({paiements.length})</TabsTrigger>
              <TabsTrigger value="notes">Notes & Évaluations ({notes.length})</TabsTrigger>
            </TabsList>
            <TabsContent value="finances" className="space-y-3 pt-3">
              {paiements.length === 0 ? (
                <div className="p-6 text-center text-xs text-muted-foreground border rounded-xl">
                  Aucun encaissement enregistré pour cet étudiant.
                </div>
              ) : (
                <div className="space-y-2">
                  {paiements.map((p) => (
                    <div key={p.id} className="p-3 border rounded-xl flex items-center justify-between text-xs">
                      <div>
                        <p className="font-semibold text-foreground">{Number(p.montant).toLocaleString("fr-FR")} {currency || "devise de l'établissement"}</p>
                        <p className="text-muted-foreground">Mode: {p.mode_paiement} • Réf: {p.reference}</p>
                      </div>
                      <Badge className="bg-emerald-600 text-white">{p.statut || "Validé"}</Badge>
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>
            <TabsContent value="notes" className="space-y-3 pt-3">
              {notes.length === 0 ? (
                <div className="p-6 text-center text-xs text-muted-foreground border rounded-xl">
                  Aucune note saisie pour le moment.
                </div>
              ) : (
                <div className="space-y-2">
                  {notes.map((n) => (
                    <div key={n.id} className="p-3 border rounded-xl flex items-center justify-between text-xs">
                      <div>
                        <p className="font-semibold text-foreground">{n.matiere_nom || n.matiere_id}</p>
                        <p className="text-muted-foreground">Coef: {n.coefficient} • Statut: {n.statut}</p>
                      </div>
                      <span className="font-bold text-sm text-primary font-mono">{n.valeur} / 20</span>
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </div>

      <StudentCardModal
        open={cardModalOpen}
        onOpenChange={setCardModalOpen}
        student={{
          matricule: student.matricule,
          nom: student.nom,
          prenom: student.prenom,
          filiere: student.filiere || "",
          niveau: student.niveau || "",
          email: student.email || "",
          telephone: student.telephone || "",
        }}
        sessionLabel={session?.annee_academique}
        status={student.statut}
        validUntil={session?.date_fin}
      />
    </div>
  );
};

export default StudentDetail;
