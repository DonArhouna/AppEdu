import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Building2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const SiteDetail = () => { const { id } = useParams(); const navigate = useNavigate(); return <div className="space-y-6"><Button variant="ghost" onClick={() => navigate("/sites")}><ArrowLeft className="mr-2 h-4 w-4" />Retour</Button><Card><CardHeader><CardTitle className="flex items-center gap-2"><Building2 className="h-5 w-5 text-primary" />Site {id}</CardTitle><CardDescription>Détail d'infrastructure</CardDescription></CardHeader><CardContent><p className="text-sm text-muted-foreground">Le module Site/Bâtiment sera disponible après l'ajout de son modèle backend.</p></CardContent></Card></div>; };
export default SiteDetail;
