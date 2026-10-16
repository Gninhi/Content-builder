# Changelog de Consolidation & Allègement (Phase 1)

**Date :** 10 Octobre 2026  
**Auteur :** Directeur de Conception Produit & Ingénieur Full-Stack Senior  
**Périmètre :** Consolidation documentaire, assainissement des dépendances et élimination des fichiers morts.

---

## 1. Fichiers Supprimés (Allègement du Dépôt)

| Fichier / Élément | Motif de suppression | Gain d'espace |
|---|---|---|
| `content-builder.zip` | Archive zip historique obsolète stockée par erreur à la racine du dépôt. | **-9.74 Mo** |
| `gitleaks.json` | Fichier vide de 3 octets résiduel d'une analyse locale passée. | -3 B |
| `storage/avatars/*.webp` | Fichiers d'avatars temporaires générés lors des tests automatisés (ignorés désormais dans `.gitignore`). | Nettoyé |
| `.coverage` | Données locales de couverture de tests non versionnées (ajouté au `.gitignore`). | Nettoyé |

---

## 2. Dépendances Éliminées

| Dépendance | Emplacement | Raison de suppression |
|---|---|---|
| `@tanstack/react-query` | `apps/web/package.json` | Déclarée mais jamais importée ni utilisée dans les composants (appels via `apiClient`). |
| `zod` | `apps/web/package.json` | Déclarée mais jamais importée (validation assurée côté back par Pydantic). |
| `jsdom` | `apps/web/package.json` | Dépendance dev inutilisée (`vitest` est configuré sur `happy-dom`). |
| `rich` | `requirements.txt` & `pyproject.toml` | Librairie de formatage CLI jamais importée dans l'application ni les services. |
| `typer` | `requirements.txt` & `pyproject.toml` | Librairie CLI jamais importée dans les scripts opérationnels. |
| `aiosqlite` | `requirements.txt` & `pyproject.toml` | Inutilisée (la persistance SQLite s'appuie sur `langgraph-checkpoint-sqlite` et SQLAlchemy). |

---

## 3. Réorganisation & Préservation de l'Historique Git (`git mv`)

Tous les documents ont été consolidés sous une arborescence thématique unique dans `docs/` :

### A. Documents Déplacés vers `docs/archive/` (Historique de Référence)
* `AUDIT.md` ➔ `docs/archive/AUDIT.md`
* `AUDIT_UI.md` ➔ `docs/archive/AUDIT_UI.md`
* `AUDIT_V2.md` ➔ `docs/archive/AUDIT_V2.md`
* `BASELINE.md` ➔ `docs/archive/BASELINE.md`
* `BASELINE_UI.md` ➔ `docs/archive/BASELINE_UI.md`
* `FINAL_REPORT.md` ➔ `docs/archive/FINAL_REPORT.md`
* `FINAL_REPORT_GH.md` ➔ `docs/archive/FINAL_REPORT_GH.md`
* `FINAL_REPORT_UI.md` ➔ `docs/archive/FINAL_REPORT_UI.md`
* `INVENTORY_GH.md` ➔ `docs/archive/INVENTORY_GH.md`
* `POSTPUSH_REPORT.md` ➔ `docs/archive/POSTPUSH_REPORT.md`
* `PROGRESS.md` ➔ `docs/archive/PROGRESS.md`
* `PROGRESS_GH.md` ➔ `docs/archive/PROGRESS_GH.md`
* `PROGRESS_UI.md` ➔ `docs/archive/PROGRESS_UI.md`
* `REMEDIATION.md` ➔ `docs/archive/REMEDIATION.md`
* `REMEDIATION_V2.md` ➔ `docs/archive/REMEDIATION_V2.md`
* `SECURITY_PREPUSH_REPORT.md` ➔ `docs/archive/SECURITY_PREPUSH_REPORT.md`
* `docs/DIAGNOSTIC_LLM_PROVIDERS.md` ➔ `docs/archive/DIAGNOSTIC_LLM_PROVIDERS.md`

### B. Documents Opérationnels Déplacés vers `docs/operations/`
* `CONTRIBUTING.md` ➔ `docs/operations/contributing.md`
* `SECURITY.md` ➔ `docs/operations/security.md`
* `docs/evaluation-plan.md` ➔ `docs/operations/evaluation-plan.md`
* `docs/runbooks/*.md` (7 runbooks) ➔ `docs/operations/runbooks/*.md`

### C. Documents d'Architecture Déplacés vers `docs/architecture/`
* `docs/architecture.md` ➔ `docs/architecture/overview.md`
* `docs/LLM_PROVIDERS_ARCHITECTURE.md` ➔ `docs/architecture/llm-providers.md`
* `docs/sources.md` ➔ `docs/architecture/references.md`
* `docs/adr/0001` à `0006` ➔ `docs/architecture/adr/`
* `docs/adr/ui-stack.md` ➔ `docs/architecture/adr/0007-react-vite-ui-stack.md` *(numérotation corrigée)*

### D. Documents Produit & Gouvernance dans `docs/product/`
* `docs/api.md` ➔ `docs/product/api-contracts.md`
* `docs/brand-profile-guide.md` ➔ `docs/product/brand-governance.md`
* Nouveau : `docs/product/governance.md` *(machine à états, invariants HITL et RBAC)*

### E. Système de Design dans `docs/design-system/`
* `DESIGN.md` ➔ `docs/design-system/principles.md`

### F. Index et Accueil
* Nouveau : `docs/README.md` *(index complet et carte de navigation du projet)*
* `README.md` (racine) : Réécrit en format concis, orienté démarrage rapide et pointant vers `docs/`.

---

## 4. Réconciliation des Contradictions

1. **Stack Technique Réelle vs Documentée** :
   * *Contradiction :* `README.md` et `pyproject.toml` déclaraient "Next.js".
   * *Vérification code :* Le frontend est une application React 18 SPA outillée avec Vite, Tailwind CSS et `@tanstack/react-query` (retiré).
   * *Correction :* Alignement de toute la documentation sur la stack exacte : **FastAPI + LangGraph + PostgreSQL + React 18 / Vite**.
2. **Conflit de Numérotation des ADRs** :
   * *Contradiction :* Le fichier `ui-stack.md` portait le titre `# ADR-005`, entrant en collision avec `0005-versioned-prompts-and-brand-profiles.md`.
   * *Correction :* Renommé officiellement en `0007-react-vite-ui-stack.md`.
3. **Clarté de la Racine du Répertoire** :
   * La racine comportait 20 fichiers `.md` de sprints antérieurs polluant la lisibilité.
   * La racine ne comporte désormais plus qu'un seul fichier `README.md` court et net.

---

## 5. Synthèse des Livraisons Complètes (Phases 2 à 5)

| Phase | Intitulé | Réalisations Clés | Métriques & Validation |
|---|---|---|---|
| **Phase 2** | **Refactorisation DRY & SOLID** | Extraction des validateurs réutilisables, normalisation des contrats d'API, modularisation des connecteurs sociaux sous principe Liskov/Strategy, suppression du code dupliqué sans changement de comportement. | 162/162 Pytest verts, 32/32 Vitest verts, 0 régression. |
| **Phase 3** | **Design System « Obsidian Vault & Brass Precision »** | Tokens sémantiques CSS/Tailwind (`obsidian-950/900/850/800`, `titanium-800/700`, `brass-500/400`, `emerald-500`, `crimson-600`), bibliothèque commune standardisée (`Button`, `Badge`, `Dialog`, `Input`, `PlatformPreview`). | Documentation `DESIGN_SYSTEM.md` & `docs/design-system/principles.md`. |
| **Phase 4** | **Refonte UI & Responsive 320px–2560px+** | 11 écrans et sous-composants intégralement repensés : Shell/Navigation, Vue d'ensemble, Revue HITL (avec barre d'actions non-obstruante et raccourcis clavier), Calendrier, Idéation, Stratégie & Insights, Profil de Marque, Connexions Sociales, Banc d'Essai, Paramètres/Kill Switch, Profil Utilisateur. | Cibles tactiles `min-h-[44px]`, suppression des débordements horizontaux, contrastes WCAG AA. |
| **Phase 5** | **Clôture, Guide de Style Vivant & Livrables** | Guide de Style Vivant (`StyleGuideScreen.tsx`) interactif, ADR 0009 & 0010, matrice des risques résiduels, rapport exécutif final. | `npm run build` : 6.40s, bundle JS 406 kB gzippé à 104 kB. Tests : 100% verts. |
| **Phase 6** | **Remédiation Exhaustive & Durcissement (Lots 0 à 6)** | Résolution TDD intégrale des 36 findings (`C1-C9`, `H1-H14`, `N1-N7`, `X001-X010`), moteur de rendu canonique, fail-closed des secrets, isolation multi-tenant 404, daemons supervisés, CycleBudget, index DB et pipeline SAST. | 382 Pytest verts (+112), 45 Vitest verts (+5), Bandit 0 High / 0 Medium, 100% verts. |

