# Matrice de Remédiation V2 — ContentOps Harness

**Date :** 2026-10-07  
**Branche :** `feat/social-prod`  
**Responsable :** Ingénieur Principal (Staff) Backend / Sécurité / Fiabilité  
**Statut Global :** 100% des findings résolus et prouvés par tests (94 tests unitaires/intégration/attaques au vert, 0 erreur Mypy sur 106 fichiers source).

---

## 1. Synthèse d'Exécution des Remédiations

| Identifiant | Domaine | Sévérité | Statut | Commit | Test de Preuve |
|---|---|---|---|---|---|
| **SEC-V2-01** | Authentification | **Critique** | **RÉSOLU** | `2231b64` | `tests/security/test_jwt_auth.py::test_dev_token_disabled_by_default_in_production` |
| **SEC-V2-02** | Autorisation | **Critique** | **RÉSOLU** | `f0fb875` | `tests/security/test_bola_idor.py::test_owner_cannot_access_other_workspace_brand` |
| **SEC-V2-03** | Authentification | **Critique** | **RÉSOLU** | `c34b8b8` | `tests/security/test_jwt_auth.py::test_jwt_key_rotation_with_kid` |
| **SEC-V2-04** | Coffre OAuth | **Critique** | **RÉSOLU** | `631057e` | `tests/security/test_oauth_vault_security.py::test_database_backed_vault_persistence_and_rotation` |
| **CONC-V2-01** | Concurrence | **Critique** | **RÉSOLU** | `2033a8d` | `tests/reliability/test_concurrency_race.py::test_database_level_lock_prevents_double_publishing` |
| **SEC-V2-05** | Isolation Multi-Tenant | **Élevée** | **RÉSOLU** | `0f6366f` | `tests/unit/test_llm_cache.py::test_cache_isolation_by_workspace` |
| **SEC-V2-06** | Autorisation | **Élevée** | **RÉSOLU** | `79da047` | `tests/security/test_bola_idor.py::test_mass_assignment_brief_rejected` |
| **SEC-V2-07** | Authentification | **Élevée** | **RÉSOLU** | `79da047` | `tests/security/test_api_surface.py::test_sources_endpoint_requires_auth` |
| **DATA-V2-01** | Intégrité Données | **Élevée** | **RÉSOLU** | `28ee4c8` | `tests/integration/test_alembic_migrations.py::test_alembic_upgrade_downgrade_cycle` |
| **FIN-V2-01** | FinOps | **Élevée** | **RÉSOLU** | `90149b2` | `tests/unit/test_pricing_config.py::test_gemini_38_flash_pricing_aligned_with_official_rates` |
| **SEC-V2-08** | Résilience | **Élevée** | **RÉSOLU** | `299e877` | `tests/security/test_api_surface.py::test_rate_limiter_trusted_proxy_header` |
| **OBS-V2-01** | Observabilité | **Moyenne** | **RÉSOLU** | `1c80757` | `tests/observability/test_json_logger.py::test_pii_redaction_oauth_and_social_tokens` |
| **EDT-V2-01** | Conformité Légale | **Moyenne** | **RÉSOLU** | `ff8b6fe` | `tests/evals/test_quality_evaluator.py::test_ai_disclosure_rule_operational_gate` |
| **MOCK-V2-01** | Intégrité Données | **Moyenne** | **RÉSOLU** | `fa67972` | `tests/contract/test_contracts.py::test_analytics_metrics_no_fake_mock_values` |
| **CODE-V2-01** | Qualité de Code | **Moyenne** | **RÉSOLU** | `bea82cb` | `mypy .` (106 fichiers analysés, 0 erreur) |
| **ROLE-V2-01** | Sécurité | **Faible** | **RÉSOLU** | `fa67972` | `tests/security/test_jwt_auth.py::test_strategy_rbac_roles_aligned` |

---

## 2. Détail Technique des Actions Correctives

### SEC-V2-01 : Forçage `ENV=production` par défaut et blocage `/dev-token`
- **Fichier :** `apps/api/routers/auth.py`
- **Action :** Remplacement de `os.getenv("ENV", "dev")` par `os.getenv("ENV", "production")`. La route `/v1/auth/dev-token` lève immédiatement une `HTTPException(403, detail="dev-token endpoint is strictly disabled in non-dev environments")` si `ENV != "dev"`.
- **Preuve :** `pytest tests/security/test_jwt_auth.py -k test_dev_token_disabled_by_default_in_production` (Passé).

### SEC-V2-02 : Élimination du BOLA / IDOR inter-workspaces
- **Fichiers :** `apps/api/routers/publications.py`, `apps/api/routers/content.py`, `apps/api/routers/workspaces.py`, `apps/api/routers/analytics.py`
- **Action :** Suppression définitive de la condition `and user.role.lower() != "owner"`. Un utilisateur ayant le rôle `Owner` est strictement borné à son propre `workspace_id`. Toute tentative d'accès inter-workspaces retourne un `HTTP 403 Forbidden`.
- **Preuve :** `pytest tests/security/test_bola_idor.py` (Passé).

### SEC-V2-03 : Rotation des clés JWT avec `kid` et validation stricte
- **Fichier :** `packages/security/auth.py`
- **Action :** Implémentation du support multi-clés `JWT_KEYS_CONFIG` avec sélection par `kid` dans le header du token JWT. Suppression de la clé par défaut faible. En l'absence de clé de signature configurée en production, l'initialisation échoue immédiatement (fail-closed).
- **Preuve :** `pytest tests/security/test_jwt_auth.py` (Passé).

