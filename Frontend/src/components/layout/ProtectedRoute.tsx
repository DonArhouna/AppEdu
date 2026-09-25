import React, { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { useRBAC, type UserRole, AVAILABLE_ROLES } from "@/contexts/RBACContext";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PageLoader } from "@/components/ui/page-loader";
import { ArrowLeft, Lock } from "lucide-react";

interface ProtectedRouteProps {
  allowedRoles?: UserRole[];
  /** Permission dynamique requise, en plus du contrôle de rôle historique. */
  requiredPermission?: string;
  /** Désactive le bypass global de l'administrateur pour les portails personnels. */
  allowSuperuser?: boolean;
  children: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  allowedRoles,
  requiredPermission,
  allowSuperuser = true,
  children,
}) => {
  const { user, isLoading } = useAuth();
  const { currentRole, currentRoleInfo, hasAccess, hasPermission } = useRBAC();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isLoading && !user) {
      navigate("/login", { replace: true });
    }
  }, [isLoading, navigate, user]);

  if (isLoading || !user) {
    return <PageLoader />;
  }

  const roleAllowed = allowSuperuser
    ? (!allowedRoles || allowedRoles.length === 0 || hasAccess(allowedRoles))
    : Boolean(allowedRoles?.includes(currentRole));
  const permissionAllowed = !requiredPermission || hasPermission(requiredPermission);
  const canAccess = roleAllowed && permissionAllowed;

  if (canAccess) {
    return <>{children}</>;
  }

  const allowedRoleInfos = AVAILABLE_ROLES.filter((role) =>
    allowedRoles?.includes(role.id)
  );

  return (
    <div className="min-h-[70vh] flex items-center justify-center p-4">
      <Card className="max-w-md w-full border-destructive/30 shadow-lg bg-card">
        <CardContent className="pt-8 pb-6 px-6 text-center space-y-4">
          <div className="mx-auto w-14 h-14 rounded-full bg-destructive/10 text-destructive flex items-center justify-center border border-destructive/20">
            <Lock className="h-7 w-7" />
          </div>

          <div className="space-y-2">
            <h2 className="text-xl font-bold text-foreground">Accès réservé / Non autorisé</h2>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Votre profil (
              <strong className="text-foreground">{currentRoleInfo.label}</strong>) ne dispose pas
              des privilèges nécessaires pour accéder à cette ressource.
              {requiredPermission && (
                <span className="mt-1 block text-xs">Permission requise : {requiredPermission}</span>
              )}
            </p>
          </div>

          <div className="p-3 bg-muted/50 rounded-lg border text-xs space-y-2 text-left">
            <p className="font-semibold text-muted-foreground uppercase text-[10px] tracking-wider">
              Profils autorisés pour ce module
            </p>
            <div className="flex flex-wrap gap-1.5">
              {allowedRoleInfos.map((role) => (
                <Badge key={role.id} variant="secondary" className="text-[11px] font-medium">
                  {role.label}
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
