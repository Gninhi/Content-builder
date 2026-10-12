# Banque de Requêtes Ciblées & Stratégie de Rotation

Afin de maximiser la pertinence et la fraîcheur des signaux tout en respectant les quotas des moteurs de recherche (DuckDuckGo, SerpAPI), ContentOps Harness exploite une **banque de requêtes ciblées avec rotation cyclique**.

---

## 1. Principes Directeurs
- **Opérateurs Booléens & Ciblage de Domaine :** Utilisation intensive des opérateurs `site:`, `filetype:`, `"..."` pour cibler les sources primaires institutionnelles et techniques.
- **Rotation Cyclique Temporelle :** À chaque exécution, une sous-sélection de requêtes est tirée au sort ou ordonnancée par date de dernière exécution pour éviter la saturation d'un mot-clé identique.
- **Budget de Requêtes :** Suivi strict du nombre d'appels par heure (stocké dans le cache SQLite) pour prévenir tout blocage d'IP ou dépassement de coût.

---

## 2. Répertoire des Requêtes par Axe

### Axe 1 : Intelligence Artificielle & Systèmes Multi-Agents (`ia`)
```text
1. "multi-agent systems" benchmarks reasoning models filetype:pdf site:arxiv.org
2. "AI Act" compliance technical requirements site:europa.eu
3. "context window" degradation long-running agent production
4. "reasoning tokens" latency cost tradeoff enterprise deployment
5. "agentic workflows" human in the loop failure modes site:github.com
6. "LLM security" prompt injection defense agent sandbox
7. "sovereign AI" France Europe infrastructure open-source
```

### Axe 2 : Frameworks & Écosystèmes Outils (`frameworks`)
```text
1. "LangGraph" state management postgres checkpointer migration
2. "FastAPI" Pydantic v2 performance async database pooling
3. "TypeScript" SDK resilience rate limiter circuit breaker
4. "Playwright" headless browser stealth automation scraping defense
5. "SQLite" WAL mode concurrency high throughput API
6. "Docker" multi-stage build Python lightweight secure container
7. "uv" Python package manager dependency resolution speed
```

### Axe 3 : Évolution des Métiers & Organisation Tech (`metiers`)
```text
1. "IA générative" transformation ingénieurs logiciels France site:france-strategie.fr
2. "développeur IA" compétences compétences émergentes 2026 site:syntec-numerique.fr
3. "gouvernance algorithmique" DSI comité de direction risques
4. "product engineer" vs "software engineer" impact assistants IA
5. "CNIL" conformité intelligence artificielle déploiement salarié
6. "tech leads" transition vers orchestrateurs de systèmes agentiques
7. "sécurité des flux agentiques" nouveaux profils cybersécurité
```

---

## 3. Algorithme de Rotation et Sélection
1. **Tri par Ancienneté :** Le pipeline ordonne les requêtes selon leur horodatage de dernière interrogation.
2. **Filtrage par Axe Actif :** Si l'utilisateur cible un axe spécifique (ex. `metiers`), seules les requêtes de cet axe sont exécutées.
3. **Plafond Dynamique :** Le paramètre `limit_per_axis` (défaut : 3) borne le nombre de requêtes simultanées par cycle de veille.
4. **Mise en Cache Déterministe :** Les réponses de requêtes identiques sont mises en cache pour 24 heures afin de minimiser le trafic réseau et garantir la reproductibilité.
