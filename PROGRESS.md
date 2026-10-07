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
  - 96 erreurs Mypy répertoriées.
- [x] **Phase 1 — Preliminary Independent Audit (Read-Only)** : Terminée.
  - `AUDIT_V2.md` rédigé avec statut mesuré et preuves pour les 10 affirmations ciblées.
  - Sources externes vérifiées et consignées dans `docs/sources.md` (LinkedIn Posts API, X API v2, Gemini 3.8 Flash, Langfuse).
  - Identification de 4 findings Critiques, 5 Élevées, 4 Moyennes, 1 Faible.
  - Questions protocolaires Q1-Q6 formulées.
- [ ] **Phase 2 — Deep Control (Reproduction Tests)** : En cours.
  - Écriture des tests d'attaque reproduisant les failles Critiques et Élevées (BOLA, concurrency race condition, cross-tenant cache leak, dev-token open default).
- [ ] **Phase 3 — Remediation** : À venir.
  - Résolution des findings Critiques/Élevées, puis Moyennes.
  - Correction des 96 erreurs Mypy.
  - Mise en place d'Alembic avec tests de migration.
  - Rédaction de `REMEDIATION_V2.md`.
- [ ] **Phase 4 — LinkedIn Social Publisher** : À venir.
- [ ] **Phase 5 — X Social Publisher** : À venir.
- [ ] **Phase 6 — OAuth 2.0 Flow (PKCE, State, Vault DB Persist)** : À venir.
- [ ] **Phase 7 — Publishing Pipeline (At-Most-Once, Kill Switch, Reconciliation)** : À venir.
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
   - Remplacement de la vérification mémoire par un verrou base de données transactionnel (`SELECT ... FOR UPDATE` ou mise à jour atomique conditionnelle `UPDATE ... WHERE status = 'SCHEDULED'`).
9. **Persistance Sécurisée des Jetons OAuth :**
   - Création du modèle de table `connected_social_accounts` stockant les blobs chiffrés en base de données, associés à un identifiant de clé `kid` pour permettre la rotation sans interruption.
10. **Tarification Gemini 3.8 Flash :**
   - Alignement immédiat sur les tarifs officiels Google AI : $0.75 / 1M tokens d'entrée, $3.75 / 1M tokens de sortie.

---

## Prochaines Actions Immédiates

1. Poser les questions de cadrage (Q1 à Q6) selon `<question_protocol>` en utilisant `ask_question`.
2. Passer à la Phase 2 : Rédiger les tests de reproduction d'attaque locaux qui échouent avant correction.
