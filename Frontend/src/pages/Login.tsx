import { useEffect, useState } from "react";
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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { setupApi } from "@/services/apiClient";
import { useAuth } from "@/contexts/AuthContext";
import logo from "@/assets/logo.svg";

const features = [
  {
    icon: Database,
    title: "Données centralisées",
    description: "Scolarité, académique et finances dans une API commune.",
  },
  {
    icon: ShieldCheck,
    title: "Accès contrôlé",
    description: "Session authentifiée et permissions adaptées aux rôles.",
  },
  {
    icon: BookOpenCheck,
    title: "Pédagogie complète",
    description: "Structure, notes et délibérations pilotées par l'API.",
  },
  {
    icon: WalletCards,
    title: "Finance fiable",
    description: "Facturation, encaissements et reçusstructurés.",
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
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const storedTheme = localStorage.getItem("theme");
    return storedTheme
      ? storedTheme === "dark"
      : window.matchMedia("(prefers-color-scheme: dark)").matches;
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", isDarkMode);
    localStorage.setItem("theme", isDarkMode ? "dark" : "light");
  }, [isDarkMode]);

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

  const handleLogin = async (event: React.FormEvent) => {
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

  return (
    <div className="relative min-h-screen overflow-hidden bg-background text-foreground">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,hsl(var(--primary)/0.12),transparent_38%),radial-gradient(circle_at_bottom_right,hsl(var(--primary)/0.08),transparent_34%)]" />

      <header className="relative z-10 mx-auto flex w-full max-w-7xl items-center justify-between px-5 py-6 sm:px-8 lg:px-10">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-border bg-card shadow-sm">
            <img src={logo} alt="EduManagePro" className="h-7 w-7 object-contain" />
          </div>
          <div>
            <p className="font-semibold tracking-tight">EduManagePro</p>
            <p className="text-xs text-muted-foreground">Gestion scolaire et universitaire</p>
          </div>
        </div>

        <Button
          type="button"
          variant="outline"
          size="icon"
          onClick={() => setIsDarkMode((value) => !value)}
          aria-label={isDarkMode ? "Activer le mode clair" : "Activer le mode sombre"}
          title={isDarkMode ? "Mode clair" : "Mode sombre"}
        >
          {isDarkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
      </header>

      <main className="relative z-10 mx-auto grid w-full max-w-7xl flex-1 items-center gap-12 px-5 pb-12 pt-4 sm:px-8 lg:grid-cols-[1.05fr_minmax(360px,0.75fr)] lg:px-10 lg:pb-20">
        <section className="hidden lg:block">
          <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1.5 text-xs font-medium text-primary">
            <LockKeyhole className="h-3.5 w-3.5" />
            Espace sécurisé
          </div>
          <h1 className="max-w-2xl text-4xl font-bold leading-tight tracking-tight xl:text-5xl">
            Pilotez votre établissement depuis un espace unique.
          </h1>
          <p className="mt-5 max-w-xl text-base leading-relaxed text-muted-foreground">
            Connectez-vous avec les identifiants définis lors de l'installation. Aucun compte de
            démonstration n'est prérempli.
          </p>

          <div className="mt-10 grid max-w-2xl gap-3 sm:grid-cols-2">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <div
                  key={feature.title}
                  className="rounded-2xl border border-border/80 bg-card/75 p-4 shadow-sm backdrop-blur"
                >
                  <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
                    <Icon className="h-4 w-4" />
                  </div>
                  <p className="text-sm font-semibold">{feature.title}</p>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                    {feature.description}
                  </p>
                </div>
              );
            })}
          </div>
        </section>

        <Card className="mx-auto w-full max-w-md border-border/80 bg-card/95 shadow-xl shadow-primary/5 backdrop-blur lg:mx-0 lg:ml-auto">
          <CardHeader className="space-y-3 pb-5">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <LockKeyhole className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-2xl tracking-tight">Connexion</CardTitle>
              <CardDescription className="mt-1.5">
                Accédez à votre espace avec les identifiants créés lors du setup.
              </CardDescription>
            </div>
          </CardHeader>

          <CardContent>
            <form onSubmit={handleLogin} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="email">Adresse email</Label>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="vous@votre-institution.org"
                    className="h-11 pl-10"
                    disabled={submitting}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Mot de passe</Label>
                <div className="relative">
                  <LockKeyhole className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    required
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    className="h-11 pl-10 pr-11"
                    disabled={submitting}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((value) => !value)}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                    aria-label={showPassword ? "Masquer le mot de passe" : "Afficher le mot de passe"}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {serverAvailable === false && (
                <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-3 py-2.5 text-xs text-destructive">
                  Le backend est inaccessible. Vérifiez PostgreSQL et le serveur FastAPI avant de réessayer.
                </div>
              )}

              <Button type="submit" className="h-11 w-full gap-2" disabled={submitting || serverAvailable === false}>
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
          </CardContent>
        </Card>
      </main>

      <footer className="relative z-10 px-5 pb-6 text-center text-xs text-muted-foreground">
        EduManagePro · v1.0.0
      </footer>
    </div>
  );
};

export default Login;
