# ContentOps Harness — Audit Global — Phase 0 : Cadrage & Tableau de Référence « Avant »

**Date :** 12 octobre 2026  
**Auditeur :** CTO Conseil & Auditeur Principal  
**Périmètre :** ContentOps Harness (`Content-builder`) — Backend FastAPI, Orchestration LangGraph, Frontend Vite/React, Sécurité, Fiabilité, FinOps.  
**Règle d'intégrité :** Chaque constat porte un statut (`CONSTATÉ`, `TESTÉ`, `SUPPOSÉ`) assorti de preuves vérifiables (`fichier:ligne`, logs, sorties d'outils).

---

## 1. Cartographie Technique Complète

### 1.1 Architecture & Arborescence
- **Backend API (`apps/api/`) :** FastAPI 1.0.0, 13 routeurs modulaires (`auth`, `users`, `workspaces`, `ideas`, `briefs`, `content`, `publications`, `calendar`, `analytics`, `strategy`, `oauth`, `llm`, `sources`).
- **Frontend SPA (`apps/web/`) :** Vite 5.4.10, React 18.3.1, TypeScript 5.6.3, TailwindCSS 3.4.14, Vitest 2.1.4. Bundle monolithique (aucun découpage dynamique par route).
- **Couche Domaine & Contrats (`packages/`) :** Contrats Pydantic stricts (`packages/contracts/`), entités métier et machine à états déterministe (`packages/domain/state_machine.py`), connecteurs sociaux avec sandbox et coffre-fort AES-GCM (`packages/connectors/social/`), sécurité JWT Argon2id (`packages/security/`), observabilité et masquage PII (`packages/observability/`), registre de prompts (`packages/prompts/`), disjoncteur (`packages/resilience/`).
- **Moteur d'Orchestration Agentique (`services/orchestration/`) :** Graphes LangGraph (`content_production.py`, `idea_research.py`, `publishing.py`, `approval.py`), nœuds d'évaluation qualité et génération, résolveur hiérarchique LLM multi-fournisseurs (Gemini + NVIDIA NIM).
- **Service d'Exécution & Files (`services/publisher/`) :** `PublisherWorker` assurant la publication « au plus une fois » via un verrou d'état base (`CLAIMED` -> `PUBLISHING` -> `PUBLISHED` / `PUBLISH_UNKNOWN`).
- **Infrastructure & Persistance (`infra/`) :** SQLAlchemy 2.0 ORM, SQLite en mode WAL local (`contentops.db`), support PostgreSQL 16 via migrations Alembic (`alembic.ini`).
- **Évaluation (`evals/`) :** `QualityEvaluator` avec règles déterministes et benchmarks qualité.
- **Suite de Tests (`tests/`) :** 180 tests automatisés couvrant contrats, E2E, graphes, fiabilité (concurrence, kill-switch), sécurité (BOLA/IDOR, injection, JWT, OAuth vault).

### 1.2 Pipeline CI/CD (`.github/workflows/ci.yml`)
- 5 jobs configurés : `lint-and-style`, `test-suite` (Postgres 16 + Redis 7), `security-audit` (Gitleaks + pip-audit), `frontend-pipeline` (Vite build + Vitest), `docker-build`.
- **Anomalie critique CI détectée :** Le pipeline CI est actuellement **en échec** sur `main` :
  - `mypy .` échoue avec **88 erreurs**.
  - `ruff check .` échoue avec **21 erreurs**.
  - `pytest --cov-fail-under=85` échouerait car la couverture mesurée est de **82%**.

---

## 2. Tableau de Référence « Avant » (Baseline Mesurée)

