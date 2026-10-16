# ADR 0011 : Clarification des Rôles des Graphes LangGraph et Élimination des Doublons d'Orchestration

**Date :** 2026-10-15  
**Statut :** Accepté  
**Contexte :**  
Le rapport d'audit a soulevé une ambiguïté quant à cinq graphes déclarés dans `langgraph.json` ou situés sous `services/orchestration/graphs/` (`publishing.py`, `quality_review.py`, `scheduling.py`, `approval.py`, `analytics.py`), signalant qu'ils ne constituent pas le chemin d'exécution primaire des routes de production de FastAPI ou des workers d'arrière-plan. Il existait un risque potentiel de divergence, de contournement des contrôles de sécurité ou de code mort (ex. `QualityReviewState`).

**Décisions d'Architecture :**

1. **Graphes de Production Primaires (API Gateway FastAPI) :**
   - `idea_research.py` : Invoqué par `/v1/ideas/generate` pour la recherche multi-angle d'idées éditoriales.
   - `content_production.py` : Invoqué par `/v1/content/generate`. Ce graphe intègre canoniquement le nœud de génération et le nœud `quality_gate_node` pour évaluer les variantes générées de manière déterministe et sémantique.
   - `strategy_insights.py` : Invoqué par `/v1/strategy/insights` pour la synthèse analytique et stratégique.

2. **Graphe de Contrôle Qualité (`quality_review.py`) :**
   - Rôle : Conservé comme point d'entrée unitaire pour exécuter isolément la grille de validation QA sans régénérer de contenu (ex. pour des benchmarks, des tests automatisés ou l'inspection dans LangGraph Studio).
   - Raccordement : Partage strictement le même nœud `quality_gate_node` et le même schéma d'état `ContentProductionState` que le pipeline de production. Le type d'état redondant et non utilisé `QualityReviewState` a été supprimé.

3. **Graphe d'Approbation HITL (`approval.py`) :**
   - Rôle : Graphe Human-in-the-Loop avec point d'interruption persistant (`interrupt_before=["human_review"]`), soutenu par un checkpointer durable (PostgresSaver / MemorySaver). Il permet l'inspection et la reprise d'approbation asynchrone via LangGraph Studio / LangGraph Cloud.
   - Cohérence avec l'API : Pour l'interface Web et l'API REST (`/v1/content/{id}/approve`), la persistance et la vérification cryptographique du hash de payload sont garanties par `repo.record_approval` et `tests/reliability/test_checkpointer_persistence.py`.

4. **Graphe de Publication (`publishing.py`) :**
   - Rôle : Strictement confiné aux scénarios de simulation et de test d'intégration sandbox (`sandbox_mode=True`).
   - Règle de Sécurité : Ce graphe ne doit **JAMAIS** se substituer au `PublisherWorker` (conforme à l'ADR 0003). La publication réelle en production nécessite la persistance dans PostgreSQL (`PublicationJobModel`), le verrouillage par le worker dédié et la signature infalsifiable de l'approbation humaine.

5. **Graphes de Programmation et Analytique (`scheduling.py`, `analytics.py`) :**
   - Rôle : Points d'entrée spécialisés pour LangGraph Studio et scripts de manipulation des contrats d'idempotence et de normalisation de métriques. Les routes API directes continuent de s'appuyer sur la persistance transactionnelle SQLAlchemy pour garantir la cohérence ACID.

**Conséquences :**
- Aucune route de production ne peut contourner les garde-fous de sécurité et d'idempotence.
- Le type mort `QualityReviewState` est éliminé sans impact.
- Les responsabilités entre l'API REST transactionnelle, les workers découplés et les graphes LangGraph sont rigoureusement documentées et testées.
