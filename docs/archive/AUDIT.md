# 🛡️ Rapport d'Audit Exhaustif — ContentOps Harness

**Date de l'audit :** 06 Octobre 2026  
**Auditeur :** Ingénieur Senior Architecture Agentique & Sécurité Applicative  
**Branche git de travail :** `audit/gemini-langfuse`  
**Statut :** Phase 1 & 2 terminées (Lecture seule, code inchangé avant validation)  

---

## Executive Summary

Le projet **ContentOps Harness** est conçu comme un système d'exploitation éditorial gouverné pour les réseaux sociaux combinant FastAPI, LangGraph, PostgreSQL (avec fallback SQLite) et une interface web. 

L'audit approfondi révèle que **si les intentions architecturales (gouvernance déterministe, machine à états stricte, vérification par empreinte cryptographique SHA-256) sont solides sur le papier, l'implémentation actuelle comporte des défaillances majeures et des simulations de surface :**

1. **Sécurité critique :** 
   - Aucun fichier `.gitignore` n'existait initialement, laissant le fichier `.env` réel exposé à tout commit intempestif.
   - Le système d'authentification et de contrôle d'accès (RBAC) repose aveuglément sur des en-têtes HTTP non signés (`X-User-Role`, `X-Workspace-Id`) avec des valeurs par défaut accordant les privilèges complets `Owner` à n'importe quel appel anonyme.
   - Les requêtes SQL dans plusieurs routers manquent d'isolation par `workspace_id` (vulnérabilités BOLA / IDOR).
2. **Simulation du moteur LLM :** 
   - Bien que des templates de prompts existent dans `packages/prompts/registry.py` et que `langchain-nvidia-ai-endpoints` soit listé dans `requirements.txt`, **aucun appel LLM réel n'est effectué dans les nœuds LangGraph** (`research.py`, `production.py`, `insights.py`). Tout le texte est généré à partir de chaînes statiques codées en dur.
3. **Observabilité inexistante :** 
   - `packages/observability/tracing.py` ne se connecte à aucun service de télémétrie : il génère un simple dictionnaire local contenant un UUID aléatoire. Langfuse n'est pas installé ni configuré.
4. **Perte d'état & Fragilité de production :** 
   - Le graphe d'approbation humaine (`approval.py`) utilise un `MemorySaver` en mémoire vive. En cas de redémarrage du conteneur ou de passage en multi-workers, tous les checkpoints de validation humaine sont perdus.
   - Les connecteurs réseaux sociaux (`linkedin.py`, `x_twitter.py`) forcent le mode sandbox et ne contiennent aucun code d'appel API réel ni gestion des jetons OAuth.
5. **Évaluations trompeuses :** 
   - Le script d'évaluation des 80 cas (`evals/evaluators/quality_evaluator.py`) force artificiellement `passed = True` sur les cas critiques (idempotence, contrôle de rôles, accès cross-tenant, indisponibilité d'outils).

---

## 🗺️ Phase 1 : Reconnaissance & Cartographie

### 1.1 Arborescence Globale