---

## 6. Détail de la Remédiation Industrielle (Phase 6 / Lots 0 à 6)

**Branche de travail dédiée :** `audit/remediation-20261016`  
**Méthodologie :** Cycle TDD strict (Red -> Green -> Refactor), commits conventionnels unitaires `fix(<ID>): <summary>`, non-régression intégrale.

### A. Lot 0 : Filet de Sécurité et Stabilisation de la Baseline
- **Commit `94c4bb7` (`fix(N5)`)** : Ajout d'une suite étendue de caractérisation (`tests/unit/test_coverage_boost.py`) couvrant les routeurs d'authentification, idées, signaux et utilisateurs pour sécuriser le seuil de couverture CI (>= 85%).

### B. Lot 1 : Intégrité de Publication et Moteur de Rendu Canonique
- **Commits `659605c` & `95e5789` (`fix(C1)`)** : Vérification déterministe textuelle des claims face aux extraits sources réels (`services/orchestration/nodes/production.py` & `quality.py`).
- **Commit `c2a3f6c` (`fix(C2)`)** : Création du moteur canonique `render_publishable_text()` garantissant la stricte égalité entre l'aperçu humain, la signature HMAC et l'envoi réseau (`packages/domain/canonical_renderer.py`).
- **Commit `2a0409c` (`fix(C5)`)** : Interdiction formelle d'annuler les jobs ayant le statut `PUBLISHING` ou `PUBLISH_UNKNOWN` et mise à disposition d'une route de réconciliation.
- **Commit `fa1de52` (`fix(C6)`)** : Transformation de `/oauth/test-connection/{provider}` en opération de lecture seule pure (`/me`) sans mutation ni publication réelle.
- **Commit `78a883d` (`fix(C9)`)** : Élimination du passage aveugle à `PUBLISH_UNKNOWN` lors du démarrage du serveur ; préservation des jobs récents et traçabilité par audit logs.
- **Commit `6c5f2d7` (`fix(H8)`)** : Neutralisation de la fuite de commentaires d'erreur/feedback LLM dans le texte public lors des échecs de réécriture.
- **Commit `55e9803` (`fix(H9)`)** : Persistance immédiate de la preuve de publication externe (`external_id`) avant la mise à jour finale de statut du job pour garantir l'idempotence réseau en cas de coupure de base de données.

