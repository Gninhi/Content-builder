import React from 'react';
import { ThumbsUp, MessageSquare, Repeat2, Send, Heart, Bookmark, Share, AlertTriangle } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { TranslationDict } from '../../i18n';
import { PLATFORMS } from '../../constants';

export interface PlatformPreviewProps {
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

export interface PreviewRenderContext {
  displayName: string;
  displayHeadline: string;
  fullText: string;
  charCount: number;
  charLimit: number;
  isOverflow: boolean;
  t: TranslationDict;
}

export interface PlatformPreviewStrategy {
  platformId: string;
  getCharLimit: () => number;
  render: (props: PlatformPreviewProps, ctx: PreviewRenderContext) => React.ReactElement;
}

// -----------------------------------------------------------------------------
// LinkedIn Preview Strategy
// -----------------------------------------------------------------------------
export const LinkedInPreviewStrategy: PlatformPreviewStrategy = {
  platformId: 'linkedin',
  getCharLimit: () => PLATFORMS.linkedin.charLimit,
  render: (props, ctx) => {
    const { hook, body, cta, hashtags = [], isAiDisclosed = true } = props;
    const { displayName, displayHeadline, charCount, charLimit, isOverflow, t } = ctx;

    return (
      <div className="bg-surface-elevated text-txt-primary rounded-xl p-4 border border-border-default shadow-subtle space-y-3 font-sans">
        {/* LinkedIn Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-accent flex items-center justify-center font-bold text-txt-inverse text-xs">
              CO
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-semibold text-xs text-txt-primary">{displayName}</span>
                <span className="text-[10px] text-txt-muted">• 1er</span>
              </div>
              <p className="text-[11px] text-txt-secondary leading-tight">{displayHeadline}</p>
              <div className="flex items-center gap-1 text-[10px] text-txt-muted">
                <span>{t.preview.just_now}</span>
                <span>•</span>
                <span>{t.preview.public}</span>
              </div>
            </div>
          </div>
          <span className="text-[10px] px-2 py-0.5 rounded bg-surface-subtle text-txt-secondary font-medium border border-border-subtle">
            LinkedIn
          </span>
        </div>

        {/* Content */}
        <div className="text-xs text-txt-primary whitespace-pre-line leading-relaxed space-y-2">
          {hook && <p className="font-bold text-txt-primary text-sm">{hook}</p>}
          <p className="text-txt-secondary">{body}</p>
          {cta && <p className="font-medium text-accent-text">{cta}</p>}
          {hashtags && hashtags.length > 0 && (
            <p className="text-accent-text font-medium">
              {hashtags.map((h) => `#${h.replace('#', '')}`).join(' ')}
            </p>
          )}
        </div>

        {/* AI Transparency */}
        {isAiDisclosed && (
          <div className="text-[10px] text-txt-muted border-t border-border-subtle pt-2 flex items-center gap-1">
            <span>{t.preview.ai_disclosed}</span>
          </div>
        )}

        {/* LinkedIn Character Counter & Action Bar */}
        <div className="pt-2 border-t border-border-subtle flex items-center justify-between text-txt-muted text-xs">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1 hover:text-txt-primary cursor-pointer transition-colors">
              <ThumbsUp className="w-3.5 h-3.5" /> {t.preview.like}
            </span>
            <span className="flex items-center gap-1 hover:text-txt-primary cursor-pointer transition-colors">
              <MessageSquare className="w-3.5 h-3.5" /> {t.preview.comment}
            </span>
            <span className="flex items-center gap-1 hover:text-txt-primary cursor-pointer transition-colors">
              <Repeat2 className="w-3.5 h-3.5" /> {t.preview.repost}
            </span>
            <span className="flex items-center gap-1 hover:text-txt-primary cursor-pointer transition-colors">
              <Send className="w-3.5 h-3.5" /> {t.preview.send}
            </span>
          </div>
          <span className={`text-[11px] ${isOverflow ? 'text-status-danger-text font-bold' : 'text-txt-muted'}`}>
            {charCount.toLocaleString()} / {charLimit.toLocaleString()}
          </span>
        </div>
      </div>
    );
  },
};

// -----------------------------------------------------------------------------
// X (Twitter) Preview Strategy
// -----------------------------------------------------------------------------
export const XPreviewStrategy: PlatformPreviewStrategy = {
  platformId: 'x',
  getCharLimit: () => PLATFORMS.x.charLimit,
  render: (props, ctx) => {
    const { hook, body, cta, hashtags = [] } = props;
    const { displayName, charCount, charLimit, isOverflow, t } = ctx;

    const handle = `@${displayName.toLowerCase().replace(/[^a-z0-9]/g, '')}`;

    return (
      <div className="bg-surface-elevated text-txt-primary rounded-xl p-4 border border-border-default shadow-subtle space-y-3 font-sans">
        {/* X Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-full bg-surface-subtle border border-border-default flex items-center justify-center font-bold text-xs text-txt-primary">
              X
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-xs text-txt-primary">{displayName}</span>
                <span className="text-[11px] text-txt-muted font-mono">{handle}</span>
                <span className="text-txt-muted text-[11px]">·</span>
                <span className="text-txt-muted text-[11px]">1m</span>
              </div>
            </div>
          </div>
          <span className="text-[10px] px-2 py-0.5 rounded bg-surface-subtle text-txt-secondary font-medium border border-border-subtle">
            X / Post
          </span>
        </div>

        {/* Tweet Body */}
        <div className="text-xs text-txt-primary whitespace-pre-line leading-relaxed space-y-2">
          {hook && <p className="font-bold text-txt-primary">{hook}</p>}
          <p className="text-txt-secondary">{body}</p>
          {cta && <p className="text-accent-text">{cta}</p>}
          {hashtags && hashtags.length > 0 && (
            <p className="text-accent-text">
              {hashtags.map((h) => `#${h.replace('#', '')}`).join(' ')}
            </p>
          )}
        </div>

        {/* Warning if overflow */}
        {isOverflow && (
          <div className="flex items-center gap-1.5 text-xs text-status-danger-text bg-status-danger-bg p-2.5 rounded-lg border border-status-danger-border">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
            <span>
              {t.preview.char_overflow_warning.replace('{current}', String(charCount))}
            </span>
          </div>
        )}

        {/* X Character Counter & Action Bar */}
        <div className="pt-2 border-t border-border-subtle flex items-center justify-between text-txt-muted text-xs">
          <div className="flex items-center gap-4">
            <MessageSquare className="w-3.5 h-3.5 hover:text-txt-primary cursor-pointer transition-colors" />
            <Repeat2 className="w-3.5 h-3.5 hover:text-txt-primary cursor-pointer transition-colors" />
            <Heart className="w-3.5 h-3.5 hover:text-txt-primary cursor-pointer transition-colors" />
            <Bookmark className="w-3.5 h-3.5 hover:text-txt-primary cursor-pointer transition-colors" />
            <Share className="w-3.5 h-3.5 hover:text-txt-primary cursor-pointer transition-colors" />
          </div>
          <span className={`text-[11px] ${isOverflow ? 'text-status-danger-text font-bold' : 'text-txt-muted'}`}>
            {charCount} / {charLimit}
          </span>
        </div>
      </div>
    );
  },
};

// -----------------------------------------------------------------------------
// Strategy Registry (Open/Closed Principle)
// -----------------------------------------------------------------------------
class PlatformPreviewRegistryClass {
  private strategies: Map<string, PlatformPreviewStrategy> = new Map();

