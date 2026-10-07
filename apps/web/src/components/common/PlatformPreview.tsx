import React from 'react';
import { ThumbsUp, MessageSquare, Repeat2, Send, Heart, Bookmark, Share, AlertTriangle } from 'lucide-react';

interface PlatformPreviewProps {
  platform: 'linkedin' | 'x' | string;
  hook: string;
  body: string;
  cta: string;
  hashtags?: string[];
  accountName?: string;
  authorName?: string;
  authorHeadline?: string;
  isAiDisclosed?: boolean;
}

export const PlatformPreview: React.FC<PlatformPreviewProps> = ({
  platform,
  hook,
  body,
  cta,
  hashtags = [],
  accountName,
  authorName,
  authorHeadline,
  isAiDisclosed = true,
}) => {
  const displayName = authorName || accountName || 'ContentOps Harness';
  const displayHeadline = authorHeadline || "Système d'exploitation éditorial agentique";
  const isLinkedIn = platform.toLowerCase() === 'linkedin';
  const fullText = [hook, body, cta, (hashtags || []).map((h) => `#${h}`).join(' ')]
    .filter(Boolean)
    .join('\n\n');

  const charCount = fullText.length;
  const maxChars = isLinkedIn ? 3000 : 280;
  const isOverflow = charCount > maxChars;

  if (isLinkedIn) {
    return (
      <div className="bg-[#1b1f23] text-slate-100 rounded-xl p-4 border border-slate-700/80 shadow-md space-y-3 font-sans">
        {/* LinkedIn Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center font-bold text-white text-xs">
              CO
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-semibold text-xs text-white">{displayName}</span>
                <span className="text-[10px] text-slate-400">• 1er</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-tight">{displayHeadline}</p>
              <div className="flex items-center gap-1 text-[10px] text-slate-400">
                <span>À l'instant</span>
                <span>•</span>
                <span>🌐 Public</span>
              </div>
            </div>
          </div>
          <span className="text-[10px] px-2 py-0.5 rounded bg-blue-900/40 text-blue-300 font-mono border border-blue-800/50">
            LinkedIn
          </span>
        </div>

        {/* Content */}
        <div className="text-xs text-slate-200 whitespace-pre-line leading-relaxed space-y-2">
          {hook && <p className="font-bold text-white text-sm">{hook}</p>}
          <p>{body}</p>
          {cta && <p className="font-medium text-sky-400">{cta}</p>}
          {hashtags && hashtags.length > 0 && (
            <p className="text-sky-400 font-medium">
              {hashtags.map((h) => `#${h.replace('#', '')}`).join(' ')}
            </p>
          )}
        </div>

        {/* AI Transparency */}
        {isAiDisclosed && (
          <div className="text-[10px] text-slate-400 border-t border-slate-800 pt-1.5 flex items-center gap-1">
            <span>✨ Assisté par agent d'IA vérifié par validation humaine</span>
          </div>
        )}

        {/* LinkedIn Character Counter & Action Bar */}
        <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-slate-400 text-xs">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1 hover:text-white cursor-pointer"><ThumbsUp className="w-3.5 h-3.5" /> J'aime</span>
            <span className="flex items-center gap-1 hover:text-white cursor-pointer"><MessageSquare className="w-3.5 h-3.5" /> Commenter</span>
            <span className="flex items-center gap-1 hover:text-white cursor-pointer"><Repeat2 className="w-3.5 h-3.5" /> Republier</span>
            <span className="flex items-center gap-1 hover:text-white cursor-pointer"><Send className="w-3.5 h-3.5" /> Envoyer</span>
          </div>
          <span className={`font-mono text-[11px] ${isOverflow ? 'text-rose-400 font-bold' : 'text-slate-400'}`}>
            {charCount.toLocaleString()} / {maxChars.toLocaleString()}
          </span>
        </div>
      </div>
    );
  }

  // X / Twitter Preview
  return (
    <div className="bg-black text-slate-100 rounded-xl p-4 border border-slate-800 shadow-md space-y-3 font-sans">
      {/* X Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center font-bold text-xs text-white">
            X
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-xs text-white">{displayName}</span>
              <span className="text-[11px] text-slate-400 font-mono">@{displayName.toLowerCase().replace(/[^a-z0-9]/g, '')}</span>
              <span className="text-slate-400 text-[11px]">·</span>
              <span className="text-slate-400 text-[11px]">1m</span>
            </div>
          </div>
        </div>
        <span className="text-[10px] px-2 py-0.5 rounded bg-slate-900 text-slate-300 font-mono border border-slate-800">
          X / Post
        </span>
      </div>

      {/* Tweet Body */}
      <div className="text-xs text-slate-200 whitespace-pre-line leading-relaxed space-y-2">
        {hook && <p className="font-bold text-white">{hook}</p>}
        <p>{body}</p>
        {cta && <p className="text-sky-400">{cta}</p>}
        {hashtags && hashtags.length > 0 && (
          <p className="text-sky-400">
            {hashtags.map((h) => `#${h.replace('#', '')}`).join(' ')}
          </p>
        )}
      </div>

      {/* Warning if overflow */}
      {isOverflow && (
        <div className="flex items-center gap-1.5 text-[11px] text-rose-400 bg-rose-950/30 p-2 rounded border border-rose-900/50">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
          <span>Dépassement de la limite X de 280 caractères ({charCount} car.) !</span>
        </div>
      )}

      {/* X Character Counter & Action Bar */}
      <div className="pt-2 border-t border-slate-900 flex items-center justify-between text-slate-400 text-xs">
        <div className="flex items-center gap-4">
          <MessageSquare className="w-3.5 h-3.5 hover:text-sky-400 cursor-pointer" />
          <Repeat2 className="w-3.5 h-3.5 hover:text-emerald-400 cursor-pointer" />
          <Heart className="w-3.5 h-3.5 hover:text-rose-400 cursor-pointer" />
          <Bookmark className="w-3.5 h-3.5 hover:text-sky-400 cursor-pointer" />
          <Share className="w-3.5 h-3.5 hover:text-sky-400 cursor-pointer" />
        </div>
        <span className={`font-mono text-[11px] ${isOverflow ? 'text-rose-400 font-bold' : 'text-slate-400'}`}>
          {charCount} / {maxChars}
        </span>
      </div>
    </div>
  );
};