### SEC-V2-04 : Coffre OAuth persisté en base de données avec chiffrement AES-GCM et rotation
- **Fichiers :** `infra/db/models.py`, `packages/connectors/social/vault.py`
- **Action :** Persistance des jetons dans la table `connected_social_accounts`. Chiffrement AES-256-GCM avec AAD lié au `workspace_id`. Chaque blob chiffré inclut la version de clé (`kid`), le nonce aléatoire (12 octets) et le tag d'authentification. Support de la relecture avec les anciennes clés et de la rotation via `rotate_master_key()`.
- **Preuve :** `pytest tests/security/test_oauth_vault_security.py` (Passé).

### CONC-V2-01 : Verrou anti-double publication au niveau base de données
- **Fichiers :** `infra/db/repository.py`, `services/publisher/worker.py`
- **Action :** Remplacement du test en mémoire par une mise à jour atomique SQL :
  `UPDATE publication_jobs SET status = 'PUBLISHING' WHERE id = :job_id AND status = 'SCHEDULED'`. Si aucune ligne n'est modifiée ou si un verrou concurrent est détecté, le worker abandonne immédiatement l'exécution.
- **Preuve :** `pytest tests/reliability/test_concurrency_race.py` (Passé).

### SEC-V2-05 : Isolation stricte du cache LLM par workspace
- **Fichiers :** `services/orchestration/nodes/research.py`, `packages/security/cache.py`
- **Action :** Ajout obligatoire de `workspace_id` dans le hash SHA-256 de chaque entrée de cache. Deux workspaces demandant des idées sur le même sujet ne peuvent pas partager de résultats en cache.
- **Preuve :** `pytest tests/unit/test_llm_cache.py` (Passé).

### SEC-V2-06 & SEC-V2-07 : Validation des tenants sur les routes POST et protection de `/v1/sources`
- **Fichiers :** `apps/api/routers/briefs.py`, `apps/api/routers/ideas.py`, `apps/api/routers/sources.py`
- **Action :** Écrasement du `workspace_id` fourni dans le corps JSON par `user.workspace_id` extrait du token JWT authentifié. Ajout de `require_roles("Owner", "Editor", "Viewer")` sur `GET /v1/sources`.
- **Preuve :** `pytest tests/security/test_bola_idor.py tests/security/test_api_surface.py` (Passé).

### DATA-V2-01 : Migrations de base de données versionnées (Alembic)
- **Fichiers :** `alembic.ini`, `infra/db/alembic/env.py`, `infra/db/alembic/versions/286e614508c4_initial_schema.py`
- **Action :** Initialisation du schéma relationnel complet via Alembic avec migration réversible (tests d'upgrade et de downgrade complets).
- **Preuve :** `pytest tests/integration/test_alembic_migrations.py` (Passé).

### FIN-V2-01 : Réconciliation tarifaire Gemini 3.8 Flash
- **Fichier :** `config/pricing.json`
- **Action :** Mise à jour des tarifs selon la documentation officielle Google AI : $0.75 / 1M tokens d'entrée, $3.75 / 1M tokens de sortie.
- **Preuve :** `pytest tests/unit/test_pricing_config.py` (Passé).

### SEC-V2-08 : Rate limiting distribué Redis et proxy de confiance
- **Fichiers :** `packages/security/limiter.py`, `apps/api/main.py`
- **Action :** Support de `REDIS_URL` pour SlowAPI, extraction sécurisée de l'adresse IP via `X-Forwarded-For` uniquement pour les IP mandataires configurées dans `TRUSTED_PROXIES`.
- **Preuve :** `pytest tests/security/test_api_surface.py` (Passé).

### OBS-V2-01 : Masquage PII et secrets OAuth
- **Fichier :** `packages/observability/pii.py`
- **Action :** Extension des expressions régulières pour filtrer les jetons d'accès LinkedIn (`AQ[a-zA-Z0-9_\-]+`), les jetons X v2, les jetons Bearer, les codes d'autorisation OAuth et les `code_verifier` PKCE.
- **Preuve :** `pytest tests/observability/test_json_logger.py` (Passé).

### EDT-V2-01 : Règle de transparence IA activable dans le Quality Gate
- **Fichiers :** `packages/domain/brand.py`, `services/orchestration/nodes/quality.py`
- **Action :** Ajout du paramètre `require_ai_disclosure` dans `BrandProfile.cta_policy`. Le `quality_gate_node` applique la vérification de la mention d'assistance par IA si la politique de marque du workspace l'exige.
- **Preuve :** `pytest tests/evals/test_quality_evaluator.py` (Passé).

### MOCK-V2-01 & ROLE-V2-01 : Suppression des métriques factices et alignement RBAC
- **Fichiers :** `apps/api/routers/analytics.py`, `apps/api/routers/strategy.py`
- **Action :** Les métriques analytiques non collectées renvoient `0` au lieu de constantes codées en dur (`12500`, `610`). Remplacement du rôle invalide `"Analyst"` par `Role.OWNER`, `Role.EDITOR`, `Role.VIEWER`.
- **Preuve :** `pytest tests/contract/test_contracts.py tests/security/test_jwt_auth.py` (Passé).

### CODE-V2-01 : Typage statique strict Mypy (0 erreur)
- **Fichiers :** `apps/api/routers/` (tous), `infra/db/repository.py`, `services/publisher/worker.py`, `services/scheduler/dispatcher.py`, `packages/connectors/social/vault.py`
- **Action :** Correction exhaustive de 103 erreurs de typage statique (coercion SQLAlchemy, types de retours, unions Optional, paramètres de dépendances FastAPI).
- **Preuve :** `/opt/anaconda3/bin/mypy .` (Success: no issues found in 106 source files).
