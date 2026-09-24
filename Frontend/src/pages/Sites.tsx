import { Building2, ServerOff } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const Sites = () => <div className="space-y-6"><div><h1 className="text-3xl font-bold text-foreground">Sites & bâtiments</h1><p className="mt-1 text-muted-foreground">Infrastructures physiques de l'établissement.</p></div><Card><CardHeader><CardTitle className="flex items-center gap-2"><Building2 className="h-5 w-5 text-primary" />Inventaire des sites</CardTitle><CardDescription>Les sites seront rattachés aux campus et exposés par l'API.</CardDescription></CardHeader><CardContent><Alert><ServerOff className="h-4 w-4" /><AlertTitle>Module backend à ajouter</AlertTitle><AlertDescription>Le modèle Site/Bâtiment n'existe pas encore. Aucun site fictif n'est affiché.</AlertDescription></Alert></CardContent></Card></div>;

export default Sites;
