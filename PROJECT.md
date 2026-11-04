# CADRAGE DU PROJET & ARCHITECTURE DU SYSTÈME (PROJECT.md)
**Plateforme** : ContentOps Harness v2.0.0  
**Statut** : Document de Référence et Contrat d'Ingénierie  
**Date de révision** : 2026-11-04  
**Responsable** : Principal Software Architect & Lead Engineer  

---

## 1. VISION, PRINCIPES DIRECTEURS & PÉRIMÈTRE

### 1.1. Mission
**ContentOps Harness** est une plateforme professionnelle de gouvernance et d'orchestration éditoriale multi-agents. Elle permet aux organisations de veiller, d'idéer, de rédiger, de valider avec supervision humaine (HITL) et de publier du contenu sur les réseaux professionnels (LinkedIn, X/Twitter) de manière fiable, mesurable et sécurisée.

### 1.2. Principes Fondamentaux d'Ingénierie
1. **Sécurité et Isolation Multi-Tenant (Zero-Trust)** : Aucune donnée ne peut être lue ou modifiée sans vérification explicite de l'appartenance au `workspace_id`. L'isolation est assurée de bout en bout (sessions API, contextes de requêtes, clés de chiffrement AES-256-GCM et politiques RLS PostgreSQL).
2. **Supervision Humaine Obligatoire (Human-In-The-Loop - HITL)** : Aucun contenu généré par un modèle LLM ne peut être publié sans une approbation humaine formelle, scellée par hachage cryptographique SHA-256 du contenu final (`approved_payload_hash`).
3. **Publication Idempotente At-Most-Once** : Les transactions de publication vers les plateformes sociales utilisent des verrous distribués et des réconciliations automatiques d'état afin de garantir qu'aucun message n'est publié deux fois.
4. **Contrôle FinOps & Résilience Agentique** : Tous les workflows d'agents LangGraph sont surveillés par des disjoncteurs (circuit breakers) et plafonnés par un budget de cycle (`CycleBudget`), prévenant tout déni de service ou surcoût par boucle infinie.
5. **Accessibilité & Sobriété Frontend** : Interface conforme aux standards **WCAG 2.1 AA**, design tokens fondés sur l'espace colorimétrique **OKLCH**, absence totale de tokens sensibles dans le stockage local du navigateur.

---

## 2. ARCHITECTURE GLOBALE DU SYSTÈME

### 2.1. Topologie des Couches Logicielles (Clean Architecture)

```
+---------------------------------------------------------------------------------------+
|                                    PRESENTATION LAYER                                 |
|   React 18 SPA (Vite 6 / Tailwind CSS / OKLCH Tokens / React Router v7 Declarative)    |
|   13 Écrans Métier, Composants Atomiques, Contextes Sécurisés (Mémoire Volatile)      |
+-------------------------------------------+-------------------------------------------+
                                            | HTTPS / JSON / Cookie HttpOnly Lax
                                            v
+---------------------------------------------------------------------------------------+
|                               DELIVERY & API GATEWAY LAYER                            |
|   FastAPI Application (Uvicorn / Lifespan Asynchrone / Corrélation X-Correlation-ID)  |
|   Middlewares (Sécurité, CSP, Taille Max, Limiteur de Débit par IP & Workspace)      |
|   14 Routeurs Métier REST (/v1/auth, /v1/workspaces, /v1/content, /v1/ideas, etc.)    |
+-------------------------------------------+-------------------------------------------+
                                            |
         +----------------------------------+----------------------------------+
         |                                                                     |
         v                                                                     v
+---------------------------------------+   +---------------------------------------+
|       APPLICATION & AGENT LAYER       |   |       DATA ACCESS & DOMAIN LAYER      |
|  - Graphes LangGraph (Production,     |   |  - Machine d'États Éditoriale         |
|    Ideation, Veille, Insights)        |   |    (ContentStateMachine)              |
|  - LLMResolver (Failover Hiérarchique)|   |  - Calculs d'Idempotence (SHA-256)    |
|  - Adaptateurs Résilients NVIDIA NIM  |   |  - Repositories Modulaires par Domaine|
|    & Google Gemini                    |   |    (UserRepository, WorkspaceRepo...) |
|  - Budgets FinOps & Circuit Breakers  |   |  - Modèles Relationnels SQLAlchemy    |
|  - Télémétrie Langfuse PII-Safe       |   |  - Migrations de Schéma 001 - 003     |
+---------------------------------------+   +---------------------------------------+
         |                                                                     |
         v                                                                     v
+---------------------------------------+   +---------------------------------------+
|       EXTERNAL CONNECTORS & TOOLS     |   |          PERSISTENCE INFRASTRUCTURE   |
|  - Outils Web Sécurisés (Anti-SSRF)   |   |  - PostgreSQL 16+ avec Row-Level      |
|  - Connecteurs arXiv, RSS, News       |   |    Security (RLS) & Schéma Dénormalisé|
|  - API Réseaux Sociaux (LinkedIn, X)  |   |  - SQLite WAL Durci (Environnement    |
|  - Coffre-fort OAuth (AES-256-GCM)    |   |    de Développement Local & Tests)    |
+---------------------------------------+   +---------------------------------------+
```

