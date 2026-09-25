/**
 * Identité institutionnelle en lecture seule, pour l'écran Documents.
 *
 * Le secrétariat émet les documents, mais n'a pas la permission de modifier
 * la configuration : l'écran de paramétrage lui est fermé. Il doit
 * néanmoins **voir** l'identité qui va figurer sur le document qu'il
 * prépare — sinon il émet à l'aveugle.
 *
 * Cette bande est donc en lecture seule, sans lien d'edition trompeur : seul
 * un compte disposant de la permission voit un renvoi vers le parametrage.
 */

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Building2, Settings } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useRBAC } from "@/contexts/RBACContext";
import { extractErrorMessage, institutionApi, PERMISSION_INSTITUTION_SETTINGS } from "@/services/apiClient";
import type { InstitutionConfig } from "@/services/apiTypes";

const IdentiteDocument = () => {
  const { hasPermission } = useRBAC();
  const canEdit = hasPermission(PERMISSION_INSTITUTION_SETTINGS);
  const [config, setConfig] = useState<InstitutionConfig | null>(null);
  const [chargement, setChargement] = useState(true);

  useEffect(() => {
    let annule = false;
    void institutionApi.getConfig().then((resultat) => {
      if (annule) return;
      if (resultat.data) setConfig(resultat.data);
      setChargement(false);
    });
    return () => {
      annule = true;
    };
  }, []);

  if (chargement) {
    return <Skeleton className="h-14 w-full" />;
  }

  // Une configuration illisible ne doit pas bloquer l'emission : on le signale
  // dans la ligne plutot que d'afficher un bandeau d'erreur qui ferait croire
  // que le module Documents est hors service.
  if (!config) {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-dashed px-4 py-3 text-sm text-muted-foreground">
        <Building2 className="h-4 w-4 shrink-0" />
        Identité de l'établissement indisponible : les documents seront émis
        sans en-tête d'établissement.
      </div>
    );
  }

  const coordonnees = [config.adresse, config.telephone, config.email].filter(Boolean);

  return (
    <div className="flex flex-col gap-3 rounded-lg border bg-muted/30 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <Building2 className="h-4 w-4 shrink-0 text-muted-foreground" />
          <span className="truncate font-medium">{config.nom}</span>
          {config.sigle && <span className="text-sm text-muted-foreground">({config.sigle})</span>}
          <Badge variant="secondary">Version {config.version}</Badge>
          {!config.logo_present && (
            <Badge variant="outline">Sans logo</Badge>
          )}
        </div>
        {coordonnees.length > 0 && (
          <p className="mt-1 truncate text-sm text-muted-foreground">
            {coordonnees.join(" · ")}
          </p>
        )}
      </div>

      {canEdit && (
        <Button asChild variant="outline" size="sm" className="shrink-0 self-start sm:self-auto">
          <Link to="/parametrage">
            <Settings className="mr-2 h-4 w-4" />
            Modifier l'identité
          </Link>
        </Button>
      )}
    </div>
  );
};

export default IdentiteDocument;