```text
DeepAgent/ (ContentOps Harness)
├── .env                         # [CRITIQUE] Fichier réel présent à la racine
├── .env.example                 # Modèle de configuration incomplet
├── .gitignore                   # [CRITIQUE] Absent à l'origine (créé pour l'audit)
├── README.md                    # Documentation générale (annonce faussement Next.js)
├── langgraph.json               # Manifeste de graphes LangGraph
├── pyproject.toml               # Configuration packaging & pytest
├── requirements.txt             # Dépendances Python (versions non épinglées)
├── apps/
│   ├── api/                     # Passerelle FastAPI
│   │   ├── dependencies.py      # RBAC & injection de session (vulnérable)
│   │   ├── main.py              # Point d'entrée de l'API & seeding
│   │   └── routers/             # 9 routers REST (sources, ideas, briefs, content, etc.)
│   └── web/                     # Frontend client (Vanilla HTML/JS/CSS, pas de Next.js)
│       ├── app.js               # Contrôleur frontend (appels API vers ws_default)
│       ├── index.html           # Structure de la SPA
│       └── style.css            # Styles personnalisés
├── packages/
│   ├── connectors/              # Connecteurs d'intégration
│   │   ├── search/tavily.py     # Recherche web (fallbacks simulés silencieux)
│   │   ├── social/              # Connecteurs LinkedIn & X (simulés)
│   │   ├── sources/             # Extracteur web et normaliseur RSS
│   │   └── storage/local.py     # Stockage de fichiers locaux
│   ├── contracts/               # Schémas Pydantic et événements de domaine
│   ├── domain/                  # Machine à états (ContentStateMachine) et idempotence
│   ├── observability/           # Censure PII, métriques et pseudo-tracing
│   └── prompts/                 # Registre de templates de prompts (PROMPTS_V1)
├── services/
│   ├── orchestration/           # 8 graphes LangGraph et nœuds d'agents
│   │   ├── graphs/              # Définition des StateGraph (idea, production, approval...)
│   │   ├── nodes/               # Implémentation des nœuds de graphe
│   │   └── state/base.py        # TypedDict d'états
│   ├── publisher/worker.py      # Worker déterministe de publication
│   └── scheduler/dispatcher.py  # Dispatcher de file d'attente (polling)
├── infra/
│   ├── db/                      # Modèles SQLAlchemy, session et repository
│   ├── docker/                  # Dockerfile.api et docker-compose.yml
│   └── migrations/              # DDL SQL (initial_schema.sql, rls_policies.sql)
├── evals/
│   ├── datasets/                # eval_dataset_80.json (80 cas de test)
│   └── evaluators/              # quality_evaluator.py (script d'évaluation)
└── tests/                       # Suite pytest (18 tests unitaires/intégration)
```

### 1.2 Points d'Entrée & Dépendances

- **Point d'entrée API :** `apps/api/main.py` démarrant une application FastAPI avec initialisation de base SQLite/PostgreSQL et amorçage d'un profil de marque par défaut (`ws_default`).
- **Point d'entrée Agentique :** `langgraph.json` déclarant 7 graphes vers `services.orchestration.graphs.*`.
- **Dépendances :**
  - Spécifiées avec des versions non épinglées (`>=`) dans `requirements.txt` et `pyproject.toml`.
  - Présence de dépendances historiques obsolètes (`langchain-nvidia-ai-endpoints>=0.1.0`).
  - Absence de `langchain-google-genai` et `langfuse`.

### 1.3 Architecture & Flux de Données

```text
       +-------------------------------------------------------------------------+
       |                         Client Web (apps/web/)                          |
       |             Vanilla JS (fetch) sans authentification obligatoire        |
       +------------------------------------+------------------------------------+
                                            | HTTP (X-User-Role: Owner par défaut)
                                            v
+---------------------------------------------------------------------------------------+
|                               FastAPI (apps/api/)                                     |
|  Dependencies: get_current_user (authentification basée sur headers clients non signés) |
+-------------------------------------------+-------------------------------------------+
                                            |
         +----------------------------------+----------------------------------+
         |                                                                     |
         v                                                                     v
+-----------------------------+                               +---------------------------------+
|  LangGraph Orchestration    |                               | Base de Données (infra/db/)     |
|  - idea_research_graph      |                               | - PostgreSQL / SQLite           |
|  - content_production_graph |                               | - SQLAlchemy Session / Repo     |
|  - quality_review_graph     |                               | - Tables: workspaces, ideas,    |
|  - approval_graph (Memory)  |<=============================>|   briefs, variants, approvals,  |
|  - scheduling_graph         |                               |   jobs, published_posts         |
|  - strategy_insights_graph  |                               +---------------------------------+
|  * Nœuds : mock statiques   |                                                ^
+-----------------------------+                                                |
         |                                                                     |
         v                                                                     |
+-------------------------------------------------------------+                |
|  Services Découplés (services/)                             |                |
|  - scheduler/dispatcher.py (Polling périodique SQLite/PG)   +----------------+
|  - publisher/worker.py (Vérification hash SHA-256)          |
|  - packages/connectors/social/ (LinkedIn & X simulés)       |
+-------------------------------------------------------------+
```

