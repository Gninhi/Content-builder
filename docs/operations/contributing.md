# Guide de Contribution (CONTRIBUTING.md)

Merci de votre intérêt pour **ContentOps Harness**. Ce projet applique des règles strictes de sécurité logicielle, de qualité de code et d'architecture pilotée par les tests (TDD).

---

## 1. Principes Directeurs

1. **Sécurité d'Abord** :
   - Aucun secret (clé d'API, mot de passe, jeton OAuth) ne doit jamais être commité.
   - Les variables sensibles doivent transiter exclusivement par l'environnement (`.env` local ignoré).
   - Tout flux réseau sortant vers les réseaux sociaux s'exécute par défaut en mode sandbox (`SOCIAL_SANDBOX_MODE=true`).
2. **Gouvernance Humaine Obligatoire (HITL)** :
   - Aucune publication directe sans validation humaine explicite par un utilisateur disposant du rôle approprié (`Owner` ou `Editor`).
3. **Qualité et Typage Stricte** :
   - Tout nouveau code Python doit respecter `ruff` et `mypy` sans avertissement.
   - Tout nouveau code frontend React/TypeScript doit compiler sans erreur sous `tsc && vite build`.

---

## 2. Environnement de Développement

### Prérequis
- Python 3.12+
- Node.js 20+ & npm 10+
- Docker & Docker Compose (pour PostgreSQL & Redis optionnels)

### Installation
```bash
# Cloner le dépôt
git clone https://github.com/Gninhi/Content-builder.git
cd Content-builder

# Environnement Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd apps/web
npm install
npm run build
cd ../..

# Configuration de base
cp .env.example .env
```

---

## 3. Workflow Git & Pull Requests

1. Créez une branche dédiée : `git checkout -b feat/ma-fonctionnalite` ou `fix/mon-correctif`.
2. Exécutez la suite de tests complète avant de commiter :
   ```bash
   pytest
   cd apps/web && npm run test && cd ../..
   ```
3. Vérifiez l'absence de secrets :
   ```bash
   gitleaks detect --source .
   ```
4. Ouvrez une Pull Request en remplissant scrupuleusement la checklist de sécurité du template de PR.

---

## 4. Signalement de Bogues et Suggestions

- Pour signaler un bogue régulier, ouvrez une issue en utilisant le template [Bug Report].
- Pour toute faille de sécurité, suivez la politique définie dans [SECURITY.md](SECURITY.md).
