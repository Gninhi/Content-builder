# Rapport d'Audit Indépendant V2 — ContentOps Harness

**Auteur :** Ingénieur Principal (Staff) Backend / Sécurité / Fiabilité  
**Date d'exécution :** 2026-10-07  
**Branche auditée :** `feat/social-prod` (dérivée de `fix/hardening`, HEAD `0f3a884`)  
**Périmètre :** Code source complet (`apps/`, `infra/`, `packages/`, `services/`, `evals/`, `tests/`, `config/`)  
**Principe directeur :** *Ne rien croire sans preuve exécutable. Fail closed.*

---

## 1. Contrôle Indépendant des 10 Affirmations d'Architecture

| # | Affirmation ciblée | Statut mesuré | Preuve factuelle & Fichier:Ligne |
|---|---|---|---|
| 1 | **Verrou anti-double publication** au niveau base de données (multi-workers) | **INFIRMÉ** | Dans `services/publisher/worker.py:52-54`, la vérification repose sur un simple test mémoire `job.status == ContentStatus.PUBLISHING.value`. Aucun `with_for_update()` ni verrou de ligne DB / Redis n'est posé. En cas d'appels simultanés sur 2 workers Uvicorn, les deux lisent `SCHEDULED` et envoient deux requêtes aux API réelles. |
| 2 | **Valeur par défaut de `ENV`** = production & protection absolue de `/dev-token` | **INFIRMÉ** | Dans `apps/api/routers/auth.py:21`, le code indique : `env = os.getenv("ENV", "dev").lower()`. La valeur par défaut est explicitement **`dev`**. En l'absence de configuration dans l'environnement (constaté dans `BASELINE.md:105`), `/v1/auth/dev-token` est actif et permet à n'importe quel attaquant non authentifié de générer des JWT Owner/Editor sur tout workspace. |
| 3 | **JWT durci** : algos restreints, rejet `alg=none`, clé forte sans défaut, rotation | **INFIRMÉ en partie** | Confirmé : `packages/security/auth.py:66` force `algorithms=["HS256"]`, ce qui rejette `alg=none`.<br>Infirmé : Ligne 23 contient une clé secrète par défaut codée en dur (`"contentops-hardened-jwt-secret-key-must-be-rotated-in-production-2026"`). Aucun `kid` dans le header, aucun mécanisme de rotation, aucun support asymétrique ou JWKS. |
| 4 | **Rate limiting** : stockage partagé, proxy de confiance, clé par workspace | **INFIRMÉ en partie** | Confirmé : `packages/security/limiter.py:20` calcule bien `ws:{workspace_id}` pour les JWT authentifiés.<br>Infirmé : `limiter = Limiter(...)` n'a aucun `storage_uri` et utilise le stockage mémoire interne de SlowAPI (`memory://`). Les compteurs ne sont pas partagés entre workers. Aucun middleware de proxy de confiance n'est configuré. |
| 5 | **Pricing Gemini 3.8 Flash** conforme aux tarifs officiels actuels | **INFIRMÉ** | Dans `config/pricing.json:8-13`, `gemini-3.8-flash` est configuré à `0.075` (input/1M) et `0.30` (output/1M). La documentation officielle Google AI ([ai.google.dev/pricing](https://ai.google.dev/pricing), vérifiée le 2026-10-07) stipule **$0.75 / 1M input** et **$3.75 / 1M output**. Les coûts sont sous-estimés par un facteur 10x à 12.5x. |
| 6 | **Cache LLM** : isolation stricte par workspace (zéro fuite multi-tenant) | **INFIRMÉ** | Dans `services/orchestration/nodes/research.py:46-52`, `cache_payload` n'inclut que `topic`, `pillars`, `audience`, et `target_count`. L'attribut `workspace_id` est omis. Le cache sert les mêmes idées générées d'un workspace A à un workspace B. |
| 7 | **Coffre OAuth** : nonces uniques, versionnement `kid`, fail-closed sur clé absente | **INFIRMÉ en partie** | Confirmé : `packages/connectors/social/vault.py:105` génère un nonce aléatoire de 12 octets (`os.urandom(12)`).<br>Infirmé : Ligne 72 utilise une clé de secours par défaut en clair. Ligne 77 utilise un dictionnaire en mémoire (`self._storage`) non persisté en base. Aucun `kid` n'est associé au blob chiffré, interdisant toute rotation sans perte des jetons existants. |
| 8 | **Logs et traces Langfuse** sans fuite de jetons (LinkedIn, X, Google, Bearer) | **INFIRMÉ** | Dans `packages/observability/pii.py:10-19`, `PIIRedactor` masque les emails, téléphones, clés Google (`AIza`) et Langfuse, mais ne dispose d'aucun motif pour les jetons LinkedIn (`AQU...`), les tokens d'accès/refresh X, ni les codes d'autorisation OAuth et code_verifiers PKCE. |
| 9 | **Migrations de base de données** versionnées (Alembic) et Mypy | **INFIRMÉ** | Aucun fichier `alembic.ini` ni dossier de migrations n'existe dans le dépôt. `infra/db/database.py:45-64` exécute `create_all` et des `ALTER TABLE` SQLite/SQL artisanaux. Mypy échoue avec 96 erreurs de typage sur 10 fichiers. |
| 10 | **Transparence IA (EU AI Act)** : déclenchement effectif dans la chaîne | **INFIRMÉ** | Dans `services/orchestration/nodes/quality.py`, le `quality_gate_node` n'invoque pas la règle de transparence IA. La règle n'est présente que dans `evals/evaluators/quality_evaluator.py:143` avec `require_ai_disclosure: bool = False` par défaut. Aucun commutateur éditorial ni politique de workspace ne permet de l'activer dans le pipeline opérationnel. |

---

## 2. Contrôle Approfondi de Sécurité, Concurrence et Résilience

### 2.1 Sécurité API (OWASP API Top 10)
1. **BOLA / IDOR Massif via `user.role.lower() != "owner"` (CRITIQUE) :**
   - Fichiers impactés :
     - `apps/api/routers/publications.py:51,72`
     - `apps/api/routers/content.py:26`
     - `apps/api/routers/workspaces.py:63`
     - `apps/api/routers/analytics.py:18`
   - Mécanisme : Le code vérifie `if resource.workspace_id != user.workspace_id and user.role.lower() != "owner":`. Tout utilisateur disposant du rôle `Owner` sur son propre espace (client A) contourne la clause et peut lire, modifier, publier et supprimer les ressources du client B.
2. **Mass Assignment / Injection de Tenant sur les routes POST (ÉLEVÉE) :**
   - `apps/api/routers/briefs.py:16` : `repo.create_brief(workspace_id=req.workspace_id, ...)` prend le `workspace_id` du body HTTP sans le comparer au token JWT.
   - `apps/api/routers/ideas.py:22-57` : Utilise `req.workspace_id` sans validation de correspondance avec `user.workspace_id`.
   - `apps/api/routers/sources.py:23-27` : Accepte le `workspace_id` arbitraire fourni dans la requête.
3. **Endpoint non authentifié exposant des données sensibles (ÉLEVÉE) :**
   - `apps/api/routers/sources.py:48-53` : `GET /v1/sources` ne requiert aucune dépendance d'authentification (`require_roles` ou `get_current_user`). N'importe quel internaute peut lister les sources, URLs et faits extraits de n'importe quel workspace via `?workspace_id=...`.
4. **Endpoint dev-token ouvert par défaut (CRITIQUE) :**
   - `apps/api/routers/auth.py:21` : Si la variable d'environnement `ENV` est absente (ce qui est le cas dans l'état initial), l'application s'initialise en mode `dev` et autorise la fabrication illimitée de tokens JWT.

### 2.2 Concurrence et Intégrité des Données
1. **Course critique (Race Condition) sur la publication (CRITIQUE) :**
   - Deux workers exécutant `PublisherWorker.execute_job(job_id)` en simultané passent tous les deux les vérifications initiales avant que le premier commit de statut `PUBLISHING` ne soit acté. Sur des bases relationnelles concurrentes ou avec plusieurs processus Uvicorn/Celery, une double publication sur les réseaux sociaux réels se produit.
2. **Absence de persistance et de transactions ACID pour les jetons OAuth (CRITIQUE) :**
   - `EncryptedOAuthTokenVault` stocke les jetons dans `self._storage: Dict[str, str] = {}`. Un redémarrage du conteneur détruit toutes les sessions OAuth des utilisateurs. Aucun modèle de base de données relationnelle ne matérialise les jetons chiffrés.
3. **Absence de clé d'idempotence native sur les API LinkedIn et X :**
   - LinkedIn Posts API et X API v2 Tweets n'acceptent pas de header standard `Idempotency-Key`. En cas de timeout réseau après envoi de la requête HTTP, l'état devient indéterminé (`PUBLISH_UNKNOWN`). Le pipeline doit enregistrer `PUBLISHING` avant l'appel et ne jamais réessayer sans réconciliation.

### 2.3 Résilience et Injection de Pannes
1. **Panne LLM et circuit breaker :**
   - `services/orchestration/llm.py` implémente un fallback dégradé, mais si le circuit breaker s'ouvre, le contenu dégradé généré ne doit JAMAIS être auto-publié sans révision humaine explicite. Dans `services/publisher/worker.py:93-100`, un verrou existe mais s'appuie sur `variant.media_spec.get("degraded")` qui peut être éludé si l'attribut est mal propagé par l'orchestrateur.
2. **Repli SlowAPI sur mémoire locale :**
   - En cas d'indisponibilité ou absence de configuration Redis, SlowAPI tombe silencieusement sur la mémoire du worker local, rendant le rate-limiting inopérant contre les attaques distribuées.

---

## 3. Matrice Exhaustive des Findings

| Identifiant | Domaine | Sévérité | Description du problème | Fichier:Ligne | Correctif requis | Effort |
|---|---|---|---|---|---|---|
| **SEC-V2-01** | Authentification | **Critique** | `ENV` par défaut à `dev`, laissant `/v1/auth/dev-token` accessible sans configuration | `apps/api/routers/auth.py:21` | Forcer `ENV="production"` par défaut (fail-closed). Bloquer strictement `/dev-token` sauf si `ENV=dev` explicitement défini. | S |
| **SEC-V2-02** | Autorisation | **Critique** | BOLA / IDOR inter-workspaces via contournement `user.role.lower() != "owner"` | `apps/api/routers/publications.py:51,72`<br>`apps/api/routers/content.py:26`<br>`apps/api/routers/workspaces.py:63`<br>`apps/api/routers/analytics.py:18` | Supprimer l'exception Owner. L'isolation par `user.workspace_id` doit être absolue pour tous les rôles. | M |
| **SEC-V2-03** | Authentification | **Critique** | Clé secrète de signature JWT par défaut en dur et absence de rotation | `packages/security/auth.py:23` | Exiger un secret fort au démarrage (fail-closed sans fallback). Implémenter support `kid` et validation stricte. | M |
| **SEC-V2-04** | Coffre OAuth | **Critique** | Coffre de jetons volatile en mémoire, clé maîtresse par défaut en dur, pas de `kid` | `packages/connectors/social/vault.py:72,77` | Persistance en DB de `ConnectedSocialAccountModel`, clé maîtresse obligatoire sans défaut, tagging avec `kid` pour rotation. | L |
| **CONC-V2-01** | Concurrence | **Critique** | Verrou anti-double publication purement en mémoire et sujet aux race conditions | `services/publisher/worker.py:37-54` | Verrou transactionnel en base (`SELECT ... FOR UPDATE` ou mise à jour atomique `UPDATE ... WHERE status='SCHEDULED'`). | M |
| **SEC-V2-05** | Isolation Multi-Tenant | **Élevée** | Clé de cache LLM partagée entre workspaces pour des sujets identiques | `services/orchestration/nodes/research.py:46-52` | Intégrer obligatoirement `workspace_id` dans `cache_payload` et la clé de cache SHA-256. | S |
| **SEC-V2-06** | Autorisation | **Élevée** | Routes `POST /v1/briefs`, `POST /v1/ideas/research` et `POST /v1/sources` acceptant un `workspace_id` arbitraire | `apps/api/routers/briefs.py:16`<br>`apps/api/routers/ideas.py:22`<br>`apps/api/routers/sources.py:23` | Remplacer ou valider strictement le `workspace_id` par celui extrait du token JWT authentifié. | S |
| **SEC-V2-07** | Authentification | **Élevée** | Route `GET /v1/sources` complètement ouverte sans authentification | `apps/api/routers/sources.py:48-53` | Ajouter la dépendance `require_roles(...)` et filtrer strictement sur `user.workspace_id`. | S |
| **DATA-V2-01** | Intégrité Données | **Élevée** | Absence de système de migrations versionnées (Alembic) | `infra/db/database.py:45-64` | Mettre en place Alembic avec script initial et migration réversible (upgrade/downgrade testés). | M |
| **FIN-V2-01** | FinOps | **Élevée** | Sous-estimation tarifaire de 10x à 12.5x dans `pricing.json` pour Gemini 3.8 Flash | `config/pricing.json:8-13` | Corriger les tarifs selon [ai.google.dev/pricing](https://ai.google.dev/pricing) ($0.75 input, $3.75 output par 1M tokens). | S |
| **SEC-V2-08** | Résilience | **Élevée** | Rate limiting en mémoire par défaut (`memory://`) et vulnérable au spoofing IP | `packages/security/limiter.py:23-28` | Configuration d'un stockage Redis partagé avec fallback sécurisé, et gestion des proxys de confiance. | M |
| **OBS-V2-01** | Observabilité | **Moyenne** | Masquage PII incomplet : motifs OAuth LinkedIn, X, PKCE et jetons absents | `packages/observability/pii.py:10-19` | Étendre les expressions régulières de censure aux motifs de jetons et codes d'autorisation OAuth. | S |
| **EDT-V2-01** | Conformité Légale | **Moyenne** | Règle de transparence IA (EU AI Act) absente du pipeline de production réel | `services/orchestration/nodes/quality.py:29-97` | Intégrer la règle dans le `quality_gate_node` avec déclenchement configurable selon la politique éditoriale. | S |
| **MOCK-V2-01** | Intégrité Données | **Moyenne** | Métriques factices codées en dur renvoyées par l'API analytics si aucun snapshot | `apps/api/routers/analytics.py:59-63` | Renvoyer 0 pour les métriques sans données réelles au lieu de valeurs trompeuses (12500, 610, etc.). | S |
| **CODE-V2-01** | Qualité de Code | **Moyenne** | 96 erreurs de typage Mypy sur 10 fichiers bloquant l'intégration continue | `infra/db/repository.py`, etc. | Corriger toutes les annotations et les coercions de types SQLAlchemy/Pydantic/LangGraph. | M |
| **ROLE-V2-01** | Sécurité | **Faible** | Rôle `"Analyst"` invoqué dans `apps/api/routers/strategy.py:17` mais absent de l'énumération `Role` | `apps/api/routers/strategy.py:17` | Aligner les rôles sur `Role.OWNER`, `Role.EDITOR`, `Role.VIEWER`. | S |

---

## 4. Tests de Reproduction des Failles Critiques et Élevées (Phase 2 Portal)

Une suite dédiée de tests d'attaque (`tests/security/test_reproduction_attacks.py`) a été exécutée pour valider empiriquement la présence de chaque vulnérabilité avant tout correctif.

```bash
pytest tests/security/test_reproduction_attacks.py -v
```

### Résultats d'Exécution :
- `test_reproduce_sec_v2_01_dev_token_default_env` : **ÉCHEC CONFIRMÉ** (`AssertionError: 200 == 403`). L'absence de variable `ENV` a permis la génération sans restriction d'un jeton JWT pour `user_id='attacker'` sur `ws_victim`.
- `test_reproduce_sec_v2_02_owner_cross_tenant_bola` : **ÉCHEC CONFIRMÉ** (`AssertionError: 200 == 403`). L'attaquant avec le rôle `Owner` dans son propre workspace a accédé au profil de marque confidentiel de `ws_victim` en raison de la clause permissive `user.role.lower() != 'owner'`.
- `test_reproduce_sec_v2_06_mass_assignment_brief_creation` : **ÉCHEC CONFIRMÉ** (`AssertionError: 200 == 403`). L'attaquant authentifié sur `ws_attacker` a pu injecter un brief éditorial directement dans `ws_victim` via le corps JSON non validé.
- `test_reproduce_sec_v2_07_unauthenticated_sources_leak` : **ÉCHEC CONFIRMÉ** (`AssertionError: 200 in (401, 403)`). La route `GET /v1/sources` a renvoyé les données sans exiger de jeton d'authentification.
- `test_reproduce_sec_v2_05_cross_tenant_cache_leak` : **ÉCHEC CONFIRMÉ** (`AssertionError: Cross-tenant cache leak detected in idea_research_node!`). Des idées confidentielles générées pour `ws_victim` ont été servies directement à `ws_attacker` depuis le cache sans isolation.
- `test_reproduce_fin_v2_01_pricing_underestimation` : **ÉCHEC CONFIRMÉ** (`AssertionError: 0.075 == 0.75`). Le fichier `config/pricing.json` configure `gemini-3.8-flash` à 10x moins que son tarif officiel réel.

**Portail Phase 2 : VALIDÉ (100% des tests de reproduction ciblés échouent contre le code non remédié).**

---

## 5. Conclusion de l'Audit V2

L'audit préliminaire et le contrôle approfondi confirment que plusieurs composants critiques nécessitent une remédiation immédiate avant tout raccordement aux API réelles de LinkedIn et de X. En particulier :
1. Les verrous de publication et de rafraîchissement doivent être déplacés en base de données relationnelle (`SELECT ... FOR UPDATE`).
2. L'isolation inter-workspaces (BOLA/IDOR) doit être sanctuarisée en supprimant le bypass d'autorité réservé au rôle `Owner`.
3. Le stockage des jetons OAuth doit être persisté en base de données de manière chiffrée (AES-GCM 256 bits avec AAD lié au workspace et identifiant de clé `kid`).
4. L'environnement doit être basculé en fail-closed (`ENV=production`).
