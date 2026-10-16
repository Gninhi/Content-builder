# 🚀 ContentOps Harness — Governed Agentic Editorial Operating System

> **Système d'exploitation éditorial agentique gouverné basé sur LangGraph, FastAPI, PostgreSQL et React 18 / Vite.**  
> *Transforme de la veille, des notes et des retours d'expérience en contenus multi-plateformes fiables, soumis à validation humaine obligatoire (HITL) et audités en continu.*

---

## 🎯 Objectif & Garanties Fondamentales

ContentOps Harness n'est pas un autoposteur. C'est un **système de gouvernance éditoriale** destiné aux décideurs, reposant sur des garanties strictes :

* **Validation Humaine Obligatoire (HITL)** : Aucune publication publique sans approbation explicite d'un utilisateur au rôle `Owner`.
* **Publication « Au Plus Une Fois »** : Statut `PUBLISHING` avant l'appel réseau, bascule en `PUBLISH_UNKNOWN` sur incident sans retry automatique, clé d'idempotence unique.
* **Scellement Cryptographique** : Tout contenu approuvé est scellé par son hash SHA-256.
* **Isolation Multi-Tenant & RBAC** : Rôles `Owner`, `Editor`, `Viewer` appliqués côté serveur, coffre OAuth chiffré (AES-256-GCM), journal d'audit append-only.
* **Apprentissage Propositionnel** : L'IA formule des recommandations aux rédacteurs sans jamais altérer automatiquement les règles de marque.

---

## ⚡ Démarrage Rapide

### 1. Prérequis & Environnement
```bash
# Activer l'environnement Python
source .venv/bin/activate

# Installer les dépendances backend
pip install -r requirements.txt

# Configurer l'environnement local
cp .env.example .env
```

### 2. Lancer le Serveur API & UI Intégrée
```bash
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload
```

* **Interface Web** : 👉 [http://localhost:8000/ui](http://localhost:8000/ui) *(ou [http://localhost:8000/](http://localhost:8000/))*
* **Documentation API Swagger** : 👉 [http://localhost:8000/docs](http://localhost:8000/docs)
* **Vérification de santé** : 👉 [http://localhost:8000/ready](http://localhost:8000/ready)

### 3. Développement Frontend (Optionnel, mode HMR)
```bash
cd apps/web
npm install
npm run dev
```
Accès direct avec rechargement à chaud : 👉 [http://localhost:3000/ui/](http://localhost:3000/ui/)

---

## 🧪 Tests & Qualité

```bash
# Tests complets backend (270 tests unitaires, intégration, sécurité, observabilité)
pytest tests/

# Vérification du typage statique
mypy .

# Analyse du code et linting
ruff check apps/ packages/ infra/ tests/

# Tests frontend (40 tests Vitest)
cd apps/web && npm test

# Build de production frontend
cd apps/web && npm run build
```

---

## 📚 Documentation Complète

La documentation exhaustive du projet est centralisée dans le dossier [`docs/`](docs/README.md) :

* **[Carte & Index de la Documentation](docs/README.md)**
* **[Architecture Système & Graphes LangGraph](docs/architecture/overview.md)**
* **[Architecture Multi-Provider LLM](docs/architecture/llm-providers.md)**
* **[Décisions d'Architecture (ADR 0001 à 0011)](docs/architecture/adr/)**
* **[Pipeline de Veille & Idéation Autonome](docs/veille/architecture.md)**
* **[Gouvernance, Machine à États & RBAC](docs/product/governance.md)**
* **[Guide du Profil de Marque](docs/product/brand-governance.md)**
* **[Contrats & Spécification des APIs](docs/product/api-contracts.md)**
* **[Système de Design & Accessibilité](docs/design-system/overview.md)**
* **[Politique de Sécurité & Signalement](docs/operations/security.md)**
* **[Runbooks d'Exploitation en Production](docs/operations/runbooks/)**
* **[Rapports d'Audits Techniques & Matrices](docs/audits/audit_exhaustif_severe_2026.md)**
* **[Changelog de Consolidation](docs/CHANGELOG_CONSOLIDATION.md)**
