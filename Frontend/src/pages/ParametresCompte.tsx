import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import {
  AlertCircle, Laptop, LogOut, MonitorSmartphone, RefreshCw, Save, Sliders, Sun, X,
} from "lucide-react";
import { toast } from "sonner";
import { authApi, extractErrorMessage } from "@/services/apiClient";
import type { AuthSession } from "@/services/apiTypes";

type ThemePreference = "light" | "dark" | "system";

const getInitialTheme = (): ThemePreference => {
  if (typeof window === "undefined") return "system";
  const stored = window.localStorage.getItem("theme");
  if (stored === "light" || stored === "dark") return stored;
  return "system";
};

const ParametresCompte = () => {
  const [theme, setTheme] = useState<ThemePreference>(getInitialTheme);
  const [systemPrefersDark, setSystemPrefersDark] = useState(() =>
    typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches
  );

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = (event: MediaQueryListEvent) => setSystemPrefersDark(event.matches);
    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, []);

  useEffect(() => {
    const isDark = theme === "dark" || (theme === "system" && systemPrefersDark);
    document.documentElement.classList.toggle("dark", isDark);
    window.localStorage.setItem("theme", theme);
  }, [systemPrefersDark, theme]);

  const handleSaveSettings = (event: React.FormEvent) => {
    event.preventDefault();
    window.localStorage.setItem("theme", theme);
    toast.success("Préférence d'affichage enregistrée dans ce navigateur.");
  };

  // -- Mes sessions (lot 2) ---------------------------------------------
  const [sessions, setSessions] = useState<AuthSession[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [confirmationAutres, setConfirmationAutres] = useState(false);
  const [sessionAFermer, setSessionAFermer] = useState<AuthSession | null>(null);

  const chargerSessions = async () => {
    setSessionsLoading(true);
    const result = await authApi.getSessions();
    if (result.error) {
      // Un backend sans le lot 2 n'expose pas ces routes : l'écran reste
      // silencieux plutôt que d'afficher une erreur permanente.
      setSessions([]);
    } else {
      setSessions(result.data?.sessions || []);
    }
    setSessionsLoading(false);
  };

  useEffect(() => {
    void chargerSessions();
  }, []);

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short" });
    } catch {
      return iso;
    }
  };

  const fermerSession = async () => {
    if (!sessionAFermer) return;
    const result = await authApi.fermerSession(sessionAFermer.id);
    if (result.error) {
      toast.error(extractErrorMessage(result.error, "La session n'a pas pu être fermée."));
      return;
    }
    toast.success(
      sessionAFermer.actuelle
        ? "Cette session est fermée : vous serez déconnecté à la prochaine action."
        : "Session fermée."
    );
    setSessionAFermer(null);
    await chargerSessions();
  };

  const fermerAutres = async () => {
    const result = await authApi.fermerAutresSessions();
    if (result.error) {
      toast.error(extractErrorMessage(result.error, "Les autres sessions n'ont pas pu être fermées."));
      return;
    }
    toast.success("Les autres sessions ont été fermées.");
    setConfirmationAutres(false);
    await chargerSessions();
  };

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Paramètres du Compte</h1>
        <p className="mt-1 text-muted-foreground">
          Personnalisez les préférences d'affichage disponibles dans cette instance.
        </p>
      </div>

      <form onSubmit={handleSaveSettings} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sun className="h-5 w-5 text-amber-500" />
              Apparence
            </CardTitle>
            <CardDescription>
              Le thème est appliqué immédiatement et conservé uniquement dans ce navigateur.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="theme">Mode Thème</Label>
              <Select value={theme} onValueChange={(value: ThemePreference) => setTheme(value)}>
                <SelectTrigger id="theme" className="w-full sm:w-[280px]">
                  <SelectValue placeholder="Choisir le thème" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="light">Clair (standard)</SelectItem>
                  <SelectItem value="dark">Sombre</SelectItem>
                  <SelectItem value="system">Système (automatique)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MonitorSmartphone className="h-5 w-5 text-primary" />
              Mes sessions
            </CardTitle>
            <CardDescription>
              Les machines où votre compte est connecté. Une session fermée ne peut plus rien rafraîchir.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {sessionsLoading && sessions.length === 0 ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <RefreshCw className="h-4 w-4 animate-spin" /> Chargement des sessions...
              </div>
            ) : sessions.length === 0 ? (
              <div className="flex items-start gap-2 text-sm text-muted-foreground" role="note">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>
                  Aucune session révocable trouvée : votre session date d'avant l'activation des sessions révocables.
                  Déconnectez-vous puis reconnectez-vous pour la faire apparaître ici.
                </span>
              </div>
            ) : (
              <ul className="divide-y divide-border/60">
                {sessions.map((session) => (
                  <li key={session.id} className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex min-w-0 items-start gap-3">
                      <Laptop className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-sm font-medium text-foreground">
                            Session du {formatDate(session.created_at)}
                          </span>
                          {session.actuelle && <Badge variant="secondary">Cette machine</Badge>}
                        </div>
                        <p className="text-xs text-muted-foreground">
                          Expire le {formatDate(session.expires_at)}
                          {session.last_used_at ? ` · dernière utilisation ${formatDate(session.last_used_at)}` : ""}
                        </p>
                      </div>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      className={session.actuelle ? "text-destructive hover:bg-destructive/10" : ""}
                      onClick={() => setSessionAFermer(session)}
                    >
                      <X className="mr-1.5 h-3.5 w-3.5" />Fermer
                    </Button>
                  </li>
                ))}
              </ul>
            )}
            {sessions.length > 1 && (
              <div className="flex justify-end border-t pt-3">
                <Button variant="outline" size="sm" onClick={() => setConfirmationAutres(true)}>
                  <LogOut className="mr-2 h-4 w-4" />Fermer les autres sessions
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-muted/60 bg-muted/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sliders className="h-5 w-5 text-muted-foreground" />
              Fonctionnalités non activées
            </CardTitle>
            <CardDescription>
              Ces préférences ne sont pas encore persistées par l'API et ne doivent pas être présentées comme actives.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-start gap-2 text-sm text-muted-foreground" role="note">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                La langue, le mode compact et l'enregistrement automatique seront disponibles après la persistance des préférences côté serveur.
              </span>
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end gap-3">
          <Button type="submit" className="shadow-md">
            <Save className="mr-2 h-4 w-4" />
            Enregistrer la préférence
          </Button>
        </div>
      </form>

      <AlertDialog open={sessionAFermer !== null} onOpenChange={(open) => !open && setSessionAFermer(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {sessionAFermer?.actuelle
                ? "Fermer cette session ?"
                : "Fermer cette session ?"}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {sessionAFermer?.actuelle
                ? "C'est la session de cette machine : vous serez déconnecté dès la prochaine action."
                : "Cette machine perdra l'accès dès sa prochaine requête."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction onClick={() => void fermerSession()} className="bg-destructive text-destructive-foreground">
              Fermer la session
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={confirmationAutres} onOpenChange={setConfirmationAutres}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Fermer toutes les autres sessions ?</AlertDialogTitle>
            <AlertDialogDescription>
              Toutes les autres machines seront déconnectées. Cette session reste ouverte.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction onClick={() => void fermerAutres()} className="bg-destructive text-destructive-foreground">
              Fermer les autres
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default ParametresCompte;
