# 📋 BASELINE.md — Base de Référence Mesurée

**Date & Heure :** 2026-10-07T16:41:00+02:00  
**Auteur :** Ingénieur Principal Backend / Sécurité / Fiabilité  
**Branche Git :** `feat/social-prod` (créée à partir de `fix/hardening`, commit `0f3a884`)  
**Objectif :** Établir l'état des lieux rigoureux, prouvé par des commandes réelles, sans complaisance ni affirmation non vérifiée.

---

## 1. État Git & Arbre de Travail

- **Branche active :** `feat/social-prod`
- **Branche parente :** `fix/hardening` (commit `0f3a884`)
- **Dernier commit :** `0f3a884 feat(ops): implement CI workflow, /ready probe, structured JSON logging, and social-ready architecture (PUB-03, OPS-01, OPS-02, OPS-03)`
- **Fichiers non suivis / modifiés :** Aucun (`working tree clean`).
- **Remotes :** Aucun remote configuré localement.
- **Vérification `.env` :**
  - Commande : `git log --all --full-history -- ".env"` → Sortie vide (le fichier `.env` n'a **JAMAIS** été suivi dans l'historique git).
  - Commande : `git check-ignore -v .env` → `.gitignore:2:.env .env` (confirmé ignoré).

---

## 2. Métriques Mesurées & Synthèse des Contrôles

| Contrôle | Commande Exécutée | Résultat Mesuré | Statut |
| :--- | :--- | :--- | :---: |
| **Pytest** | `/opt/anaconda3/bin/pytest --cov=...` | **78 passés**, 0 échec, **0 warning** en 4.38s | 🟢 VERT |
| **Couverture globale** | `pytest-cov` (tout le projet) | **83%** (2 929 statements, 491 missed) | 🟡 À hausser (>= 85%) |
| **Linter (Ruff)** | `/opt/anaconda3/bin/ruff check .` | **0 erreur** (`All checks passed!`) | 🟢 VERT |
| **Typage (Mypy global)** | `/opt/anaconda3/bin/mypy .` | **96 erreurs dans 10 fichiers** | 🔴 ÉCHEC (P0 technique) |
| **Audit dépendances** | `pip-audit -r requirements.txt` | **0 vulnérabilité connue** | 🟢 VERT |
| **Scan secrets (Working tree)**| Script regex exhaustif | **0 secret réel détecté** | 🟢 VERT |
| **Scan secrets (Historique git)**| Script regex sur tous les commits | **0 secret réel détecté** | 🟢 VERT |
| **Build Docker** | `docker info` | Daemon Docker inactif sur la machine hôte | ⚪ Non exécutable localement |

---

## 3. Détail de la Couverture de Code par Package

```text
Package / Module                                       Stmts   Miss   Cover
---------------------------------------------------------------------------
apps/api/dependencies.py                                  36      1     97%
apps/api/main.py                                         118     25     79%
apps/api/routers/ (analytics, publications, ideas...)    223     94     58%
evals/evaluators/quality_evaluator.py                    206     10     95%
infra/db/models.py                                       162      0    100%
infra/db/repository.py                                   170     28     84%
packages/cache/ (sqlite, redis, factory)                 184     36     80%
packages/connectors/social/ (base, sandbox, vault)       174     16     91%
packages/contracts/ (schemas, events)                    187      1     99%
packages/domain/ (entities, state_machine, idempotency)  199      9     95%
packages/observability/ (correlation, json, metrics)     215     63     71%
packages/resilience/circuit_breaker.py                   107     12     89%
packages/security/auth.py                                 26      0    100%
services/orchestration/llm.py                             85      7     92%
services/orchestration/graphs/                            91     17     81%
services/orchestration/nodes/                            253     70     72%
services/publisher/worker.py                              95     16     83%
---------------------------------------------------------------------------
TOTAL                                                   2929    491     83%
```

---

## 4. Analyse des 96 Erreurs Mypy Détectées

Lors de l'audit précédent, mypy avait été exécuté avec un périmètre restreint (`--follow-imports=silent` ou fichiers spécifiques de sécurité). L'exécution sans filtre (`mypy .`) met en évidence 96 erreurs de typage réparties dans 10 fichiers :

