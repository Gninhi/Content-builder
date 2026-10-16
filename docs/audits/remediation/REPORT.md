# RAPPORT TECHNIQUE DE CARTOGRAPHIE, D'AUDIT ET PLAN DE REMÉDIATION
**Projet** : ContentOps Harness / DeepAgent (`Gninhi/Content-builder`)  
**Branche** : `audit/remediation-20261016`  
**Date d'évaluation** : 16 Octobre 2026  
**Auteurs** : Équipe d'ingénierie (Auditeur, Architecte, Ingénieur TDD, Revueur Indépendant)

---

## 1. Baseline Chiffrée Initiale (Phase 0)

Avant toute modification du code source, les mesures de référence ont été établies sur l'environnement de développement :

| Indicateur / Outil | Mesure Initiale | Objectif Cible | Écart / Risque Constaté |
| :--- | :--- | :--- | :--- |
| **Pytest** (`pytest -q --ignore=tests/e2e --cov`) | 270 passés (34.75s) | 100% passés | Vert, mais plusieurs suites non exécutées par défaut. |
| **Couverture réelle backend** | **80%** (1 590 lignes non couvertes) | **>= 85%** | **Échec au seuil CI** configuré à 85% (`--cov-fail-under=85`). |
| **Ruff** (`ruff check .`) | 0 violation | 0 violation | Conforme. |
| **Mypy** (`mypy .`) | 0 erreur (avec overrides actuels) | 0 erreur | 1 erreur de typage révélée hors overrides (`apps/api/main.py:304`). |
| **Bandit** (`bandit -r ... -ll`) | 1 Medium flagged | 0 Medium | B104 (faux-positif anti-SSRF `0.0.0.0` dans `quality_evaluator.py`). |
| **Pip-Audit** (`pip-audit -r requirements.txt`) | 0 vulnérabilité dans lock direct | 0 vulnérabilité | Dépendances directes saines. |
| **Npm Audit** (`apps/web`) | 5 High vulnerabilities | 0 vulnérabilité | Dépendance `braces <= 3.0.3` via `tailwindcss` (upstream pending). |
| **Vitest Frontend** | 40/40 tests réussis (1.06s) | 40/40 passés | Conforme. |
| **Vite Build Frontend** | Succès en 6.08s (303.41 kB) | Build propre | Conforme. |
| **Alembic Migrations** | Upgrade/Downgrade fonctionnels | Réversible | Divergence SQL init vs migrations (RLS absent des migrations). |

---

## 2. Graphes d'Architecture et Modélisation Formelle (Phase 0.3)

### (a) Flux de données d'un contenu (de la veille à la publication)

```mermaid
flowchart TD
    subgraph Sourcing["1. Ingestion & Veille"]
        RSS[Flux RSS Externes] --> Veille[VeilleWorker Daemon]
        Web[Pages Web Scrappées] --> Veille
        Veille --> Signals[(Signals Table)]
    end

    subgraph Ideation["2. Idéation & Briefing"]
        Signals --> IdeasAgent[Research Graph / Ideas Agent]
        IdeasAgent --> Ideas[(Ideas Table)]
        Ideas --> BriefBuilder[Brief Builder Node]
        BriefBuilder --> Brief[(Briefs Table)]
    end

    subgraph Generation["3. Production & Qualité"]
        Brief --> ProdNode[Production Node LangGraph]
        ProdNode --> ClaimsGen[Claims & Arguments Extractor]
        ProdNode --> ContentVariants[(Content Variants Table)]
        ContentVariants --> QAGate[Quality Review Node]
        QAGate -->|Rejet auto / Hallucination| ProdNode
    end

    subgraph HITL["4. Validation Humaine (Checkpointing)"]
        QAGate -->|Score >= 90| ApprovalQueue[Review Inbox / Interruption Graph]
        ApprovalQueue -->|Édition Humaine| RecalculateSeal[HMAC Approval Seal]
        ApprovalQueue -->|Approbation| StatusApproved[ContentStatus = APPROVED]
    end

    subgraph Publishing["5. Ordonnancement & Publication Réseau"]
        StatusApproved --> SchedulerJob[(Publication Jobs Table)]
        SchedulerJob --> Dispatcher[Scheduler Dispatcher]
        Dispatcher --> PublisherWorker[Publisher Worker]
        PublisherWorker --> SafeRenderer[render_publishable_text Canonical]
        SafeRenderer --> LinkedIn[LinkedIn Connector API]
        SafeRenderer --> XTwitter[X / Twitter Connector API]
        LinkedIn --> ExternalProof[External ID Persisted]
        XTwitter --> ExternalProof
        ExternalProof --> FinalState[JobStatus = PUBLISHED / ARCHIVED]
    end
```

