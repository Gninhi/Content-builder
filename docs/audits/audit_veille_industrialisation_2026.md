# RAPPORT D'AUDIT COMPLET ET PLAN D'INDUSTRIALISATION DE LA VEILLE
**Système :** ContentOps Harness (`Content-builder`)  
**Branche / Commit audité :** `main` @ `4dbcba9` (arbre de travail vérifié propre)  
**Rôle :** Architecte Logiciel Senior, Ingénieur IA (LangChain / LangGraph), Data Platform & DevSecOps  
**Date d'audit :** 14 Octobre 2026  
**Mode d'audit :** Lecture Seule stricte (Phase A)  

---

## A. SYNTHÈSE EXÉCUTIVE

L'audit approfondi de la chaîne **« Veille Technologique → Idéation → Production → Publication »** confirme que le projet dispose de briques fondamentales robustes en aval :
1. Un mécanisme de publication à garanties strictes (*At-Most-Once*, verrouillage `PUBLISHING`, transition sans rejeu `PUBLISH_UNKNOWN` lors des timeouts ambigus).
2. Un coffre-fort de jetons OAuth chiffré en AES-256-GCM avec AAD (`workspace_id`) et isolation multitenant étanche.
3. Une chaîne de validation humaine (HITL) obligatoire scellant le contenu exact avant programmation.
4. Un pipeline de conversion transactionnel et idempotent (`convert_signal_to_idea`) ancrant les idées sur les faits primaires des signaux.

Cependant, **la chaîne de veille amont est aujourd'hui incapable d'opérer comme un service de production autonome, récurrent et observable**. Trois défaillances systémiques empêchent son exploitation réelle :
1. **Absence complète de planificateur/worker de veille autonome :** Il n'existe aucun daemon, worker d'arrière-plan, tâche Cron ou file persistée pour la veille. La collecte ne s'exécute **que si un utilisateur clique manuellement sur le bouton « Collecter » dans l'interface web**.
2. **Déconnexion totale entre le catalogue des sources et la collecte :** Bien qu'une table `veille_sources` et des endpoints CRUD existent, le moteur de collecte `VeillePipeline.run_collection_cycle` **n'interroge jamais les sources configurées en base**. Il exécute des requêtes de recherche web statiques et des connecteurs hardcodés. Ajouter ou désactiver une source en base n'a strictement aucun effet sur la collecte.
3. **Fraîcheur factice et métriques approximatives :** Les connecteurs extraient la date de publication mais le pipeline la remplace par des constantes codées en dur (`days_old=7` ou `days_old=3`). De plus, le calcul de la richesse factuelle repose sur un simple test `any(c.isdigit())`, confondant n'importe quel chiffre avec une preuve statistique ou factuelle corroborée.

**Conclusion d'aptitude à la production :** **NON APTE À LA PRODUCTION** en l'état pour la collecte autonome quotidienne. L'industrialisation de la veille (Phase B) est indispensable pour transformer ce prototype réactif en service autonome gouverné.

---

## B. CARTOGRAPHIE DE L'ARCHITECTURE RÉELLE

### 1. Composants et Arborescence
- **API Backend :** FastAPI (`apps/api/main.py`), routeurs modulaires (`signals.py`, `ideation.py`, `production.py`, `publishing.py`, `auth.py`).
- **Orchestration LangGraph :**
  - Graphe Idéation : `services/orchestration/graphs/ideation.py` (`research.py`).
  - Graphe Production : `services/orchestration/graphs/editorial.py` (`production.py`, `quality.py`, `approval.py`).
- **Moteur de Veille :** `services/orchestration/veille/pipeline.py`.
- **Connecteurs de Données :**
  - Moteurs Web : `WebSearchTool` (`packages/tools/web_search.py` - SerpAPI + fallback DuckDuckGo).
  - Connecteurs Officiels : `OfficialDataConnectors` (`packages/tools/data_connectors.py` - arXiv, GitHub, HackerNews, HuggingFace, RSS).
- **Planification & Workers :**
  - `services/scheduler/dispatcher.py` : gère uniquement les jobs de publication dus (`PublicationJobModel`). **Aucun composant de veille.**
  - `services/publisher/worker.py` : worker de publication LinkedIn et X.
