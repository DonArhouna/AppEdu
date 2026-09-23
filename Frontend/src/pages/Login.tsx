import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Lock,
  Mail,
  Eye,
  EyeOff,
  ShieldCheck,
  Loader2,
  Wrench,
  Sun,
  Moon,
  Sparkles,
} from "lucide-react";
import logo from "@/assets/logo.svg";
import loginBg from "@/assets/login-bg.png";
import { toast } from "sonner";
import { authApi, setupApi } from "@/services/apiClient";
import { useRBAC, UserRole } from "@/contexts/RBACContext";

const Login = () => {
  const navigate = useNavigate();
  const { setCurrentRole } = useRBAC();

  const [email, setEmail] = useState("admin@edumanagepro.com");
  const [password, setPassword] = useState("Admin@2026!");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(() => {
    return (
      document.documentElement.classList.contains("dark") ||
      localStorage.getItem("theme") === "dark"
    );
  });

  // Synchronisation du thème clair/sombre
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add("dark");
      localStorage.setItem("theme", "dark");
    } else {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("theme", "light");
    }
  }, [isDarkMode]);

  // Vérifier si le système a déjà été configuré
  useEffect(() => {
    async function checkStatus() {
      const res = await setupApi.getStatus();
      if (res.data && !res.data.is_configured) {
        toast.info("Premier démarrage détecté. Redirection vers l'assistant d'installation...");
        navigate("/setup");
      }
    }
    checkStatus();
  }, [navigate]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanEmail = email.trim();
    if (!cleanEmail) {
      toast.warning("Veuillez renseigner votre adresse email.");
      return;
    }
    if (!password) {
      toast.warning("Veuillez renseigner votre mot de passe.");
      return;
    }

    setLoading(true);
    const res = await authApi.login(cleanEmail, password);
    setLoading(false);

    if (res.error) {
      const errMessage =
        typeof res.error === "string"
          ? res.error
          : "Identifiants invalides ou mot de passe incorrect.";
      toast.error(errMessage);
      return;
    }

    if (res.data?.user) {
      const user = res.data.user;
      if (user.role) {
        setCurrentRole(user.role as UserRole);
      }
      toast.success(`Connexion réussie ! Bienvenue, ${user.prenom || user.nom}.`);
      navigate("/");
    } else {
      toast.success("Connexion réussie ! Bienvenue sur EduManagePro.");
      navigate("/");
    }
  };

  const handleForgotPassword = () => {
    toast.info(
      "Réinitialisation du mot de passe : Veuillez contacter l'administrateur technique de votre établissement.",
      { duration: 5000 }
    );
  };

  const handleSupport = () => {
    toast.info("Support technique EMP : support@edumanagepro.com | +225 27 22 00 00", {
      duration: 5000,
    });
  };

  const handleDemoLogin = (role: string, demoEmail: string) => {
    setEmail(demoEmail);
    setPassword("Admin@2026!");
    toast.info(`Identifiants ${role} chargés. Cliquez sur Se connecter.`);
  };

  return (
    <div className="h-screen max-h-screen w-full grid lg:grid-cols-2 bg-background text-foreground selection:bg-primary/20 overflow-hidden">
      {/* ==================================================================== */}
      {/* COLONNE GAUCHE : STORYTELLING, IMAGE DE FOND & BRANDING */}
      {/* ==================================================================== */}
      <div className="relative hidden lg:flex flex-col justify-between p-8 xl:p-12 border-r border-border/50 overflow-hidden h-full">
        {/* Image de fond avec cover & centrage */}
        <div
          className="absolute inset-0 bg-cover bg-center bg-no-repeat transition-transform duration-700 ease-out scale-[1.02]"
          style={{ backgroundImage: `url(${loginBg})` }}
        />

        {/* Overlay semi-transparent assombri pour garantir un contraste parfait (WCAG AAA) */}
        <div className="absolute inset-0 bg-gradient-to-t from-slate-950/95 via-slate-950/80 to-slate-900/70 backdrop-blur-[1px]" />

        {/* Halo lumineux subtil aux couleurs de la marque */}
        <div className="absolute -top-20 -left-20 h-72 w-72 rounded-full bg-primary/20 blur-3xl pointer-events-none" />

        {/* 1. Brand Header */}
        <div className="relative z-10 flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-primary via-primary/90 to-primary/70 p-0.5 shadow-lg flex items-center justify-center">
            <img src={logo} alt="EduManagePro" className="h-full w-full object-contain rounded-[10px] bg-slate-900 p-1" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-base tracking-tight text-white drop-shadow-sm">
                EduManagePro
              </span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-black tracking-wider bg-primary/30 text-blue-300 border border-primary/40 uppercase">
                EMP
              </span>
            </div>
            <p className="text-[10px] text-slate-300 uppercase tracking-widest font-medium">
              Système de Gestion Universitaire
            </p>
          </div>
        </div>

        {/* 2. Core Storytelling & Accroche (dimensionnement compact sans scroll) */}
        <div className="relative z-10 space-y-5 max-w-lg my-auto py-4">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-white/10 border border-white/15 text-xs text-blue-200 backdrop-blur-md">
              <Sparkles className="h-3.5 w-3.5 text-blue-300" />
              <span>Plateforme Universitaire Intégrée</span>
            </div>

            <h1 className="text-3xl xl:text-4xl font-extrabold tracking-tight text-white leading-tight drop-shadow-md">
              Pilotez votre <span className="text-blue-400 italic font-semibold underline decoration-blue-400/40 underline-offset-4">scolarité</span> en toute simplicité.
            </h1>
            <p className="text-xs xl:text-sm text-slate-200/90 leading-relaxed">
              Une plateforme intuitive et performante pour centraliser la gestion de vos étudiants, des délibérations ECTS/LMD, des paiements et de la pédagogie.
            </p>
          </div>

          {/* Carte interactive compacte */}
          <div className="rounded-xl border border-white/15 bg-slate-900/60 backdrop-blur-md p-3.5 shadow-2xl space-y-2.5 text-white">
            <div className="flex items-center justify-between text-xs pb-2 border-b border-white/10">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="font-semibold text-slate-100">Système Connecté</span>
              </div>
              <span className="text-[11px] font-mono text-slate-300">Session 2025-2026</span>
            </div>

            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="p-2 rounded-lg bg-white/5 border border-white/10">
                <div className="text-[9px] font-medium text-slate-300 uppercase">Architecture</div>
                <div className="text-xs font-bold text-white mt-0.5">LMD / ECTS</div>
              </div>
              <div className="p-2 rounded-lg bg-white/5 border border-white/10">
                <div className="text-[9px] font-medium text-slate-300 uppercase">Multi-Tenant</div>
                <div className="text-xs font-bold text-white mt-0.5">Dédié & Isolé</div>
              </div>
              <div className="p-2 rounded-lg bg-white/5 border border-white/10">
                <div className="text-[9px] font-medium text-slate-300 uppercase">Caisse & Reçus</div>
                <div className="text-xs font-bold text-white mt-0.5">Temps Réel</div>
              </div>
            </div>
          </div>

          {/* 3. Indicateurs de Confiance (Trust Metrics) */}
          <div className="grid grid-cols-3 gap-4 pt-1 border-t border-white/10">
            <div>
              <div className="text-xl xl:text-2xl font-black text-white">100%</div>
              <div className="text-[10px] font-semibold text-slate-300 uppercase tracking-wider mt-0.5">
                Conforme LMD
              </div>
            </div>
            <div>
              <div className="text-xl xl:text-2xl font-black text-white">99.9%</div>
              <div className="text-[10px] font-semibold text-slate-300 uppercase tracking-wider mt-0.5">
                Disponibilité
              </div>
            </div>
            <div>
              <div className="text-xl xl:text-2xl font-black text-white">Multi-Site</div>
              <div className="text-[10px] font-semibold text-slate-300 uppercase tracking-wider mt-0.5">
                Campus & Filières
              </div>
            </div>
          </div>
        </div>

        {/* 4. Footer gauche */}
        <div className="relative z-10 text-[11px] text-slate-400 font-medium flex items-center justify-between">
          <span>© 2026 EduManagePro. Tous droits réservés.</span>
          <span className="font-mono text-[10px] opacity-75">v1.0.0</span>
        </div>
      </div>

      {/* ==================================================================== */}
      {/* COLONNE DROITE : FORMULAIRE DE CONNEXION (SANS SCROLL À 100%) */}
      {/* ==================================================================== */}
      <div className="relative flex flex-col justify-between p-6 sm:p-8 xl:p-10 h-full overflow-y-auto lg:overflow-hidden">
        {/* Barre supérieure : Bascule de Thème (Light / Dark) */}
        <div className="flex items-center justify-between w-full shrink-0">
          {/* Mobile Logo Only */}
          <div className="lg:hidden flex items-center gap-2">
            <img src={logo} alt="EduManagePro" className="h-6 w-6 object-contain" />
            <span className="font-bold text-sm">EduManagePro</span>
          </div>

          <div className="ml-auto">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsDarkMode(!isDarkMode)}
              className="h-7 px-2.5 rounded-lg border-border/60 text-xs gap-1.5 text-muted-foreground hover:text-foreground"
              title="Basculer entre le mode clair et le mode sombre"
            >
              {isDarkMode ? (
                <>
                  <Sun className="h-3 w-3 text-amber-500" />
                  <span className="hidden sm:inline">Mode Clair</span>
                </>
              ) : (
                <>
                  <Moon className="h-3 w-3 text-indigo-500" />
                  <span className="hidden sm:inline">Mode Sombre</span>
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Contenu Central : Formulaire de Connexion dimensionné avec précision */}
        <div className="w-full max-w-sm mx-auto my-auto space-y-5 py-2">
          {/* Titre & Sous-titre */}
          <div className="space-y-1">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              Bienvenue
            </h2>
            <p className="text-xs text-muted-foreground">
              Connectez-vous à votre espace administrateur EduManagePro
            </p>
          </div>

          {/* Formulaire */}
          <form onSubmit={handleLogin} className="space-y-4">
            {/* Champ Email */}
            <div className="space-y-1.5">
              <Label htmlFor="email" className="text-xs font-semibold text-foreground">
                Adresse email
              </Label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                <Input
                  id="email"
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-10 h-10 bg-background/60 border-border/80 text-sm focus-visible:ring-primary rounded-lg transition-all"
                  placeholder="admin@edumanagepro.com"
                />
              </div>
            </div>

            {/* Champ Mot de passe */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <Label htmlFor="password" className="text-xs font-semibold text-foreground">
                  Mot de passe
                </Label>
                <button
                  type="button"
                  onClick={handleForgotPassword}
                  className="text-[11px] font-medium text-primary hover:text-primary/80 transition-colors focus:outline-none"
                >
                  Mot de passe oublié ?
                </button>
              </div>

              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-10 pr-10 h-10 bg-background/60 border-border/80 text-sm focus-visible:ring-primary rounded-lg transition-all"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground focus:outline-none p-1 rounded transition-colors"
                  aria-label={showPassword ? "Masquer le mot de passe" : "Afficher le mot de passe"}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            {/* Bouton de Connexion Principal */}
            <Button
              type="submit"
              disabled={loading}
              className="w-full h-10 text-sm font-semibold rounded-lg bg-primary hover:bg-primary/90 text-primary-foreground shadow-md hover:shadow-primary/20 transition-all flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" /> Connexion en cours...
                </>
              ) : (
                <>Se connecter</>
              )}
            </Button>
          </form>

          {/* Raccourci Compte Administrateur Initial (Format compact) */}
          <div className="p-2.5 rounded-lg border border-border/50 bg-muted/25 text-xs space-y-1">
            <div className="flex items-center justify-between font-semibold text-foreground">
              <span className="flex items-center gap-1.5 text-primary text-[11px]">
                <ShieldCheck className="h-3.5 w-3.5" /> Compte Super-Administrateur
              </span>
              <button
                type="button"
                onClick={() => handleDemoLogin("Admin", "admin@edumanagepro.com")}
                className="text-[11px] text-primary hover:underline font-medium"
              >
                Charger
              </button>
            </div>
            <p className="text-[10px] text-muted-foreground font-mono">
              admin@edumanagepro.com
            </p>
          </div>

          {/* Liens Secondaires */}
          <div className="text-center space-y-1.5 text-xs text-muted-foreground">
            <div>
              Besoin d'aide ?{" "}
              <button
                type="button"
                onClick={handleSupport}
                className="font-semibold text-primary hover:underline"
              >
                Support technique
              </button>
            </div>

            <div>
              <Link
                to="/setup"
                className="text-[11px] text-muted-foreground/80 hover:text-foreground inline-flex items-center gap-1 hover:underline"
              >
                <Wrench className="h-3 w-3" /> Reconfigurer l'instance (Setup Wizard)
              </Link>
            </div>
          </div>
        </div>

        {/* Pied de page colonne droite */}
        <div className="text-center text-[10px] text-muted-foreground/60 py-1 shrink-0">
          Connexion sécurisée TLS 1.3 · Chiffrement des jetons JWT HS256
        </div>
      </div>
    </div>
  );
};

export default Login;