---

## 🔍 Phase 2 : Tableau Récapitulatif des Findings

| ID | Axe | Sévérité | Titre du Problème | Localisation | Effort |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **SEC-01** | 1. Sécurité | **Critique** | Clés API réelles en clair sur disque et absence initiale de `.gitignore` | `.env:11,17,25`, `.gitignore` | S |
| **SEC-02** | 1. Sécurité | **Critique** | Authentification et RBAC factices via en-têtes HTTP non vérifiés (Bypass total) | `apps/api/dependencies.py:14-23` | M |
| **SEC-03** | 1. Sécurité | **Élevée** | Défense anti-injection de prompt basée sur une regex naïve facilement contournable | `packages/connectors/sources/web_extractor.py:13-29` | M |
| **SEC-04** | 1. Sécurité | **Élevée** | Absence de contrôle d'accès multi-tenant (BOLA / IDOR sur `workspace_id`) | `apps/api/routers/ideas.py:22`, `calendar.py:14-24` | M |
| **SEC-05** | 1. Sécurité | **Élevée** | Consultation non authentifiée des profils de marque sensibles | `apps/api/routers/workspaces.py:57-65` | S |
| **SEC-06** | 1. Sécurité | **Moyenne** | Ingestion de sources sans vérification SSRF ni extraction HTTP réelle | `apps/api/routers/sources.py:17` | M |
| **SEC-07** | 1. Sécurité | **Moyenne** | Mot de passe PostgreSQL par défaut codé en dur dans docker-compose | `infra/docker/docker-compose.yml:9,34` | S |
| **REL-01** | 2. Fiabilité | **Critique** | Nœuds d'agents entièrement mockés sans appel LLM ni gestion d'erreurs | `services/orchestration/nodes/production.py:25-72`, `research.py:45-77` | L |
| **REL-02** | 2. Fiabilité | **Critique** | Checkpointer éphémère `MemorySaver` pour les interruptions humaines HITL | `services/orchestration/graphs/approval.py:22-26` | M |
| **REL-03** | 2. Fiabilité | **Élevée** | Absence de timeouts, limites d'itérations et de circuit-breaker sur LangGraph | `services/orchestration/graphs/*.py` | M |
| **REL-04** | 2. Fiabilité | **Moyenne** | Masquage silencieux des exceptions Tavily et génération de données fictives | `packages/connectors/search/tavily.py:37-38` | S |
| **EDT-01** | 3. Éditorial | **Élevée** | Quality Gate déterministe par simple recherche textuelle de sous-chaînes | `services/orchestration/nodes/quality.py:68-76` | M |
| **EDT-02** | 3. Éditorial | **Élevée** | Absence de détection des doublons sur 90 jours glissants | `services/orchestration/nodes/research.py:60-77` | M |
| **EDT-03** | 3. Éditorial | **Moyenne** | Non-conformité AI Act et RGPD (absence de mention obligatoire de génération IA) | `services/orchestration/nodes/production.py:79-100` | S |
| **PUB-01** | 4. Publication | **Critique** | Crash potentiel et désynchronisation temporelle (`datetime.utcnow()` vs aware) | `services/scheduler/dispatcher.py:19-28` | S |
| **PUB-02** | 4. Publication | **Élevée** | Absence de verrouillage concurrent (`SKIP LOCKED`) dans le dispatcher | `services/scheduler/dispatcher.py:20-28` | M |
| **PUB-03** | 4. Publication | **Élevée** | Connecteurs LinkedIn et X en sandbox forcée sans implémentation d'API réelle | `packages/connectors/social/linkedin.py:28-36`, `x_twitter.py:30-38` | L |
| **PUB-04** | 4. Publication | **Moyenne** | Kill-switch d'urgence purement documentaire et manuel | `docs/runbooks/kill_switch.md:7-22` | M |
| **COD-01** | 5. Qualité code | **Critique** | Bug bloquant `repo.db.models` rendant les métriques de stratégie inopérantes | `apps/api/routers/strategy.py:22` | S |
| **COD-02** | 5. Qualité code | **Élevée** | Dépendances non épinglées (`>=`) dans `requirements.txt` et `pyproject.toml` | `requirements.txt:2-30`, `pyproject.toml:13-30` | S |
| **COD-03** | 5. Qualité code | **Moyenne** | Utilisation intensive de `datetime.utcnow()` déprécié en Python 3.12+ | Partout dans le projet (30 warnings pytest) | M |
| **COD-04** | 5. Qualité code | **Faible** | Tromperie documentaire : l'UI annoncée comme Next.js est en Vanilla HTML/JS | `README.md:3,81`, `apps/web/` | S |
| **TST-01** | 6. Tests | **Critique** | Suite d'évaluation biaisée avec assertions court-circuitées `passed = True` | `evals/evaluators/quality_evaluator.py:86-100` | M |
| **TST-02** | 6. Tests | **Élevée** | Évaluateur de qualité orphelin et exclu de la suite automatisée `pytest` | `evals/evaluators/quality_evaluator.py:1-122` | S |
| **TST-03** | 6. Tests | **Moyenne** | Absence de configuration `pythonpath = ["."]` provoquant l'échec de pytest | `pyproject.toml:38-41` | S |
| **CST-01** | 7. Coûts/Perf | **Élevée** | Absence de système de cache sémantique pour les appels LLM | `services/orchestration/` | M |
| **CST-02** | 7. Coûts/Perf | **Moyenne** | Modèle de calcul de coûts obsolète basé sur des tarifs génériques fixes | `packages/observability/metrics.py:10-23` | S |
| **OBS-01** | 8. Observabilité | **Critique** | Tracing totalement factice (aucun envoi réseau ni intégration Langfuse) | `packages/observability/tracing.py:13-29` | M |
| **OBS-02** | 8. Observabilité | **Élevée** | Absence de scores d'évaluation et de feedback humain corrélés aux traces | `apps/api/routers/content.py:65-72` | M |
| **OPS-01** | 9. Exploitation | **Élevée** | Absence de pipeline CI/CD automatisé | Répertoire `.github/workflows/` inexistant | M |
| **OPS-02** | 9. Exploitation | **Moyenne** | Conteneur Docker exécuté en tant que `root` | `infra/docker/Dockerfile.api:1-21` | S |

