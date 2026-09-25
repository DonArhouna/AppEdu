import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowUpRight, ArrowDownRight, Minus, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export interface KpiCardProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  value: string | number;
  icon: LucideIcon;
  subtitle?: string;
  trend?: string;
  trendDirection?: "up" | "down" | "neutral";
  trendLabel?: string;
  colorVariant?: "primary" | "emerald" | "amber" | "purple" | "rose" | "sky" | "indigo";
}

const colorVariantStyles = {
  primary: {
    borderBar: "bg-primary",
    iconBg: "bg-primary/10 text-primary",
  },
  emerald: {
    borderBar: "bg-emerald-500",
    iconBg: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  },
  amber: {
    borderBar: "bg-amber-500",
    iconBg: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  },
  purple: {
    borderBar: "bg-purple-500",
    iconBg: "bg-purple-500/10 text-purple-600 dark:text-purple-400",
  },
  rose: {
    borderBar: "bg-rose-500",
    iconBg: "bg-rose-500/10 text-rose-600 dark:text-rose-400",
  },
  sky: {
    borderBar: "bg-sky-500",
    iconBg: "bg-sky-500/10 text-sky-600 dark:text-sky-400",
  },
  indigo: {
    borderBar: "bg-indigo-500",
    iconBg: "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400",
  },
};

export const KpiCard = React.forwardRef<HTMLDivElement, KpiCardProps>(
  (
    {
      title,
      value,
      icon: Icon,
      subtitle,
      trend,
      trendDirection = "up",
      trendLabel = "vs période précédente",
      colorVariant = "primary",
      className,
      ...props
    },
    ref
  ) => {
    const styles = colorVariantStyles[colorVariant] || colorVariantStyles.primary;

    const renderTrendIcon = () => {
      if (trendDirection === "up") {
        return <ArrowUpRight className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />;
      }
      if (trendDirection === "down") {
        return <ArrowDownRight className="h-3.5 w-3.5 text-rose-600 dark:text-rose-400 shrink-0" />;
      }
      return <Minus className="h-3.5 w-3.5 text-muted-foreground shrink-0" />;
    };

    const getTrendTextColor = () => {
      if (trendDirection === "up") return "text-emerald-600 dark:text-emerald-400";
      if (trendDirection === "down") return "text-rose-600 dark:text-rose-400";
      return "text-muted-foreground";
    };

    return (
      <Card
        ref={ref}
        className={cn(
          "card-base relative overflow-hidden transition-all duration-200 hover:shadow-md",
          className
        )}
        {...props}
      >
        {/* Accent bar on left */}
        <div className={cn("absolute left-0 top-0 bottom-0 w-1", styles.borderBar)} />

        <CardHeader className="flex min-w-0 flex-row items-center justify-between pb-2 pl-5 pr-4 pt-4">
          <CardTitle className="min-w-0 truncate text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            {title}
          </CardTitle>
          <div className={cn("rounded-xl p-2 shrink-0 transition-transform group-hover:scale-105", styles.iconBg)}>
            <Icon className="h-4 w-4" />
          </div>
        </CardHeader>

        <CardContent className="pl-5 pr-4 pb-4.5 pt-0">
          <div className="break-words text-2xl font-bold tracking-tight text-foreground">{value}</div>

          {subtitle && (
            <p className="text-xs text-muted-foreground mt-0.5 truncate">{subtitle}</p>
          )}

          {trend && (
            <p className="text-xs mt-1.5 flex items-center gap-1 font-medium leading-none">
              {renderTrendIcon()}
              <span className={cn("font-semibold", getTrendTextColor())}>{trend}</span>
              <span className="text-muted-foreground font-normal truncate">{trendLabel}</span>
            </p>
          )}
        </CardContent>
      </Card>
    );
  }
);

KpiCard.displayName = "KpiCard";
