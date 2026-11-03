-- ==============================================================================
-- CONTENTOPS HARNESS - MIGRATION 003: DENORMALIZE WORKSPACE_ID (DB-01)
-- ==============================================================================
-- Eliminates multi-table recursive joins in PostgreSQL Row Level Security (RLS)
-- and query execution paths by adding direct indexed workspace_id foreign keys.

-- 1. Alter tables to add workspace_id column
ALTER TABLE content_packages ADD COLUMN IF NOT EXISTS workspace_id VARCHAR(64) REFERENCES workspaces(id) ON DELETE CASCADE;
ALTER TABLE content_variants ADD COLUMN IF NOT EXISTS workspace_id VARCHAR(64) REFERENCES workspaces(id) ON DELETE CASCADE;
ALTER TABLE approvals ADD COLUMN IF NOT EXISTS workspace_id VARCHAR(64) REFERENCES workspaces(id) ON DELETE CASCADE;
ALTER TABLE publication_jobs ADD COLUMN IF NOT EXISTS workspace_id VARCHAR(64) REFERENCES workspaces(id) ON DELETE CASCADE;
ALTER TABLE published_posts ADD COLUMN IF NOT EXISTS workspace_id VARCHAR(64) REFERENCES workspaces(id) ON DELETE CASCADE;
ALTER TABLE metric_snapshots ADD COLUMN IF NOT EXISTS workspace_id VARCHAR(64) REFERENCES workspaces(id) ON DELETE CASCADE;

-- 2. Backfill existing data
UPDATE content_packages p
SET workspace_id = b.workspace_id
FROM content_briefs b
WHERE p.brief_id = b.id AND p.workspace_id IS NULL;

UPDATE content_variants v
SET workspace_id = p.workspace_id
FROM content_packages p
WHERE v.package_id = p.id AND v.workspace_id IS NULL;

UPDATE approvals a
SET workspace_id = v.workspace_id
FROM content_variants v
WHERE a.variant_id = v.id AND a.workspace_id IS NULL;

UPDATE publication_jobs j
SET workspace_id = v.workspace_id
FROM content_variants v
WHERE j.variant_id = v.id AND j.workspace_id IS NULL;

UPDATE published_posts pp
SET workspace_id = j.workspace_id
FROM publication_jobs j
WHERE pp.job_id = j.id AND pp.workspace_id IS NULL;

UPDATE metric_snapshots m
SET workspace_id = pp.workspace_id
FROM published_posts pp
WHERE m.post_id = pp.id AND m.workspace_id IS NULL;

-- Default fallback to default workspace if any orphans remain
UPDATE content_packages SET workspace_id = 'ws_default' WHERE workspace_id IS NULL;
UPDATE content_variants SET workspace_id = 'ws_default' WHERE workspace_id IS NULL;
UPDATE approvals SET workspace_id = 'ws_default' WHERE workspace_id IS NULL;
UPDATE publication_jobs SET workspace_id = 'ws_default' WHERE workspace_id IS NULL;
UPDATE published_posts SET workspace_id = 'ws_default' WHERE workspace_id IS NULL;
UPDATE metric_snapshots SET workspace_id = 'ws_default' WHERE workspace_id IS NULL;

-- 3. Set NOT NULL constraints
ALTER TABLE content_packages ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE content_variants ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE approvals ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE publication_jobs ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE published_posts ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE metric_snapshots ALTER COLUMN workspace_id SET NOT NULL;

-- 4. Create performance indexes
CREATE INDEX IF NOT EXISTS ix_content_packages_workspace_created ON content_packages(workspace_id, created_at);
CREATE INDEX IF NOT EXISTS ix_content_variants_ws_status ON content_variants(workspace_id, status);
CREATE INDEX IF NOT EXISTS ix_approvals_workspace_reviewed ON approvals(workspace_id, reviewed_at);
CREATE INDEX IF NOT EXISTS ix_publication_jobs_ws_status_sched ON publication_jobs(workspace_id, status, scheduled_at);
CREATE INDEX IF NOT EXISTS ix_published_posts_workspace_published ON published_posts(workspace_id, published_at);
CREATE INDEX IF NOT EXISTS ix_metric_snapshots_workspace_observed ON metric_snapshots(workspace_id, observed_at);

-- 5. Replace RLS SubPlan policies with direct equality checks
DROP POLICY IF EXISTS packages_isolation_policy ON content_packages;
CREATE POLICY packages_isolation_policy ON content_packages FOR ALL USING (workspace_id = current_workspace_id());

DROP POLICY IF EXISTS variants_isolation_policy ON content_variants;
CREATE POLICY variants_isolation_policy ON content_variants FOR ALL USING (workspace_id = current_workspace_id());

DROP POLICY IF EXISTS approvals_isolation_policy ON approvals;
CREATE POLICY approvals_isolation_policy ON approvals FOR ALL USING (workspace_id = current_workspace_id());

DROP POLICY IF EXISTS publication_jobs_isolation_policy ON publication_jobs;
CREATE POLICY publication_jobs_isolation_policy ON publication_jobs FOR ALL USING (workspace_id = current_workspace_id());

DROP POLICY IF EXISTS published_posts_isolation_policy ON published_posts;
CREATE POLICY published_posts_isolation_policy ON published_posts FOR ALL USING (workspace_id = current_workspace_id());

DROP POLICY IF EXISTS metric_snapshots_isolation_policy ON metric_snapshots;
CREATE POLICY metric_snapshots_isolation_policy ON metric_snapshots FOR ALL USING (workspace_id = current_workspace_id());