---

## 🔬 Détail des Findings par Axe

### Axe 1 : Sécurité Applicative

#### [SEC-01] Critique — Clés API réelles en clair sur disque et absence initiale de `.gitignore`
- **Localisation :** `.env:11,17,25` et racine du projet.
- **Preuve :** Le fichier `.env` contenait des clés API opérationnelles en clair, et aucun fichier `.gitignore` n'existait dans le répertoire de travail.
- **Impact :** Tout `git add .` ou initialisation de dépôt risque d'exposer immédiatement des secrets de production sur un serveur git public ou partagé.
- **Correctif :** Conserver le `.gitignore` créé (ignorant strictement `.env`, `.venv`, `.db`), révoquer immédiatement les clés exposées et basculer sur un gestionnaire de secrets sécurisé.
- **Effort :** S

#### [SEC-02] Critique — Authentification et RBAC factices via en-têtes HTTP non vérifiés
- **Localisation :** `apps/api/dependencies.py:14-23`
- **Preuve :**
  ```python
  def get_current_user(
      x_user_id: str = Header("user_owner", alias="X-User-Id"),
      x_user_role: str = Header("Owner", alias="X-User-Role"),
      x_workspace_id: str = Header("ws_default", alias="X-Workspace-Id"),
  ) -> UserContext:
  ```