### 2.2. Flux de Traitement et Scénarios d'Exécution
1. **Veille & Détection de Signaux** :
   - Le démon `VeilleSchedulerWorker` interroge périodiquement les connecteurs documentaires configurés (flux RSS, API ArXiv).
   - Les URLs cibles sont inspectées par `validate_target_url_security` pour bloquer toute tentative de SSRF vers les réseaux privés, loopback ou métadonnées cloud.
   - Les signaux capturés sont assainis via `PromptInjectionGuard.defang_text()` et qualifiés dans `signals`.
2. **Idéation & Formulation de Sujets** :
   - L'utilisateur déclenche la génération d'idées depuis `IdeationScreen`.
   - L'agent LangGraph `IdeaResearchGraph` consulte les signaux qualifiés et le profil de voix de marque.
   - Les sources externes sont encapsulées dans des balises `<untrusted_external_data>` avant rendu du prompt.
3. **Rédaction & sas de Validation HITL** :
   - Le brief est converti en variantes de publication adaptées aux plateformes cibles (LinkedIn post long, X thread/post court).
   - Les variantes produites sont soumises à la file d'attente de relecture humaine (`InboxScreen`).
   - L'utilisateur peut approuver (`APPROVED`), rejeter (`REJECTED`) ou demander une réécriture guidée par agent (`REQUEST_REVISION`).
   - L'approbation scelle l'empreinte SHA-256 du payload édité.
4. **Publication Idempotente & Calendrier** :
   - Le worker de publication `PublisherWorker` acquiert un verrou exclusif sur la tâche de publication (`publication_jobs`).
   - L'empreinte SHA-256 courante est comparée au sceau de l'approbation : tout écart annule la publication pour altération illégitime (`TAMPER_DETECTED`).
   - Le connecteur social publie le message ; en cas de succès, le statut passe à `PUBLISHED` et l'ID externe est horodaté dans `published_posts`.
   - Si une coupure réseau intervient pendant l'appel sortant, la tâche bascule en `PUBLISH_UNKNOWN` pour une réconciliation déterministe supervisée.

---

## 3. FEATURE INVENTORY RELIÉ AUX ANOMALIES

Ce tableau exhaustif recense chaque fonctionnalité opérationnelle du système, les modules qui l'implémentent, son statut actuel et l'ensemble des anomalies identifiées lors de l'audit (Phase 1) :