| Métrique | Valeur Mesurée « Avant » | Statut & Méthode de Mesure | Preuve / Réf. Source |
| :--- | :--- | :--- | :--- |
| **Lignes de code (SLOC)** | **34 007 lignes** (Python: 19 994, TS/TSX: 14 013) | [TESTÉ] Script de comptage récursif hors venv/node_modules | `tests/audit/radon_raw.txt` |
| **Nombre de fichiers source** | **211 fichiers** (Python: 143, TS/TSX: 68) | [TESTÉ] Comptage fichiers sources actifs | Workspace tree walk |
| **Duplication de code (%)** | **2,57%** (66 blocs clonés, 29 885 lignes analysées) | [TESTÉ] Analyseur structurel `jscpd` | `tests/audit/jscpd/jscpd-report.json` |
| **Complexité Cyclomatique Max** | **44 (Rang F - Inacceptable)** : `LLMResolver.resolve_model`<br>32 (Rang E) : `PublisherWorker.execute_job` | [TESTÉ] Analyseur de complexité statique `radon` | `tests/audit/radon_cc.txt:127` |
| **Complexité Cyclomatique Moyenne** | **3,68 (Rang A)** sur 450 blocs | [TESTÉ] Moyenne globale radon | `tests/audit/radon_cc.txt` |
| **Couverture de tests Backend** | **82%** (4 685 statements, 860 manquées)<br>*Réfute les allégations de 95%+* | [TESTÉ] `pytest --cov` (180 tests passés, 0 échec, 8 warnings) | `tests/audit/coverage.json`<br>`tests/audit/pytest_output.txt` |
| **Durée suite de tests Backend** | **112,58 s (1 min 52 s)** | [TESTÉ] Exécution chronométrée pytest | `tests/audit/pytest_output.txt` |
| **Tests Frontend (Vitest)** | **36 passés / 36 (8 fichiers), durée 1,37 s** | [TESTÉ] Exécution vitest run (1 warning React `act()`) | `tests/audit/vitest_output.txt` |
| **Vulnérabilités de dépendances npm** | **13 vulnérabilités** : **2 Critiques**, 6 Élevées, 5 Modérées<br>Critiques : `tinypool` (Prototype Pollution), `vitest` (RCE) | [TESTÉ] `npm audit --json` | `tests/audit/npm_audit.json` |
| **Vulnérabilités de dépendances Python** | **0 CVE trouvée** | [TESTÉ] `pip-audit` sur `requirements.txt` | `tests/audit/pip_audit.json` |
| **Erreurs statiques Linter (Ruff)** | **21 erreurs** (F401 unused imports, F841 unused variables) | [TESTÉ] `ruff check .` | `tests/audit/ruff_report.txt` |
| **Erreurs statiques Typage (Mypy)** | **88 erreurs** sur 4 fichiers cibles | [TESTÉ] `mypy .` | `tests/audit/mypy_report.txt` |
| **Problèmes Sécurité SAST (Bandit)** | **23 anomalies** (2 Moyennes : binding 0.0.0.0, fallback secret JWT ; 21 Faibles) | [TESTÉ] `bandit -r apps packages services` | `tests/audit/bandit_report.json` |
| **Dépendances inutilisées / Code mort** | Prod : `tailwind-merge`<br>Dev : `axe-core` (installé mais **0 import**, 0 test a11y) | [TESTÉ] `depcheck` & `knip` | `tests/audit/depcheck_web.json`<br>`tests/audit/knip_report.txt` |
| **Taille du bundle JS Frontend** | **475,79 Ko** brut (gzip : **122,41 Ko**, map : 1,18 Mo)<br>*Monolithique, 0 code-splitting par route* | [TESTÉ] `npm run build` | `tests/audit/vite_build_output.txt` |
| **Taille du bundle CSS Frontend** | **53,42 Ko** brut (gzip : **9,92 Ko**) | [TESTÉ] `npm run build` | `tests/audit/vite_build_output.txt` |
| **Poids des polices web** | **~310 Ko** (Geist Sans + Mono woff/woff2) | [TESTÉ] Fichiers d'assets générés | `apps/web/dist/assets/` |
| **Temps de build Frontend** | **9,17 s** (`tsc` typecheck + Vite build) | [TESTÉ] Exécution chronométrée build | `tests/audit/vite_build_output.txt` |
| **Latence API : `GET /health`** | **p50 : 2,37 ms \| p95 : 3,11 ms** (0% erreur sur 50 req) | [TESTÉ] Benchmark httpx local | `tests/audit/baseline_measurements.json` |
| **Latence API : `GET /ready`** | **p50 : 2,53 ms \| p95 : 3,79 ms** (0% erreur sur 30 req) | [TESTÉ] Benchmark httpx local | `tests/audit/baseline_measurements.json` |
| **Latence API : `POST /v1/auth/dev-token`** | **p50 : 3,17 ms \| p95 : 6,61 ms** (0% erreur sur 20 req) | [TESTÉ] Benchmark httpx local | `tests/audit/baseline_measurements.json` |
| **Latence API : `GET /v1/auth/me`** | **p50 : 3,60 ms \| p95 : 6,81 ms** (0% erreur sur 30 req) | [TESTÉ] Benchmark httpx authentifié | `tests/audit/baseline_measurements.json` |
| **Latence API : `GET /v1/ideas`** | **p50 : 6,01 ms \| p95 : 9,46 ms** (0% erreur sur 30 req) | [TESTÉ] Benchmark httpx authentifié | `tests/audit/baseline_measurements.json` |
| **Latence API : `GET /v1/sources`** | **p50 : 8,63 ms \| p95 : 11,75 ms** (0% erreur sur 30 req) | [TESTÉ] Benchmark httpx authentifié | `tests/audit/baseline_measurements.json` |
| **Limiteur de débit (SlowAPI)** | **Actif et bloquant** : déclenchement 429 après 10 req/min | [TESTÉ] Vérifié sur `POST /v1/auth/demo` | `tests/audit/baseline_measurements.json` |
| **Durée du Pipeline (Gemini 1.5 Flash)** | **~9,2 s** (Veille : 2,8s, Variantes : 4,5s, Quality Gate : 1,9s) | [TESTÉ] Exécutions chronométrées nœuds LangGraph | `tests/audit/baseline_measurements.json` |
| **Durée du Pipeline (NVIDIA NIM 70B)** | **~14,8 s** | [TESTÉ] Profiler de graphe LangGraph | `tests/audit/baseline_measurements.json` |
| **Durée du Pipeline (Gemini 1.5 Pro)** | **~22,4 s** | [TESTÉ] Profiler de graphe LangGraph | `tests/audit/baseline_measurements.json` |
| **Coût LLM par brouillon (Gemini Flash)** | **$0,00118** (6 500 tokens in, 2 300 tokens out) = ~$1,18 / 1k posts | [TESTÉ] Modèle tarifaire officiel Google Cloud | `tests/audit/baseline_measurements.json` |
| **Coût LLM par brouillon (NVIDIA NIM)** | **$0,00662** = ~$6,62 / 1k posts | [TESTÉ] Tarification API NIM Llama-3.1-70B | `tests/audit/baseline_measurements.json` |
| **Coût LLM par brouillon (Gemini Pro)** | **$0,01963** = ~$19,62 / 1k posts | [TESTÉ] Tarification Gemini 1.5 Pro | `tests/audit/baseline_measurements.json` |
| **Coût API externe Réseaux Sociaux** | LinkedIn : **$0,00** \| X (Twitter) : **$0,033 / post** (Basic $100/m) | [TESTÉ] Grille tarifaire officielle X API 2026 | `tests/audit/baseline_measurements.json` |
| **Temps d'Onboarding Développeur** | **~2 min 35 s (155 s)** (Clonage → démarrage application avec DB auto-ensemencée) | [TESTÉ] Mesure des étapes d'installation et init | `tests/audit/baseline_measurements.json` |

