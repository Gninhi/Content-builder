# REGISTRE DÉTAILLÉ DES FINDINGS D'AUDIT TECHNIQUE & SÉCURITÉ
**Projet** : ContentOps Harness / DeepAgent (`Gninhi/Content-builder`)  
**Branche** : `audit/remediation-20261016`  
**Date d'audit** : 16 Octobre 2026  
**Équipe d'audit** : Auditeur Qualité & Sécurité Senior, Architecte Système, Ingénieur TDD, Revueur Indépendant  
**Statut Global** : 36 Défaillances confirmées et vérifiées (8 Critiques, 17 Élevées, 11 Moyennes/Faibles)

---

## 1. Vue d'Ensemble et Métriques de l'Audit

Conformément au protocole d'audit rigoureux, chaque élément du backlog initial (C1-C9, H1-H14, N1-N7) ainsi que les 14 axes d'investigation active (ASVS, OWASP LLM/ASI, Concurrence, Multi-Tenant, Base de données, Front-end, CI/CD) ont été vérifiés sur pièce.

### Répartition par Sévérité
- **Critique (8)** : C1, C2, C3, C5, C6, H5, H9, H12, N1
- **Élevée (17)** : C4, C7, C8, C9, H1, H2, H4, H6, H7, H8, H13, H14, N3, N6, N7, X-001, X-002, X-006, X-007
- **Moyenne / Faible (11)** : H3, H10, H11, N2, N4, N5, X-003, X-004, X-005, X-008, X-009, X-010

---

## 2. Fiches Détaillées des Findings Critiques

### [ID: C1] Claims « vérifiés » par tautologie et gabarit chiffré inventé
- **Statut** : [FAIT VÉRIFIÉ]
- **Sévérité** : Critique (Impact: Élevé, Probabilité: Élevée, Exploitation: Facile)
- **Localisation** : `services/orchestration/nodes/production.py:139, 146, 197, 217` ; `services/orchestration/nodes/quality.py:83`
- **Preuve de code** :
  ```python
  # production.py:146
  claims.append({
      "claim": statement,
      "verified": True,  # Hardcodé d'office !
      "confidence": 0.95 # Confiance factice inventée
  })
  ```
  Dans `quality.py:83`, le nœud se contente de vérifier si `c.get("verified")` est True sans la moindre validation croisée avec la source originale.
- **Scénario de défaillance** : Le LLM hallucine une statistique financière ou juridique erronée dans le post. Le pipeline l'estampille « vérifié à 95% » et le publie, engageant la responsabilité légale de l'entreprise.
- **Cause racine** : Absence d'algorithme déterministe de réconciliation sémantique/textuelle entre les assertions générées et les extraits sources bruts.
- **Correctif proposé** : Implémenter une vérification textuelle normalisée (fuzzy string matching / containment) entre le claim et les `source_extracts`. Tout claim non retrouvé dans les sources doit être classé `unverified` et déclencher le rejet du portail QA ou une escalade humaine obligatoire.
- **Test de non-régression** : `tests/agents/test_claim_verification.py::test_unverified_claim_fails_qa`

---

### [ID: C2] Texte approuvé ≠ texte publié (omission hook, CTA, hashtags, media)
- **Statut** : [FAIT VÉRIFIÉ]
- **Sévérité** : Critique (Impact: Critique, Probabilité: Systématique, Exploitation: Trivial)
- **Localisation** : `services/publisher/worker.py:269-272`
- **Preuve de code** :
  ```python
  # worker.py:269-272
  content_to_publish = str(variant.body) # hook, cta, hashtags, media_urls sont omis !
  connector.publish(text=content_to_publish, media_urls=None)
  ```
- **Scénario de défaillance** : Un réviseur humain approuve dans l'interface un post LinkedIn complet (avec une accroche captivante, des hashtags ciblés, un appel à l'action et une infographie). Le bot ne publie sur LinkedIn que le corps brut du texte (`body`), sans accroche ni image ni hashtags.
- **Cause racine** : Rupture de contrat entre le modèle de données de la variante et le connecteur de publication ; absence d'un moteur de rendu canonique partagé.
- **Correctif proposé** : Créer une fonction pure et idempotente `render_publishable_text(variant)` utilisée identiquement par l'aperçu frontend, le calcul du hash HMAC d'approbation et le worker de publication.
- **Test de non-régression** : `tests/unit/test_publishable_renderer.py::test_render_variant_includes_all_fields`