- **Persistance & Données (PostgreSQL / SQLite) :**
  - Modèles SQLAlchemy (`infra/db/models.py`) : `VeilleSourceModel`, `SignalModel`, `IdeaModel`, `ContentBriefModel`, `ContentPackageModel`, `PublicationJobModel`.
  - Cache HTTP SQLite : `search_cache.sqlite` pour `WebSearchTool`.
- **Frontend :** React 18 / TypeScript / Vite (`apps/web/src/screens/VeilleScreen.tsx`).

### 2. Matrice d'État des Composants Critiques
| Composant | Implémenté | Dans le flux réel | Configuré | Persisté | Testé | Validé en prod |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `VeilleSourceModel` (CRUD) | OUI | NON (déconnecté du pipeline) | OUI | OUI | OUI | NON |
| `VeillePipeline.run_collection_cycle` | OUI | Manuel (clic UI uniquement) | OUI | OUI | OUI | NON |
| `OfficialDataConnectors` | OUI | Partiel (hardcodé, ignore DB) | OUI | NON | OUI | NON |
| Scheduler Veille Quotidien | **NON** | **NON** | **NON** | **NON** | **NON** | **NON** |
| Déduplication 90 jours (URL/Titre) | OUI | OUI | OUI | OUI | OUI | OUI |
| Conversion Signal $\to$ Idée | OUI | OUI | OUI | OUI | OUI | OUI |
| Validation HITL Publication | OUI | OUI | OUI | OUI | OUI | OUI |
| Worker Publication At-Most-Once | OUI | OUI | OUI | OUI | OUI | OUI |

---

## C. MATRICE DES CONSTATS D'AUDIT

### Constat C1 — Absence de Scheduler Autonome pour la Veille (P0 - Critique)
- **Domaine :** Automatisation / SRE
- **Statut :** Confirmé
- **Fichier :** `services/scheduler/dispatcher.py` & `apps/api/routers/signals.py:113-130`
- **Description :** Il n'existe aucun composant planificateur, thread d'arrière-plan ou worker asynchrone exécutant périodiquement `VeillePipeline.run_collection_cycle`. Le dispatcher actuel ne gère que les publications de posts (`PublicationJobModel`).
- **Preuve technique :** Aucun appel à `run_collection_cycle` dans toute l'arborescence `services/scheduler/` ni dans `apps/api/main.py`. L'unique point d'entrée est l'endpoint HTTP `POST /v1/signals/collect`. Si aucun utilisateur ne clique, aucune veille n'a lieu.
- **Cause racine :** Le développement s'est focalisé sur la validation interactive de la veille plutôt que sur un worker headless.
- **Conséquence :** Perte de l'avantage concurrentiel d'un radar continu ; rupture de service si l'équipe n'ouvre pas le dashboard.
- **Correctif envisagé :** Créer un modèle `VeilleScheduleModel` / table de jobs de veille persistée, et un daemon/worker de veille autonome qui interroge PostgreSQL avec verrouillage atomique (`SKIP LOCKED`) et respect du fuseau horaire du workspace (`Europe/Paris` par défaut).
- **Effort :** Moyen (2-3 jours) | **Risques :** Concurrence si plusieurs instances Uvicorn tournent.

### Constat C2 — Catalogue des Sources Déconnecté du Pipeline Réel (P0 - Critique)
- **Domaine :** Data Platform / Architecture
- **Statut :** Confirmé
- **Fichier :** `services/orchestration/veille/pipeline.py:171-248`
- **Description :** La méthode `_collect_official_connectors` appelle directement en dur arXiv, HuggingFace, GitHub Releases et HackerNews sans jamais interroger la table `veille_sources`. De même, la recherche web utilise une liste statique de requêtes prédéfinies.
- **Preuve technique :** Dans `pipeline.py`, `repo.list_veille_sources` n'est jamais appelé. Les sources configurées par l'Owner via `POST /v1/signals/sources` restent inertes en base.
- **Cause racine :** Câblage rapide initial de connecteurs de démonstration sans raccordement dynamique à l'ORM.
- **Conséquence :** L'utilisateur configure des flux RSS ou des sources prioritaires dans l'interface, mais le système ne les interroge jamais.
- **Correctif :** Faire en sorte que `VeillePipeline.run_collection_cycle` charge toutes les sources actives (`is_active=True`) du workspace depuis `repo.list_veille_sources` et dispatch dynamiquement selon `source_type` (rss, web, arxiv, github, hackernews).
- **Effort :** Moyen (1-2 jours) | **Risques :** Gestion des timeouts par source défaillante.