- **Impact :** Tout appelant HTTP peut s'attribuer le rôle `Owner` sans token JWT, sans signature cryptographique et sans mot de passe. Pire, un appel sans aucun en-tête reçoit par défaut le rôle `Owner` !
- **Correctif :** Implémenter une authentification standard (Bearer JWT ou API Key hashée) vérifiée en base ou via Supabase Auth/OAuth.
- **Effort :** M

#### [SEC-03] Élevée — Défense anti-injection de prompt basée sur une regex naïve
- **Localisation :** `packages/connectors/sources/web_extractor.py:13-29`
- **Preuve :** Le filtrage repose sur 5 expressions régulières en anglais (`ignore previous instructions`, `system: you are`).
- **Impact :** Des attaques en français, en encodage base64, en leetspeak ou avec des formulations indirectes contournent trivialement ce filtre et peuvent détourner le LLM lors de l'ingestion de sources web non fiables.
- **Correctif :** Isoler le contenu externe non fiable dans des délimiteurs stricts XML/Markdown et utiliser un modèle de classification de sécurité (Guardrails ou Gemini Safety Settings).
- **Effort :** M

#### [SEC-04] Élevée — Absence de contrôle d'accès multi-tenant (BOLA / IDOR)
- **Localisation :** `apps/api/routers/ideas.py:22`, `apps/api/routers/calendar.py:14-24`, `apps/api/routers/analytics.py:32`
- **Preuve :** Dans `calendar.py`, la requête `repo.db.query(PublicationJobModel).all()` retourne l'intégralité des publications de tous les workspaces sans filtrer par `workspace_id`.
- **Impact :** Fuite de données inter-entreprises (cross-tenant data leakage) permettant à un client de consulter les idées et plannings d'un autre client.
- **Correctif :** Filtrer systématiquement chaque requête par le `workspace_id` validé du token utilisateur et activer les politiques RLS (`infra/migrations/002_rls_policies.sql`).
- **Effort :** M

#### [SEC-05] Élevée — Consultation non authentifiée des profils de marque sensibles
- **Localisation :** `apps/api/routers/workspaces.py:57-65`
- **Preuve :** L'endpoint `GET /v1/brand-profiles/{workspace_id}` ne comporte aucune dépendance `Depends(require_roles(...))` ni vérification d'utilisateur.
- **Impact :** N'importe quel internaute peut aspirer la ligne éditoriale, la cible, la voix et les sujets interdits d'une entreprise.
- **Correctif :** Ajouter la dépendance `user: UserContext = Depends(require_roles("Owner", "Editor", "Analyst"))`.
- **Effort :** S

---

### Axe 2 : Fiabilité de l'Agent

#### [REL-01] Critique — Nœuds d'agents entièrement mockés sans appel LLM réel
- **Localisation :** `services/orchestration/nodes/production.py:25-72`, `research.py:45-77`, `insights.py:17-48`
- **Preuve :** Dans `production.py`, les variantes LinkedIn et X sont des chaînes Python statiques interpolées avec des formats fixes :
  ```python
  hook = f"Pourquoi 80% des projets IA échouent sans gouvernance éditoriale claire ?"
  ```
- **Impact :** Le système ne génère en réalité aucun contenu dynamique ; il simule le comportement d'un agent.
- **Correctif :** Intégrer `ChatGoogleGenerativeAI` (`gemini-3.8-flash`) avec structured outputs (Pydantic) et binding aux prompts versionnés de `packages/prompts/registry.py`.
- **Effort :** L

#### [REL-02] Critique — Checkpointer éphémère `MemorySaver` pour les interruptions HITL
- **Localisation :** `services/orchestration/graphs/approval.py:22-26`
- **Preuve :**
  ```python
  checkpointer = MemorySaver()
  graph = builder.compile(checkpointer=checkpointer, interrupt_before=["human_review"])
  ```
- **Impact :** `MemorySaver` conserve l'état des threads en RAM. En cas de redémarrage de l'API, de déploiement d'une nouvelle version ou de plusieurs réplicas de conteneurs, les validations humaines en attente sont perdues.
- **Correctif :** Remplacer par `PostgresSaver` (ou `SqliteSaver` en local) relié à la base de données persistante.
- **Effort :** M

