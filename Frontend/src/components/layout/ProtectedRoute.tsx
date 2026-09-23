import React from "react";
import { Link } from "react-router-dom";
import { useRBAC, type UserRole, AVAILABLE_ROLES } from "@/contexts/RBACContext";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ShieldAlert, ArrowLeft, Lock } from "lucide-react";

interface ProtectedRouteProps {
  allowedRoles?: UserRole[];
  children: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ allowedRoles, children }) => {
  const { currentRole, currentRoleInfo, hasAccess } = useRBAC();

  if (!allowedRoles || allowedRoles.length === 0 || hasAccess(allowedRoles)) {
    return <>{children}</>;
  }

  const allowedRoleInfos = AVAILABLE_ROLES.filter((r) => allowedRoles.includes(r.id));

  return (
    <div className="min-h-[70vh] flex items-center justify-center p-4">
      <Card className="max-w-md w-full border-destructive/30 shadow-lg bg-card">
        <CardContent className="pt-8 pb-6 px-6 text-center space-y-4">
          <div className="mx-auto w-14 h-14 rounded-full bg-destructive/10 text-destructive flex items-center justify-center border border-destructive/20">
            <Lock className="h-7 w-7" />
          </div>

          <div className="space-y-2">
            <h2 className="text-xl font-bold text-foreground">Accès Réservé / Non Autorisé</h2>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Votre profil actuel (<strong className="text-foreground">{currentRoleInfo.label}</strong>) ne dispose pas des privilèges nécessaires pour accéder à cette ressource.
            </p>
          </div>

          <div className="p-3 bg-muted/50 rounded-lg border text-xs space-y-2 text-left">
            <p className="font-semibold text-muted-foreground uppercase text-[10px] tracking-wider">
              Profils autorisés pour ce module :
            </p>
            <div className="flex flex-wrap gap-1.5">
              {allowedRoleInfos.map((r) => (
                <Badge key={r.id} variant="secondary" className="text-[11px] font-medium">
                  {r.label}
                </Badge>
              ))}
            </div>
          </div>

          <div className="pt-2 flex flex-col sm:flex-row gap-2 justify-center">
            <Button asChild variant="outline" size="sm">
              <Link to="/">
                <ArrowLeft className="h-4 w-4 mr-1.5" />
                Retour au Tableau de Bord
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
