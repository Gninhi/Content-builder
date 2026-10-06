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
