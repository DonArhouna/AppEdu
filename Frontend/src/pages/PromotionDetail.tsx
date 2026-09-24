import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, GraduationCap, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { sessionsApi, etudiantsApi } from "@/services/apiClient";
import type { AcademicSession, Student } from "@/services/apiTypes";

const PromotionDetail = () => { const { id } = useParams(); const navigate = useNavigate(); const [session, setSession] = useState<AcademicSession | null>(null); const [students, setStudents] = useState<Student[]>([]); useEffect(() => { void (async () => { const [s, e] = await Promise.all([sessionsApi.getById(id || ""), etudiantsApi.getAll({ sessionId: id })]); setSession(s.data); setStudents(e.data || []); })(); }, [id]); return <div className="space-y-6"><Button variant="ghost" onClick={() => navigate("/promotions")}><ArrowLeft className="mr-2 h-4 w-4" />Retour</Button><Card><CardHeader><CardTitle className="flex items-center gap-2"><GraduationCap className="h-5 w-5 text-primary" />{session?.nom || "Promotion"}</CardTitle><CardDescription>{students.length} étudiant(s) rattaché(s)</CardDescription></CardHeader><CardContent>{session ? <p className="text-sm text-muted-foreground">Code {session.code} · {session.annee_academique} · {session.statut}</p> : <Loader2 className="h-5 w-5 animate-spin" />}</CardContent></Card></div>; };
export default PromotionDetail;
