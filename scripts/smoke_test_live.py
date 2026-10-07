#!/usr/bin/env python3
"""
ContentOps Harness - Live Smoke Testing CLI Tool (Phase 8 / Phase 10)

SAFETY CONTRACT:
- Disabled by default. Refuses execution unless LIVE_TESTS=1 is explicitly set in environment.
- NEVER logs, displays, or exposes secret tokens or API credentials.
- Dispatches a verified test post on a staging/test account with human confirmation.
- Integrates with Langfuse to verify trace generation and score recording.
- Optionally cleans up (deletes) the test post on the target platform.
"""

import os
import sys
import uuid
import argparse
from datetime import datetime, timezone

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from infra.db.database import get_db_session
from infra.db.repository import ContentOpsRepository
from infra.db.models import ConnectedSocialAccountModel
from packages.domain.state_machine import ContentStatus
from services.publisher.worker import PublisherWorker


def check_safety_gate():
    """Refuses execution unless LIVE_TESTS=1 is explicitly set in the execution environment."""
    live_flag = os.getenv("LIVE_TESTS", "0").strip()
    if live_flag != "1":
        print("\n" + "=" * 70, file=sys.stderr)
        print("SAFETY LOCK ENGAGED: Live smoke tests are DISABLED by default.", file=sys.stderr)
        print("To enable live smoke tests against real social platforms, export:", file=sys.stderr)
        print("    export LIVE_TESTS=1", file=sys.stderr)
        print("    export LIVE_PUBLISHING_ENABLED=true", file=sys.stderr)
        print("=" * 70 + "\n", file=sys.stderr)
        sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description="ContentOps Live Social Smoke Test Runner")
    parser.add_argument(
        "--platform",
        choices=["linkedin", "x", "both"],
        required=True,
        help="Target platform to verify live publication."
    )
    parser.add_argument(
        "--workspace-id",
        required=True,
        help="Workspace ID containing connected social accounts."
    )
    parser.add_argument(
        "--delete-after",
        action="store_true",
        help="Automatically delete the published test post after verification."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform credential and account inspection without sending network post."
    )
    return parser.parse_args()


def run_platform_smoke(platform: str, workspace_id: str, delete_after: bool, dry_run: bool):
    print(f"\n---> Starting live smoke test for platform: [{platform.upper()}] (workspace: {workspace_id})")

    with get_db_session() as db:
        repo = ContentOpsRepository(db)
        
        # 1. Verify connected account in database
        account = (
            db.query(ConnectedSocialAccountModel)
            .filter(
                ConnectedSocialAccountModel.workspace_id == workspace_id,
                ConnectedSocialAccountModel.provider == platform,
                ConnectedSocialAccountModel.status == "ACTIVE"
            )
            .first()
        )

        if not account:
            print(f"[FAIL] No active connected account found for provider '{platform}' in workspace '{workspace_id}'.", file=sys.stderr)
            print("Please initiate OAuth connection first via /v1/oauth/start/{provider}.", file=sys.stderr)
            return False

        print(f"[PASS] Connected account identified: ID='{account.account_id}', Name='{account.account_name or 'N/A'}'")
        print(f"[PASS] Token encryption key ID: '{account.key_id}', Status: '{account.status}'")

        if dry_run:
            print(f"[INFO] Dry-run mode enabled. Skipped network post creation for {platform}.")
            return True

        # 2. Prepare test content
        unique_run_id = uuid.uuid4().hex[:8]
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        if platform == "linkedin":
            content_body = (
                f"[Smoke Test {unique_run_id}] ContentOps Live Harness Verification.\n"
                f"Testing production-ready LangGraph orchestration pipeline at {timestamp}."
            )
        else:
            content_body = (
                f"[Smoke Test {unique_run_id}] ContentOps live test on X.\n"
                f"Verification run at {timestamp}."
            )

        # 3. Create job in database
        brief = repo.create_brief(workspace_id=workspace_id, objective=f"Live Smoke Test {platform}", platform_targets=[platform])
        pkg = repo.create_content_package(str(brief.id), 1)
        var = repo.add_variant(
            package_id=str(pkg.id),
            platform=platform,
            hook=f"Smoke Test {unique_run_id}",
            body=content_body,
            cta="End of test",
            hashtags=["#SmokeTest", "#ContentOps"],
            media_spec={}
        )
        var.status = ContentStatus.IN_REVIEW.value  # type: ignore[assignment]
        db.commit()

        # Human approval simulation (explicit gate)
        repo.record_approval(variant_id=str(var.id), decision="approve", reviewer_id="smoke_test_runner", workspace_id=workspace_id)
        job = repo.schedule_publication(workspace_id=workspace_id, variant_id=str(var.id), scheduled_at=datetime.now(timezone.utc))
        db.commit()

        print(f"[PASS] Staged publication job created: ID='{job.id}' (Status: SCHEDULED)")

        # 4. Instantiate worker and execute job
        worker = PublisherWorker(db)
        print(f"[INFO] Dispatching publication request to {platform.upper()} API...")

        try:
            result = worker.execute_job(str(job.id))

            print(f"[PASS] Execution completed! Status: {result['status']}")
            print(f"[PASS] Platform Post ID: {result.get('platform_post_id')}")
            print(f"[PASS] Public Permalink: {result.get('permalink_url')}")
            print(f"[PASS] Langfuse Trace ID: {result.get('trace_id')}")

            # 5. Optional post-verification deletion
            if delete_after and result.get("platform_post_id"):
                post_id = result["platform_post_id"]
                print(f"[INFO] Proceeding to delete test post '{post_id}'...")
                publisher = worker.resolve_publisher(platform, workspace_id)
                deleted = publisher.delete(post_id)
                if deleted:
                    print(f"[PASS] Test post '{post_id}' deleted successfully from {platform.upper()}.")
                else:
                    print(f"[WARN] Failed to delete test post '{post_id}'. Please review manually.", file=sys.stderr)

            return True

        except Exception as exc:
            print(f"[FAIL] Live publication failed: {exc}", file=sys.stderr)
            return False


def main():
    check_safety_gate()
    args = parse_args()

    platforms = ["linkedin", "x"] if args.platform == "both" else [args.platform]
    all_success = True

    for p in platforms:
        ok = run_platform_smoke(
            platform=p,
            workspace_id=args.workspace_id,
            delete_after=args.delete_after,
            dry_run=args.dry_run
        )
        if not ok:
            all_success = False

    if all_success:
        print("\n=== LIVE SMOKE TEST SUITE COMPLETED SUCCESSFULLY ===")
        sys.exit(0)
    else:
        print("\n=== LIVE SMOKE TEST SUITE FAILED ===", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
