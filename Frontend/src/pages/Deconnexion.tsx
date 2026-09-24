import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { LogOut, Loader2, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";

const Deconnexion = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();

  useEffect(() => {
    logout();
    toast.info("Déconnexion en cours...");
    const timer = setTimeout(() => {
      toast.success("Vous avez été déconnecté avec succès.");
      navigate("/login");
    }, 1500);

    return () => clearTimeout(timer);
  }, [logout, navigate]);

  return (
    <div className="min-h-[70vh] flex items-center justify-center p-4">
      <Card className="w-full max-w-md shadow-xl text-center border-primary/20">
        <CardContent className="p-8 space-y-6">
          <div className="mx-auto h-16 w-16 rounded-full bg-destructive/10 text-destructive flex items-center justify-center animate-pulse">
            <LogOut className="h-8 w-8" />
          </div>

          <div className="space-y-2">
            <h2 className="text-2xl font-bold text-foreground">Déconnexion d'EduManagePro</h2>
            <p className="text-sm text-muted-foreground">
              Fermeture sécurisée de votre session en cours...
            </p>
          </div>

          <div className="flex items-center justify-center gap-2 text-primary font-medium text-xs">
            <Loader2 className="h-4 w-4 animate-spin" /> Redirection vers la page de connexion...
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Deconnexion;
