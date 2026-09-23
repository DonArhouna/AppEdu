import { Loader2 } from "lucide-react";

export const PageLoader = () => {
  return (
    <div className="h-[60vh] w-full flex flex-col items-center justify-center gap-3">
      <div className="relative flex items-center justify-center">
        <div className="h-12 w-12 rounded-full border-4 border-primary/20 border-t-primary animate-spin" />
        <Loader2 className="h-6 w-6 text-primary absolute animate-pulse" />
      </div>
      <p className="text-xs font-medium text-muted-foreground tracking-wide animate-pulse">
        Chargement des données EduManagePro...
      </p>
    </div>
  );
};