### (b) Frontières de Confiance & Segments de Sécurité

```mermaid
graph TD
    subgraph Untrusted["Zone Non de Confiance (Extérieur)"]
        Browser[SPA React / Client Browser]
        ThirdPartyWeb[Web Public / Flux RSS]
        OAuthIdP[Fournisseurs OAuth LinkedIn / X]
    end

    subgraph Perimeter["Périmètre d'Entrée & Contrôle d'Accès"]
        RateLimiter[Rate Limiter TRUSTED_PROXIES]
        AuthGuard[JWT Auth & Session Revocation Guard]
        RBACGuard[RBAC & Workspace Isolation Guard]
        CORS_CSP[En-têtes Stricts CSP / HSTS / CORS]
    end

    subgraph Orchestration["Zone d'Orchestration & IA Sécurisée"]
        PromptArmor[Sanitiseur Anti-Injection Prompt Injection]
        LangGraphPipe[LangGraph State Machines]
        CycleBudgetGuard[CycleBudget Token/Time Controller]
        ResolverLLM[LLM Multi-Provider Resolver Sovereign]
    end

    subgraph TrustedInternal["Zone de Confiance Interne (Persistance & Vault)"]
        Vault[AES-GCM 256 Token Vault]
        PostgreSQL[(PostgreSQL Multi-Tenant RLS)]
        Redis[(Redis Checkpoint & State Cache)]
    end

    subgraph OutboundZone["Zone de Sortie Contrôlée"]
        SSRFProxy[SSRF Safe Fetcher Anti-Rebinding]
        SocialPublisher[Idempotent Social Publisher]
    end

    Browser -->|HTTPS + Bearer| Perimeter
    Perimeter --> Orchestration
    ThirdPartyWeb --> SSRFProxy
    SSRFProxy --> Orchestration
    Orchestration --> TrustedInternal
    Orchestration --> OutboundZone
    OutboundZone --> OAuthIdP
```

### (c) Machine à États & Écritures Réelles Comparées

```mermaid
stateDiagram-v2
    [*] --> DRAFT : Création initiale
    DRAFT --> IN_REVIEW : Soumission révision
    IN_REVIEW --> QA_FAILED : Rejet QA / Non-sourcé
    QA_FAILED --> IN_REVIEW : Réécriture / Correction
    IN_REVIEW --> APPROVED : Validation HITL (HMAC Seal)
    
    APPROVED --> SCHEDULED : Planification date/heure
    SCHEDULED --> PUBLISHING : Prise en charge Worker
    
    PUBLISHING --> PUBLISHED : 200 OK + External ID
    PUBLISHING --> PUBLISH_UNKNOWN : Crash / Coupure réseau non résolue
    PUBLISHING --> PUBLISH_FAILED : Rejet définitif réseau (4xx)
    
    PUBLISH_UNKNOWN --> RECONCILED : Route de réconciliation dédiée
    RECONCILED --> PUBLISHED : Confirmation externe
    RECONCILED --> SCHEDULED : Absence de publication confirmée
    
    PUBLISHED --> ARCHIVED : Rétention / Archivage
    SCHEDULED --> CANCELLED : Annulation par l'utilisateur
```

**Anomalies d'écriture directe détectées (Bypass de la machine à états)** :
- `apps/api/routers/publications.py:80,82` : Réécriture directe `job.status = CANCELLED` et `variant.status = APPROVED` sans contrôle préalable de l'état `PUBLISHING`.
- `services/publisher/worker.py:147,173,183,204,226,335` : Multiples `setattr(job, "status", JobStatus.PUBLISH_FAILED)` directs écrasant les statuts sans journalisation unifiée.
- `apps/api/main.py:77,80` : Écriture directe `job.status = JobStatus.PUBLISH_UNKNOWN` lors du reboot sur tous les jobs en cours.

