import { useState, type FormEvent } from "react";
import { AlertCircle, FileCheck2, Search, ShieldCheck } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const VerificationDocument = () => {
  const [code, setCode] = useState("");
  const [searched, setSearched] = useState(false);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (code.trim()) setSearched(true);
  };

  return (
    <div className="min-h-screen bg-muted/30 px-4 py-12 text-foreground">
      <div className="mx-auto max-w-xl space-y-6">
        <div className="text-center"><div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary"><ShieldCheck className="h-7 w-7" /></div><h1 className="text-3xl font-bold">Vérification de document</h1><p className="mt-2 text-sm text-muted-foreground">Saisissez le code présent sur le document officiel.</p></div>
        <Card><CardHeader><CardTitle className="flex items-center gap-2"><FileCheck2 className="h-5 w-5 text-primary" />Contrôler un code</CardTitle><CardDescription>La vérification sera effectuée par le service de documents du backend.</CardDescription></CardHeader><CardContent><form onSubmit={submit} className="space-y-4"><div className="space-y-2"><Label htmlFor="verification-code">Code de vérification</Label><Input id="verification-code" value={code} onChange={(event) => setCode(event.target.value)} placeholder="Code fourni sur le document" required /></div><Button type="submit" className="w-full"><Search className="mr-2 h-4 w-4" />Vérifier</Button></form></CardContent></Card>
        {searched && <Alert><AlertCircle className="h-4 w-4" /><AlertTitle>Service de vérification non configuré</AlertTitle><AlertDescription>Aucun registre de documents n'est encore exposé par le backend. Aucun résultat fictif n'est affiché.</AlertDescription></Alert>}
      </div>
    </div>
  );
};

export default VerificationDocument;
