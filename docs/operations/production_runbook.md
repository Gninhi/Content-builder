# Runbook d'Exploitation et de Production — ContentOps Harness v2.0

## 1. Architecture Opérationnelle

ContentOps Harness repose sur une architecture **Evidence-First Content Operations** articulée autour de :
- **API Backend (`apps/api/main.py`)** : FastAPI + SQLAlchemy (PostgreSQL en production avec Row-Level Security `002_rls_policies.sql`, SQLite en développement/test).
- **Orchestration LangGraph (`langgraph.json`)** :
  - `idea_research` (`collect_sources -> evidence_enrichment -> ideate_and_score`, enrichissement documentaire borné à max 2 appels d'outils via `AgentToolRegistry`).
  - `content_production` (`generate_variants <-> quality_gate`, boucle réflexive bornée `max_qa_retries = 1` soit max 2 passes).
  - `strategy_insights` (`generate_strategy_insights`, apprentissage propositionnel non-destructif).
- **Workers asynchrones (`services/scheduler/`)** :
  - `VeilleSchedulerWorker` : collecte multi-connecteurs (`rss`, `arxiv`, `github`, `hackernews`, `huggingface`, `semantic_scholar`, `crossref`, `web`) et entonnoir hybride (pré-qualification déterministe 100 % + enrichissement LLM borné à `VEILLE_MAX_ENRICHMENTS_PER_CYCLE=15`).
  - `PublicationDispatcherWorker` : publication sociale gouvernée avec vérification de hash cryptographique d'approbation humaine (`payload_hash`), idempotence et respect du Kill-Switch.

## 2. Variables d'Environnement Critiques

| Variable | Description | Défaut / Recommandation Prod |
|---|---|---|
| `APP_ENV` | Environnement d'exécution (`development`, `test`, `production`) | `production` |
| `DATABASE_URL` | DSN PostgreSQL de production | `postgresql+psycopg2://...` |
| `JWT_SECRET_KEY` | Clé de signature JWT (min. 32 caractères aléatoires) | Obligatoire en prod |
| `SOCIAL_TOKEN_ENCRYPTION_KEY` | Clé Fernet de chiffrement au repos des tokens OAuth et clés API | Obligatoire en prod |
| `STRICT_LLM_AVAILABILITY` | Retourne `503 LLM_PROVIDERS_DOWN` si les fournisseurs LLM sont indisponibles | `true` en prod |
| `VEILLE_MAX_ENRICHMENTS_PER_CYCLE` | Plafond de candidats enrichis par extraction documentaire + LLM par cycle | `15` |
| `CYCLE_BUDGET_MAX_TOKENS` | Budget FinOps maximal de tokens par exécution de graphe | `50000` |

## 3. Procédures d'Urgence (SOP)

### 3.1 Activation du Kill-Switch Global ou par Workspace
En cas de compromission d'un compte social ou d'anomalie éditoriale :
1. Appeler `POST /v1/workspaces/{workspace_id}/kill-switch` (rôle `Owner` requis) avec `{"enabled": true}`.
2. Le worker de publication (`PublicationDispatcherWorker`) bloque immédiatement tout job `SCHEDULED` ou `PUBLISHING` pour ce workspace.

### 3.2 Purge du Cache LLM ou Recherche
Les sorties `DEMO`, `DEGRADED`, `NO_DATA` et `FALLBACK` ne sont jamais mises en cache (`is_cacheable_llm_output`). En cas de changement de politique éditoriale nécessitant une invalidation immédiate :
- Redis : `redis-cli KEYS "llm_cache:v2:{workspace_id}:*" | xargs redis-cli DEL`
- SQLite : `DELETE FROM llm_cache;`

### 3.3 Vérification des Migrations Alembic
Avant tout déploiement :
```bash
.venv/bin/alembic heads
.venv/bin/alembic upgrade head
```
La révision `8f3a4b5c6d7e` garantit la présence de `veille_sources`, `signals` (incluant `enrichment_status`), `ideas.signal_id` et `user_refresh_tokens.revoked_at`.