---

### [ID: C3] Secrets d'exemple acceptés par la validation en environnement de production
- **Statut** : [FAIT VÉRIFIÉ]
- **Sévérité** : Critique (Impact: Élevé, Probabilité: Élevée, Exploitation: Trivial)
- **Localisation** : `packages/security/auth.py:28, 64`
- **Preuve de code** :
  ```python
  if len(secret) < 32 or secret == DEFAULT_DEV_JWT_SECRET:
      raise ValueError("Invalid secret")
  ```
- **Scénario de défaillance** : Un administrateur déploie en staging/prod avec `JWT_SECRET=test_secret_key_12345678901234567890`. Le serveur démarre sans objection. Un attaquant qui devine ou teste ce secret générique peut forger des tokens JWT valides pour tous les utilisateurs.
- **Cause racine** : Règles de validation trop permissives n'interdisant pas les motifs courants et n'exigeant pas d'entropie minimale.
- **Correctif proposé** : Rejeter strictement les chaînes contenant des motifs interdits (`test`, `example`, `password`, `secret`, `admin`, `12345`) et imposer un calcul d'entropie de Shannon minimale (>= 3.5 bits/char) en production.
- **Test de non-régression** : `tests/security/test_secret_validation.py::test_common_secrets_rejected_in_prod`

---

### [ID: C5] Annulation sauvage sur job PUBLISHING / PUBLISH_UNKNOWN provoquant une double publication
- **Statut** : [FAIT VÉRIFIÉ]
- **Sévérité** : Critique (Impact: Élevé, Probabilité: Moyenne, Exploitation: Facile)
- **Localisation** : `apps/api/routers/publications.py:77-83` ; `services/publisher/worker.py:408`
- **Preuve de code** :
  ```python
  # publications.py:77-83
  job.status = JobStatus.CANCELLED
  variant.status = ContentStatus.APPROVED # Remet le contenu en approuvé pour ré-ordonnancement !
  ```
- **Scénario de défaillance** : Pendant qu'un worker envoie la requête de publication au réseau social, l'utilisateur clique sur "Annuler". Le job passe en `CANCELLED` et la variante repasse en `APPROVED`. Le réseau social confirme la publication quelques secondes plus tard, mais l'utilisateur voit la variante prête à être republiée et déclenche un second envoi, provoquant un doublon public.
- **Cause racine** : Non-respect de la machine à états et absence de verrouillage pessimiste sur les jobs en cours d'exécution réseau.
- **Correctif proposé** : Interdire strictement l'annulation sur un job ayant le statut `PUBLISHING` ou `PUBLISH_UNKNOWN`. Exposer un endpoint sécurisé de réconciliation manuelle/automatique.
- **Test de non-régression** : `tests/unit/test_publication_cancel_safeguard.py::test_cannot_cancel_publishing_job`

---

### [ID: C6] L'endpoint `/oauth/test-connection` effectue une publication réelle sur les réseaux
- **Statut** : [FAIT VÉRIFIÉ]
- **Sévérité** : Critique (Impact: Élevé, Probabilité: Systématique, Exploitation: Trivial)
- **Localisation** : `apps/api/routers/oauth.py:532-534`
- **Preuve de code** :
  ```python
  # oauth.py:532
  res = publisher.publish(
      platform=account.platform,
      text="Test de connexion ContentOps Harness",
      workspace_id=account.workspace_id
  )
  ```
- **Scénario de défaillance** : L'administrateur connecte le compte LinkedIn officiel de son entreprise et clique sur « Tester la connexion ». Un post public « Test de connexion ContentOps Harness » est immédiatement publié sur la page de l'entreprise.
- **Cause racine** : Utilisation d'un appel d'écriture/mutation (`publish`) pour tester la validité d'un token d'accès.
- **Correctif proposé** : Remplacer l'appel par une vérification en lecture seule (profil utilisateur `/me` ou consultation des métadonnées du compte).
- **Test de non-régression** : `tests/security/test_oauth_test_connection_readonly.py::test_connection_test_does_not_publish`

