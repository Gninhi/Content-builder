export type UserRole = 'Owner' | 'Editor' | 'Viewer' | 'ServiceAgent';

export interface UserSummary {
  id: string;
  email: string;
  full_name: string;
  display_name?: string | null;
  avatar_url?: string | null;
  email_verified: boolean;
  language: string;
  theme: string;
}

export interface WorkspaceMembershipSummary {
  workspace_id: string;
  name: string;
  role: string;
  timezone: string;
  is_owner: boolean;
  is_demo?: boolean;
}

export interface UserSession {
  user_id: string;
  role: UserRole;
  workspace_id: string;
  token: string;
  user?: UserSummary;
  workspaces?: WorkspaceMembershipSummary[];
  is_demo?: boolean;
  expires_at?: string | null;
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

export interface LLMProviderInfo {
  provider_id: string;
  display_name: string;
  adapter_type: string;
  is_configured: boolean;
  is_enabled: boolean;
  base_url?: string;
  default_model: string;
  last_test_status?: string;
  last_test_at?: string;
  last_test_message?: string;
}

export interface LLMModelInfo {
  provider_id: string;
  model_id: string;
  full_id: string;
  display_name: string;
  capabilities: Record<string, boolean | null>;
  parameters: Record<string, any>;
  provenance: string;
  last_refreshed_at: string;
  is_available: boolean;
}

export interface TaskLLMOverride {
  provider_id: string;
  model_id: string;
  temperature?: number;
  inherit_default: boolean;
}

export interface WorkspaceLLMConfig {
  workspace_id: string;
  default_provider_id: string;
  default_model_id: string;
  default_temperature: number;
  task_overrides: Record<string, TaskLLMOverride>;
  provider_settings: Record<string, Record<string, any>>;
  updated_at?: string;
}

export interface LLMConnectionTestResult {
  success: boolean;
  provider_id: string;
  model_id: string;
  latency_ms: number;
  message: string;
  tested_at: string;
}

export interface UserWorkspace {
  workspace_id: string;
  name: string;
  role: string;
  timezone: string;
  is_owner: boolean;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  display_name?: string | null;
  job_title?: string | null;
  avatar_url?: string | null;
  timezone: string;
  language: string;
  theme: string;
  notification_preferences: Record<string, boolean>;
  ui_preferences: Record<string, any>;
  created_at: string;
  updated_at: string;
  workspaces: UserWorkspace[];
}

export interface UserProfileUpdate {
  full_name?: string;
  display_name?: string;
  job_title?: string;
  timezone?: string;
  language?: 'fr' | 'en' | 'es' | 'de';
  theme?: 'dark' | 'light' | 'system';
  notification_preferences?: Record<string, boolean>;
  ui_preferences?: Record<string, any>;
}

export interface SessionInfo {
  id: string;
  token_jti: string;
  user_agent?: string | null;
  ip_address?: string | null;
  last_active_at: string;
  expires_at: string;
  is_current: boolean;
}

export interface PersonalDataExport {
  exported_at: string;
  user: Record<string, any>;
  workspaces: any[];
  sessions: any[];
  recent_audit_logs: any[];
}

export type VeilleAxis = 'ia' | 'frameworks' | 'metiers';
export type TrustLevel = 'A' | 'B' | 'C';
export type SignalStatus = 'NEW' | 'QUALIFIED' | 'REJECTED' | 'CONVERTED';

export interface SignalFact {
  claim: string;
  source_id?: string;
  verified?: boolean;
}

export interface VeilleSignal {
  id: string;
  workspace_id: string;
  canonical_url?: string | null;
  title: string;
  summary: string;
  axis: VeilleAxis | string;
  trust_level: TrustLevel | string;
  qualification_score: number;
  qualification_criteria: Record<string, any>;
  facts: SignalFact[];
  executive_takeaway: string;
  status: SignalStatus | string;
  is_synthetic: boolean;
  created_at: string;
}

export interface VeilleSource {
  id: string;
  workspace_id: string;
  name: string;
  url: string;
  axis: VeilleAxis | string;
  trust_level: TrustLevel | string;
  source_type: string;
  is_active: boolean;
  health_status: string;
  last_polled_at?: string | null;
  error_message?: string | null;
  created_at: string;
}

export interface VeilleRun {
  id: string;
  workspace_id: string;
  status: 'RUNNING' | 'COMPLETED' | 'DEGRADED' | 'FAILED' | string;
  trigger_type: 'SCHEDULED' | 'MANUAL' | string;
  axis?: string | null;
  sources_contacted: number;
  sources_failed: number;
  signals_discovered: number;
  signals_saved: number;
  signals_qualified: number;
  signals_rejected: number;
  error_summary?: string | null;
  started_at: string;
  completed_at?: string | null;
}

export interface VeilleScheduleStatus {
  workspace_id: string;
  timezone: string;
  scheduled_hour: number;
  scheduled_minute: number;
  is_due: boolean;
  last_run?: VeilleRun | null;
  next_scheduled_run: string;
  active_sources_count: number;
  failing_sources_count: number;
}
