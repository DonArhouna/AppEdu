import { useOfflineStatus } from "@/hooks/useOfflineStatus";
import { WifiOff, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

export const OfflineBanner = () => {
  const { isOffline } = useOfflineStatus();

  if (!isOffline) return null;

  return (
    <div className="bg-amber-600 text-white px-4 py-2 text-xs font-medium flex items-center justify-between shadow-md transition-all animate-in slide-in-from-top duration-300">
      <div className="flex items-center gap-2">
        <WifiOff className="h-4 w-4 animate-pulse shrink-0" />
        <span>
          <strong>Mode Hors-Ligne Actif</strong> — Vos modifications (saisie de notes, absences) sont enregistrées localement et seront synchronisées dès le rétablissement de la connexion.
        </span>
      </div>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => window.location.reload()}
        className="text-white hover:bg-amber-700 h-6 px-2 text-[11px] shrink-0"
      >
        <RefreshCw className="h-3 w-3 mr-1" /> Reconnecter
      </Button>
    </div>
  );
};