---

## 3. Matrice Complète Route × Rôle × Tenant

| Méthode & Route | Authentification Requise | Rôles Autorisés | Filtrage Workspace Obligatoire | Validation Tenant BOLA/IDOR |
| :--- | :--- | :--- | :--- | :--- |
| `GET /` | Non | Public | Non | N/A |
| `GET /health` | Non | Public | Non | N/A |
| `GET /ready` | Non | Public | Non | Masquer détails internes |
| `GET /metrics` | **Recommandé** | Admin / Monitoring | Non | Restreindre IP ou Token interne |
| `POST /v1/auth/register` | Non | Public | Non | N/A |
| `POST /v1/auth/login` | Non | Public | Non | N/A (Timing constant) |
| `POST /v1/auth/refresh` | Non | Public (Refresh Token) | Non | Fenêtre de grâce 20s |
| `POST /v1/auth/dev-token` | **À désactiver en prod** | Test uniquement | Oui | Bloquer si APP_ENV != test |
| `POST /v1/auth/switch-workspace`| Oui | Membre du workspace | Oui | Contrôle `WorkspaceMember` |
| `GET /v1/auth/me` | Oui | Tous rôles | Non | Données de l'utilisateur connecté |
| `GET /v1/me` | Oui | Tous rôles | Non | Données de l'utilisateur connecté |
| `PATCH /v1/me` | Oui | Tous rôles | Non | Restreindre champs mutables |
| `DELETE /v1/me` | Oui | Tous rôles | Non | Soft-delete / Purge conforme |
| `POST /v1/me/avatar` | Oui | Tous rôles | Non | Sniffing MIME binaire |
| `POST /v1/workspaces` | Oui | Tous rôles authentifiés | Non | **Lier au user connecté (N1)** |
| `GET /v1/workspaces/{id}` | Oui | Membres du workspace | Oui | 404 si non membre |
| `POST /v1/workspaces/{id}/kill-switch` | Oui | Owner, Admin | Oui | 404 si non membre |
| `GET /v1/ideas` | Oui | Viewer, Editor, Admin, Owner | Oui | **Filtrer obligatoirement (X-001)** |
| `POST /v1/ideas/research` | Oui | Editor, Admin, Owner | Oui | Contrôler CycleBudget (N3) |
| `POST /v1/briefs` | Oui | Editor, Admin, Owner | Oui | Contrôler tenant_id |
| `POST /v1/content/generate` | Oui | Editor, Admin, Owner | Oui | Contrôler tenant_id + budget |
| `POST /v1/content/{id}/approve` | Oui | Editor, Admin, Owner | Oui | **Vérifier HMAC seal (H8)** |
| `POST /v1/content/{id}/rewrite` | Oui | Editor, Admin, Owner | Oui | Éviter feedback leak (H8) |
| `GET /v1/signals` | Oui | Viewer, Editor, Admin, Owner | Oui | **Filtrer obligatoirement (X-001)** |
| `POST /v1/signals/collect` | Oui | Admin, Owner, ServiceAgent | Oui | Contrôler tenant_id |
| `POST /v1/publications/schedule`| Oui | Editor, Admin, Owner | Oui | Contrôler tenant_id |
| `POST /v1/publications/{id}/cancel` | Oui | Editor, Admin, Owner | Oui | **Refuser si PUBLISHING (C5)** |
| `POST /v1/publications/{id}/publish-now` | Oui | Admin, Owner | Oui | Idempotency lock strict |
| `GET /v1/oauth/accounts` | Oui | Viewer, Editor, Admin, Owner | Oui | Filtrer par workspace_id |
| `GET /v1/oauth/start/{provider}` | Oui | Admin, Owner | Oui | State lié à session cookie |
| `GET /v1/oauth/callback/{provider}` | Non (Callback IdP) | Public avec state valide | Oui | CSP sans inline script (H10) |
| `POST /v1/oauth/test-connection/{provider}` | Oui | Admin, Owner | Oui | **Lecture seule /me (C6)** |
| `GET /v1/llm/config/{ws_id}` | Oui | Admin, Owner | Oui | 404 si non membre |
| `PUT /v1/llm/config/{ws_id}` | Oui | Owner | Oui | Pas d'auto-création fantôme (N4) |

