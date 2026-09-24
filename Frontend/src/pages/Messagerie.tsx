import { Mail, ServerOff } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const Messagerie = () => <div className="space-y-6"><div><h1 className="text-3xl font-bold text-foreground">Messagerie interne</h1><p className="mt-1 text-muted-foreground">Conversations et notifications de l'établissement.</p></div><Card><CardHeader><CardTitle className="flex items-center gap-2"><Mail className="h-5 w-5 text-primary" />Messagerie</CardTitle><CardDescription>Aucune conversation fictive n'est affichée.</CardDescription></CardHeader><CardContent><Alert><ServerOff className="h-4 w-4" /><AlertTitle>Service non configuré</AlertTitle><AlertDescription>La messagerie sera activée après la création des tables et endpoints de conversations, messages et notifications.</AlertDescription></Alert></CardContent></Card></div>;

export default Messagerie;