| ID Fonctionnalité | Intitulé & Description Métier | Modules Backend & Fichiers Clés | Composants Frontend | Statut Actuel | Anomalies Associées |
|---|---|---|---|---|---|
| **FEAT-AUTH-01** | Inscription, vérification email & mot de passe Argon2id | `apps/api/routers/auth.py`, `packages/security/passwords.py` | `AuthScreen.tsx`, `AuthContext.tsx` | Opérationnel | `ANOM-15` (Rate limit spoofing) |
| **FEAT-AUTH-02** | Rotation des Refresh Tokens & Invalidation Famille | `apps/api/routers/auth.py`, `packages/security/tokens.py` | `lib/api.ts`, `AuthContext.tsx` | Opérationnel | `ANOM-38` (_KEY_RING figé) |
| **FEAT-AUTH-03** | Mode Connexion Rapide / Démo Éphémère | `apps/api/routers/auth.py` | `AuthScreen.tsx`, `AuthContext.tsx` | Dégradé | `ANOM-08` (Appel /dev-token 404) |
| **FEAT-USER-01** | Profil Utilisateur & Sessions Multi-Appareils | `apps/api/routers/users.py`, `auth.py` | `UserProfileScreen.tsx`, `SecurityTab.tsx` | Dégradé | `ANOM-18` (Duplication /auth/me), `ANOM-31` (Contraste) |
| **FEAT-USER-02** | Upload d'Avatar avec Assainissement WebP Pillow | `apps/api/routers/users.py` | `UserProfileScreen.tsx`, `AvatarUpload.tsx` | Dégradé | `ANOM-23` (Blocage event loop), `ANOM-37` (Orphelins disque) |
| **FEAT-USER-03** | Export RGPD (Art. 15) & Droit à l'Oubli (Art. 17) | `apps/api/routers/users.py`, `infra/db/repository.py` | `UserProfileScreen.tsx`, `GdprTab.tsx` | Partiel | `ANOM-37` (Avatars non purgés) |
| **FEAT-WKSP-01** | Gestion Multi-Tenant, Membres & Rôles RBAC | `apps/api/routers/workspaces.py`, `dependencies.py` | `SettingsScreen.tsx`, `AppShell.tsx` | Dégradé | `ANOM-03` (Cycle repo -> auth cache), `ANOM-22` (Cache non borné) |
| **FEAT-BRND-01** | Profils de Voix de Marque, Tonalité & Règles Négatives | `apps/api/routers/brand_profiles.py`, `repository.py` | `BrandProfileScreen.tsx` | Dégradé | `ANOM-27` (Alert bloquant natif) |
| **FEAT-SRCE-01** | Ingestion de Sources Web & Protection Anti-SSRF | `apps/api/routers/sources.py`, `packages/tools/browse.py` | `VeilleScreen.tsx`, `SourceModal.tsx` | Vulnérable | `ANOM-14` (DNS Rebinding TOCTOU) |
| **FEAT-SIGN-01** | Radar de Veille, Qualification de Signaux & Ordonnanceur | `apps/api/routers/signals.py`, `services/scheduler/` | `VeilleScreen.tsx`, `SignalCard.tsx` | Opérationnel | `ANOM-07` (Masquage dates pass), `ANOM-45` (H1 dupliqué) |
| **FEAT-IDEA-01** | Génération & Scoring d'Idées par Agent LangGraph | `apps/api/routers/ideas.py`, `nodes/research.py` | `IdeationScreen.tsx`, `IdeaCard.tsx` | Vulnérable | `ANOM-02` (Prompt injection sources) |
| **FEAT-BRF-01** | Création & Structuration de Briefs Éditoriaux | `apps/api/routers/briefs.py` | `IdeationScreen.tsx`, `BriefModal.tsx` | Incomplet | `ANOM-40` (Absence GET briefs) |
| **FEAT-CONT-01** | Génération Multi-Plateforme (LinkedIn, X/Twitter) | `apps/api/routers/content.py`, `nodes/production.py` | `InboxScreen.tsx`, `PlatformPreview.tsx` | Opérationnel | `ANOM-05` (Unused imports), `ANOM-42` (Typage any) |
| **FEAT-CONT-02** | Sas de Validation Humaine (HITL) & Raccourcis Clavier | `apps/api/routers/content.py`, `domain/state_machine.py`| `InboxScreen.tsx`, `useHitlShortcuts.ts` | Dégradé | `ANOM-11` (Shortcuts dans select), `ANOM-30` (ARIA listbox) |
| **FEAT-CONT-03** | Réécriture Guidée par Agent (Quality Revision) | `apps/api/routers/content.py`, `nodes/quality.py` | `InboxScreen.tsx`, `RevisionDialog.tsx` | Opérationnel | `ANOM-05` (Unused imports) |
| **FEAT-PUBL-01** | Dispatch Immédiat & Planification At-Most-Once | `apps/api/routers/publications.py`, `services/publisher/`| `CalendarScreen.tsx`, `PublishModal.tsx` | Dégradé | `ANOM-16` (Jointures récursives 5 tables) |
| **FEAT-CAL-01** | Visualisation Calendrier Synchronisée par Workspace | `apps/api/routers/calendar.py` | `CalendarScreen.tsx` | Incomplet | `ANOM-45` (Vue semaine fictive) |
| **FEAT-ANLT-01** | Métriques Sociales & Hypothèses Stratégiques | `apps/api/routers/analytics.py`, `strategy.py` | `InsightsScreen.tsx` | Dégradé | `ANOM-16` (Jointures 6 tables), `ANOM-29` (Filtre 30d déconnecté) |
| **FEAT-OATH-01** | Coffre-Fort OAuth AES-256-GCM & Connexions Réseaux | `apps/api/routers/oauth.py`, `packages/security/` | `ConnectionsScreen.tsx` | Opérationnel | `ANOM-26` (Classe text-txt manquante) |
| **FEAT-LLM-01** | Catalogue & Résolveur Multi-Fournisseurs (NVIDIA/Gemini)| `services/orchestration/resolver.py`, `providers/` | `SettingsScreen.tsx`, `LLMTab.tsx` | Dégradé | `ANOM-06` (Signature request Mypy), `ANOM-41` (Appel live tests) |
| **FEAT-FINO-01** | Quotas FinOps, Circuit Breaker & Budgets de Tokens | `packages/resilience/` | `SettingsScreen.tsx` | Dégradé | `ANOM-21` (Lock manquant CircuitBreaker) |
| **FEAT-DSGN-01** | Design Tokens OKLCH, Palettes & Système Anti-FOUC | `apps/web/src/styles/tokens.css`, `index.html` | Tous écrans (`AppShell.tsx`, etc.) | Opérationnel | `ANOM-26` (Token text-txt manquant) |
| **FEAT-A11Y-01** | Conformité d'Accessibilité Numérique WCAG 2.1 AA | `apps/web/src/components/common/` | Tous composants | Bloqué | `ANOM-09` (useId formulaires), `ANOM-10` (Focus trap tiroir) |
| **FEAT-PERF-01** | Performance Client, Découpage de Bundle & Réseau | `apps/web/src/App.tsx`, `vite.config.ts` | `DashboardScreen.tsx` | Dégradé | `ANOM-12` (Waterfall), `ANOM-35` (Doublons inbox), `ANOM-36` (Bundle 348k) |
| **FEAT-SEO-01** | Référencement Naturel & Métadonnées Sociales | `apps/web/public/`, `index.html` | Shell global | Bloqué | `ANOM-33` (Titre statique), `ANOM-34` (robots/sitemap absents) |
| **FEAT-CICD-01** | Validation Automatisée des Tests & Linters | `tests/`, `.github/workflows/ci.yml` | Suite Vitest, Suite Playwright | Bloqué | `ANOM-01` (Pytest collection crash), `ANOM-05` (Ruff), `ANOM-13` (Playwright) |

