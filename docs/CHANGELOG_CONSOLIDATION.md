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

