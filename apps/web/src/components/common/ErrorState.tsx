import React from 'react';
import { Button } from './Button';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorStateProps {
  title?: string;
  message: string;
  correlationId?: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Erreur de chargement',
  message,
  correlationId,
  onRetry,
}) => {
  return (
    <div className="panel-surface p-6 sm:p-8 rounded-xl text-center max-w-md mx-auto space-y-4 border border-status-danger-border bg-status-danger-bg">
      <div className="w-12 h-12 rounded-lg bg-status-danger-bg border border-status-danger-border text-status-danger-text flex items-center justify-center mx-auto">
        <AlertCircle className="w-6 h-6" />
      </div>
      <div>
        <h3 className="text-base font-bold text-status-danger-text">{title}</h3>
        <p className="text-xs text-status-danger-text/90 mt-1 leading-relaxed">{message}</p>
      </div>

      {correlationId && (
        <p className="text-[11px] font-mono text-txt-secondary bg-surface py-1.5 px-3 rounded border border-border">
          ID de support : <span className="font-semibold">{correlationId}</span>
        </p>
      )}

      {onRetry && (
        <div className="pt-2">
          <Button variant="outline" size="sm" onClick={onRetry} className="gap-2">
            <RefreshCw className="w-4 h-4" />
            <span>Réessayer</span>
          </Button>
        </div>
      )}
    </div>
  );
};