#### [REL-03] Élevée — Absence de timeouts et de limites d'itérations sur les graphes
- **Localisation :** `services/orchestration/graphs/*.py`
- **Preuve :** Aucune configuration de `recursion_limit` ou de timeout httpx/asyncio lors de l'invocation des graphes.
- **Impact :** Risque de blocage indéfini des workers en cas de blocage d'un appel réseau ou de boucle de réécriture infinie (`REWRITE_REQUESTED` ➔ `DRAFT`).
- **Correctif :** Définir un `recursion_limit=15` et un `timeout` explicite dans la configuration d'invocation de chaque graphe.
- **Effort :** M

---

### Axe 3 : Garde-fous Éditoriaux

#### [EDT-01] Élevée — Quality Gate purement déterministe par recherche de sous-chaînes
- **Localisation :** `services/orchestration/nodes/quality.py:68-76`
- **Preuve :**
  ```python
  for topic in prohibited_topics:
      if topic.lower() in body_lower:
          violations.append(topic)
  ```
- **Impact :** Une formulation synonyme ou métaphorique d'un sujet interdit échappe totalement à la détection. De même, aucun contrôle de cohérence stylistique n'est opéré par un LLM-as-a-judge.
- **Correctif :** Combiner la validation déterministe (longueur, caractères) avec une vérification sémantique par LLM rapide (`gemini-3.8-flash`) appliquant le template `quality_gate`.
- **Effort :** M

#### [EDT-02] Élevée — Absence de détection des doublons sur 90 jours glissants
- **Localisation :** `services/orchestration/nodes/research.py:60-77`
- **Preuve :** Les idées sont générées sans interroger l'historique des publications des 90 derniers jours en base de données.
- **Impact :** Risque de saturer l'audience avec des sujets ou angles identiques publiés quelques jours auparavant.
- **Correctif :** Injecter les titres et angles des 90 derniers jours dans le contexte d'état du graphe de recherche pour déduplication sémantique.
- **Effort :** M

#### [EDT-03] Moyenne — Non-conformité AI Act et transparence IA
- **Localisation :** `services/orchestration/nodes/production.py:79-100`
- **Preuve :** Aucun champ de métadonnées n'indique l'obligation de mentionner l'assistance IA sur les plateformes où cela est requis par la législation européenne (AI Act).
- **Correctif :** Ajouter une balise et un flag `ai_generated_disclosure_required` dans le contrat `ContentVariant`.
- **Effort :** S

---

### Axe 4 : Planification et Publication

#### [PUB-01] Critique — Risque de crash temporel (`datetime.utcnow()` vs aware)
- **Localisation :** `services/scheduler/dispatcher.py:19-28`
- **Preuve :**
  ```python
  now = datetime.utcnow()
  due_jobs = self.db.query(PublicationJobModel).filter(
      PublicationJobModel.scheduled_at <= now, ...
  )
  ```
- **Impact :** Si `scheduled_at` stocké en base est converti en datetime timezone-aware (UTC), la comparaison en Python lève une exception non gérée `TypeError: can't compare offset-naive and offset-aware datetimes`, stoppant tout le dispatcher.
- **Correctif :** Utiliser `datetime.now(timezone.utc)` de manière homogène dans tout le codebase.
- **Effort :** S

#### [PUB-02] Élevée — Absence de verrouillage concurrent (`SKIP LOCKED`)
- **Localisation :** `services/scheduler/dispatcher.py:20-28`
- **Preuve :** Polling direct sans clause `with_for_update(skip_locked=True)`.
- **Impact :** Si plusieurs instances du scheduler tournent simultanément (haute disponibilité ou conteneurs multiples), elles récupèrent le même job au même moment et déclenchent des doubles publications.
- **Correctif :** Ajouter un verrou pessimiste transactionnel sur la ligne de job lors de la sélection.
- **Effort :** M

