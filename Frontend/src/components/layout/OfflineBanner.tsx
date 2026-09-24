import { useOfflineStatus } from "@/hooks/useOfflineStatus";
import { WifiOff, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

export const OfflineBanner = () => {
  const { isOffline } = useOfflineStatus();

  if (!isOffline) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-center justify-between gap-3 bg-amber-600 px-4 py-2 text-xs font-medium text-white shadow-md transition-all"
    >
      <div className="flex items-center gap-2">
        <WifiOff className="h-4 w-4 shrink-0" />
        <span>
          <strong>Mode hors ligne actif.</strong>{" "}
          Les données et les modifications nécessitent une connexion au serveur. Aucune saisie locale n'est conservée.
        </span>
      </div>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={() => window.location.reload()}
        className="h-6 shrink-0 px-2 text-[11px] text-white hover:bg-amber-700"
      >
        <RefreshCw className="mr-1 h-3 w-3" /> Réessayer
      </Button>
    </div>
  );
};
