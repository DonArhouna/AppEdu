import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, UserRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const PersonnelDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  return <div className="space-y-6"><Button variant="ghost" onClick={() => navigate("/personnel")}><ArrowLeft className="mr-2 h-4 w-4" />Retour</Button><Card><CardHeader><CardTitle className="flex items-center gap-2"><UserRound className="h-5 w-5 text-primary" />Fiche du personnel</CardTitle><CardDescription>Identifiant : {id}</CardDescription></CardHeader><CardContent><p className="text-sm text-muted-foreground">Les attributs RH détaillés ne sont pas encore exposés par le backend. Aucun profil fictif n'est affiché.</p></CardContent></Card></div>;
};

export default PersonnelDetail;