#### [PUB-03] Élevée — Connecteurs LinkedIn et X en sandbox forcée sans API réelle
- **Localisation :** `packages/connectors/social/linkedin.py:28-36`, `x_twitter.py:30-38`
- **Preuve :** La méthode `publish()` génère des UUIDs aléatoires et retourne une simulation sans aucun appel HTTP vers LinkedIn API v2 ou X API v2.
- **Impact :** Impossibilité totale de publier réellement en production.
- **Correctif :** Implémenter le mode production avec client HTTP OAuth (gestion des tokens, rafraîchissement automatique et backoff exponentiel sur 429).
- **Effort :** L

---

### Axe 5 : Qualité du Code & Architecture

#### [COD-01] Critique — Bug bloquant `repo.db.models` rendant les métriques inopérantes
- **Localisation :** `apps/api/routers/strategy.py:22`
- **Preuve :**
  ```python
  snapshots_models = repo.db.query(repo.db.models.MetricSnapshotModel).all() if hasattr(repo.db, 'models') else []
  ```
- **Impact :** `repo.db` est une instance de `sqlalchemy.orm.Session`, qui ne possède pas d'attribut `models`. L'expression retourne TOUJOURS une liste vide `[]`. Les analyses stratégiques n'ont jamais accès aux métriques réelles !
- **Correctif :** Remplacer par `repo.db.query(MetricSnapshotModel).all()`.
- **Effort :** S

#### [COD-02] Élevée — Dépendances non épinglées dans les fichiers de configuration
- **Localisation :** `requirements.txt:2-30`, `pyproject.toml:13-30`
- **Preuve :** Toutes les dépendances utilisent `>=` (`fastapi>=0.110.0`, `langgraph>=0.2.0`).
- **Impact :** Risque de rupture de build inattendue lors de la mise à jour automatique d'une dépendance mineure ou majeure.
- **Correctif :** Épingler les versions exactes (`==`) ou utiliser un lockfile (`uv.lock` ou `poetry.lock`).
- **Effort :** S

#### [COD-03] Moyenne — Utilisation de `datetime.utcnow()` déprécié en Python 3.12+
- **Localisation :** Présent dans 14 fichiers du projet (infra/db, domain, packages, services).
- **Preuve :** Déclenche 30 `DeprecationWarning` à chaque exécution de la suite de tests.
- **Correctif :** Remplacer systématiquement par `datetime.now(timezone.utc)`.
- **Effort :** M

---

### Axe 6 : Tests & Évaluations

#### [TST-01] Critique — Suite d'évaluation biaisée avec assertions court-circuitées `passed = True`
- **Localisation :** `evals/evaluators/quality_evaluator.py:86-100`
- **Preuve :**
  ```python
  elif action == "retry_publish_same_idempotency_key":
      passed = True
  elif action == "cross_tenant_access":
      passed = True
  elif action == "role_permission_check":
      passed = True
  elif family == "Cas d'échec/outils indisponibles":
      passed = True
  ```
- **Impact :** Le rapport d'évaluation affiche un taux de succès trompeur (100%) alors que les tests les plus critiques en matière de sécurité et d'idempotence ne sont même pas exécutés.
- **Correctif :** Remplacer ces conditions par de véritables assertions sur la base de données et la machine à états.
- **Effort :** M

#### [TST-02] Élevée — Évaluateur de qualité orphelin et exclu de `pytest`
- **Localisation :** `evals/evaluators/quality_evaluator.py`
- **Preuve :** Aucun test dans `tests/` n'appelle `QualityEvaluator().run_evaluations()`.
- **Impact :** Les 80 cas d'évaluation ne sont jamais exécutés dans le cycle de développement normal.
- **Correctif :** Créer un test `tests/evals/test_quality_evaluator.py` intégrant le dataset dans la suite de tests automatisée.
- **Effort :** S

---

### Axe 7 : Coûts, Performances & Observabilité

