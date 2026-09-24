import { AlertCircle, ServerOff, ShieldCheck } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const JournalAudit = () => <div className="space-y-6"><div><h1 className="text-3xl font-bold text-foreground">Journal d'audit</h1><p className="mt-1 text-muted-foreground">Traçabilité des actions sensibles.</p></div><Card><CardHeader><CardTitle className="flex items-center gap-2"><ShieldCheck className="h-5 w-5 text-primary" />Événements d'audit</CardTitle><CardDescription>Aucun journal fictif n'est injecté dans l'interface.</CardDescription></CardHeader><CardContent><Alert><ServerOff className="h-4 w-4" /><AlertTitle>Module backend requis</AlertTitle><AlertDescription>La table d'audit et ses endpoints protégés doivent être créés avant de pouvoir afficher les traces réelles.</AlertDescription></Alert></CardContent></Card></div>;

export default JournalAudit;