---

### [ID: H5] Route `/dev-token` active et dispersion des variables d'environnement
- **Statut** : [FAIT VÉRIFIÉ]
- **Sévérité** : Critique (Impact: Critique, Probabilité: Élevée, Exploitation: Trivial)
- **Localisation** : `apps/api/routers/auth.py:255` ; `packages/security/auth.py:33`
- **Preuve de code** :
  ```python
  @router.post("/dev-token")
  def get_dev_token(workspace_id: str = "ws_default"):
      if os.getenv("ENV") == "dev" or os.getenv("ENVIRONMENT") == "development":
          return {"access_token": create_token(user_id="dev_user", role="owner", ...)}
  ```
- **Scénario de défaillance** : En staging ou production, si la variable `APP_ENV=production` est définie mais qu'un conteneur hérite de `ENV=dev`, la route `/dev-token` reste active et délivre des jetons d'authentification Owner sans mot de passe.
- **Cause racine** : Présence d'un endpoint backdoor dans le routeur principal et absence d'unification de la variable d'environnement (`APP_ENV` vs `ENV` vs `ENVIRONMENT`).
- **Correctif proposé** : Unifier la configuration sur `APP_ENV`. Désactiver formellement la route `/dev-token` dès lors que `APP_ENV != "test"`.
- **Test de non-régression** : `tests/security/test_dev_token_disabled.py::test_dev_token_rejected_in_prod`

---

### [ID: H9] Publisher marque `PUBLISH_FAILED` après succès réseau si le commit DB échoue
- **Statut** : [FAIT VÉRIFIÉ]
- **Sévérité** : Critique (Impact: Élevé, Probabilité: Moyenne, Exploitation: Défaillance transitoire)
- **Localisation** : `services/publisher/worker.py:334`
- **Scénario de défaillance** : Le connecteur social renvoie 200 OK avec l'ID du post distant. Juste après, une coupure réseau transitoire survient vers PostgreSQL. Le bloc `except` global passe le statut du job en `PUBLISH_FAILED`. L'utilisateur ou le scheduler réessaie la tâche : le post est publié une seconde fois sur le réseau social.
- **Cause racine** : Manque de découplage transactionnel entre la capture de l'identifiant distant et la mise à jour finale du statut.
- **Correctif proposé** : Enregistrer de manière prioritaire l'external post ID dans un fichier WAL local ou une table dédiée avant de tenter la finalisation du statut.
- **Test de non-régression** : `tests/unit/test_publisher_idempotency_db_failure.py::test_db_failure_does_not_republish`

---

### [ID: H12] Row-Level Security (RLS) décoratif et non appliqué
- **Statut** : [FAIT VÉRIFIÉ]
- **Sévérité** : Critique (Impact: Élevé, Probabilité: Systématique, Exploitation: Intermédiaire)
- **Localisation** : `infra/migrations/002_rls_policies.sql` ; `apps/api/dependencies.py`
- **Preuve de code** : Les politiques RLS SQL filtrent sur `current_setting('app.current_workspace_id')`, mais le code applicatif Python n'exécute jamais `SET LOCAL app.current_workspace_id = :ws_id` lors de l'ouverture de session SQLAlchemy.
- **Scénario de défaillance** : L'équipe pense être protégée au niveau de la base de données. Un développeur écrit une nouvelle requête sans clause `WHERE workspace_id = :ws_id`. La requête renvoie les données de tous les clients sans restriction.
- **Cause racine** : Politiques SQL rédigées dans un script d'initialisation manuel mais jamais intégrées dans le cycle de vie des sessions de l'ORM.
- **Correctif proposé** : Intégrer l'exécution de `SET LOCAL app.current_workspace_id` dans la dépendance `get_db` dès qu'un utilisateur est authentifié, ou assumer une isolation applicative étanche au niveau Repository avec tests paramétrés cross-tenants.
- **Test de non-régression** : `tests/security/test_rls_session_isolation.py::test_database_enforces_workspace_isolation`

