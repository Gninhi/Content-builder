# Matrice de Remédiation & Durcissement (REMEDIATION.md)

Ce document suit la résolution exhaustive des failles recensées dans [AUDIT.md](file:///Users/seansiehigninhi/Dossier_dev/apps/F-LangGraph/DeepAgent/AUDIT.md).
Chaque correctif est rattaché à son commit atomique et à ses tests de non-régression.

---

## 📊 Matrice Globale de Traitement

| ID Finding | Axe | Sévérité / Priorité | Titre & Description du Problème | Correctif Prévu | Phase | Statut | Commit & Tests |
| :--- | :--- | :---: | :--- | :--- | :---: | :---: | :--- |
| **SEC-01** | Sécurité | **P0 (Critique)** | Secrets sur disque & absence `.gitignore` | `.gitignore` strict, `.env.example` propre, scan gitleaks/trufflehog | P1 | **RÉSOLU** | Initialisé en phase audit / scan historique |
| **SEC-02** | Sécurité | **P0 (Critique)** | Faux RBAC via `X-User-Role` | Validation JWT stricte (HMAC/RSA, exp, iss, aud), claims vérifiés, émetteur dev local | P1 | **RÉSOLU** | `tests/security/test_jwt_auth.py` |
| **SEC-03** | Sécurité | **P0 (Élevée)** | Injection de prompt via données web | Délimitation stricte `<untrusted_content>`, escaping, non-interprétation en instruction, validation schéma Pydantic | P1 | **RÉSOLU** | `tests/security/test_prompt_injection.py` |
| **SEC-04** | Sécurité | **P0 (Élevée)** | Vulnérabilités BOLA / IDOR sur `workspace_id` | Repository centralisé avec injection et filtrage systématique du `workspace_id` | P1 | **RÉSOLU** | `tests/security/test_bola_idor.py` |
| **SEC-05** | Sécurité | **P0 (Élevée)** | Profils de marque exposés sans RBAC | Guard RBAC explicite sur `GET /v1/brand-profiles/{workspace_id}` | P1 | **RÉSOLU** | `tests/security/test_jwt_auth.py` |
| **SEC-06** | Sécurité | **P1 (Moyenne)** | SSRF et surface API non durcie | Rate limiting, CORS restrictif, body size limit, headers sécurité, validation URL | P1 | **RÉSOLU** | `tests/security/test_api_surface.py` |
| **SEC-07** | Sécurité | **P1 (Moyenne)** | Image Docker root et secrets en clair | Conteneur non-root (`appuser`), HEALTHCHECK, `.dockerignore` strict | P1 | **RÉSOLU** | `infra/docker/Dockerfile.api` |
| **REL-01** | Fiabilité | **P0 (Critique)** | Nœuds d'agents sans appels LLM réels | Migration Gemini 3.8 Flash + sorties structurées Pydantic (traité) | P2 | **RÉSOLU** | `audit/gemini-langfuse` |
| **REL-02** | Fiabilité | **P0 (Critique)** | Checkpointer en mémoire volatile (`MemorySaver`) | `PostgresSaver` / `SqliteSaver` persistant avec persistance de l'état HITL après redémarrage | P2 | **RÉSOLU** | `tests/reliability/test_checkpointer_persistence.py` |
| **REL-03** | Fiabilité | **P0 (Élevée)** | Absence de timeouts, retries, circuit breaker | Timeouts httpx/LLM, backoff exponentiel + jitter sur 429/5xx, circuit breaker, limite de récursion | P2 | **RÉSOLU** | `tests/reliability/test_resilience_and_killswitch.py` |
| **REL-04** | Fiabilité | **P1 (Moyenne)** | Masquage silencieux d'erreurs Tavily / fallback | Mode dégradé explicite avec flag `degraded=true`, tag Langfuse et blocage de publication automatique | P2 | **RÉSOLU** | `tests/reliability/test_degraded_mode.py` |
| **EDT-01** | Éditorial | **P1 (Élevée)** | Quality gate naïf par simple sous-chaîne | Véritable évaluateur : règles déterministes (longueur, liens, hashtags) + LLM Judge structuré | P3 | **À FAIRE** | `tests/unit/test_quality_evaluator_robust.py` |
| **EDT-02** | Éditorial | **P1 (Élevée)** | Absence de détection des doublons sur 90j | Calcul de similarité et indexation des publications des 90 derniers jours | P3 | **À FAIRE** | `tests/unit/test_duplicate_90d.py` |
| **EDT-03** | Éditorial | **P2 (Moyenne)** | Non-conformité AI Act (absence mention IA) | Inclusion obligatoire de la mention de transparence légale sur les contenus générés | P3 | **À FAIRE** | `tests/unit/test_ai_act_compliance.py` |
| **PUB-01** | Publication | **P0 (Critique)** | Crash désynchronisation temporelle UTC/naïve | Migration intégrale vers `datetime.now(timezone.utc)`, suppression des `utcnow()` | P2 | **RÉSOLU** | `tests/reliability/test_resilience_and_killswitch.py` |
| **PUB-02** | Publication | **P0 (Élevée)** | Concurrence dispatcher sans verrouillage | Transitions strictes de la machine à états et lock anti-double publication | P2 | **RÉSOLU** | `tests/reliability/test_state_machine_and_concurrency.py` |
| **PUB-03** | Publication | **P1 (Élevée)** | Connecteurs sociaux réels non branchés | **Reporté justifié (Hors périmètre prompt)** : Connecteurs sandbox conservés, mise en place de `SocialPublisher`, OAuth Token Vault et modèles | Social Ready | **À FAIRE** | `tests/unit/test_social_publisher_interface.py` |
| **PUB-04** | Publication | **P0 (Moyenne)** | Kill switch purement manuel / documentaire | Kill switch global (env var & DB) vérifié avant toute publication + plafond de fréquence | P2 | **RÉSOLU** | `tests/reliability/test_resilience_and_killswitch.py` |
| **COD-01** | Code | **P0 (Critique)** | Bug `repo.db.models` dans router strategy | Remplacement par `repo.db.query(MetricSnapshotModel)` | Pré | **RÉSOLU** | `audit/gemini-langfuse` |
| **COD-02** | Code | **P1 (Élevée)** | Dépendances non épinglées | Épinglage strict des versions et génération d'un lockfile | P4 | **À FAIRE** | `requirements.lock` |
| **COD-03** | Code | **P1 (Moyenne)** | 30 warnings pytest sur `datetime.utcnow()` | Remplacement systématique par `datetime.now(timezone.utc)` | P2 | **RÉSOLU** | Suite pytest à 0 warnings (54/54 pass) |
| **COD-04** | Code | **P2 (Faible)** | Clarification documentaire UI | Documentation mise à jour sur le frontend Vanilla moderne | P5 | **RÉSOLU** | `AUDIT.md` / `README.md` |
| **TST-01** | Tests | **P0 (Critique)** | Faux `passed = True` dans quality_evaluator | Réécriture de l'évaluateur de qualité avec vraies assertions | P3 | **À FAIRE** | `tests/evals/test_quality_evaluator.py` |
| **TST-02** | Tests | **P1 (Élevée)** | Évaluateur orphelin hors suite pytest | Intégration de l'évaluation dans la suite de tests automatisée `pytest` | P3 | **À FAIRE** | `tests/evals/test_eval_datasets.py` |
| **TST-03** | Tests | **P1 (Moyenne)** | Erreur pytest sans pythonpath | Configuration `pythonpath = ["."]` dans `pyproject.toml` | Pré | **RÉSOLU** | `audit/gemini-langfuse` |
| **CST-01** | Coûts | **P1 (Élevée)** | Absence de cache sémantique LLM | Interface de cache LLM (SQLite/Redis configurable), TTL et invalidation | P4 | **À FAIRE** | `tests/unit/test_llm_cache.py` |
| **CST-02** | Coûts | **P1 (Moyenne)** | Tarifs codés en dur dans le code | Fichier de configuration `config/pricing.json` avec source officielle et date | P4 | **À FAIRE** | `tests/unit/test_pricing_config.py` |
| **OBS-01** | Observabilité | **P0 (Critique)** | Tracing LangSmith/factice | Remplacement par SDK Langfuse officiel (`CallbackHandler`) | Pré | **RÉSOLU** | `audit/gemini-langfuse` |
| **OBS-02** | Observabilité | **P0 (Élevée)** | Absence de feedback corrélé aux traces | Enregistrement des scores QA et HITL via `create_score` Langfuse | Pré | **RÉSOLU** | `audit/gemini-langfuse` |
| **OPS-01** | Ops | **P1 (Élevée)** | Absence de pipeline CI/CD automatisé | `.github/workflows/ci.yml` (pytest, ruff, mypy, pip-audit, secret scan) | P5 | **À FAIRE** | `.github/workflows/ci.yml` |
| **OPS-02** | Ops | **P1 (Moyenne)** | Conteneur Docker exécuté en `root` | Dockerfile durci avec utilisateur non-root (`appuser`), HEALTHCHECK, image minimale | P1/P5 | **À FAIRE** | `infra/docker/Dockerfile.api` |

---

## 🎯 Plan de Déploiement par Phases

- **Phase 1 : Sécurité Applicative P0** (JWT, RBAC, BOLA/IDOR, Secret Scan, Surface API, Prompt Injection, Docker non-root).
- **Phase 2 : Fiabilité Système P0** (Checkpointer persistant, Machine à états, Idempotence, Mode dégradé, Résilience LLM, Kill switch, Horodatages UTC).
- **Phase 3 : Évaluation & Qualité** (Vrai Quality Gate, Détection doublons 90j, Dataset versionné, Intégration CI).
- **Phase 4 : Coûts, Cache & Observabilité** (Fichier pricing externe, Cache LLM, Routage par tâche, Versions épinglées, Correlation ID).
- **Phase 5 : Exploitation & Ops** (GitHub Actions CI, Endpoints `/health` & `/ready`, Logs JSON structurés, Runbooks).
- **Social Ready** : Interface `SocialPublisher`, Coffre de jetons OAuth abstrait et chiffré, Modèles de comptes connectés.