### Constat C3 — Écrasement des Dates de Publication et Fraîcheur Simulée (P1 - Élevé)
- **Domaine :** Intégrité des Données / Algorithme
- **Statut :** Confirmé
- **Fichier :** `services/orchestration/veille/pipeline.py:205, 237, 281`
- **Description :** Bien que `OfficialDataConnectors` extraie la véritable date de publication (`published_date`), `VeillePipeline` attribue une valeur fixe `days_old = 3` pour les connecteurs et `days_old = 7` pour les résultats de recherche web lors de l'appel à `compute_qualification_score`.
- **Preuve technique :** Ligne 205: `days_old=3`, Ligne 281: `days_old=7`.
- **Cause racine :** Remplacement d'une gestion complète de parsing ISO/RFC par une constante pour satisfaire les tests unitaires initiaux.
- **Conséquence :** Le score de fraîcheur est complètement biaisé ; un article publié il y a 2 ans via un moteur de recherche reçoit le même score de fraîcheur qu'un article d'hier.
- **Correctif :** Calculer le delta réel `(now_utc - published_datetime).days` avec parsing robuste des dates, et pénaliser les dates absentes sans inventer de valeur.
- **Effort :** Faible (0.5 jour).

### Constat C4 — Détection Naïve des Faits Chiffrés (P1 - Élevé)
- **Domaine :** Intégrité Factuelle / NLP
- **Statut :** Confirmé
- **Fichier :** `services/orchestration/veille/pipeline.py:273`
- **Description :** La condition `has_metrics = any(char.isdigit() for char in sanitized_snippet)` est utilisée pour déclarer qu'un signal contient des faits chiffrés et lui attribuer des points de densité factuelle.
- **Preuve technique :** N'importe quel texte contenant "2026", "v1" ou "top 10" est considéré comme contenant des mesures factuelles vérifiées.
- **Cause racine :** Heuristique primitive non affinée.
- **Conséquence :** Surévaluation de signaux marketing superficiels au détriment de réelles analyses quantitatives.
- **Correctif :** Remplacer le test unaire par une expression régulière extrayant de véritables métriques chiffrées (pourcentages, devises, ordres de grandeur, benchmarks $x\times$) et associer explicitement le fait à son extrait source.
- **Effort :** Faible (0.5 jour).

### Constat C5 — Absence de Traçabilité des Erreurs et de Santé des Sources (P1 - Élevé)
- **Domaine :** Observabilité / SRE
- **Statut :** Confirmé
- **Fichier :** `services/orchestration/veille/pipeline.py:192-234`
- **Description :** Lorsqu'un connecteur échoue, l'exception est interceptée par un `logger.warning`, mais `VeilleSourceModel.health_status` n'est jamais mis à jour (`ERROR`, `FAILING`), `last_polled_at` reste nul, et l'erreur n'est pas persistée en base.
- **Preuve technique :** La table `veille_sources` a des colonnes `health_status`, `error_message`, `last_polled_at`, mais aucune mise à jour n'a lieu lors d'un cycle.
- **Cause racine :** Omission de l'enregistrement de l'état d'exécution au niveau de l'ORM.
- **Conséquence :** L'utilisateur ou l'opérateur ne sait pas si une source silencieuse est normale (aucun nouvel article) ou en panne (timeout/erreur HTTP).
- **Correctif :** Mettre à jour `last_polled_at`, `health_status` (`OK`, `DEGRADED`, `ERROR`) et `error_message` pour chaque source après chaque tentative.
- **Effort :** Faible (0.5 jour).

