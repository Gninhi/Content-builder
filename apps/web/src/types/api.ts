export type UserRole = 'Owner' | 'Editor' | 'Viewer' | 'ServiceAgent';

export interface UserSession {
  user_id: string;
  role: UserRole;
  workspace_id: string;
  token: string;
}

export type ContentStatus =
  | 'DRAFT'
  | 'PENDING_REVIEW'
  | 'APPROVED'
  | 'SCHEDULED'
  | 'PUBLISHING'
  | 'PUBLISHED'
  | 'FAILED'
  | 'PUBLISH_UNKNOWN';

export interface Workspace {
  id: string;
  name: string;
  timezone: string;
  owner_id: string;
  kill_switch_enabled: boolean;
  created_at?: string;
}

export interface BrandProfile {
  id?: string;
  workspace_id: string;
  audience: string[];
  voice: string;
  pillars: string[];
  prohibited_topics: string[];
  cta_policy: {
    allowed_ctas: string[];
    max_per_post: number;
  };
  version?: number;
  created_at?: string;
}

export interface FactClaim {
  claim: string;
  confidence_score: number;
}

export interface QualityGateReport {
  brand_alignment_score: number;
  prohibited_topics_clean: boolean;
  duplicate_detected: boolean;
  ai_disclosure_compliant: boolean;
  passed: boolean;
  details?: string[];
}

export interface InboxVariant {
  id: string;
  package_id?: string;
  platform: 'linkedin' | 'x' | string;
  hook: string;
  body: string;
  cta: string;
  hashtags?: string[];
  media_spec?: Record<string, unknown>;
  claims?: FactClaim[];
  payload_hash: string;
  status: ContentStatus;
  quality_gate_report?: QualityGateReport;
  created_at?: string;
  is_degraded?: boolean;
}

export interface IdeaItem {
  id: string;
  workspace_id: string;
  topic: string;
  angle: string;
  novelty_score: number;
  relevance_score: number;
  effort_estimate: string;
  priority_score: number;
  status: 'new' | 'accepted' | 'dismissed';
  source_reference?: string;
}

export interface CalendarEvent {
  id: string;
  title: string;
  platform: 'linkedin' | 'x' | string;
  scheduled_at: string;
  status: ContentStatus;
  variant_id: string;
}

export interface AnalyticsOverview {
  total_impressions: number;
  average_engagement_rate: number;
  total_clicks: number;
  published_posts_count: number;
  llm_budget_spent: number;
  llm_budget_limit: number;
  degraded_count: number;
}

export interface StrategyInsight {
  id: string;
  recommendation: string;
  rationale: string;
  platform: string;
  priority: 'high' | 'medium' | 'low';
}

export interface ConnectedAccount {
  platform: 'linkedin' | 'x';
  account_name: string;
  status: 'connected' | 'disconnected' | 'expired';
  expires_in_days?: number;
  scopes: string[];
  monthly_used?: number;
  monthly_limit?: number;
}

export interface GovernanceSettings {
  kill_switch_enabled: boolean;
  max_publications_per_hour: number;
  social_sandbox_mode: boolean;
  live_publishing_enabled: boolean;
}