---

## 4. Regroupement des Findings par Cause Racine

1. **Rupture de la Chaîne d'Intégrité de Publication (Cause Racine 1)** :
   - *Findings couverts* : `C1`, `C2`, `C5`, `C6`, `C9`, `H8`, `H9`.
   - *Origine* : Absence d'un module de rendu canonique unique, d'une machine à états exclusive et de contrôles déterministes sur les allégations (claims).
2. **Vulnérabilités de Configuration et Gestion des Secrets (Cause Racine 2)** :
   - *Findings couverts* : `C3`, `C8`, `H5`, `H6`, `H7`, `H14`, `N6`.
   - *Origine* : Fragmentation des variables d'environnement (`ENV` vs `ENVIRONMENT` vs `APP_ENV`), valeurs par défaut permissives et absence de fail-closed au démarrage.
3. **Contrôle d'Accès, Identité et Cloisonnement Multi-Tenant (Cause Racine 3)** :
   - *Findings couverts* : `N1`, `N2`, `C4`, `H1`, `H3`, `H4`, `H12`, `H13`, `X-001`, `X-002`, `X-003`, `X-007`.
   - *Origine* : Modèle de session stateless incomplet (absence de validation active en base), faux RLS non injecté dans SQLAlchemy, et dissociation entre utilisateur authentifié et création de ressources.
4. **Ordonnancement, Supervision Asynchrone et FinOps LLM (Cause Racine 4)** :
   - *Findings couverts* : `C7`, `N3`, `X-004`.
   - *Origine* : Absence de daemons asynchrones intégrés au cycle de vie de l'application et non-injection des compteurs de budget dans les graphes agentiques.
5. **Robustesse Frontend, Qualité de Données et Schéma DB (Cause Racine 5)** :
   - *Findings couverts* : `H2`, `H10`, `H11`, `N4`, `N5`, `N7`, `X-005`, `X-006`, `X-008`, `X-009`, `X-010`.
   - *Origine* : Gestion d'erreur globale frontend inadaptée, incohérence des index relationnels en base et résidus de données de démonstration codées en dur.

---

## 5. Découpage du Plan de Remédiation en Lots Indépendants (Phase 2)

### Lot 0 : Filet de Sécurité et Stabilisation de la Baseline
- **Objectif** : Figer le socle de test, introduire les tests de caractérisation et corriger le déficit de couverture pour atteindre les >= 85% exigés par la CI.
- **Périmètre** : `N5`, ajout des suites de tests unitaires sur les routeurs non couverts (`tests/unit/test_coverage_boost.py`).
- **Critères d'acceptation** : `pytest --cov` atteint >= 85% de couverture globale ; aucun test existant ne régresse.
- **Plan de retour arrière** : Réversion du commit unitaire sans impact de production.

### Lot 1 : Intégrité de Publication et Moteur de Rendu Canonique
- **Objectif** : Garantir que ce qui est publié est strictement identique à ce qui a été approuvé, interdire les annulations dangereuses et supprimer la publication réelle lors des tests de connexion.
- **Périmètre** : `C1`, `C2`, `C5`, `C6`, `C9`, `H8`, `H9`.
- **Actions clés** :
  1. `render_publishable_text(variant)` unique pour aperçu, signature HMAC et publication.
  2. Vérification déterministe textuelle des claims face aux extraits sources réels.
  3. Verrouillage strict de l'annulation (`publications.py`) sur les jobs `PUBLISHING` ou `PUBLISH_UNKNOWN`.
  4. Remplacement de `publisher.publish()` par `/me` en lecture seule dans `/oauth/test-connection`.
  5. Élimination de l'injection de feedback d'erreur dans le corps du texte public.
- **Critères d'acceptation** : Tests TDD rouges -> verts ; impossibilité mathématique de publier un texte différent du texte scellé par l'humain.
- **Plan de retour arrière** : Rollback git du lot 1 ; compatibilité ascendante préservée sur le schéma.

