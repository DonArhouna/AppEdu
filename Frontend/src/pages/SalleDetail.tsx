import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, DoorOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const SalleDetail = () => { const { id } = useParams(); const navigate = useNavigate(); return <div className="space-y-6"><Button variant="ghost" onClick={() => navigate("/salles")}><ArrowLeft className="mr-2 h-4 w-4" />Retour</Button><Card><CardHeader><CardTitle className="flex items-center gap-2"><DoorOpen className="h-5 w-5 text-primary" />Salle {id}</CardTitle><CardDescription>Détail de la salle</CardDescription></CardHeader><CardContent><p className="text-sm text-muted-foreground">Le module Salle sera disponible après l'ajout de son modèle backend.</p></CardContent></Card></div>; };
export default SalleDetail;
