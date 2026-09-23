import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Sliders, Sun, Moon, Globe, Shield, Save, Smartphone, Key } from "lucide-react";
import { toast } from "sonner";

const ParametresCompte = () => {
  const [theme, setTheme] = useState("system");
  const [langue, setLangue] = useState("fr");
  const [compactMode, setCompactMode] = useState(false);
  const [autoSave, setAutoSave] = useState(true);

  const handleSaveSettings = (e: React.FormEvent) => {
    e.preventDefault();
    toast.success("Vos préférences d'affichage et de système ont été appliquées.");
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Paramètres du Compte</h1>
        <p className="text-muted-foreground mt-1">
          Personnalisez votre expérience d'utilisation, affichage et préférences système
        </p>
      </div>

      <form onSubmit={handleSaveSettings} className="space-y-6">
        {/* Apparence */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sun className="h-5 w-5 text-amber-500" />
              Apparence & Thème
            </CardTitle>
            <CardDescription>
              Personnalisez les couleurs et le style visuel d'EduManagePro.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="theme">Mode Thème</Label>
              <Select value={theme} onValueChange={setTheme}>
                <SelectTrigger id="theme" className="w-full sm:w-[280px]">
                  <SelectValue placeholder="Choisir le thème" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="light">Clair (Standard)</SelectItem>
                  <SelectItem value="dark">Sombre (Dark Mode)</SelectItem>
                  <SelectItem value="system">Système (Automatique)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between py-2 border-t">
              <div>
                <p className="font-medium text-sm">Mode Affichage Compact</p>
                <p className="text-xs text-muted-foreground">
                  Réduit les espacements dans les tableaux et les listes.
                </p>
              </div>
              <Switch checked={compactMode} onCheckedChange={setCompactMode} />
            </div>
          </CardContent>
        </Card>

        {/* Langue & Région */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Globe className="h-5 w-5 text-blue-500" />
              Langue & Région
            </CardTitle>
            <CardDescription>
              Définissez la langue par défaut et le format de date.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="langue">Langue de l'interface</Label>
              <Select value={langue} onValueChange={setLangue}>
                <SelectTrigger id="langue" className="w-full sm:w-[280px]">
                  <SelectValue placeholder="Langue" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="fr">Français (FR)</SelectItem>
                  <SelectItem value="en">English (US)</SelectItem>
                  <SelectItem value="es">Español</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Sauvegarde & Comportement */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sliders className="h-5 w-5 text-emerald-500" />
              Comportement & Sauvegarde
            </CardTitle>
            <CardDescription>
              Ajustez l'enregistrement automatique lors des saisies de notes et formulaires.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between py-2">
              <div>
                <p className="font-medium text-sm">Enregistrement Automatique en Brouillon</p>
                <p className="text-xs text-muted-foreground">
                  Sauvegarde vos saisies de notes et formulaires toutes les 30 secondes.
                </p>
              </div>
              <Switch checked={autoSave} onCheckedChange={setAutoSave} />
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end gap-3">
          <Button type="submit" className="shadow-md">
            <Save className="h-4 w-4 mr-2" />
            Enregistrer les préférences
          </Button>
        </div>
      </form>
    </div>
  );
};

export default ParametresCompte;