### Constat C6 — Mode Démo Activé par Défaut dans le Frontend (P2 - Moyen)
- **Domaine :** UX / Gouvernance
- **Statut :** Confirmé
- **Fichier :** `apps/web/src/screens/VeilleScreen.tsx:54`
- **Description :** `const [isDemoMode, setIsDemoMode] = useState<boolean>(true);` active le mode démo par défaut à chaque chargement de l'écran.
- **Preuve technique :** Si l'utilisateur clique directement sur "Collecter les Signaux", il injecte des signaux synthétiques sans interrogation web, sauf s'il pense à basculer le toggle.
- **Cause racine :** Confort de développement conservé en production.
- **Conséquence :** Risque de pollution de la base avec des signaux de démo pour un utilisateur inattentif.
- **Correctif :** Passer `isDemoMode` à `false` par défaut en production, afficher un bandeau d'avertissement très clair quand le mode démo est actif, et interdire la conversion de signaux démo en idées de production sans confirmation.
- **Effort :** Faible (0.5 jour).

---

## D. MATRICE D'ÉCARTS (EXIGENCES vs CODE vs TESTS)

| Exigence Produit | Code Existant | Suite de Tests | Comportement Validé | Écart Constaté |
| :--- | :--- | :--- | :--- | :--- |
| **Collecte récurrente automatique** | Aucun scheduler pour la veille | Aucun test de scheduler de veille | Uniquement déclenchement manuel HTTP | **Écart P0 : Scheduler inexistant** |
| **Catalogue dynamique de sources** | `VeilleSourceModel` + API CRUD | Tests unitaires du modèle seuls | Non utilisé par le moteur de collecte | **Écart P0 : Sources découplées** |
| **Dates de publication réelles** | Remplacé par `days_old = 3 / 7` | Vérifie le calcul avec dates passées en argument | Calcul fictif lors de la collecte réelle | **Écart P1 : Fraîcheur simulée** |
| **Déduplication robuste 90j** | SHA-256 URL canonique + Titre | Test `test_t11_temporal_deduplication_90_days` valide | Conforme et atomique | **Conforme** |
| **Conversion Signal $\to$ Idée** | Endpoint transactionnel idempotent | Test `test_veille_to_ideation_conversion` valide | Conforme avec ref de preuves | **Conforme** |
| **Contrôle de publication At-Most-Once** | `PublisherWorker` avec verrou SQL | Test `test_t7_worker_concurrency_locking` valide | Conforme | **Conforme** |
| **Validation HITL obligatoire** | Statut `APPROVED` requis avant publication | Test `test_social_publishers` valide | Conforme | **Conforme** |

---

## E. DIAGNOSTIC APPROFONDI DE LA COLLECTE QUOTIDIENNE

La collecte actuelle n'est **ni automatisée, ni observable** pour les raisons d'architecture suivantes :
1. **Couplage synchrone au cycle de vie HTTP :** `POST /v1/signals/collect` effectue la collecte de façon synchrone dans la requête FastAPI. Si la requête timeout (navigateur fermé ou proxy timeout), le traitement peut être interrompu.
2. **Absence d'entité de suivi de collecte (`VeilleRunModel`) :** Il n'existe pas de table traçant les exécutions globales de collecte (quand elle a démarré, quand elle s'est achevée, combien de sources ont été scannées, combien d'erreurs ont été rencontrées, quel volume de signaux nouveaux a été inséré).
3. **Absence de daemon d'arrière-plan :** Seul le `PublisherWorker` dispose d'une boucle périodique (`services/publisher/worker.py`), mais il est spécialisé dans l'envoi de posts.
4. **Gestion de fuseau horaire orpheline :** Bien que `WorkspaceModel` possède un champ `timezone` (ex. `Europe/Paris`), aucun mécanisme ne l'utilise pour calculer l'heure d'exécution quotidienne (ex. 07h00 heure locale).

---

## F. PLAN DE REMÉDIATION PRIORISÉ (PHASE B)

Le plan est découpé en **4 lots cohérents** minimisant l'impact sur l'existant :

