# Diagnostic Architectural Initial (Lot 1) — Providers LLM & Sélection des Modèles

**Date d'audit :** 9 Octobre 2026  
**Branche active :** `feat/ui-production`  
**Commit SHA de base :** `f7bae269051be1bf4db8744bdcca291100dcedaa`  
**Dépôt :** `Gninhi/Content-builder`  
**Auteur :** Architecte Logiciel Senior & DevSecOps  

---

## 1. État des Lieux du Système Actuel

### 1.1 Providers et SDK Existants
- **Provider unique actuellement intégré :** Google Gemini.
- **SDK utilisé :** `langchain-google-genai` (v4.4.0) via `ChatGoogleGenerativeAI`.
- **Package déjà présent dans l'environnement :** `langchain-nvidia-ai-endpoints` (v1.2.1) fournissant `ChatNVIDIA`.
- **Client HTTP :** `httpx` (v0.28.1) disponible pour la découverte REST et les contrôles réseau.

### 1.2 Modèles et Paramètres Codés en Dur
- **Modèle par défaut codé en dur :** `gemini-3.8-flash` dans `services/orchestration/llm.py` (lignes 94, 96, 125).
- **Températures codées en dur :**
  - `ideation` (`nodes/research.py`) : `0.3` (modèle `fast`)
  - `production` (`nodes/production.py`) : `0.4` (modèle `reasoning`)
  - `rewrite` (`apps/api/routers/content.py`) : `0.3` (modèle `reasoning`)
  - `strategy` (`nodes/insights.py`) : `0.2` (modèle `reasoning`)
- **Résilience :** Circuit breaker global `CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)` et retries basiques (`LLM_MAX_RETRIES=3`, `LLM_TIMEOUT_SECONDS=30.0`).

### 1.3 Consommateurs LLM vs Nœuds Déterministes

| Tâche / Module | Nature du Nœud | Format d'Appel LLM | Sortie Attendue |
| :--- | :--- | :--- | :--- |
| **Recherche d'idées (`ideation`)** | **Agentique / LLM** | `model.with_structured_output(GeneratedIdeasBatch)` | Liste d'idées avec scores et angles |
| **Génération variantes (`production`)** | **Agentique / LLM** | `model.with_structured_output(GeneratedVariant)` | Post formaté (hook, body, cta, claims) |
| **Réécriture relecteur (`rewrite`)** | **Agentique / LLM** | `model.with_structured_output(GeneratedVariant)` | Révision intégrant le feedback humain |
| **Recommandations (`strategy`)** | **Agentique / LLM** | `model.with_structured_output(GeneratedStrategyBatch)` | Hypothèses et recommandations stratégiques |
| **Quality Gate (`quality`)** | **DÉTERMINISTE (0 LLM)** | Règles regex, longueurs X/LinkedIn, claims check | Score QA et validation |
| **Validation humaine (`approval`)** | **DÉTERMINISTE (0 LLM)** | Hash SHA-256, machine à états HITL | Transition vers approuvé / rejeté |
| **Planification (`scheduling`)** | **DÉTERMINISTE (0 LLM)** | Calcul d'horodatage et anti-collision | Création de job |
| **Publication (`publishing`)** | **DÉTERMINISTE (0 LLM)** | Connecteurs OAuth, chiffrement AES-256 | Diffusion sandbox ou live |
| **Analytique (`analytics`)** | **DÉTERMINISTE (0 LLM)** | Métriques d'engagement et agrégations | Snapshots |

### 1.4 Gestion des Secrets et Persistance
- **Secrets :** Uniquement variables d'environnement serveur (`GOOGLE_API_KEY`). Aucune clé n'est persistée en base de données ni exposée au frontend.
- **Réglages LLM :** Variables d'environnement partielles (`LLM_MODEL_FOR_IDEATION`, `LLM_MODEL_FOR_STRATEGY`). Aucune table relationnelle ne stocke actuellement les choix par espace de travail (`workspace_id`).

### 1.5 Résultats de la Ligne de Base (Baseline)
- **Tests Backend (`pytest`) :** **133 passed** sur 133 (0 échec, durée 57s).
- **Tests Frontend (`vitest`) :** **21 passed** sur 21 (0 échec, durée 1.02s).
- **Linter & Typage :** Ruff (0 erreur), Mypy (0 erreur sur 120 fichiers).

---

## 2. Architecture Retenue

```
┌────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Apps/Web)                             │
│     Paramètres > Intelligence Artificielle & Modèles LLM               │
│     - État Providers (Configuré / Non configuré / Erreur)              │
│     - Choix Modèle par défaut (Gemini / NVIDIA)                        │
│     - Overrides par Tâche (Ideation / Production / Rewrite / Strategy) │
│     - Test de Connexion explicite (Zero secret côté client)            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ REST API (/v1/llm/*)
┌───────────────────────────────────▼────────────────────────────────────┐
│                         FASTAPI BACKEND                                │
│   - Auth & RBAC (Owner/Editor pour configuration, Viewer lecture seule) │
│   - Validation des requêtes et protection SSRF endpoints personnalisés │
│   - Persistance relationnelle : WorkspaceLLMSettingsModel              │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                 RÉSOLVEUR CENTRALISÉ (LLMResolver)                     │
│  Ordre de résolution strict :                                          │
│  1. Override explicite du run (si autorisé)                            │
│  2. Override de la tâche (ideation, production, rewrite, strategy)     │
│  3. Configuration par défaut du workspace                              │
│  4. Configuration d'environnement (LLM_MODEL_FOR_*, GEMINI_MODEL)      │
│  5. Fallback historique (gemini-3.8-flash)                             │
│  * Validation : provider activé + clé présente + capacité supportée    │
│  * Strict : AUCUN fallback silencieux vers un autre provider           │
└──────────────────┬─────────────────────────────────┬───────────────────┘
                   │                                 │
     ┌─────────────▼──────────────┐   ┌──────────────▼────────────────┐
     │   GeminiProviderAdapter    │   │     NVIDIAProviderAdapter     │
     │  - SDK: ChatGoogle...      │   │  - SDK: ChatNVIDIA            │
     │  - Modèles: gemini-3.8...  │   │  - URL: api.nvidia.com/v1     │
     │  - Secret: GOOGLE_API_KEY  │   │  - Secret: NVIDIA_API_KEY     │
     └────────────────────────────┘   └───────────────────────────────┘
```

---

## 3. Plan d'Implémentation par Lots

- **Lot 1 :** Diagnostic et Baseline *(Complété)*
- **Lot 2 :** Registre de providers, contrats typés et résolveur centralisé (`packages/contracts`, `services/orchestration/providers/`, `services/orchestration/resolver.py`).
- **Lot 3 :** Adaptateur NVIDIA, catalogue avec provenance et découverte sécurisée (`services/orchestration/providers/nvidia.py`).
- **Lot 4 :** Persistance des réglages (`WorkspaceLLMSettingsModel`, migration), endpoints API `/v1/llm/*` et test de connexion explicite.
- **Lot 5 :** Intégration aux workflows LangGraph (nœuds research, production, rewrite, insights) et figeage du contexte de run.
- **Lot 6 :** Interface utilisateur de configuration des providers et modèles (`SettingsScreen.tsx`, composant dédié, traductions).
- **Lot 7 :** Tests exhaustifs (unitaires, intégration, mocks, régression, sécurité), documentation mise à jour et rapport final.