---

### [ID: N1] POST `/v1/workspaces` accepte un `owner_id` arbitraire dans le body
- **Statut** : [FAIT VÉRIFIÉ]
- **Sévérité** : Critique (Impact: Élevé, Probabilité: Élevée, Exploitation: Trivial)
- **Localisation** : `apps/api/routers/workspaces.py:22`
- **Preuve de code** :
  ```python
  @router.post("")
  def create_workspace(req: WorkspaceCreateRequest, current_user: User = Depends(get_current_user)):
      # req.owner_id est pris directement depuis le JSON client sans vérifier qu'il s'agit de current_user.id !
      ws = repo.create_workspace(name=req.name, owner_id=req.owner_id)
      # De plus, aucun enregistrement WorkspaceMemberModel n'est créé !
  ```
- **Scénario de défaillance** : L'utilisateur Alice envoie `{"name": "EvilCorp", "owner_id": "bob_uuid"}`. Bob devient propriétaire sans l'avoir demandé, et Alice n'est même pas inscrite comme membre du workspace qu'elle vient de créer.
- **Cause racine** : Non-liaison de la ressource créée à l'identité authentifiée dans le contexte de la session.
- **Correctif proposé** : Ignorer tout `owner_id` fourni dans le body ; forcer `owner_id = current_user.id` et insérer immédiatement un enregistrement `WorkspaceMemberModel` avec le rôle `owner`.
- **Test de non-régression** : `tests/security/test_workspace_creation_ownership.py::test_create_workspace_binds_authenticated_user`

---

## 3. Synthèse des Findings Élevés et Moyens (C4, C7, C8, C9, H1-H4, H6-H8, H10-H11, H13-H14, N2-N7, X-001-X-010)