#### [OBS-01] Critique — Tracing totalement factice sans connexion réseau
- **Localisation :** `packages/observability/tracing.py:13-29`
- **Preuve :**
  ```python
  @classmethod
  def get_run_metadata(cls, workspace_id, graph_name, node_name, extra_tags=None):
      run_id = str(uuid.uuid4())
      return {
          "run_id": run_id,
          "workspace_id": workspace_id,
          "graph": graph_name,
          "node": node_name, ...
      }
  ```
- **Impact :** Zéro visibilité en production. Aucune trace de cycle, aucun span par sous-agent, aucune métrique de latence ou de coût n'est envoyée à Langfuse.
- **Correctif :** Intégrer nativement le SDK Langfuse (`langfuse.callback.CallbackHandler` pour LangChain/LangGraph) et instrumenter les spans par nœud et par outil.
- **Effort :** M

#### [OBS-02] Élevée — Absence de scores d'évaluation et de feedback humain rattachés aux traces
- **Localisation :** `apps/api/routers/content.py:65-72`, `approval.py`
- **Preuve :** Les décisions humaines (approbation, rejet, réécriture) et les scores de QA ne sont pas remontés à la trace Langfuse correspondante via l'API de scores (`langfuse.score()`).
- **Impact :** Impossibilité d'analyser la qualité des générations et de corréler les rejets humains aux versions de prompts dans le dashboard d'observabilité.
- **Correctif :** Lier le `trace_id` stocké en base à l'enregistrement de l'approbation et poster un score d'évaluation dans Langfuse lors de la décision HITL.
- **Effort :** M

---

## ⚡ Quick Wins Recommandés (Moins de 2h de dev)

1. **Correction du bug `repo.db.models` (COD-01) :** Remplacer par `repo.db.query(MetricSnapshotModel).all()` dans `apps/api/routers/strategy.py:22`.
2. **Ajout de `pythonpath = ["."]` dans `pyproject.toml` (TST-03) :** Permet d'exécuter `pytest` directement sans préfixe `PYTHONPATH=.`.
3. **Protection de l'endpoint sensible de profil de marque (SEC-05) :** Ajouter le guard RBAC sur `GET /v1/brand-profiles/{workspace_id}`.
4. **Correction du type de date naïve (PUB-01) :** Harmoniser vers `datetime.now(timezone.utc)`.
5. **Nettoyage des faux scores dans l'évaluateur (TST-01) :** Supprimer les `passed = True` aveugles.

---

## 📅 Plan de Remédiation Priorisé

### Phase A : Migration Cible & Observabilité (Prévue dans la mission)
1. **Migration vers Gemini 3.8 Flash :**
   - Installer `langchain-google-genai`.
   - Remplacer `langchain-nvidia-ai-endpoints` par `ChatGoogleGenerativeAI(model="gemini-3.8-flash")`.
   - Brancher les appels LLM réels dans les nœuds LangGraph (`research.py`, `production.py`, `insights.py`) avec sorties structurées Pydantic.
2. **Intégration complète de l'observabilité Langfuse :**
   - Retirer toute dépendance ou variable superflue.
   - Installer `langfuse` et configurer le callback handler pour LangGraph.
   - Instrumenter chaque nœud, enregistrer les tokens, latences, tags et scores de validation humaine.
3. **Mise à jour complète du `.env.example` :**
   - Documenter les variables requises : `GOOGLE_API_KEY`, `GEMINI_MODEL=gemini-3.8-flash`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`.

### Phase B : Sécurisation & Contrôle d'Accès
1. Remplacer le faux RBAC par une authentification par clé d'API ou jeton JWT.
2. Appliquer les filtres d'isolation multi-tenant `workspace_id` sur toutes les requêtes SQL (BOLA/IDOR).
3. Remplacer le `MemorySaver` éphémère par un `SqliteSaver` / `PostgresSaver` persistant.

### Phase C : Fiabilisation de la Publication & Tests
1. Implémenter les connecteurs sociaux réels avec gestion OAuth et rate-limiting.
2. Ajouter le verrouillage concurrent `SKIP LOCKED` dans le dispatcher.
3. Intégrer les 80 cas d'évaluation dans `pytest` avec des assertions réelles non court-circuitées.