---

## 4. MILESTONES ET LOTS DE TRAVAIL (FEUILLE DE ROUTE LOTS 1 À 4)

L'ensemble des 45 anomalies est réparti de manière ordonnancée et cohérente au sein de **4 lots techniques séquentiels**, garantissant qu'aucune régression n'est introduite et que les dépendances techniques sont strictement respectées :

```
+-----------------------------------------------------------------------------------------+
| LOT 1 : DÉBLOCAGE CRITIQUE DE LA VALIDATION & SÉCURITÉ IMMÉDIATE (P0/P1)                |
| - Réparer l'import obsolète tests/agents/test_agent_verification_battery.py (ANOM-01)   |
| - Neutraliser l'injection de prompt indirecte dans research.py via defang & tags (ANOM-02)|
| - Corriger les 7 imports inutilisés Ruff F401 (ANOM-05)                                 |
| - Corriger la signature Mypy _TimeoutSession.request dans nvidia.py (ANOM-06)           |
| - Remplacer l'appel /dev-token par /demo dans le frontend (ANOM-08)                     |
| - Ajouter le fallback React.useId() sur Input, Select et Textarea (ANOM-09)             |
| - Sécuriser le tiroir mobile Sidebar avec focus trap et touche Échap (ANOM-10)          |
| - Exclure les balises <select> du hook useHitlShortcuts (ANOM-11)                       |
| - Paralléliser le chargement Dashboard via Promise.allSettled (ANOM-12)                |
| - Réaligner la suite Playwright sur le routeur HTML5 (ANOM-13)                          |
| - Mocker les appels réseau de découverte NVIDIA dans les tests (ANOM-41)                |
| -> CRITÈRE DE SUCCÈS : Pytest complet passe à 100%, Ruff 0 erreur, Mypy passe en CI.   |
+--------------------------------------------+--------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
| LOT 2 : DÉCOUPLAGE ARCHITECTURAL, RLS & RÉSILIENCE (P1/P2)                              |
| - Découpler infra/db/repository.py de apps.api.dependencies (ANOM-03)                   |
| - Découpler packages/observability de services/orchestration (ANOM-04)                  |
| - Éliminer les 10 masquages silencieux except Exception: pass (ANOM-07)                 |
| - Corriger le TOCTOU DNS Rebinding dans browse.py avec IP pinning (ANOM-14)             |
| - Sécuriser l'extraction d'IP client dans le rate limiter (ANOM-15)                    |
| - Refactoriser les requêtes SQL analytics, strategy et worker sur workspace_id (ANOM-16)|
| - Déprécier la route dupliquée /v1/auth/me au profit de /v1/me (ANOM-18)                |
| - Ajouter un verrou de thread dans CircuitBreaker (ANOM-21)                             |
| - Borner le cache AuthSessionCache avec politique d'éviction LRU (ANOM-22)              |
| - Décharger l'upload d'avatar bloquant sur un threadpool (ANOM-23)                      |
| -> CRITÈRE DE SUCCÈS : Dépendances circulaires critiques purgées, RLS fail-closed.     |
+--------------------------------------------+--------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
| LOT 3 : DETTE TECHNIQUE, PERSISTANCE MODULAIRE & DESIGN SYSTEM (P2)                     |
| - Modulariser ContentOpsRepository dans infra/db/repos/ (ANOM-17)                       |
| - Supprimer ignore_errors = true dans pyproject.toml et typer proprement (ANOM-19)      |
| - Retirer les directives résiduelles # type: ignore dans main.py (ANOM-20)              |
| - Aligner pyproject.toml et requirements.txt, purger packages inutilisés (ANOM-24, 25)  |
| - Ajouter la classe Tailwind .text-txt dans tailwind.config.js (ANOM-26)                |
| - Remplacer alert() par showToast dans BrandProfileScreen (ANOM-27)                     |
| - Repositionner les toasts mobiles à bottom-16 pour libérer la navigation (ANOM-28)    |
| - Connecter le filtre de période Insights à l'API backend (ANOM-29)                     |
| - Corriger les violations WAI-ARIA role="listbox" (ANOM-30)                             |
| - Rehausser le contraste de --text-muted à 4.5:1 (ANOM-31)                              |
| - Rendre accessibles au clavier tous les aperçus et toggles (ANOM-32)                   |
| - Synchroniser dynamiquement document.title lors de la navigation (ANOM-33)             |
| - Générer robots.txt, sitemap.xml, balise canonical et métadonnées Open Graph (ANOM-34) |
| - Dédupliquer les appels /v1/inbox au montage (ANOM-35)                                 |
| - Fractionner le bundle Vite (lazy AuthScreen et manualChunks vendor) (ANOM-36)         |
| -> CRITÈRE DE SUCCÈS : Bundle JS < 150 kB, WCAG AA conforme, zéro classe CSS manquante.|
+--------------------------------------------+--------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
| LOT 4 : RGPD, COMPLÉTUDE API, OUTILLAGE & PRÉPARATION PRODUCTION (P3)                  |
| - Supprimer physiquement les fichiers WebP d'avatars au droit à l'oubli (ANOM-37)       |
| - Rendre dynamique l'accès à _KEY_RING pour la rotation à chaud (ANOM-38)               |
| - Aligner la version retournée par /ready sur "2.0.0" (ANOM-39)                         |
| - Implémenter les routes de consultation GET /v1/briefs (ANOM-40)                       |
| - Renforcer le typage Pydantic des états LangGraph et des interfaces TS (ANOM-42)       |
| - Installer et configurer l'outillage de linting frontend ESLint/Biome (ANOM-43)        |
| - Créer le package.json racine délimitant le monorepo (ANOM-44)                         |
| - Finaliser la vue semaine du calendrier et purger les polices .woff (ANOM-45)          |
| -> CRITÈRE DE SUCCÈS : 100% des 45 anomalies résolues, audit final au statut VALIDÉ.    |
+-----------------------------------------------------------------------------------------+
```