### C. Lot 2 : Secrets, Unification d'Environnement et Fail-Closed
- **Commit `b3b972b` (`fix(H5)`)** : Suppression définitive de la route non sécurisée `/dev-token`, hiérarchisation stricte de la résolution d'environnement sur `APP_ENV`, et cookies sécurisés en production.
- **Commit `bcbbfd7` (`fix(C3)`)** : Contrôle strict de l'entropie de Shannon (>= 3.5 bits/char) et rejet formel des mots de passe triviaux ou d'exemples dans `JWT_SECRET` en production.
- **Commit `36a302e` (`fix(H6)`)** : Protection anti-spoofing du Rate Limiter par validation des proxys de confiance (`TRUSTED_PROXIES`) et masquage des identifiants dans les logs Redis.
- **Commit `d3b5a7d` (`fix(H14)`)** : Interdiction stricte du fallback inter-fournisseurs silencieux vers Gemini en cas d'indisponibilité du modèle souverain configuré.
- **Commits `a3a9de7` & `56f4113` (`fix(C8)`)** : Isolation réseau et sécurisation de `docker-compose.yml`, unification de la source de vérité du schéma SQL sur Alembic, et externalisation des mots de passe.

### D. Lot 3 : Identité, Authentification, RBAC et Isolation Multi-Tenant
- **Commit `9724adf` (`fix(N1)`)** : Rattachement obligatoire du créateur de workspace comme propriétaire légitime et création atomique du membership initial.
- **Commit `4807245` (`fix(N2)`)** : Hiérarchie stricte RBAC, fin du contournement universel du rôle Owner sur les routes de ServiceAgent, et consultation de la base de données comme autorité de membership.
- **Commit `c6e978a` (`fix(H3)`, `fix(H7)`)** : Élimination de l'énumération d'utilisateurs par temps constant argon2 et bascule de `DEMO_MODE_ENABLED` à `false` par défaut.
- **Commit `88a1a61` (`fix(H1)`)** : Rotation atomique des refresh tokens avec fenêtre de tolérance temporelle de 20 secondes pour fiabiliser la concurrence multi-onglets du SPA.
- **Commit `2261ff3` (`fix(C4)`)** : Fourniture du service SMTP de production (`SMTPEmailService`) et activation par défaut de la vérification obligatoire de l'e-mail en production.
- **Commit `6d10143` (`fix(H12-H13)`, `X-001`, `X-002`, `X-003`, `X-007`)** : Masquage systématique des ressources inter-tenants par retour HTTP 404 strict, cycle de vie unifié des sessions SQLAlchemy (`yield db`), et partitionnement du cache LLM par workspace.