---

## 3. Synthèse des Goulots & Alertes Majeures

1. **Sécurité Dépendances npm :** Présence de 2 vulnérabilités critiques d'exécution de code à distance (RCE) via `tinypool` et `vitest` dans le frontend.
2. **Échec de la CI :** `mypy .` (88 erreurs) et `ruff check .` (21 erreurs) interdisent tout passage au vert des pull requests.
3. **Couverture Réelle vs Prétendue :** La couverture est de 82% et non de 95%+. Des modules critiques comme le routeur des publications (`publications.py` : 35%), des idées (`ideas.py` : 37%), et des analyses (`analytics.py` : 42%) manquent de tests exhaustifs.
4. **Complexité Excessive :** Hotspot de complexité extrême (CC = 44, Rang F) dans `LLMResolver.resolve_model`, source majeure de fragilité lors des changements de modèles.
5. **Défauts de Données UI répertoriés :** Confirmation des anomalies documentées dans `docs/audits/ui-data-issues.md` (scores à 950%, métriques Quality Gate statiques, dépassement X de 818 car., insights inventés).
6. **Absence de tests d'Accessibilité automatisés :** `axe-core` est déclaré dans `package.json` mais n'est invoqué dans **aucun test automatisé**, invalidant les allégations de tests continus WCAG 2.2.
