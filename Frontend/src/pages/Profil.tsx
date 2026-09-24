import { useEffect, useState, type FormEvent } from "react";
import { Camera, Key, Lock, Save, Shield, User } from "lucide-react";
import { toast } from "sonner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuth } from "@/contexts/AuthContext";
import { authApi, setupApi } from "@/services/apiClient";

const Profil = () => {
  const { user, refreshUser } = useAuth();
  const [profile, setProfile] = useState({ prenom: "", nom: "", email: "", telephone: "" });
  const [institution, setInstitution] = useState("");
  const [passwords, setPasswords] = useState({ current: "", next: "", confirm: "" });
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);

  useEffect(() => {
    if (!user) return;
    setProfile({ prenom: user.prenom || "", nom: user.nom || "", email: user.email || "", telephone: user.telephone || "" });
    void setupApi.getStatus().then((result) => setInstitution(result.data?.etablissement_nom || ""));
  }, [user]);

  const saveProfile = async (event: FormEvent) => {
    event.preventDefault();
    setSavingProfile(true);
    const result = await authApi.updateMe({ prenom: profile.prenom, nom: profile.nom, telephone: profile.telephone || null });
    setSavingProfile(false);
    if (result.error) { toast.error(result.error); return; }
    await refreshUser();
    toast.success("Profil mis à jour.");
  };

  const changePassword = async (event: FormEvent) => {
    event.preventDefault();
    if (passwords.next !== passwords.confirm) { toast.error("Les nouveaux mots de passe ne correspondent pas."); return; }
    if (passwords.next.length < 8) { toast.error("Le mot de passe doit contenir au moins 8 caractères."); return; }
    setSavingPassword(true);
    const result = await authApi.changePassword({ current_password: passwords.current, new_password: passwords.next });
    setSavingPassword(false);
    if (result.error) { toast.error(result.error); return; }
    setPasswords({ current: "", next: "", confirm: "" });
    toast.success("Mot de passe mis à jour.");
  };

  const initials = `${profile.prenom.charAt(0)}${profile.nom.charAt(0)}`.toUpperCase() || "—";
  return <div className="space-y-8 max-w-5xl mx-auto"><div className="rounded-2xl bg-primary p-6 text-primary-foreground shadow-lg"><div className="flex flex-col sm:flex-row items-center gap-6"><Avatar className="h-24 w-24 border-4 border-white/30"><AvatarFallback className="bg-white/20 text-2xl font-bold text-white">{initials}</AvatarFallback></Avatar><div className="text-center sm:text-left"><div className="flex flex-wrap items-center justify-center sm:justify-start gap-2"><h1 className="text-2xl font-bold">{profile.prenom} {profile.nom}</h1><Badge className="bg-white/20 text-white border-none">{user?.role || "NON RENSEIGNÉ"}</Badge></div><p className="text-white/80 text-sm">{profile.email || "Email non renseigné"}</p><p className="text-white/70 text-xs">{institution || "Établissement non renseigné"}</p></div></div></div><Tabs defaultValue="informations" className="space-y-6"><TabsList className="grid grid-cols-2 sm:grid-cols-3 w-full sm:w-auto"><TabsTrigger value="informations"><User className="h-4 w-4" />Informations</TabsTrigger><TabsTrigger value="securite"><Lock className="h-4 w-4" />Sécurité</TabsTrigger><TabsTrigger value="sessions"><Shield className="h-4 w-4" />Sessions</TabsTrigger></TabsList><TabsContent value="informations"><Card><CardHeader><CardTitle>Informations personnelles</CardTitle><CardDescription>Seules les informations présentes dans le backend sont modifiables.</CardDescription></CardHeader><CardContent><form onSubmit={saveProfile} className="space-y-4"><div className="grid gap-4 sm:grid-cols-2"><div className="space-y-2"><Label htmlFor="profile-prenom">Prénom</Label><Input id="profile-prenom" value={profile.prenom} onChange={(event) => setProfile({ ...profile, prenom: event.target.value })} /></div><div className="space-y-2"><Label htmlFor="profile-nom">Nom</Label><Input id="profile-nom" value={profile.nom} onChange={(event) => setProfile({ ...profile, nom: event.target.value })} /></div></div><div className="grid gap-4 sm:grid-cols-2"><div className="space-y-2"><Label htmlFor="profile-email">Email</Label><Input id="profile-email" value={profile.email} readOnly /></div><div className="space-y-2"><Label htmlFor="profile-telephone">Téléphone</Label><Input id="profile-telephone" value={profile.telephone} onChange={(event) => setProfile({ ...profile, telephone: event.target.value })} /></div></div><Button type="submit" disabled={savingProfile}><Save className="mr-2 h-4 w-4" />{savingProfile ? "Enregistrement..." : "Enregistrer"}</Button></form></CardContent></Card></TabsContent><TabsContent value="securite"><Card><CardHeader><CardTitle>Changer de mot de passe</CardTitle><CardDescription>Le changement est effectué par l'API avec vérification du mot de passe actuel.</CardDescription></CardHeader><CardContent><form onSubmit={changePassword} className="max-w-md space-y-4"><div className="space-y-2"><Label htmlFor="current-password">Mot de passe actuel</Label><Input id="current-password" type="password" required value={passwords.current} onChange={(event) => setPasswords({ ...passwords, current: event.target.value })} /></div><div className="space-y-2"><Label htmlFor="new-password">Nouveau mot de passe</Label><Input id="new-password" type="password" minLength={8} required value={passwords.next} onChange={(event) => setPasswords({ ...passwords, next: event.target.value })} /></div><div className="space-y-2"><Label htmlFor="confirm-password">Confirmation</Label><Input id="confirm-password" type="password" minLength={8} required value={passwords.confirm} onChange={(event) => setPasswords({ ...passwords, confirm: event.target.value })} /></div><Button type="submit" disabled={savingPassword}><Key className="mr-2 h-4 w-4" />{savingPassword ? "Modification..." : "Modifier le mot de passe"}</Button></form></CardContent></Card><Alert><Shield className="h-4 w-4" /><AlertTitle>Double authentification</AlertTitle><AlertDescription>La configuration 2FA n'est pas encore exposée par le backend.</AlertDescription></Alert></TabsContent><TabsContent value="sessions"><Card><CardHeader><CardTitle>Connexions</CardTitle><CardDescription>Les sessions et appareils connectés ne sont pas encore persistés.</CardDescription></CardHeader><CardContent><Alert><Camera className="h-4 w-4" /><AlertTitle>Historique indisponible</AlertTitle><AlertDescription>Aucune session fictive n'est affichée. Le module d'audit sera activé après son endpoint backend.</AlertDescription></Alert></CardContent></Card></TabsContent></Tabs></div>;
};

export default Profil;
