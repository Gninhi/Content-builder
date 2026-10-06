-- ==============================================================================
-- CONTENTOPS HARNESS - INITIAL SCHEMA MIGRATION (PostgreSQL / Supabase)
-- ==============================================================================

CREATE TABLE IF NOT EXISTS workspaces (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    timezone VARCHAR(64) DEFAULT 'UTC',
    owner_id VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS brand_profiles (
    id VARCHAR(64) PRIMARY KEY,
    workspace_id VARCHAR(64) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    audience JSONB NOT NULL DEFAULT '[]'::jsonb,
    voice TEXT NOT NULL,
    pillars JSONB NOT NULL DEFAULT '[]'::jsonb,
    prohibited_topics JSONB NOT NULL DEFAULT '[]'::jsonb,
    cta_policy JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_brand_profiles_workspace ON brand_profiles(workspace_id);

CREATE TABLE IF NOT EXISTS content_sources (
    id VARCHAR(64) PRIMARY KEY,
    workspace_id VARCHAR(64) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    type VARCHAR(32) NOT NULL, -- url, note, text, rss
    canonical_url TEXT,
    raw_content_ref TEXT NOT NULL,
    extracted_facts JSONB NOT NULL DEFAULT '[]'::jsonb,
    provenance JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(32) DEFAULT 'ingested',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_sources_workspace ON content_sources(workspace_id);

CREATE TABLE IF NOT EXISTS ideas (
    id VARCHAR(64) PRIMARY KEY,
    workspace_id VARCHAR(64) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    title VARCHAR(512) NOT NULL,
    angle TEXT NOT NULL,
    pillar VARCHAR(128) NOT NULL,
    audience VARCHAR(128) NOT NULL,
    evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    novelty_score NUMERIC(4,2) DEFAULT 0.0,
    relevance_score NUMERIC(4,2) DEFAULT 0.0,
    effort_score NUMERIC(4,2) DEFAULT 0.0,
    total_score NUMERIC(4,2) DEFAULT 0.0,
    priority VARCHAR(16) DEFAULT 'high',
    risks JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(32) DEFAULT 'IDEA',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ideas_workspace ON ideas(workspace_id);

CREATE TABLE IF NOT EXISTS content_briefs (
    id VARCHAR(64) PRIMARY KEY,
    idea_id VARCHAR(64) REFERENCES ideas(id) ON DELETE SET NULL,
    workspace_id VARCHAR(64) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    objective TEXT NOT NULL,
    campaign_id VARCHAR(64),
    platform_targets JSONB NOT NULL DEFAULT '["linkedin", "x"]'::jsonb,
    requirements JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(32) DEFAULT 'BRIEFED',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS content_packages (
    id VARCHAR(64) PRIMARY KEY,
    brief_id VARCHAR(64) NOT NULL REFERENCES content_briefs(id) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    model_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    qa_score NUMERIC(5,2) DEFAULT 0.0,
    status VARCHAR(32) DEFAULT 'DRAFT',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS content_variants (
    id VARCHAR(64) PRIMARY KEY,
    package_id VARCHAR(64) NOT NULL REFERENCES content_packages(id) ON DELETE CASCADE,
    platform VARCHAR(32) NOT NULL,
    hook TEXT NOT NULL,
    body TEXT NOT NULL,
    cta TEXT NOT NULL,
    hashtags JSONB NOT NULL DEFAULT '[]'::jsonb,
    media_spec JSONB NOT NULL DEFAULT '{}'::jsonb,
    claims JSONB NOT NULL DEFAULT '[]'::jsonb,
    payload_hash VARCHAR(64) NOT NULL,
    status VARCHAR(32) DEFAULT 'DRAFT',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_variants_package ON content_variants(package_id);

CREATE TABLE IF NOT EXISTS approvals (
    id VARCHAR(64) PRIMARY KEY,
    variant_id VARCHAR(64) NOT NULL REFERENCES content_variants(id) ON DELETE CASCADE,
    decision VARCHAR(32) NOT NULL, -- approve, edit, reject, request_rewrite
    reviewer_id VARCHAR(64) NOT NULL,
    feedback TEXT,
    payload_hash VARCHAR(64) NOT NULL,
    reviewed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_approvals_variant ON approvals(variant_id);

CREATE TABLE IF NOT EXISTS publication_jobs (
    id VARCHAR(64) PRIMARY KEY,
    variant_id VARCHAR(64) NOT NULL REFERENCES content_variants(id) ON DELETE CASCADE,
    platform VARCHAR(32) NOT NULL,
    scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL,
    idempotency_key VARCHAR(64) UNIQUE NOT NULL,
    status VARCHAR(32) DEFAULT 'SCHEDULED',
    attempt_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_jobs_status_scheduled ON publication_jobs(status, scheduled_at);

CREATE TABLE IF NOT EXISTS published_posts (
    id VARCHAR(64) PRIMARY KEY,
    job_id VARCHAR(64) NOT NULL REFERENCES publication_jobs(id) ON DELETE CASCADE,
    external_post_id VARCHAR(128) NOT NULL,
    final_payload JSONB NOT NULL,
    platform VARCHAR(32) NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE NOT NULL,
    permalink TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS metric_snapshots (
    id VARCHAR(64) PRIMARY KEY,
    post_id VARCHAR(64) NOT NULL REFERENCES published_posts(id) ON DELETE CASCADE,
    observed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    impressions INTEGER DEFAULT 0,
    engagements INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_metrics_post ON metric_snapshots(post_id);

CREATE TABLE IF NOT EXISTS agent_runs (
    id VARCHAR(64) PRIMARY KEY,
    workspace_id VARCHAR(64) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    graph VARCHAR(64) NOT NULL,
    node VARCHAR(64) NOT NULL,
    trace_id VARCHAR(128) NOT NULL,
    input_ref TEXT,
    output_ref TEXT,
    prompt_version VARCHAR(32),
    model VARCHAR(64),
    cost NUMERIC(8,6) DEFAULT 0.0,
    status VARCHAR(32) DEFAULT 'completed',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_agent_runs_trace ON agent_runs(trace_id);