  constructor() {
    this.register('linkedin', LinkedInPreviewStrategy);
    this.register('x', XPreviewStrategy);
    this.register('twitter', XPreviewStrategy);
  }

  public register(platformId: string, strategy: PlatformPreviewStrategy): void {
    this.strategies.set(platformId.toLowerCase().trim(), strategy);
  }

  public getStrategy(platformId: string): PlatformPreviewStrategy {
    const key = platformId.toLowerCase().trim();
    return this.strategies.get(key) || this.strategies.get('linkedin') || LinkedInPreviewStrategy;
  }
}

export const PlatformPreviewRegistry = new PlatformPreviewRegistryClass();

// -----------------------------------------------------------------------------
// Main PlatformPreview Component
// -----------------------------------------------------------------------------
export const PlatformPreview: React.FC<PlatformPreviewProps> = (props) => {
  const { t } = useLanguage();
  const {
    platform,
    hook,
    body,
    cta,
    hashtags = [],
    accountName,
    authorName,
    authorHeadline,
  } = props;

  const strategy = PlatformPreviewRegistry.getStrategy(platform);
  const charLimit = strategy.getCharLimit();

  const displayName = authorName || accountName || t.preview.default_author;
  const displayHeadline = authorHeadline || t.preview.default_headline;

  const fullText = [hook, body, cta, (hashtags || []).map((h) => `#${h}`).join(' ')]
    .filter(Boolean)
    .join('\n\n');

  const charCount = fullText.length;
  const isOverflow = charCount > charLimit;

  const renderContext: PreviewRenderContext = {
    displayName,
    displayHeadline,
    fullText,
    charCount,
    charLimit,
    isOverflow,
    t,
  };

  return strategy.render(props, renderContext);
};
