-- ==============================================================================
-- CONTENTOPS HARNESS - ROW LEVEL SECURITY (RLS) POLICIES
-- ==============================================================================

-- Enable RLS on core tenant-scoped tables
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE brand_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE ideas ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_briefs ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY;

-- Helper function: get current active workspace from session
CREATE OR REPLACE FUNCTION current_workspace_id() RETURNS TEXT AS $$
    SELECT NULLIF(current_setting('app.current_workspace_id', true), '');
$$ LANGUAGE sql STABLE;

-- Workspace Isolation Policy
CREATE POLICY workspace_isolation_policy ON brand_profiles
    FOR ALL
    USING (workspace_id = current_workspace_id());

CREATE POLICY sources_isolation_policy ON content_sources
    FOR ALL
    USING (workspace_id = current_workspace_id());

CREATE POLICY ideas_isolation_policy ON ideas
    FOR ALL
    USING (workspace_id = current_workspace_id());

CREATE POLICY briefs_isolation_policy ON content_briefs
    FOR ALL
    USING (workspace_id = current_workspace_id());

CREATE POLICY agent_runs_isolation_policy ON agent_runs
    FOR ALL
    USING (workspace_id = current_workspace_id());

-- Extended RLS coverage for Veille, Signals, Social Accounts, and LLM Settings
ALTER TABLE veille_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE veille_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_llm_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE connected_social_accounts ENABLE ROW LEVEL SECURITY;

CREATE POLICY veille_sources_isolation_policy ON veille_sources
    FOR ALL
    USING (workspace_id = current_workspace_id());

CREATE POLICY veille_runs_isolation_policy ON veille_runs
    FOR ALL
    USING (workspace_id = current_workspace_id());

CREATE POLICY signals_isolation_policy ON signals
    FOR ALL
    USING (workspace_id = current_workspace_id());

CREATE POLICY workspace_llm_settings_isolation_policy ON workspace_llm_settings
    FOR ALL
    USING (workspace_id = current_workspace_id());

CREATE POLICY connected_social_accounts_isolation_policy ON connected_social_accounts
    FOR ALL
    USING (workspace_id = current_workspace_id());

-- Extended RLS coverage for Content Pipeline Hierarchy (Direct Denormalized Workspace Isolation - DB-01)
ALTER TABLE content_packages ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_variants ENABLE ROW LEVEL SECURITY;
ALTER TABLE approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE publication_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE published_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE metric_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY packages_isolation_policy ON content_packages
    FOR ALL
    USING (workspace_id = current_workspace_id());

CREATE POLICY variants_isolation_policy ON content_variants
    FOR ALL
    USING (workspace_id = current_workspace_id());

CREATE POLICY approvals_isolation_policy ON approvals
    FOR ALL
    USING (workspace_id = current_workspace_id());

CREATE POLICY publication_jobs_isolation_policy ON publication_jobs
    FOR ALL
    USING (workspace_id = current_workspace_id());

CREATE POLICY published_posts_isolation_policy ON published_posts
    FOR ALL
    USING (workspace_id = current_workspace_id());

CREATE POLICY metric_snapshots_isolation_policy ON metric_snapshots
    FOR ALL
    USING (workspace_id = current_workspace_id());

