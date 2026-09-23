import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Switch } from "@/components/ui/switch";
import {
  User,
  Shield,
  Key,
  Bell,
  Camera,
  Save,
  CheckCircle2,
  Lock,
  Smartphone,
  History,
  Globe
} from "lucide-react";
import { toast } from "sonner";

const Profil = () => {
  const [profile, setProfile] = useState({
    prenom: "Marie",
    nom: "Dupont",
    email: "m.dupont@univ-edumanage.com",
    telephone: "+33 6 12 34 56 78",
    role: "Administrateur Principal",
    etablissement: "Institut Supérieur EduManage",
    bio: "Responsable de la transformation digitale et de la gestion administrative de l'établissement.",
  });

  const [passwords, setPasswords] = useState({
    current: "",
    new: "",
    confirm: "",
  });

  const [notifications, setNotifications] = useState({
    emailInscriptions: true,
    emailFactures: true,
    secutiteAlerts: true,
    weeklyReport: false,
  });

  const handleSaveProfile = (e: React.FormEvent) => {
    e.preventDefault();
    toast.success("Vos informations de profil ont été enregistrées avec succès.");
  };

  const handleChangePassword = (e: React.FormEvent) => {
    e.preventDefault();
    if (passwords.new !== passwords.confirm) {
      toast.error("Le nouveau mot de passe et sa confirmation ne correspondent pas.");
      return;
    }
    if (passwords.new.length < 8) {
      toast.error("Le mot de passe doit contenir au moins 8 caractères.");
      return;
    }
    toast.success("Votre mot de passe a été mis à jour avec succès.");
    setPasswords({ current: "", new: "", confirm: "" });
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Header Banner */}
      <div className="relative rounded-2xl bg-gradient-to-r from-primary via-primary/80 to-secondary p-6 sm:p-8 text-primary-foreground shadow-lg overflow-hidden">
        <div className="absolute right-0 top-0 bottom-0 opacity-10 pointer-events-none">
          <Shield className="h-64 w-64 -mr-16 -mt-16" />
        </div>

        <div className="relative flex flex-col sm:flex-row items-center gap-6">
          <div className="relative group cursor-pointer">
            <Avatar className="h-24 w-24 border-4 border-white/30 shadow-xl">
              <AvatarImage src="" />
              <AvatarFallback className="bg-sidebar-accent text-sidebar-foreground text-2xl font-bold">
                MD
              </AvatarFallback>
            </Avatar>
            <div className="absolute inset-0 rounded-full bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
              <Camera className="h-6 w-6 text-white" />
            </div>
          </div>

          <div className="text-center sm:text-left space-y-1">
            <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2">
              <h1 className="text-2xl sm:text-3xl font-bold">
                {profile.prenom} {profile.nom}
              </h1>
              <Badge className="bg-white/20 hover:bg-white/30 text-white border-none">
                {profile.role}
              </Badge>
            </div>
            <p className="text-white/80 text-sm">{profile.email}</p>
            <p className="text-white/60 text-xs">{profile.etablissement}</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="informations" className="space-y-6">
        <TabsList className="grid grid-cols-3 sm:grid-cols-4 w-full sm:w-auto">
          <TabsTrigger value="informations" className="gap-2">
            <User className="h-4 w-4" />
            <span className="hidden sm:inline">Informations</span>
          </TabsTrigger>
          <TabsTrigger value="securite" className="gap-2">
            <Lock className="h-4 w-4" />
            <span className="hidden sm:inline">Sécurité</span>
          </TabsTrigger>
          <TabsTrigger value="notifications" className="gap-2">
            <Bell className="h-4 w-4" />
            <span className="hidden sm:inline">Notifications</span>
          </TabsTrigger>
          <TabsTrigger value="sessions" className="gap-2">
            <History className="h-4 w-4" />
            <span className="hidden sm:inline">Connexions</span>
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Informations Personnelles */}
        <TabsContent value="informations">
          <Card>
            <CardHeader>
              <CardTitle>Informations Personnelles</CardTitle>
              <CardDescription>
                Mettez à jour vos informations de compte et coordonnées.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSaveProfile} className="space-y-6">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="prenom">Prénom</Label>
                    <Input
                      id="prenom"
                      value={profile.prenom}
                      onChange={(e) => setProfile({ ...profile, prenom: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="nom">Nom</Label>
                    <Input
                      id="nom"
                      value={profile.nom}
                      onChange={(e) => setProfile({ ...profile, nom: e.target.value })}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="email">Adresse Email</Label>
                    <Input
                      id="email"
                      type="email"
                      value={profile.email}
                      onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="telephone">Téléphone Direct</Label>
                    <Input
                      id="telephone"
                      value={profile.telephone}
                      onChange={(e) => setProfile({ ...profile, telephone: e.target.value })}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="bio">Biographie / Note de poste</Label>
                  <Input
                    id="bio"
                    value={profile.bio}
                    onChange={(e) => setProfile({ ...profile, bio: e.target.value })}
                  />
                </div>

                <div className="flex justify-end">
                  <Button type="submit" className="shadow-md">
                    <Save className="h-4 w-4 mr-2" />
                    Enregistrer les modifications
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 2: Sécurité */}
        <TabsContent value="securite">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Changer de mot de passe</CardTitle>
                <CardDescription>
                  Il est recommandé d'utiliser un mot de passe fort contenant au moins 8 caractères.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleChangePassword} className="space-y-4 max-w-md">
                  <div className="space-y-2">
                    <Label htmlFor="current">Mot de passe actuel</Label>
                    <Input
                      id="current"
                      type="password"
                      required
                      value={passwords.current}
                      onChange={(e) => setPasswords({ ...passwords, current: e.target.value })}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="new">Nouveau mot de passe</Label>
                    <Input
                      id="new"
                      type="password"
                      required
                      value={passwords.new}
                      onChange={(e) => setPasswords({ ...passwords, new: e.target.value })}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="confirm">Confirmer le nouveau mot de passe</Label>
                    <Input
                      id="confirm"
                      type="password"
                      required
                      value={passwords.confirm}
                      onChange={(e) => setPasswords({ ...passwords, confirm: e.target.value })}
                    />
                  </div>

                  <Button type="submit" className="w-full sm:w-auto">
                    <Key className="h-4 w-4 mr-2" />
                    Mettre à jour le mot de passe
                  </Button>
                </form>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Authentification à Deux Facteurs (2FA)</CardTitle>
                <CardDescription>
                  Renforcez la sécurité de votre compte avec Google Authenticator ou SMS.
                </CardDescription>
              </CardHeader>
              <CardContent className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-3 rounded-xl bg-primary/10 text-primary">
                    <Smartphone className="h-6 w-6" />
                  </div>
                  <div>
                    <p className="font-semibold">Double authentification</p>
                    <p className="text-xs text-muted-foreground">
                      Actuellement désactivée sur ce compte.
                    </p>
                  </div>
                </div>
                <Button
                  variant="outline"
                  onClick={() => toast.info("Configuration 2FA en cours de développement...")}
                >
                  Configurer 2FA
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Tab 3: Notifications */}
        <TabsContent value="notifications">
          <Card>
            <CardHeader>
              <CardTitle>Préférences d'Alertes et Notifications</CardTitle>
              <CardDescription>
                Choisissez les événements pour lesquels vous souhaitez recevoir un email.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between py-2 border-b">
                <div>
                  <p className="font-medium text-sm">Nouvelles Inscriptions</p>
                  <p className="text-xs text-muted-foreground">
                    Recevoir une alerte quand un dossier d'inscription est soumis.
                  </p>
                </div>
                <Switch
                  checked={notifications.emailInscriptions}
                  onCheckedChange={(val) =>
                    setNotifications({ ...notifications, emailInscriptions: val })
                  }
                />
              </div>

              <div className="flex items-center justify-between py-2 border-b">
                <div>
                  <p className="font-medium text-sm">Paiements & Factures</p>
                  <p className="text-xs text-muted-foreground">
                    Alerte sur les encaissements ou retards de frais de scolarité.
                  </p>
                </div>
                <Switch
                  checked={notifications.emailFactures}
                  onCheckedChange={(val) =>
                    setNotifications({ ...notifications, emailFactures: val })
                  }
                />
              </div>

              <div className="flex items-center justify-between py-2 border-b">
                <div>
                  <p className="font-medium text-sm">Alertes de Sécurité</p>
                  <p className="text-xs text-muted-foreground">
                    Connexion depuis un nouvel appareil ou tentative suspecte.
                  </p>
                </div>
                <Switch
                  checked={notifications.secutiteAlerts}
                  onCheckedChange={(val) =>
                    setNotifications({ ...notifications, secutiteAlerts: val })
                  }
                />
              </div>

              <div className="flex items-center justify-between py-2">
                <div>
                  <p className="font-medium text-sm">Rapport Hebdomadaire BI</p>
                  <p className="text-xs text-muted-foreground">
                    Un résumé des performances académiques et financières chaque lundi.
                  </p>
                </div>
                <Switch
                  checked={notifications.weeklyReport}
                  onCheckedChange={(val) =>
                    setNotifications({ ...notifications, weeklyReport: val })
                  }
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 4: Historique des Sessions */}
        <TabsContent value="sessions">
          <Card>
            <CardHeader>
              <CardTitle>Sessions Actives & Historique</CardTitle>
              <CardDescription>
                Aperçu des appareils connectés à votre compte EduManagePro.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 rounded-xl bg-emerald-500/10 border border-emerald-200">
                  <div className="flex items-center gap-3">
                    <Globe className="h-5 w-5 text-emerald-600" />
                    <div>
                      <p className="font-semibold text-sm">Windows PC • Chrome (Session Actuelle)</p>
                      <p className="text-xs text-muted-foreground">Paris, France • IP: 192.168.1.45</p>
                    </div>
                  </div>
                  <Badge className="bg-emerald-600">Actif</Badge>
                </div>

                <div className="flex items-center justify-between p-4 rounded-xl border">
                  <div className="flex items-center gap-3">
                    <Smartphone className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <p className="font-semibold text-sm">iPhone 14 • Safari Mobile</p>
                      <p className="text-xs text-muted-foreground">Dernière activité: Hier à 18:22</p>
                    </div>
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => toast.info("Session fermée.")}>
                    Déconnecter
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Profil;
