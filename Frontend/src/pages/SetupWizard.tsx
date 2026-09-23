import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Server,
  Building2,
  UserCheck,
  KeyRound,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  Loader2,
  AlertTriangle,
  Sparkles,
  Database,
  Lock,
  Mail,
  Phone,
  MapPin,
  Globe,
} from "lucide-react";
import { toast } from "sonner";
import { setupApi } from "@/services/apiClient";
import logo from "@/assets/logo.svg";

export default function SetupWizard() {
  const navigate = useNavigate();

  // État du statut système
  const [checkingStatus, setCheckingStatus] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [setupCompleted, setSetupCompleted] = useState(false);
  const [dbStatus, setDbStatus] = useState<any>(null);

  // Étape courante (1 à 4)
  const [currentStep, setCurrentStep] = useState(1);

  // Formulaire Étape 1 : Base de données
  const [dbConfig, setDbConfig] = useState({
    useDefault: true,
    host: "localhost",
    port: 5432,
    database: "edumanagepro",
    user: "postgres",
    password: "",
  });

  // Formulaire Étape 2 : Établissement
  const [etablissement, setEtablissement] = useState({
    nom: "Institut Supérieur des Technologies & Management",
    code: "ISTM",
    email: "contact@istm-edu.com",
    telephone: "+225 27 22 00 00",
    adresse: "Cocody Riviera, Boulevard de France",
    ville: "Abidjan",
    pays: "Côte d'Ivoire",
    devise: "FCFA",
  });

  // Formulaire Étape 3 : SuperAdmin
  const [admin, setAdmin] = useState({
    nom: "Directeur",
    prenom: "Principal",
    email: "admin@edumanagepro.com",
    telephone: "+225 07 00 00 01",
    password: "",
    confirmPassword: "",
  });

  // Formulaire Étape 4 : Licence & Options
  const [licence, setLicence] = useState({
    licenseKey: "EMP-LIC-2026-ENTERPRISE-PRO",
    initDefaultAcademicSession: true,
  });

  // 1. Vérification préliminaire au chargement
  useEffect(() => {
    async function checkInit() {
      setCheckingStatus(true);
      const res = await setupApi.getStatus();
      setCheckingStatus(false);
      if (res.data) {
        setDbStatus(res.data);
        if (res.data.is_configured) {
          toast.info("Le système est déjà configuré. Redirection vers la page de connexion...");
          navigate("/login");
        }
      }
    }
    checkInit();
  }, [navigate]);

  // Calcul de la complexité du mot de passe
  const getPasswordStrength = () => {
    const pwd = admin.password;
    let score = 0;
    if (pwd.length >= 8) score += 25;
    if (/[A-Z]/.test(pwd)) score += 25;
    if (/[0-9]/.test(pwd)) score += 25;
    if (/[^A-Za-z0-9]/.test(pwd)) score += 25;
    return score;
  };

  const passwordStrength = getPasswordStrength();

  // Soumission finale
  const handleFinalSubmit = async () => {
    if (admin.password !== admin.confirmPassword) {
      toast.error("Les deux mots de passe ne correspondent pas.");
      return;
    }
    if (admin.password.length < 6) {
      toast.error("Le mot de passe doit contenir au moins 6 caractères.");
      return;
    }

    setSubmitting(true);
    const payload = {
      etablissement: {
        nom: etablissement.nom,
        code: etablissement.code,
        adresse: `${etablissement.adresse}, ${etablissement.ville}, ${etablissement.pays}`,
        telephone: etablissement.telephone,
        email: etablissement.email,
        devise: etablissement.devise,
        license_key: licence.licenseKey,
      },
      admin: {
        nom: admin.nom,
        prenom: admin.prenom,
        email: admin.email,
        password: admin.password,
        telephone: admin.telephone,
      },
      database: dbConfig.useDefault
        ? undefined
        : {
            host: dbConfig.host,
            port: Number(dbConfig.port),
            database: dbConfig.database,
            user: dbConfig.user,
            password: dbConfig.password,
          },
      init_default_academic_session: licence.initDefaultAcademicSession,
    };

    const res = await setupApi.initialize(payload);
    setSubmitting(false);

    if (res.error) {
      if (res.status === 409) {
        toast.warning("Ce système a déjà été initialisé.");
        navigate("/login");
      } else {
        toast.error(`Erreur d'initialisation : ${res.error}`);
      }
      return;
    }

    toast.success("Initialisation d'EduManagePro terminée avec succès !");
    setSetupCompleted(true);
  };

  if (checkingStatus) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center space-y-4">
          <Loader2 className="h-10 w-10 animate-spin text-primary mx-auto" />
          <p className="text-sm text-muted-foreground font-medium">
            Vérification de l'état d'initialisation du serveur...
          </p>
        </div>
      </div>
    );
  }

  // Écran de Succès Final
  if (setupCompleted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-sidebar via-background to-sidebar p-4">
        <Card className="max-w-md w-full border-emerald-500/30 shadow-2xl text-center p-6 space-y-6">
          <div className="mx-auto h-16 w-16 rounded-full bg-emerald-500/10 flex items-center justify-center text-emerald-500">
            <CheckCircle2 className="h-10 w-10" />
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl font-bold text-foreground">Système Initialisé !</h2>
            <p className="text-sm text-muted-foreground">
              L'établissement <strong>{etablissement.nom}</strong> et votre compte Super-Administrateur sont prêts.
            </p>
          </div>
          <div className="bg-muted/50 rounded-lg p-4 text-left text-xs space-y-2">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Identifiant Admin :</span>
              <span className="font-semibold">{admin.email}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Devise retenue :</span>
              <span className="font-semibold">{etablissement.devise}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Session académique :</span>
              <span className="font-semibold">
                {licence.initDefaultAcademicSession ? "2025-2026 (Active)" : "À configurer"}
              </span>
            </div>
          </div>
          <Button
            onClick={() => navigate("/login")}
            className="w-full bg-primary hover:bg-primary/90 text-primary-foreground font-semibold"
          >
            Se Connecter au Portail <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-sidebar via-background to-sidebar flex flex-col justify-center items-center p-4">
      {/* Container Principal */}
      <div className="w-full max-w-2xl space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="mx-auto h-14 w-14 rounded-2xl bg-gradient-to-br from-primary via-primary/80 to-secondary p-1 shadow-lg flex items-center justify-center">
            <img src={logo} alt="EduManagePro" className="h-full w-full object-contain rounded-xl bg-sidebar" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Bienvenue dans EduManagePro
          </h1>
          <p className="text-xs text-muted-foreground">
            Assistant de premier démarrage & paramétrage initial de votre instance
          </p>
        </div>

        {/* Stepper Indicator */}
        <div className="grid grid-cols-4 gap-2">
          {[
            { num: 1, title: "Infrastructure", icon: Database },
            { num: 2, title: "Établissement", icon: Building2 },
            { num: 3, title: "SuperAdmin", icon: UserCheck },
            { num: 4, title: "Licence", icon: KeyRound },
          ].map((s) => {
            const Icon = s.icon;
            const isDone = currentStep > s.num;
            const isCurrent = currentStep === s.num;
            return (
              <div
                key={s.num}
                className={`flex flex-col items-center p-2 rounded-lg text-center transition-all ${
                  isCurrent
                    ? "bg-primary/10 border border-primary/30 text-primary"
                    : isDone
                    ? "bg-muted/50 text-muted-foreground"
                    : "opacity-50 text-muted-foreground"
                }`}
              >
                <div
                  className={`h-7 w-7 rounded-full flex items-center justify-center text-xs font-bold mb-1 ${
                    isCurrent
                      ? "bg-primary text-primary-foreground"
                      : isDone
                      ? "bg-emerald-500 text-white"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {isDone ? "✓" : s.num}
                </div>
                <span className="text-[11px] font-medium hidden sm:inline">{s.title}</span>
              </div>
            );
          })}
        </div>

        {/* Wizard Card */}
        <Card className="border-border/60 shadow-xl backdrop-blur">
          {/* ÉTAPE 1 : INFRASTRUCTURE & BASE DE DONNÉES */}
          {currentStep === 1 && (
            <>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Database className="h-5 w-5 text-primary" /> Étape 1 : Connexion Base de Données
                </CardTitle>
                <CardDescription className="text-xs">
                  Vérification de la connectivité avec le serveur de stockage PostgreSQL.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="bg-primary/5 border border-primary/20 rounded-lg p-4 flex items-start gap-3">
                  <Server className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                  <div className="text-xs space-y-1">
                    <p className="font-semibold text-foreground">Environnement Conteneurisé / Détection Automatique</p>
                    <p className="text-muted-foreground">
                      Le backend configure automatiquement le pool de connexions asynchrone (Asyncpg) et applique les
                      migrations Alembic lors de la validation.
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-2 pt-2">
                  <Checkbox
                    id="useDefaultDb"
                    checked={dbConfig.useDefault}
                    onCheckedChange={(checked) =>
                      setDbConfig({ ...dbConfig, useDefault: !!checked })
                    }
                  />
                  <Label htmlFor="useDefaultDb" className="text-xs font-normal">
                    Utiliser les paramètres de base de données par défaut du fichier d'environnement (.env)
                  </Label>
                </div>

                {!dbConfig.useDefault && (
                  <div className="grid grid-cols-2 gap-3 pt-2 border-t border-border/40">
                    <div className="space-y-1">
                      <Label className="text-xs">Hôte PostgreSQL</Label>
                      <Input
                        value={dbConfig.host}
                        onChange={(e) => setDbConfig({ ...dbConfig, host: e.target.value })}
                        className="text-xs h-9"
                        placeholder="localhost"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Port</Label>
                      <Input
                        type="number"
                        value={dbConfig.port}
                        onChange={(e) => setDbConfig({ ...dbConfig, port: Number(e.target.value) })}
                        className="text-xs h-9"
                        placeholder="5432"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Nom de la Base</Label>
                      <Input
                        value={dbConfig.database}
                        onChange={(e) => setDbConfig({ ...dbConfig, database: e.target.value })}
                        className="text-xs h-9"
                        placeholder="edumanagepro"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Utilisateur</Label>
                      <Input
                        value={dbConfig.user}
                        onChange={(e) => setDbConfig({ ...dbConfig, user: e.target.value })}
                        className="text-xs h-9"
                        placeholder="postgres"
                      />
                    </div>
                    <div className="col-span-2 space-y-1">
                      <Label className="text-xs">Mot de passe</Label>
                      <Input
                        type="password"
                        value={dbConfig.password}
                        onChange={(e) => setDbConfig({ ...dbConfig, password: e.target.value })}
                        className="text-xs h-9"
                        placeholder="••••••••"
                      />
                    </div>
                  </div>
                )}
              </CardContent>
              <CardFooter className="flex justify-end border-t border-border/40 pt-4">
                <Button onClick={() => setCurrentStep(2)} className="text-xs h-9">
                  Continuer <ArrowRight className="ml-2 h-3.5 w-3.5" />
                </Button>
              </CardFooter>
            </>
          )}

          {/* ÉTAPE 2 : PROFIL ÉTABLISSEMENT */}
          {currentStep === 2 && (
            <>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Building2 className="h-5 w-5 text-primary" /> Étape 2 : Profil de l'Établissement
                </CardTitle>
                <CardDescription className="text-xs">
                  Renseignez les données d'identité de l'université ou de l'école.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-3 gap-3">
                  <div className="col-span-2 space-y-1">
                    <Label className="text-xs">Nom complet de l'établissement *</Label>
                    <Input
                      required
                      value={etablissement.nom}
                      onChange={(e) => setEtablissement({ ...etablissement, nom: e.target.value })}
                      className="text-xs h-9"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Sigle / Code *</Label>
                    <Input
                      required
                      value={etablissement.code}
                      onChange={(e) => setEtablissement({ ...etablissement, code: e.target.value.toUpperCase() })}
                      className="text-xs h-9 font-mono"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs">Email officiel</Label>
                    <Input
                      type="email"
                      value={etablissement.email}
                      onChange={(e) => setEtablissement({ ...etablissement, email: e.target.value })}
                      className="text-xs h-9"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Téléphone standard</Label>
                    <Input
                      value={etablissement.telephone}
                      onChange={(e) => setEtablissement({ ...etablissement, telephone: e.target.value })}
                      className="text-xs h-9"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div className="col-span-2 space-y-1">
                    <Label className="text-xs">Adresse géographique</Label>
                    <Input
                      value={etablissement.adresse}
                      onChange={(e) => setEtablissement({ ...etablissement, adresse: e.target.value })}
                      className="text-xs h-9"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Devise monétaire *</Label>
                    <Select
                      value={etablissement.devise}
                      onValueChange={(val) => setEtablissement({ ...etablissement, devise: val })}
                    >
                      <SelectTrigger className="text-xs h-9">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="FCFA">FCFA (XOF/XAF)</SelectItem>
                        <SelectItem value="EUR">EUR (€)</SelectItem>
                        <SelectItem value="USD">USD ($)</SelectItem>
                        <SelectItem value="GNF">GNF (Franc guinéen)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </CardContent>
              <CardFooter className="flex justify-between border-t border-border/40 pt-4">
                <Button variant="outline" onClick={() => setCurrentStep(1)} className="text-xs h-9">
                  <ArrowLeft className="mr-2 h-3.5 w-3.5" /> Précédent
                </Button>
                <Button
                  onClick={() => {
                    if (!etablissement.nom || !etablissement.code) {
                      toast.error("Veuillez renseigner le nom et le code de l'établissement.");
                      return;
                    }
                    setCurrentStep(3);
                  }}
                  className="text-xs h-9"
                >
                  Continuer <ArrowRight className="ml-2 h-3.5 w-3.5" />
                </Button>
              </CardFooter>
            </>
          )}

          {/* ÉTAPE 3 : COMPTE SUPER-ADMINISTRATEUR */}
          {currentStep === 3 && (
            <>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <UserCheck className="h-5 w-5 text-primary" /> Étape 3 : Compte Super-Administrateur
                </CardTitle>
                <CardDescription className="text-xs">
                  Créez les identifiants d'accès maître pour gérer toute la plateforme.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs">Nom de famille *</Label>
                    <Input
                      required
                      value={admin.nom}
                      onChange={(e) => setAdmin({ ...admin, nom: e.target.value })}
                      className="text-xs h-9"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Prénom(s) *</Label>
                    <Input
                      required
                      value={admin.prenom}
                      onChange={(e) => setAdmin({ ...admin, prenom: e.target.value })}
                      className="text-xs h-9"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs">Email de connexion (Login) *</Label>
                    <Input
                      type="email"
                      required
                      value={admin.email}
                      onChange={(e) => setAdmin({ ...admin, email: e.target.value })}
                      className="text-xs h-9"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Téléphone mobile</Label>
                    <Input
                      value={admin.telephone}
                      onChange={(e) => setAdmin({ ...admin, telephone: e.target.value })}
                      className="text-xs h-9"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 pt-1">
                  <div className="space-y-1">
                    <Label className="text-xs">Mot de passe maître *</Label>
                    <Input
                      type="password"
                      required
                      value={admin.password}
                      onChange={(e) => setAdmin({ ...admin, password: e.target.value })}
                      className="text-xs h-9"
                      placeholder="Min. 6 caractères"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Confirmation *</Label>
                    <Input
                      type="password"
                      required
                      value={admin.confirmPassword}
                      onChange={(e) => setAdmin({ ...admin, confirmPassword: e.target.value })}
                      className="text-xs h-9"
                      placeholder="Confirmez le mot de passe"
                    />
                  </div>
                </div>

                {/* Barre de force du mot de passe */}
                {admin.password && (
                  <div className="space-y-1 pt-1">
                    <div className="flex justify-between text-[11px] text-muted-foreground">
                      <span>Sécurité du mot de passe</span>
                      <span>
                        {passwordStrength <= 25 && "Faible"}
                        {passwordStrength === 50 && "Moyen"}
                        {passwordStrength === 75 && "Bon"}
                        {passwordStrength === 100 && "Excellent"}
                      </span>
                    </div>
                    <Progress value={passwordStrength} className="h-1.5" />
                  </div>
                )}
              </CardContent>
              <CardFooter className="flex justify-between border-t border-border/40 pt-4">
                <Button variant="outline" onClick={() => setCurrentStep(2)} className="text-xs h-9">
                  <ArrowLeft className="mr-2 h-3.5 w-3.5" /> Précédent
                </Button>
                <Button
                  onClick={() => {
                    if (!admin.email || !admin.password) {
                      toast.error("Veuillez renseigner l'email et le mot de passe.");
                      return;
                    }
                    if (admin.password !== admin.confirmPassword) {
                      toast.error("Les deux mots de passe ne correspondent pas.");
                      return;
                    }
                    setCurrentStep(4);
                  }}
                  className="text-xs h-9"
                >
                  Continuer <ArrowRight className="ml-2 h-3.5 w-3.5" />
                </Button>
              </CardFooter>
            </>
          )}

          {/* ÉTAPE 4 : LICENCE & FINALISATION */}
          {currentStep === 4 && (
            <>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <KeyRound className="h-5 w-5 text-primary" /> Étape 4 : Licence & Finalisation
                </CardTitle>
                <CardDescription className="text-xs">
                  Validation de la clé d'activation et génération des paramètres initiaux.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-1">
                  <Label className="text-xs">Clé de Licence / Code d'activation</Label>
                  <Input
                    value={licence.licenseKey}
                    onChange={(e) => setLicence({ ...licence, licenseKey: e.target.value })}
                    className="text-xs h-9 font-mono uppercase"
                    placeholder="EMP-LIC-2026-XXXX-XXXX"
                  />
                  <p className="text-[11px] text-muted-foreground">
                    Laisse active la licence standard pour le déploiement actuel.
                  </p>
                </div>

                <div className="bg-muted/40 border border-border/40 rounded-lg p-3 space-y-2">
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="initSession"
                      checked={licence.initDefaultAcademicSession}
                      onCheckedChange={(c) =>
                        setLicence({ ...licence, initDefaultAcademicSession: !!c })
                      }
                    />
                    <Label htmlFor="initSession" className="text-xs font-semibold cursor-pointer">
                      Générer la session académique initiale 2025-2026
                    </Label>
                  </div>
                  <p className="text-[11px] text-muted-foreground pl-6">
                    Crée automatiquement la session active 2025-2026 avec le calendrier financier en 10 tranches mensuelles (Octobre à Juillet).
                  </p>
                </div>

                {/* Récapitulatif */}
                <div className="border border-border/40 rounded-lg p-3 text-xs space-y-1.5 bg-background">
                  <p className="font-bold text-foreground text-xs border-b border-border/40 pb-1">
                    Récapitulatif de votre configuration :
                  </p>
                  <div className="grid grid-cols-2 gap-2 text-muted-foreground pt-1">
                    <div>Établissement : <strong className="text-foreground">{etablissement.nom}</strong></div>
                    <div>Code : <strong className="text-foreground">{etablissement.code}</strong></div>
                    <div>SuperAdmin : <strong className="text-foreground">{admin.email}</strong></div>
                    <div>Devise : <strong className="text-foreground">{etablissement.devise}</strong></div>
                  </div>
                </div>
              </CardContent>
              <CardFooter className="flex justify-between border-t border-border/40 pt-4">
                <Button variant="outline" onClick={() => setCurrentStep(3)} className="text-xs h-9" disabled={submitting}>
                  <ArrowLeft className="mr-2 h-3.5 w-3.5" /> Précédent
                </Button>
                <Button
                  onClick={handleFinalSubmit}
                  disabled={submitting}
                  className="bg-primary hover:bg-primary/90 text-primary-foreground text-xs h-9 font-semibold"
                >
                  {submitting ? (
                    <>
                      <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" /> Initialisation en cours...
                    </>
                  ) : (
                    <>
                      <Sparkles className="mr-2 h-3.5 w-3.5" /> Initialiser EduManagePro
                    </>
                  )}
                </Button>
              </CardFooter>
            </>
          )}
        </Card>
      </div>
    </div>
  );
}
