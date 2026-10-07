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
    <div className="glass-panel p-8 rounded-2xl text-center max-w-md mx-auto space-y-4 border border-rose-500/30 bg-rose-950/20">
      <div className="w-14 h-14 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center mx-auto">
        <AlertCircle className="w-7 h-7" />
      </div>
      <div>
        <h3 className="text-base font-bold text-white">{title}</h3>
        <p className="text-xs text-rose-200/80 mt-1 leading-relaxed">{message}</p>
      </div>

      {correlationId && (
        <p className="text-[11px] font-mono text-slate-400 bg-slate-900/60 py-1 px-2.5 rounded-lg border border-slate-800">
          ID de support : <span className="text-cyan-300">{correlationId}</span>
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
