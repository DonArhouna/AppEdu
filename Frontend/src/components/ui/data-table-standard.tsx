import * as React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight, Inbox } from "lucide-react";
import { cn } from "@/lib/utils";

interface DataTableStandardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  headerSlot?: React.ReactNode;
  footerSlot?: React.ReactNode;
  totalItems?: number;
  currentPage?: number;
  totalPages?: number;
  onPageChange?: (page: number) => void;
  isEmpty?: boolean;
  emptyMessage?: string;
  emptyDescription?: string;
}

export const DataTableStandard = React.forwardRef<HTMLDivElement, DataTableStandardProps>(
  (
    {
      children,
      headerSlot,
      footerSlot,
      totalItems,
      currentPage = 1,
      totalPages = 1,
      onPageChange,
      isEmpty = false,
      emptyMessage = "Aucun enregistrement trouvé",
      emptyDescription = "Essayez d'ajuster vos critères de recherche ou vos filtres.",
      className,
      ...props
    },
    ref
  ) => {
    return (
      <Card ref={ref} className={cn("card-base overflow-hidden", className)} {...props}>
        {/* Optional top filter/search slot */}
        {headerSlot && (
          <div className="p-4 border-b border-border/60 bg-muted/20 flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
            {headerSlot}
          </div>
        )}

        {/* Table content */}
        <CardContent className="p-0">
          {isEmpty ? (
            <div className="py-12 px-4 text-center">
              <div className="h-12 w-12 rounded-2xl bg-muted/50 flex items-center justify-center mx-auto mb-3 text-muted-foreground">
                <Inbox className="h-6 w-6" />
              </div>
              <h3 className="text-sm font-semibold text-foreground">{emptyMessage}</h3>
              <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
                {emptyDescription}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto scrollbar-thin">{children}</div>
          )}
        </CardContent>

        {/* Standardized pagination footer */}
        {(footerSlot || (onPageChange && totalPages > 1) || totalItems !== undefined) && (
          <div className="px-4 py-3 border-t border-border/60 bg-muted/10 flex flex-col sm:flex-row gap-2 items-center justify-between text-xs text-muted-foreground">
            {footerSlot ? (
              footerSlot
            ) : (
              <>
                <div>
                  {totalItems !== undefined ? (
                    <span>
                      Total : <strong className="text-foreground">{totalItems}</strong> éléments
                    </span>
                  ) : (
                    <span>Page {currentPage} sur {totalPages}</span>
                  )}
                </div>

                {onPageChange && totalPages > 1 && (
                  <div className="flex items-center gap-1">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onPageChange(Math.max(1, currentPage - 1))}
                      disabled={currentPage <= 1}
                      className="h-7 px-2 text-xs rounded-lg"
                    >
                      <ChevronLeft className="h-3.5 w-3.5 mr-1" /> Précédent
                    </Button>
                    <span className="px-2 font-medium">
                      {currentPage} / {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
                      disabled={currentPage >= totalPages}
                      className="h-7 px-2 text-xs rounded-lg"
                    >
                      Suivant <ChevronRight className="h-3.5 w-3.5 ml-1" />
                    </Button>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </Card>
    );
  }
);

DataTableStandard.displayName = "DataTableStandard";