---

## 5. CODE LAYOUT & DIRECTIVES D'ORGANISATION

### 5.1. Règle d'Or de l'Arborescence
Le répertoire `.agents/teamwork/` est **strictement réservé aux métadonnées des agents** (briefings, plans, journaux de progression, rapports de handoff).  
**AUCUN FICHIER SOURCE, AUCUN TEST ET AUCUNE DONNÉE NE PEUT Y ÊTRE IMPLANTÉ.**

### 5.2. Emplacements Désignés des Fichiers de Code
- **Backend FastAPI** :
  - Points d'entrée et cycle de vie : `apps/api/main.py`.
  - Dépendances d'injection (Auth, Tenant, DB) : `apps/api/dependencies.py`.
  - Routeurs REST : `apps/api/routers/<domaine>.py`.
- **Frontend React 18** :
  - Composants partagés et primitives UI : `apps/web/src/components/<catégorie>/`.
  - Écrans métier de premier niveau : `apps/web/src/screens/<Écran>Screen.tsx`.
  - Styles, tokens et thèmes : `apps/web/src/styles/` et `tailwind.config.js`.
  - Contextes d'état global : `apps/web/src/context/<Domaine>Context.tsx`.
- **Persistance et Infrastructure** :
  - Modèles SQLAlchemy : `infra/db/models.py`.
  - Repositories de domaine : `infra/db/repos/<domaine>_repository.py`.
  - Connexion de base de données et hooks RLS : `infra/db/database.py`.
  - Migrations SQL versionnées : `infra/migrations/<numero>_<nom>.sql`.