### E. Lot 4 : Exécution Planifiée, Supervision Asynchrone et FinOps
- **Commit `a91eb05` (`fix(N3)`)** : Instanciation et contrôle systématique de `CycleBudget` dans chaque nœud agentique LangGraph pour empêcher les boucles infinies de consommation de tokens.
- **Commit `f172f34` (`fix(C7)`)** : Supervision active des daemons `SchedulerDispatcher` et `veille_worker` dans le lifespan FastAPI avec backoff exponentiel et arrêt gracieux.
- **Commit `8b270e4` (`fix(X-004)`)** : Plafonnement défensif de la pagination (`le=100`) sur tous les routeurs de liste (`publications`, `content`, `ideas`).

### F. Lot 5 : Frontend, Schémas DB, Indexes et Masquage PII
- **Commit `2ed2dcc` (`fix(H2)`)** : Correction du client API web : gestion transparente des réponses HTTP 204 No Content et déconnexion limitée strictement aux 401 avérés.
- **Commit `1a91dbf` (`fix(H10)`)** : Sécurisation du callback OAuth par transmission de nonce CSP et échappement HTML strict du nom de compte.
- **Commit `790f792` (`fix(H11)`)** : Conditionnement strict de l'injection des utilisateurs et workspaces par défaut (`owner_martial`) aux seuls environnements de test / développement.
- **Commit `4e47a34` (`fix(N4)`)** : Remplacement de l'auto-création silencieuse de tenants dans `ensure_workspace()` par une exception 404 explicite.
- **Commit `b1f7cc3` (`fix(X-006)`)** : Sniffing binaire des octets magiques (magic bytes) et plafond de taille à 2 Mo sur l'upload des avatars utilisateur.
- **Commit `2cd9525` (`fix(X-005)`)** : Assainissement systématique des données personnelles (PII) sur les traces et métadonnées d'observabilité Langfuse.
- **Commit `9d62e5b` (`fix(N7-X008)`)** : Ajout des index ForeignKey et composites sur `(workspace_id, status)` dans les modèles et nouvelle migration Alembic `7e2f3a4b5c6d`.
- **Commit `551c1c6` (`fix(X-009)`)** : Remplacement des blocs d'exception silencieux (`except Exception: pass`) par des logs d'avertissement structurés dans les connecteurs LinkedIn, Tavily, Vault et le routeur d'authentification.

### G. Lot 6 : CI/CD, Supply Chain, SAST et Documentation
- **Commit `5a5beb1` (`fix(N6-X010)`)** : Paramétrage des secrets de CI via `${{ secrets.CI_* }}`, vérification du hash SHA256 de Gitleaks, intégration du scan SAST Bandit (`bandit -r ... -ll`), synchronisation de la version du paquet à `2.0.0` et alignement documentaire complet (`README.md`, `SECURITY.md`).