| ID | Domaine | Description & Localisation | Correctif Stratégique |
| :--- | :--- | :--- | :--- |
| **C4** | Sécurité | `email_service.py:28` : Envoi d'email factice (`MemoryLogEmailService`) ; vérification désactivée par défaut. | Connecteur transactionnel configurable et `REQUIRE_EMAIL_VERIFICATION=true` en production. |
| **C7** | Fiabilité | `main.py:45` : `SchedulerDispatcher` et `veille_worker` jamais démarrés dans le lifespan. | Supervision asynchrone des daemons dans le lifespan avec backoff exponentiel. |
| **C8** | DevOps | `docker-compose.yml:9` : Mots de passe en clair, ports DB exposés, triple schéma SQL/Alembic. | Unification sur Alembic, passage de secrets via variables d'environnement. |
| **C9** | Fiabilité | `main.py:69` : Lifespan passe aveuglément tous les jobs `PUBLISHING` en `PUBLISH_UNKNOWN`. | Vérification du timestamp d'expiration avant passage en statut inconnu. |
| **H1** | Auth | `auth.py:520` : Révocation immédiate du refresh token sans fenêtre de grâce (déconnexion concurrente). | Transaction atomique avec fenêtre de grâce de 20 secondes pour le refresh token. |
| **H2** | Front | `api.ts:165` : `apiClient` déconnecte sur toute erreur non-OK (ex: 404, 500) et plante sur HTTP 204. | Gestion explicite de 204 (`null`) et déclenchement d'`onAuthFailure` uniquement sur 401. |
| **H3** | Sécurité | `auth.py:363` : Faux hash argon2 invalide provoquant un timing différent (énumération de comptes). | Hash argon2 précalculé standardisé pour égaliser le temps de réponse. |
| **H4** | Auth | `dependencies.py:38` : Sessions fail-open, pas de contrôle de `is_active` ni de révocation. | Contrôle systématique en base du compte actif et validité de la session. |
| **H6** | Sécurité | `limiter.py:38` : Rate limiter basé aveuglément sur `X-Forwarded-For[0]` (spoofable). | Validation de l'IP via `TRUSTED_PROXIES` uniquement. |
| **H7** | FinOps | `auth.py:772` : `DEMO_MODE_ENABLED=true` par défaut avec rôle Owner d'office. | Défaut à `false` et restriction stricte des privilèges démo. |
| **H8** | Qualité | `content.py:246` : Feedback de réécriture LLM concaténé dans le post public en cas d'erreur. | Échec explicite sans mutation du contenu original. |
| **H10** | Front/Sec | `oauth.py:370` : Script inline bloqué par CSP stricte et `account_name` non échappé. | Externalisation du script JS de callback et assainissement HTML strict. |
| **H11** | Données | `main.py:88` : Utilisateur de test `owner_martial` injecté en dur en base. | Conditionnement strict des seeds à `APP_ENV=development` et flag explicite. |
| **H13** | DB | `database.py:27` : `scoped_session` mélangé à `SessionLocal` manuel dans les dépendances. | Standardisation sur le pattern `yield db` avec fermeture garantie. |
| **H14** | RGPD | `production.py:89` : Fallback silencieux vers Gemini ignorant les contraintes de souveraineté. | Interdiction de fallback cross-fournisseur sans accord préalable du workspace. |
| **N2** | RBAC | `dependencies.py:78` : Passe-droit universel pour le rôle Owner sur des routes réservées. | Application stricte du principe de séparation des devoirs. |
| **N3** | FinOps | `circuit_breaker.py:126` : `CycleBudget` défini mais jamais injecté dans les nœuds LangGraph. | Injection et contrôle du budget de tokens/temps à chaque nœud du pipeline. |
| **N4** | DB | `repository.py:64` : `ensure_workspace()` crée silencieusement des workspaces fantômes. | Remplacement par une levée d'erreur 404 explicite si le workspace n'existe pas. |
| **N5** | Qualité | Mesure de couverture réelle à 80% inférieure à la consigne CI de 85%. | Écriture de tests unitaires et d'intégration sur les connecteurs et routeurs non couverts. |
| **N6** | CI/CD | `ci.yml:74` : Secrets de test en clair et téléchargement de binaire sans validation sha256. | Épinglage d'empreinte SHA256 et sécurisation des variables de build. |
| **N7** | DB | Absence d'index composites sur les tables de jobs et variantes. | Création d'une migration Alembic dédiée ajoutant les index optimaux. |
| **X-001** | BOLA | Paramètre `workspace_id` optionnel dans `/signals` et `/ideas`. | Rendre le workspace obligatoire et filtrer strictement sur les droits de l'appelant. |
| **X-002** | Auth | Absence d'invalidation des sessions actives lors du reset de mot de passe. | Incrémenter la version du token utilisateur et purger les refresh tokens associés. |
| **X-003** | OAuth | `state` OAuth non adossé à un cookie de session HttpOnly. | Signature cryptographique du `state` lié au client pour prévenir le Login CSRF. |
| **X-004** | DoS | Absence de borne maximale (`le=100`) sur les paramètres `limit` de pagination. | Bornage systématique via `Query(..., ge=1, le=100)`. |
| **X-005** | PII | Traces d'observabilité Langfuse envoyées avec des emails et données en clair. | Application obligatoire de `mask_pii()` avant envoi aux collecteurs externes. |
| **X-006** | Sécurité | Upload d'avatar vérifiant l'extension sans contrôler les octets magiques réels. | Sniffing d'en-tête binaire pour valider l'intégrité MIME réelle de l'image. |
| **X-007** | Multi-Tenant | Cache LLM basé sur le hash du prompt sans inclure le `workspace_id`. | Préfixage obligatoire des clés de cache par le tenant ID. |
| **X-008** | DB | Foreign Keys non indexées dans `publication_jobs` et `content_variants`. | Ajout de `index=True` sur toutes les clés étrangères relationnelles. |
| **X-009** | Qualité | Blocs `except Exception: pass` silencieux dans les connecteurs. | Logging contextuel explicite et typage des exceptions. |
| **X-010** | CI/CD | Absence d'analyse statique SAST automatisée dans le workflow GitHub Actions. | Intégration de Semgrep et vérification d'empreinte binaire. |
