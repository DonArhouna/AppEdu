import { FolderOpen, ServerOff } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const Ressources = () => <div className="space-y-6"><div><h1 className="text-3xl font-bold text-foreground">Ressources pédagogiques</h1><p className="mt-1 text-muted-foreground">Supports, syllabus et documents de cours.</p></div><Card><CardHeader><CardTitle className="flex items-center gap-2"><FolderOpen className="h-5 w-5 text-primary" />Stockage documentaire</CardTitle><CardDescription>Aucune ressource de démonstration n'est injectée.</CardDescription></CardHeader><CardContent><Alert><ServerOff className="h-4 w-4" /><AlertTitle>Module backend à ajouter</AlertTitle><AlertDescription>Le stockage de fichiers, les métadonnées et les droits de téléchargement doivent être exposés par des endpoints dédiés avant activation.</AlertDescription></Alert></CardContent></Card></div>;

export default Ressources;
