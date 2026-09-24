import { ServerOff, UsersRound } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const Salles = () => <div className="space-y-6"><div><h1 className="text-3xl font-bold text-foreground">Salles de cours</h1><p className="mt-1 text-muted-foreground">Capacités, équipements et affectations.</p></div><Card><CardHeader><CardTitle className="flex items-center gap-2"><UsersRound className="h-5 w-5 text-primary" />Inventaire des salles</CardTitle><CardDescription>Les salles seront reliées aux cours et aux bâtiments.</CardDescription></CardHeader><CardContent><Alert><ServerOff className="h-4 w-4" /><AlertTitle>Module backend à ajouter</AlertTitle><AlertDescription>Aucune salle fictive n'est affichée. Le modèle Salle et ses endpoints seront ajoutés avant activation.</AlertDescription></Alert></CardContent></Card></div>;

export default Salles;