### Lot 2 : Secrets, Unification d'Environnement et Fail-Closed
- **Objectif** : Empêcher le démarrage en production avec des secrets faibles, unifier la configuration sur `APP_ENV` et neutraliser les backdoors de test.
- **Périmètre** : `C3`, `C8`, `H5`, `H6`, `H7`, `H14`, `N6`.
- **Actions clés** :
  1. Unification sur `APP_ENV` (dépréciation avertie de `ENV` et `ENVIRONMENT`).
  2. Validation stricte de l'entropie et interdiction des chaînes courantes dans `JWT_SECRET`.
  3. Suppression ou désactivation stricte de `/dev-token` en dehors de `APP_ENV=test`.
  4. Bascule de `DEMO_MODE_ENABLED` à `false` par défaut.
  5. Sécurisation de l'extraction d'IP dans le Rate Limiter (`TRUSTED_PROXIES`).
  6. Interdiction du fallback LLM silencieux vers Gemini sans accord explicite du workspace.
- **Critères d'acceptation** : Démarrage refusé immédiatement si `APP_ENV=production` avec secret trivial ; tests d'attaque configuration réussis.

### Lot 3 : Identité, Rôles, Authentification et Isolation Multi-Tenant
- **Objectif** : Éliminer l'usurpation de création de tenant, durcir la rotation de refresh tokens et fiabiliser la session.
- **Périmètre** : `N1`, `N2`, `C4`, `H1`, `H3`, `H4`, `H12`, `H13`, `X-001`, `X-002`, `X-003`, `X-007`.
- **Actions clés** :
  1. Liaison obligatoire de `owner_id = current_user.id` et création immédiate de `WorkspaceMemberModel` lors de `POST /v1/workspaces`.
  2. Égalisation du temps de réponse argon2 sur les emails inexistants (hash précalculé).
  3. Contrôle systématique du compte actif (`is_active`) et invalidation lors du reset de mot de passe.
  4. Fenêtre de grâce de 20s sur la rotation de refresh token.
  5. Remplacement du mélange `scoped_session` / `SessionLocal` par le pattern `yield db` propre.
  6. Partitionnement de tout cache LLM par `workspace_id`.
- **Critères d'acceptation** : 0 faille IDOR/BOLA sur la matrice de tests d'isolation cross-tenant.

### Lot 4 : Exécution Planifiée, Supervision Asynchrone et Budgets FinOps
- **Objectif** : Activer les daemons de planification dans le cycle de vie applicatif et borner strictement la consommation de tokens.
- **Périmètre** : `C7`, `N3`, `X-004`.
- **Actions clés** :
  1. Démarrage supervisé de `SchedulerDispatcher` et `veille_worker` dans le `lifespan` FastAPI avec backoff et arrêt gracieux.
  2. Injection et contrôle de `CycleBudget` dans chaque étape des graphes LangGraph.
  3. Plafonnement de la pagination (`le=100`) sur tous les routeurs.
- **Critères d'acceptation** : Déclenchement automatique des tâches arrivées à échéance ; interruption nette des graphes en dépassement de budget.

### Lot 5 : Frontend, Qualité de Données et Nettoyage des Modèles
- **Objectif** : Stabiliser le client web sur les erreurs non-401, assainir les scripts CSP, purger les faux profils et indexer la base.
- **Périmètre** : `H2`, `H10`, `H11`, `N4`, `N7`, `X-005`, `X-006`, `X-008`, `X-009`.
- **Actions clés** :
  1. Correction d'`api.ts` (support HTTP 204 et logout uniquement sur 401).
  2. Externalisation du script OAuth callback et échappement strict de `account_name`.
  3. Suppression des profils fictifs codés en dur (`owner_martial`) et isolation des seeds à l'environnement de test.
  4. Remplacement d'`ensure_workspace()` par une exception 404 explicite.
  5. Migration Alembic ajoutant les index composites sur ForeignKey (`publication_jobs`, `content_variants`).
  6. Sniffing binaire MIME pour l'upload d'avatar et masquage PII sur les traces Langfuse.