- **`apps/api/routers/content.py` & `apps/api/routers/publications.py` :**
  - Les modèles SQLAlchemy retournent des attributs de type `Column[str]` ou `Column[datetime]` au lieu de `str` ou `datetime`. Ces colonnes sont injectées directement dans des schémas Pydantic sans conversion explicite.
- **`apps/api/routers/ideas.py` & `apps/api/routers/strategy.py` :**
  - Invocations de `graph.invoke()` avec des types de retour `GraphOutput[StateT]` ou surcharges `Pregel` de LangGraph non typées strictement.
  - Compréhension de liste typée `List[object]` au lieu de `List[str]`.
- **`apps/api/routers/analytics.py` :**
  - Comparaison `max()` impliquant des types SQLAlchemy `Column[int]`.

Ces 96 erreurs doivent être intégralement résolues lors de la Phase 3.

---

## 5. Diagnostic de Configuration Réelle (Sans Fuite de Secret)

Exécution de [`scripts/diagnose_config.py`](file:///Users/seansiehigninhi/Dossier_dev/apps/F-LangGraph/DeepAgent/scripts/diagnose_config.py) :

```text
=== DIAGNOSTIC DE CONFIGURATION DE L'ENVIRONNEMENT ===
Format : STRICTEMENT 'défini / non défini' (aucune valeur ni longueur exposée)

  DATABASE_URL                     : défini
  LOG_LEVEL                        : défini
  GOOGLE_API_KEY                   : défini
  GEMINI_MODEL                     : défini
  LANGFUSE_PUBLIC_KEY              : défini
  LANGFUSE_SECRET_KEY              : défini
  TAVILY_API_KEY                   : défini
  SOCIAL_SANDBOX_MODE              : défini
  LINKEDIN_CLIENT_ID               : défini
  LINKEDIN_CLIENT_SECRET           : défini
  LINKEDIN_ACCESS_TOKEN            : défini
  X_API_KEY                        : défini
  X_API_SECRET                     : défini
  X_ACCESS_TOKEN                   : défini

  ENV                              : non défini (doit être configuré 'production' par défaut)
  CHECKPOINTER_TYPE                : non défini (doit être explicité)
  JWT_SECRET_KEY                   : non défini (utilise clé dev locale temporaire)
  SECRET_VAULT_KEY                 : non défini (utilise clé dev locale temporaire)
  LINKEDIN_REDIRECT_URI            : non défini (à déclarer pour OAuth)
  X_CLIENT_ID                      : non défini (à mapper sur X_API_KEY ou déclarer)
  X_CLIENT_SECRET                  : non défini (à mapper sur X_API_SECRET ou déclarer)
  X_REDIRECT_URI                   : non défini (à déclarer pour OAuth)
  KILL_SWITCH_GLOBAL               : non défini (défaut false)
```

---

## 6. Réconciliation des Chiffres Contradictoires

1. **Nombre de tests :**
   - **Historique initial :** 18 tests dans `tests/`, tandis que le rapport PRD mentionnait "80 cas d'évaluation". Ces 80 cas tournaient en fait dans un script standalone `evals/evaluators/quality_evaluator.py` contenant des assertions factices `passed = True`.
   - **Phase 1-2 (Hardening) :** Réécriture de la machine à états, checkpointer et sécurité → **54 tests**.
   - **Phase 3 (Qualité) :** Intégration de l'évaluateur de qualité et du dataset golden dans pytest → **58 tests**.
   - **Phase 4 (Coûts & Cache) :** Ajout des tests pricing, LLM cache et correlation ID → **69 tests**.
   - **Phase 5 (Ops & Social Ready) :** Ajout des probes `/health` & `/ready`, formatteur JSON et coffre OAuth chiffré → **78 tests passants**.
2. **Statut Mypy :**
   - Le précédent rapport affichait "Mypy: OK" car la commande ciblait uniquement les packages modifiés. L'audit complet révèle les **96 erreurs** documentées ci-dessus.

---

## 🏁 Portail de Phase 0 : Validé
La base de référence est établie et consignée. Nous pouvons engager la **Phase 1 : Audit Préliminaire Approfondi (Lecture Seule)**.