- **Packages Partagés & Sécurité** :
  - Contrats et schémas partagés : `packages/contracts/`.
  - Primitives cryptographiques et sécurité : `packages/security/`.
  - Résilience et budgets FinOps : `packages/resilience/`.
  - Télémétrie et journalisation : `packages/observability/`.
- **Tests** :
  - Tests unitaires : `tests/unit/`.
  - Tests d'intégration API et DB : `tests/integration/`.
  - Tests de sécurité et isolation tenant : `tests/security/`.
  - Tests de bout en bout navigateur : `tests/e2e/`.

---

## 6. INTERFACE CONTRACTS & SPÉCIFICATIONS FORMELLES

### 6.1. Contrats d'En-têtes et de Formatage HTTP
Toute requête HTTP entrante et sortante respecte les contrats de transport suivants :
- **En-tête de Corrélation** : `X-Correlation-ID` obligatoire sur chaque réponse, généré ou relayé par middleware.
- **En-têtes de Sécurité Systématiques** :
  - `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; ...`
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- **Format Standard des Réponses d'Erreur** :
  ```json
  {
    "detail": "Description compréhensible du motif de rejet sans fuite interne",
    "correlation_id": "corr_c8a7b1e4f201"
  }
  ```

### 6.2. Contrat d'Authentification et Contexte Multi-Tenant
1. **Jeton d'Accès Bearer JWT** :
   - Signature : HMAC-SHA256 (`HS256`).
   - Durée de vie : 900 secondes (15 minutes).
   - Payload obligatoire :
     ```json
     {
       "sub": "usr_94b8e1f0",
       "workspace_id": "ws_7a2f10c8",
       "role": "owner | editor | viewer",
       "jti": "jti_41b9d038",
       "iss": "contentops-api",
       "aud": "contentops-web",
       "exp": 1730700000,
       "nbf": 1730699100
     }
     ```
2. **Jeton de Rafraîchissement (Cookie HttpOnly)** :
   - Attributs du cookie : `HttpOnly; SameSite=Lax; Path=/v1/auth/refresh; Max-Age=604800; Secure (si HTTPS)`.
   - Persistance base : Empreinte SHA-256 stockée dans `refresh_tokens`.
   - Révocation : Toute réutilisation d'un jeton déjà consommé hors fenêtre de tolérance (20s) entraîne l'invalidation immédiate de la famille de jetons complète.

### 6.3. Contrat de Sceau Cryptographique HITL & Publication At-Most-Once
1. **Empreinte d'Approbation** :  
   `approved_payload_hash = SHA-256(variant.title + "\n" + variant.body + "\n" + sorted(media_urls))`
2. **Vérification Pré-Publication** :  
   Avant tout appel d'API vers les réseaux sociaux, `PublisherWorker` recalcule l'empreinte de la variante ciblée. Si `current_hash != approved_payload_hash`, la tâche bascule immédiatement à l'état `TAMPER_DETECTED` et la publication est suspendue avec alerte d'audit.

### 6.4. Contrat d'Encapsulation des Données Externes Non Fiables
Tout contenu textuel issu du web (articles, flux RSS, signaux) injecté dans le contexte d'un agent LLM doit être obligatoirement délimité par la balise XML normalisée :
```xml
<untrusted_external_data origin="https://exemple.com/article" source_id="src_123">
Contenu textuel préalablement assaini par PromptInjectionGuard.defang_text()
</untrusted_external_data>
```
Les directives du modèle spécifient impérativement que le texte situé à l'intérieur de ces balises est purement informatif et ne doit en aucun cas être interprété comme une instruction impérative.

---
*Fin du document de référence PROJECT.md — Validé pour la planification Phase 2.*
