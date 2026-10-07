# ContentOps Harness — Journal de Reprise (PROGRESS.md)

**Branche active :** `feat/social-prod`  
**Dernière mise à jour :** 2026-10-07  
**Ingénieur responsable :** Staff Backend / Sécurité / Fiabilité

---

## État d'avancement par Phase

- [x] **Phase 0 — Preflight & Baseline** : Terminée.
  - Baseline mesurée dans `BASELINE.md`.
  - 78 tests passés (83% couverture globale).
  - 0 secret dans le workspace et l'historique git. `.env` ignoré et non suivi.
  - 96 erreurs Mypy répertoriées initialement.
- [x] **Phase 1 — Preliminary Independent Audit (Read-Only)** : Terminée.
  - `AUDIT_V2.md` rédigé avec statut mesuré et preuves pour les 10 affirmations ciblées.
  - Sources externes vérifiées et consignées dans `docs/sources.md` (LinkedIn Posts API, X API v2, Gemini 3.8 Flash, Langfuse).
  - Identification de 4 findings Critiques, 5 Élevées, 4 Moyennes, 1 Faible.
- [x] **Phase 2 — Deep Control (Reproduction Tests)** : Terminée.
  - Suite de reproduction d'attaque `tests/security/test_reproduction_attacks.py` écrite et validée : toutes les failles Critiques/Élevées ont échoué contre le code non remédié.
- [x] **Phase 3 — Remediation** : Terminée.
  - 100% des findings Critiques, Élevées et Moyennes résolus via des commits atomiques dédiés.
  - Verrou de publication transactionnel en base (`UPDATE ... WHERE status = 'SCHEDULED'`).
  - `ENV` forcé à `production` par défaut (fail-closed), `/v1/auth/dev-token` bloqué sauf si `ENV=dev`.
  - BOLA / IDOR inter-workspaces éliminé (suppression du contournement rôle Owner).
  - Rotation de clés JWT avec `kid` et validation stricte.
  - Coffre OAuth persisté en base de données (`ConnectedSocialAccountModel`) avec chiffrement AES-GCM 256 bits, AAD workspace_id, et version de clé `kid`.
  - Cache LLM déterministe isolé par `workspace_id`.
  - Protection des routes POST et `GET /v1/sources`.
  - Rate limiting distribué Redis et support des proxys de confiance.
  - Réconciliation tarifaire Gemini 3.8 Flash ($0.75 / $3.75).
  - Masquage PII étendu aux jetons LinkedIn, X, Bearer et OAuth PKCE.
  - Règle de transparence IA configurable dans le Quality Gate.
  - Schéma relationnel versionné via Alembic (`286e614508c4_initial_schema.py`) avec tests d'upgrade/downgrade réversibles.
  - Typage Mypy : 0 erreur sur 106 fichiers source.
  - Suite de tests : 94 tests unitaires, d'intégration et de sécurité au vert.
  - Matrice livrée : `REMEDIATION_V2.md`.
- [ ] **Phase 4 — LinkedIn Social Publisher** : En cours.
  - Implémentation de `LinkedInSocialPublisher` héritant de `SocialPublisher`.
  - Profil personnel (`urn:li:person:{sub}` via OpenID `userinfo`).
  - Scopes : `openid profile w_member_social`.
  - Publication via `POST https://api.linkedin.com/rest/posts` avec `LinkedIn-Version` et `X-Restli-Protocol-Version: 2.0.0`.
  - Alerte expiration J-7 et statut reconnexion requise.
- [ ] **Phase 5 — X Social Publisher** : À venir.
  - Implémentation de `XSocialPublisher` héritant de `SocialPublisher`.
  - OAuth 2.0 PKCE, scopes `tweet.read tweet.write users.read offline.access`.
  - Publication `POST https://api.x.com/2/tweets`, rafraîchissement atomique des jetons, plafonds stricts.
- [ ] **Phase 6 — OAuth 2.0 Flow (PKCE, State, Vault DB Persist)** : À venir.
  - Routes `/v1/oauth/start/{provider}` et `/v1/oauth/callback/{provider}`.
- [ ] **Phase 7 — Publishing Pipeline (At-Most-Once, Kill Switch, Reconciliation)** : À venir.
  - Transition `PUBLISHING` -> `PUBLISHED` / `PUBLISH_UNKNOWN`.
- [ ] **Phase 8 — Comprehensive Tests Suite (Respx, Redis/Postgres Integration)** : À venir.
- [ ] **Phase 9 — Production Readiness & Runbooks** : À venir.
- [ ] **Phase 10 — Live Smoke Validation** : À venir (guidée avec l'utilisateur).

---

## Décisions Clés & Architecture (Validées en Phase 1)

1. **Q1 — LinkedIn Cible :** Profil personnel uniquement (`openid profile w_member_social`, identifiant `urn:li:person:{sub}`). Pages entreprise hors périmètre v1.
2. **Q2 — Format des Médias :** Texte seul pour la v1. Déterministe et conforme aux limites des plateformes sans flux d'upload binaire lourd.
3. **Q3 — Déploiement Cible :** PostgreSQL managé standard + Redis partagé (pour rate-limiting SlowAPI, verrous distribués et cache LLM).
4. **Q4 — Stratégie JWT :** Tokens JWT émis et signés par l'application. Clé forte obligatoire sans valeur par défaut permissive, support d'identifiant de clé `kid` pour rotation fluide.
5. **Q5 — Volume & Plafonds :** Cadence cible de 2 publications par jour (~60 publications/mois), avec garde-fous de coût stricts et plafonds horaires/mensuels configurables.
6. **Q6 — Transparence IA (EU AI Act) :** Décision éditoriale configurable par workspace / marque (désactivée par défaut, activable via politique de marque dans `BrandProfile`).
7. **Isolation Stricte des Tenants (Fail Closed) :**
   - Le rôle `Owner` est strictement limité à son propre workspace (`user.workspace_id`). Aucune exception cross-tenant ne sera tolérée.
8. **Concurrence & Publication :**
   - Remplacement de la vérification mémoire par un verrou base de données transactionnel (`UPDATE ... WHERE status = 'SCHEDULED'`).
9. **Persistance Sécurisée des Jetons OAuth :**
   - Création du modèle de table `connected_social_accounts` stockant les blobs chiffrés en base de données, associés à un identifiant de clé `kid` pour permettre la rotation sans interruption.
10. **Tarification Gemini 3.8 Flash :**
    - Alignement immédiat sur les tarifs officiels Google AI : $0.75 / 1M tokens d'entrée, $3.75 / 1M tokens de sortie.

---

## Prochaines Actions Immédiates

1. **Phase 4 :** Implémenter le connecteur `LinkedInSocialPublisher` dans `packages/connectors/social/linkedin.py`.
2. **Phase 5 :** Implémenter le connecteur `XSocialPublisher` dans `packages/connectors/social/x_twitter.py`.
3. Écrire les tests unitaires et de contrat correspondants (avec `respx` ou `unittest.mock`).
