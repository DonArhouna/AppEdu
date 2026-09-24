import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { AlertCircle, Save, Sliders, Sun } from "lucide-react";
import { toast } from "sonner";

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
    </div>
  );
};

export default ParametresCompte;
