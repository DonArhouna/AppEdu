import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { AlertCircle, ArrowLeft, BookOpen, Clock, Loader2, RefreshCw } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { KpiCard } from "@/components/ui/kpi-card";
import { Separator } from "@/components/ui/separator";
import { structureApi, extractErrorMessage } from "@/services/apiClient";
import type { Matiere, TeachingUnit } from "@/services/apiTypes";

const MatiereDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [matiere, setMatiere] = useState<Matiere | null>(null);
  const [parent, setParent] = useState<TeachingUnit | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true); setError(null);
    const result = await structureApi.getMatiereById(id);
    if (result.error || !result.data) {
      setError(result.error || "Matière introuvable.");
    } else {
      setMatiere(result.data);
      setParent(null);
      if (result.data.ue_id) {
        const ueResult = await structureApi.getUEById(result.data.ue_id);
        if (ueResult.data) setParent(ueResult.data);
      }
    }
    setLoading(false);
  }, [id]);
  useEffect(() => { void load(); }, [load]);

  if (loading) return <div className="flex items-center justify-center gap-2 p-16 text-sm text-muted-foreground"><Loader2 className="h-5 w-5 animate-spin" />Chargement de la matière...</div>;
  if (error || !matiere) return <div className="space-y-4"><Button variant="ghost" onClick={() => navigate("/matieres")}><ArrowLeft className="mr-2 h-4 w-4" />Retour</Button><Alert variant="destructive"><AlertCircle className="h-4 w-4" /><AlertTitle>Matière indisponible</AlertTitle><AlertDescription>{error || "Matière introuvable."}</AlertDescription><Button className="mt-3" variant="outline" size="sm" onClick={load}><RefreshCw className="mr-2 h-4 w-4" />Réessayer</Button></Alert></div>;

  const totalHours = matiere.heures_cm + matiere.heures_td + matiere.heures_tp;
  return <div className="space-y-6"><div className="flex items-center gap-4"><Button variant="ghost" size="icon" onClick={() => navigate("/matieres")}><ArrowLeft className="h-4 w-4" /></Button><div><div className="flex items-center gap-3"><h1 className="text-3xl font-bold text-foreground">{matiere.nom}</h1><Badge>ECUE</Badge></div><p className="text-sm text-muted-foreground">{matiere.code}{parent ? ` • ${parent.nom}` : ""}</p></div></div><div className="grid gap-4 md:grid-cols-3"><KpiCard title="Crédits" value={`${matiere.credits} ECTS`} icon={BookOpen} subtitle="Credits de l'ECUE" colorVariant="primary" /><KpiCard title="Coefficient" value={matiere.coefficient} icon={BookOpen} subtitle="Poids de l'évaluation" colorVariant="emerald" /><KpiCard title="Volume horaire" value={`${totalHours}h`} icon={Clock} subtitle="CM, TD & TP" colorVariant="sky" /></div><Card><CardHeader><CardTitle className="flex items-center gap-2"><BookOpen className="h-5 w-5 text-primary" />Informations persistées</CardTitle><CardDescription>Les valeurs ci-dessous proviennent de l'API.</CardDescription></CardHeader><CardContent className="space-y-4"><div className="grid gap-3 md:grid-cols-2"><div><span className="text-xs text-muted-foreground">UE parente</span><p>{parent?.nom || "Non renseignée"}</p></div><div><span className="text-xs text-muted-foreground">Filière</span><p>{parent?.filiere?.nom || "Non renseignée"}</p></div><div><span className="text-xs text-muted-foreground">Niveau</span><p>{parent?.niveau || "Non renseigné"}</p></div><div><span className="text-xs text-muted-foreground">Semestre</span><p>{parent?.semestre || "Non renseigné"}</p></div><div><span className="text-xs text-muted-foreground">Enseignant</span><p>{matiere.enseignant_nom || "Non assigné"}</p></div></div><Separator /><div><span className="text-xs text-muted-foreground">Description</span><p className="mt-1 text-sm">{matiere.description || "Aucune description fournie."}</p></div></CardContent></Card></div>;
};

export default MatiereDetail;
