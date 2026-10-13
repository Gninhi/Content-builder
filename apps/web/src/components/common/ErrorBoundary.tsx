import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertCircle, RefreshCw, LayoutDashboard } from 'lucide-react';
import { Button } from './Button';

interface ErrorBoundaryProps {
  children: ReactNode;
  level?: 'page' | 'root';
  onNavigate?: (screen: string) => void;
  fallbackTitle?: string;
  fallbackMessage?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  correlationId: string;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  public state: ErrorBoundaryState = {
    hasError: false,
    error: null,
    correlationId: '',
  };

  public static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    const correlationId = 'err_' + Math.random().toString(36).substring(2, 10);
    return { hasError: true, error, correlationId };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log sanitized error trace for diagnostics
    console.error('[ContentOps ErrorBoundary]', {
      name: error.name,
      message: error.message,
      componentStack: errorInfo.componentStack,
      correlationId: this.state.correlationId,
    });
  }

  private handleRetry = () => {
    this.setState({ hasError: false, error: null, correlationId: '' });
  };

  private handleGoHome = () => {
    this.setState({ hasError: false, error: null, correlationId: '' });
    if (this.props.onNavigate) {
      this.props.onNavigate('dashboard');
    } else {
      window.location.hash = 'dashboard';
    }
  };

  private handleReloadApp = () => {
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      const isRoot = this.props.level === 'root';

      if (isRoot) {
        return (
          <div className="flex min-h-screen items-center justify-center bg-app text-txt-primary p-6">
            <div className="max-w-md w-full bg-surface border border-border-default rounded-2xl p-6 sm:p-8 shadow-elevated text-center space-y-5">
              <div className="w-14 h-14 rounded-xl bg-status-danger-bg border border-status-danger-border text-status-danger-text flex items-center justify-center mx-auto">
                <AlertCircle className="w-7 h-7" />
              </div>
              <div className="space-y-2">
                <h1 className="text-lg font-bold text-txt-primary">
                  {this.props.fallbackTitle || 'Interruption inattendue de l’application'}
                </h1>
                <p className="text-xs text-txt-secondary leading-relaxed">
                  {this.props.fallbackMessage ||
                    'Un incident d’affichage est survenu. Votre session et vos données restent préservées en toute sécurité.'}
                </p>
              </div>

              {this.state.correlationId && (
                <div className="text-[11px] font-mono text-txt-muted bg-app py-1.5 px-3 rounded-lg border border-border-subtle inline-block">
                  Réf. incident : <span className="font-semibold text-txt-primary">{this.state.correlationId}</span>
                </div>
              )}

              <div className="pt-2 flex flex-col sm:flex-row gap-2.5 justify-center">
                <Button variant="primary" size="md" onClick={this.handleReloadApp} className="gap-2 justify-center">
                  <RefreshCw className="w-4 h-4" />
                  <span>Recharger l’application</span>
                </Button>
              </div>
            </div>
          </div>
        );
      }

      // Page-level fallback (sidebar and topbar remain functional)
      return (
        <div className="py-12 px-4 flex items-center justify-center">
          <div className="max-w-lg w-full bg-surface border border-border-default rounded-xl p-6 sm:p-8 shadow-subtle text-center space-y-4">
            <div className="w-12 h-12 rounded-xl bg-status-danger-bg border border-status-danger-border text-status-danger-text flex items-center justify-center mx-auto">
              <AlertCircle className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-base font-bold text-txt-primary">
                {this.props.fallbackTitle || 'Impossible d’afficher cet écran'}
              </h2>
              <p className="text-xs text-txt-secondary mt-1.5 leading-relaxed">
                {this.props.fallbackMessage ||
                  'Une anomalie est survenue lors du rendu des données de cet écran. La navigation reste active.'}
              </p>
            </div>

            {this.state.correlationId && (
              <p className="text-[10px] font-mono text-txt-muted">
                Identifiant : <span className="text-txt-primary">{this.state.correlationId}</span>
              </p>
            )}

            <div className="pt-3 flex items-center justify-center gap-3 flex-wrap">
              <Button variant="outline" size="sm" onClick={this.handleRetry} className="gap-1.5">
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Réessayer</span>
              </Button>
              <Button variant="secondary" size="sm" onClick={this.handleGoHome} className="gap-1.5">
                <LayoutDashboard className="w-3.5 h-3.5" />
                <span>Tableau de bord</span>
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