### Lot 1 — Raccordement du Catalogue de Sources et Fraîcheur Réelle (P1)
- **Objectif :** Rendre le moteur de collecte dynamique et factuellement exact.
- **Actions :**
  1. Modifier `VeillePipeline.run_collection_cycle` pour charger les sources actives (`repo.list_veille_sources(workspace_id, is_active=True)`).
  2. Router chaque source vers son connecteur approprié (`RSS`, `ArXiv`, `GitHub`, `HackerNews`, `WebSearch`).
  3. Parser les vraies dates de publication (`published_date`) et calculer le delta exact en jours.
  4. Mettre à jour `last_polled_at` et `health_status` sur `VeilleSourceModel`.
  5. Améliorer la détection des métriques chiffrées (regex au lieu de `isdigit()`).

### Lot 2 — Architecture du Planificateur Autonome de Veille (P0)
- **Objectif :** Déclencher la veille quotidiennement de manière autonome, persistée et idempotente.
- **Actions :**
  1. Ajouter un modèle `VeilleRunModel` traçant chaque exécution de veille (id, workspace_id, status, sources_contacted, signals_discovered, errors, started_at, completed_at).
  2. Implémenter `VeilleSchedulerWorker` :
     - Tourne en tâche de fond indépendante (ou cron léger géré au niveau du conteneur/service).
     - Vérifie pour chaque workspace si une collecte est due (en fonction du fuseau horaire du workspace et de l'heure programmée, par défaut 07:00).
     - Verrouillage transactionnel PostgreSQL (`FOR UPDATE SKIP LOCKED`) pour empêcher les doubles exécutions multi-instances.
  3. Exposer dans l'API l'état de la dernière et de la prochaine collecte (`GET /v1/signals/schedule-status`).

### Lot 3 — Observabilité et Sécurisation Frontend (P2)
- **Objectif :** Rendre l'interface fidèle et transparente.
- **Actions :**
  1. Mettre le mode Démo à `false` par défaut dans `VeilleScreen.tsx`.
  2. Afficher les métadonnées de santé des sources dans la modale de gouvernance des sources (dernière date de poll, statut OK/ERREUR).
  3. Afficher sur l'écran Veille la date du dernier cycle réussi et l'état des sources.

### Lot 4 — Validation E2E et Tests de Non-Régression
- **Objectif :** Prouver la conformité sans dépendance externe incontrôlée.
- **Actions :**
  1. Tests unitaires de raccordement des sources dynamiques avec mocks étanches.
  2. Tests de concurrence sur le `VeilleSchedulerWorker` (double worker ne déclenchant pas de double collecte).
  3. Tests de reprise après crash / panne transitoire d'une source.

---

## G. DÉCISIONS D'ARCHITECTURE SOUMISES À ARBITRAGE (POINT D'ARRÊT)

Avant d'entamer la Phase B, les choix d'architecture suivants sont soumis à votre validation :

1. **Architecture du Scheduler de Veille :**
   - **Option A (Recommandée) : Worker autonome PostgreSQL + loop asyncio (similaire à `PublisherWorker`).**
     *Avantages :* Zéro nouvelle dépendance d'infrastructure (pas besoin de Redis ou RabbitMQ). Verrouillage simple en base via `FOR UPDATE SKIP LOCKED`. Idéal pour l'échelle actuelle et la cohérence avec le reste du repo.
   - **Option B : Celery Beat / Redis.**
     *Inconvénients :* Introduit Redis, alourdit le Compose, ajoute un point de panne et des coûts opérationnels inutiles au stade actuel.
2. **Fréquence et Heure d'Exécution :**
   - Proposition : Collecte quotidienne planifiée à **07h00 heure locale du workspace** (fuseau configuré, ex. `Europe/Paris`), avec possibilité de déclenchement manuel ponctuel pour l'Owner/Editor.
3. **Comportement en cas de panne partielle de source :**
   - Proposition : Tolérance aux pannes (*Fail-soft*) : si 1 source sur 10 échoue (ex: GitHub rate limit), la collecte continue pour les 9 autres. La source défaillante passe en `health_status='ERROR'` avec le message d'erreur consigné, sans faire échouer l'ensemble du cycle.
