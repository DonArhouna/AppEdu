import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  BookOpenCheck,
  Database,
  Eye,
  EyeOff,
  Loader2,
  LockKeyhole,
  Mail,
  Moon,
  ShieldCheck,
  Sun,
  WalletCards,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { setupApi } from "@/services/apiClient";
import { useAuth } from "@/contexts/AuthContext";
import logo from "@/assets/logo.svg";

const features = [
  {
    icon: Database,
    title: "Scolarité centralisée",
    description: "Dossiers, inscriptions et parcours réunis dans un espace cohérent.",
  },
  {
    icon: ShieldCheck,
    title: "Accès maîtrisé",
    description: "Les habilitations sont contrôlées côté serveur pour chaque module.",
  },
  {
    icon: BookOpenCheck,
    title: "Pilotage pédagogique",
    description: "Structure académique, notes et délibérations au même endroit.",
  },
  {
    icon: WalletCards,
    title: "Finances structurées",
    description: "Facturation, encaissements et justificatifs reliés aux dossiers.",
  },
];

const Login = () => {
  const navigate = useNavigate();
  const { login, user, isLoading: authLoading } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [serverAvailable, setServerAvailable] = useState<boolean | null>(null);
  const [isLightMode, setIsLightMode] = useState(() => {
    const storedTheme = localStorage.getItem("theme");
    return storedTheme
      ? storedTheme === "light"
      : !window.matchMedia("(prefers-color-scheme: dark)").matches;
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", !isLightMode);
    localStorage.setItem("theme", isLightMode ? "light" : "dark");
  }, [isLightMode]);

  useEffect(() => {
    if (!authLoading && user) {
      navigate("/", { replace: true });
    }
  }, [authLoading, navigate, user]);

  useEffect(() => {
    let active = true;
    const checkStatus = async () => {
      const result = await setupApi.getStatus();
      if (!active) return;
      if (result.error) {
        setServerAvailable(false);
        return;
      }
      setServerAvailable(true);
      if (result.data && !result.data.is_configured) {
        toast.info("Première installation détectée. Ouverture de l'assistant...");
        navigate("/setup", { replace: true });
      }
    };
    void checkStatus();
    return () => {
      active = false;
    };
  }, [navigate]);

  const handleLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedEmail = email.trim().toLowerCase();
    if (!normalizedEmail || !password) {
      toast.warning("Renseignez votre email et votre mot de passe.");
      return;
    }

    setSubmitting(true);
    const result = await login(normalizedEmail, password);
    setSubmitting(false);

    if (result.error) {
      toast.error(result.error);
      return;
    }
    if (result.data?.user) {
      toast.success(`Bienvenue, ${result.data.user.prenom || result.data.user.nom}.`);
      navigate("/", { replace: true });
    }
  };

  const renderThemeButton = () => (
    <Button
      type="button"
      variant="outline"
      size="icon"
      onClick={() => setIsLightMode((value) => !value)}
      aria-label={isLightMode ? "Activer le mode sombre" : "Activer le mode clair"}
      title={isLightMode ? "Mode sombre" : "Mode clair"}
      className="border-slate-200 bg-white/80 text-slate-700 hover:bg-white dark:border-white/15 dark:bg-white/10 dark:text-slate-200 dark:hover:bg-white/15"
    >
      {isLightMode ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
    </Button>
  );

  return (
    <div className="h-[100dvh] w-full overflow-hidden bg-slate-100 text-slate-900 transition-colors dark:bg-[#07111f] dark:text-slate-100">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_18%_18%,rgba(14,165,233,0.14),transparent_30%),radial-gradient(circle_at_84%_80%,rgba(37,99,235,0.12),transparent_34%)] dark:bg-[radial-gradient(circle_at_18%_18%,rgba(14,165,233,0.20),transparent_30%),radial-gradient(circle_at_84%_80%,rgba(37,99,235,0.18),transparent_34%)]" />
      <div className="pointer-events-none absolute inset-0 opacity-[0.35] [background-image:linear-gradient(rgba(100,116,139,0.10)_1px,transparent_1px),linear-gradient(90deg,rgba(100,116,139,0.10)_1px,transparent_1px)] [background-size:48px_48px] dark:opacity-[0.16] dark:[background-image:linear-gradient(rgba(148,163,184,0.12)_1px,transparent_1px),linear-gradient(90deg,rgba(148,163,184,0.12)_1px,transparent_1px)]" />

      <div className="relative mx-auto grid h-full w-full max-w-[1600px] grid-cols-1 lg:grid-cols-[minmax(0,1.08fr)_minmax(420px,0.92fr)]">
        <section className="relative hidden min-h-0 flex-col justify-between px-8 py-6 sm:px-12 lg:flex xl:px-20">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-white/15 dark:bg-white/10 dark:shadow-lg dark:shadow-sky-950/30">
                <img src={logo} alt="EduManagePro" className="h-6 w-6 object-contain" />
              </div>
              <div>
                <p className="font-semibold tracking-tight text-slate-900 dark:text-white">EduManagePro</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">Gestion scolaire et universitaire</p>
              </div>
            </div>
            {renderThemeButton()}
          </div>

          <div className="max-w-3xl py-3">
            <h1 className="text-4xl font-semibold leading-[1.06] tracking-tight text-slate-950 dark:text-white xl:text-5xl 2xl:text-6xl">
              Le pilotage de votre établissement, sans rupture.
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-600 dark:text-slate-300 xl:text-[0.95rem]">
              Un espace unique pour la scolarité, l'académique et les finances, avec des règles d'accès explicites et des données persistées dans votre instance.
            </p>

            <div className="mt-4 grid max-w-3xl gap-2.5 sm:grid-cols-2">
              {features.map((feature) => {
                const Icon = feature.icon;
                return (
                  <div key={feature.title} className="rounded-2xl border border-slate-200 bg-white/80 p-3.5 shadow-sm backdrop-blur-sm dark:border-white/10 dark:bg-white/[0.045]">
                    <div className="mb-2 flex h-8 w-8 items-center justify-center rounded-xl bg-sky-700/10 text-sky-700 dark:bg-sky-400/10 dark:text-sky-300">
                      <Icon className="h-4 w-4" />
                    </div>
                    <p className="text-sm font-semibold leading-snug text-slate-900 dark:text-white">{feature.title}</p>
                    <p className="mt-0.5 text-xs leading-snug text-slate-500 dark:text-slate-400">{feature.description}</p>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-500">
            <span>EduManagePro · v1.0.0</span>
            <span className="inline-flex items-center gap-1.5"><ShieldCheck className="h-3.5 w-3.5" />Données persistées dans votre instance</span>
          </div>
        </section>

        <section className="relative flex min-h-0 items-center justify-center px-5 py-5 sm:px-10 lg:px-12">
          <div className="flex w-full max-w-[420px] flex-col justify-center">
            <div className="mb-5 flex items-center justify-between gap-3 lg:hidden">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white shadow-sm dark:border-white/15 dark:bg-white/10">
                  <img src={logo} alt="EduManagePro" className="h-6 w-6 object-contain" />
                </div>
                <div>
                  <p className="font-semibold tracking-tight text-slate-900 dark:text-white">EduManagePro</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Gestion scolaire et universitaire</p>
                </div>
              </div>
              {renderThemeButton()}
            </div>

            <div className="rounded-[28px] border border-slate-200 bg-white/90 p-5 shadow-2xl shadow-slate-300/30 backdrop-blur-xl dark:border-white/10 dark:bg-white/[0.06] dark:shadow-slate-950/40 sm:p-8">
              <div className="mb-6">
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-sky-700/10 text-sky-700 dark:bg-sky-400/10 dark:text-sky-300">
                  <LockKeyhole className="h-5 w-5" />
                </div>
                <h2 className="text-2xl font-semibold tracking-tight text-slate-950 dark:text-white">Connexion</h2>
                <p className="mt-1.5 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                  Utilisez les identifiants définis pour votre établissement.
                </p>
              </div>

              <form onSubmit={handleLogin} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email" className="text-slate-700 dark:text-slate-200">Adresse email</Label>
                  <div className="relative">
                    <Mail className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400 dark:text-slate-500" />
                    <Input
                      id="email"
                      type="email"
                      autoComplete="email"
                      required
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                      placeholder="vous@votre-institution.org"
                      className="h-11 border-slate-200 bg-white pl-10 text-slate-900 placeholder:text-slate-400 focus-visible:border-sky-600 focus-visible:ring-sky-500/30 dark:border-white/10 dark:bg-white/[0.06] dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus-visible:border-sky-400 dark:focus-visible:ring-sky-400/30"
                      disabled={submitting}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password" className="text-slate-700 dark:text-slate-200">Mot de passe</Label>
                  <div className="relative">
                    <LockKeyhole className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400 dark:text-slate-500" />
                    <Input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      autoComplete="current-password"
                      required
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      className="h-11 border-slate-200 bg-white pl-10 pr-11 text-slate-900 placeholder:text-slate-400 focus-visible:border-sky-600 focus-visible:ring-sky-500/30 dark:border-white/10 dark:bg-white/[0.06] dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus-visible:border-sky-400 dark:focus-visible:ring-sky-400/30"
                      disabled={submitting}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((value) => !value)}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500/40 dark:text-slate-400 dark:hover:bg-white/10 dark:hover:text-white dark:focus:ring-sky-400/50"
                      aria-label={showPassword ? "Masquer le mot de passe" : "Afficher le mot de passe"}
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                <div aria-live="polite">
                  {serverAvailable === false && (
                    <div className="rounded-xl border border-rose-700/20 bg-rose-700/5 px-3 py-2.5 text-xs leading-relaxed text-rose-800 dark:border-rose-400/25 dark:bg-rose-400/10 dark:text-rose-200">
                      Le backend est inaccessible. Vérifiez PostgreSQL et le serveur FastAPI avant de réessayer.
                    </div>
                  )}
                </div>

                <Button
                  type="submit"
                  className="h-11 w-full bg-sky-700 font-semibold text-white hover:bg-sky-800 focus-visible:ring-sky-500/40 dark:bg-sky-500 dark:text-slate-950 dark:hover:bg-sky-400 dark:focus-visible:ring-sky-400/50"
                  disabled={submitting || serverAvailable === false}
                >
                  {submitting ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Connexion en cours...
                    </>
                  ) : (
                    "Se connecter"
                  )}
                </Button>
              </form>
            </div>

            <p className="mt-4 text-center text-xs leading-relaxed text-slate-500 dark:text-slate-500">
              Aucun identifiant de démonstration n'est prérempli.
            </p>

            <div className="mt-4 flex items-center justify-center gap-4 text-xs text-slate-500 dark:text-slate-400">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-sky-700/20 bg-sky-700/5 px-3 py-1.5 font-medium text-sky-800 dark:border-sky-400/25 dark:bg-sky-400/10 dark:text-sky-200">
                <LockKeyhole className="h-3.5 w-3.5" />
                Espace sécurisé
              </span>
              <span className="hidden sm:inline">·</span>
              <span className="hidden sm:inline">Connexion JWT</span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default Login;
