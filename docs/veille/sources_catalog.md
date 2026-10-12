# Catalogue Curé des Sources Officielles de Veille

Ce catalogue recense les sources validées et intégrées par défaut dans le pipeline de veille de ContentOps Harness.

---

## 1. Axe IA & Systèmes Multi-Agents (`ia`)

| Nom de la Source | Type | Niveau Confiance | URL / Endpoint | Rationale & Pertinence |
| :--- | :--- | :---: | :--- | :--- |
| **ArXiv AI Preprints** | `arxiv` | **A** | `https://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.CL` | Recherche de pointe, architectures de modèles, benchmarks de raisonnement. |
| **Hugging Face Daily Papers** | `web` | **A** | `https://huggingface.co/papers` | Papiers les plus débattus et reproduits par la communauté open-source. |
| **EU AI Act Official Monitor** | `web` | **A** | `https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai` | Cadre réglementaire contraignant pour les entreprises européennes. |
| **Inria AI Research Hub** | `rss` | **A** | `https://www.inria.fr/fr/actualites/rss` | Recherche souveraine française et européenne sur les agents et l'éthique IA. |
| **NVIDIA Developer Blog** | `web` | **B** | `https://developer.nvidia.com/blog` | Optimisation de l'inférence, microservices NIM, architectures d'accélération. |
| **The Batch (DeepLearning.AI)** | `rss` | **B** | `https://www.deeplearning.ai/the-batch/` | Synthèses éditoriales d'experts sur l'adoption en entreprise. |

---

## 2. Axe Frameworks & Écosystèmes Outils (`frameworks`)

| Nom de la Source | Type | Niveau Confiance | URL / Endpoint | Rationale & Pertinence |
| :--- | :--- | :---: | :--- | :--- |
| **GitHub Trending (Python & TS)** | `github` | **A** | `https://api.github.com/search/repositories` | Adoption réelle, stars et vélocité des bibliothèques émergentes. |
| **LangChain & LangGraph Releases** | `github` | **A** | `https://github.com/langchain-ai/langgraph/releases` | Nouveautés sur l'orchestration avec état et la persistance agentique. |
| **FastAPI Releases & Announcements** | `github` | **A** | `https://github.com/tiangolo/fastapi/releases` | Évolutions du standard des API asynchrones en Python. |
| **Pydantic Official Updates** | `web` | **A** | `https://docs.pydantic.dev` | Typage strict et validation de schémas structurés pour les LLM. |
| **Hacker News Tech Frontpage** | `hackernews` | **C** | `https://hacker-news.firebaseio.com/v0/topstories.json` | Retours d'expérience bruts de développeurs et signaux faibles. |

---

## 3. Axe Évolution des Métiers de la Tech (`metiers`)

| Nom de la Source | Type | Niveau Confiance | URL / Endpoint | Rationale & Pertinence |
| :--- | :--- | :---: | :--- | :--- |
| **CNIL Intelligence Artificielle** | `web` | **A** | `https://www.cnil.fr/fr/intelligence-artificielle` | Recommandations juridiques et conformité RGPD sur les données d'entraînement. |
| **France Stratégie Tech & Emploi** | `web` | **A** | `https://www.france-strategie.fr` | Analyses macroéconomiques sur l'impact de l'automatisation sur les métiers. |
| **ANSSI Alertes & Guides** | `web` | **A** | `https://www.cert.ssi.gouv.fr/feed/` | Sécurité opérationnelle, gestion des vulnérabilités logicielles. |
| **Syntec Numérique Observatoire** | `web` | **B** | `https://syntec-numerique.fr` | Baromètres de recrutement et transformation des profils ESN / Tech en France. |
| **IEEE Spectrum Careers & Computing** | `rss` | **B** | `https://spectrum.ieee.org/rss/computing` | Tendances de fond sur la mutation du rôle des ingénieurs logiciels. |

---

## 4. Politique de Gouvernance des Sources
1. **Accès et Modification :** L'ajout, l'édition ou la suppression d'une source est strictement réservé au rôle **Owner** via l'endpoint `/v1/signals/sources`.
2. **Seed Initial :** Les espaces de travail peuvent initialiser automatiquement ce catalogue via le bouton d'injection de l'interface ou `POST /v1/signals/sources/seed`.
3. **Surveillance de la Santé (Health Check) :** Chaque source dispose d'un attribut `health_status` (`healthy`, `degraded`, `failing`) mis à jour lors de chaque cycle de collecte.