- **Critères d'acceptation** : Tests Vitest verts ; aucune régression UI ; absence de requêtes lentes sur les volumétries de test.

### Lot 6 : CI/CD, Supply Chain, Documentation et Finition
- **Objectif** : Valider l'intégrité des dépendances, intégrer le SAST, aligner la documentation et synchroniser les versions.
- **Périmètre** : `N6`, `X-010`, documentation (`README.md`, `SECURITY.md`).
- **Actions clés** :
  1. Épinglage du checksum SHA256 pour les binaires téléchargés en CI (Gitleaks).
  2. Intégration d'un job SAST léger (Semgrep / Bandit) dans le workflow CI.
  3. Alignement des métriques et promesses du README (nombres de tests, garanties de sécurité réelles).
  4. Réconciliation des versions de paquets (1.0.0 vs 2.0.0).
- **Critères d'acceptation** : Pipeline CI 100% verte sur GitHub Actions ; conformité stricte entre code et promesses documentaires.

---

## 6. Questions Ouvertes Soumises à Décision Humaine (Gate Obligatoire)

Avant d'engager la Phase 3 (implémentation et commits par finding), l'équipe sollicite votre arbitrage sur les 5 points structurants suivants :

1. **Fournisseur de Service E-mail (Finding C4)** :
   - *Option A (Recommandée)* : Implémenter une interface générique SMTP/Resend avec variables `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` et activer un mode bouchon (`MemoryLogEmailService`) uniquement si `APP_ENV=test` ou `development`.
   - *Option B* : Intégrer un provider SaaS unique (ex. Resend ou SendGrid).
   - *Option C* : Maintenir `MemoryLogEmailService` en simulant l'envoi dans les logs même en production (déconseillé).

2. **Stratégie d'Isolation de Données Multi-Tenant (Finding H12)** :
   - *Option A (Recommandée - Pragmatisme & Robustesse)* : Maintenir l'isolation applicative étanche via les filtres SQL explicites du Repository SQLAlchemy (`workspace_id` obligatoire et validé par JWT), supprimer le script SQL RLS partiel et non-maintenu qui crée une fausse sensation de sécurité, et blinder avec une suite de tests automatisés cross-tenants.
   - *Option B (Défense en profondeur PostgreSQL RLS)* : Intégrer formellement `SET LOCAL app.current_workspace_id = :ws_id` dans chaque session SQLAlchemy via un écouteur d'événement (`event.listens_for(Engine, "checkout")`) ou la dépendance `get_db`, et intégrer les politiques RLS dans les migrations Alembic (nécessite que l'utilisateur de base de données applicatif ne soit pas superuser / BYPASSRLS).

3. **Politique de Rôles sur la Validation de Contenu (HITL / Rôles)** :
   - *Option A (Recommandée)* : Seuls les rôles `Editor`, `Admin` et `Owner` peuvent approuver ou éditer un contenu avant publication. Le rôle `Viewer` est strictement en lecture seule.
   - *Option B* : Séparation stricte des tâches : l'`Editor` ne peut que rédiger/corriger, seul l'`Admin` ou `Owner` peut signer l'approbation finale pour publication réseau.

4. **Sort de la Route `/dev-token` et Données de Test (Findings H5, H11)** :
   - *Option A (Recommandée)* : Conditionner l'enregistrement de la route `/dev-token` et l'injection de l'utilisateur `owner_martial` strictement au mode test (`APP_ENV=test` ou `development` avec flag explicite `ENABLE_DEV_FIXTURES=true`). En `production`, la route renvoie 404 (non montée) et aucun profil n'est créé d'office.
   - *Option B* : Supprimer totalement la route `/dev-token` et les profils de test du code source de l'API.

5. **Traitement des Fichiers de Documentation et Chemins Absolus Locaux** :
   - *Option A (Recommandée)* : Conserver la structure documentaire existante en remplaçant systématiquement les chemins absolus locaux machine (`file:///Users/seansiehigninhi/...`) par des chemins relatifs au dépôt (`file://./...` ou liens markdown relatifs).
   - *Option B* : Nettoyer et consolider les documents redondants dans `docs/`.
