import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  erreur: Error | null;
}

/**
 * Barriere d'erreur applicative.
 *
 * Sans elle, une exception de rendu laisse un ecran blanc et l'utilisateur
 * doit recharger manuellement. Ici, le message est explicite et la reprise
 * possible, sans masquer la cause en production : le detail technique reste
 * dans la console du navigateur.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { erreur: null };

  static getDerivedStateFromError(erreur: Error): ErrorBoundaryState {
    return { erreur };
  }

  componentDidCatch(erreur: Error, infos: ErrorInfo): void {
    console.error("Erreur de rendu interceptée :", erreur, infos.componentStack);
  }

  private reinitialiser = () => {
    this.setState({ erreur: null });
  };

  render(): ReactNode {
    const { erreur } = this.state;
    if (!erreur) return this.props.children;

    return (
      <div className="flex min-h-[70vh] items-center justify-center p-4">
        <div className="w-full max-w-lg rounded-2xl border border-destructive/30 bg-card p-6 shadow-lg">
          <div className="mb-4 flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-destructive/10 text-destructive">
              <AlertTriangle className="h-5 w-5" />
            </span>
            <div>
              <h2 className="text-lg font-semibold text-foreground">
                Un module n'a pas pu s'afficher
              </h2>
              <p className="text-sm text-muted-foreground">
                Le reste de l'application reste utilisable.
              </p>
            </div>
          </div>
          <p className="mb-4 rounded-lg bg-muted/50 p-3 font-mono text-xs text-muted-foreground">
            {erreur.message}
          </p>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="inline-flex items-center rounded-lg border border-input px-3 py-2 text-sm font-medium hover:bg-accent"
            >
              Recharger la page
            </button>
            <button
              type="button"
              onClick={this.reinitialiser}
              className="inline-flex items-center rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Réessayer
            </button>
          </div>
        </div>
      </div>
    );
  }
}

export default ErrorBoundary;
