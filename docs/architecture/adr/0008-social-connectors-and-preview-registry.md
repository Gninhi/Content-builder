# ADR-0008 : Abstraction Extensible des Connecteurs Sociaux et Stratégie de Prévisualisation Frontend (SOLID / OCP / LSP)

**Date :** 10 Octobre 2026  
**Statut :** Accepté  
**Décideurs :** Principal Software Architect & Full-Stack Security Auditor  
**Consulté :** Équipes Backend, Frontend & DevSecOps  

---

## 1. Contexte et Problématique

Lors de l'audit de code approfondi de ContentOps Harness (Content-builder), plusieurs violations architecturales majeures ont été identifiées :

1. **Violation du principe Open/Closed (OCP) et Liskov Substitution (LSP) sur les connecteurs sociaux backend :**
   - Les connecteurs `LinkedInSocialPublisher`, `XSocialPublisher` et `SandboxSocialPublisher` implémentaient des interfaces asymétriques avec des logiques de rejeu (`retry`) ad-hoc et des exceptions non normalisées.
   - L'ajout d'une nouvelle plateforme (ex. Bluesky, Threads, Mastodon) imposait de modifier directement les branches conditionnelles du worker `services/publisher/worker.py`.
   - Certaines implémentations de retry automatique menaçaient le garde-fou critique de publication « au plus une fois » (*at-most-once delivery*), avec un risque de double diffusion en cas de timeout réseau.

2. **Violation de l'Open/Closed Principle sur les prévisualisations frontend :**
   - Le composant `PlatformPreview.tsx` comportait des blocs conditionnels imbriqués pour chaque réseau social (`if (platform === 'linkedin') ... else if (platform === 'x') ...`), empêchant toute extension modulaire.

3. **Monolithisme des écrans frontend :**
   - `UserProfileScreen.tsx` (1136 lignes), `InboxScreen.tsx` (635 lignes) et `CalendarScreen.tsx` (417 lignes) concentraient logique métier, requêtes réseau, gestionnaires d'événements clavier, formulaires et modales, compliquant la testabilité et la maintenance.

---

## 2. Décisions d'Architecture

### A. Backend : `BaseSocialPublisher` et `SocialPublisherRegistry`
- **Contrat Abstraction Unified (`packages/connectors/social/base.py`) :**  
  Définition d'une classe abstraite `BaseSocialPublisher` imposant :
  - `platform_name: str`
  - `max_chars: int`
  - `publish(content_payload, credentials, idempotency_key) -> SocialPublishResult`
  - `validate_content(content_payload) -> Tuple[bool, Optional[str]]`
  - `get_rate_limit_status(credentials) -> Dict[str, Any]`
- **Registre dynamique déclaratif (`SocialPublisherRegistry`) :**  
  Toutes les plateformes s'enregistrent via `@SocialPublisherRegistry.register("plateforme")`.  
  Le worker `services/publisher/worker.py` résout désormais la classe de connecteur via `SocialPublisherRegistry.get_publisher_class(...)`, éliminant tout branchement conditionnel en dur.
- **Test de Caractérisation de Liskov (`tests/unit/test_connector_liskov_characterization.py`) :**  
  Vérification formelle que tout connecteur enregistré peut être substitué sans régression comportementale, avec propagation déterministe des exceptions réseau et d'authentification.

### B. Frontend : Stratégie de Prévisualisation (`PlatformPreviewRegistry`)
- `apps/web/src/components/common/PlatformPreview.tsx` applique le patron de conception **Strategy** :
  - `LinkedInPreviewStrategy`
  - `XPreviewStrategy`
  - `PlatformPreviewRegistry` central
- Les prévisualisations sont découplées, internationalisées (FR/EN) et enrichies de compteurs de caractères précis par rapport aux limites réelles des plateformes (3000 car. LinkedIn, 280 car. X).

### C. Dé-monolithisation des Écrans (Single Responsibility Principle)
- **`UserProfileScreen.tsx` :** Découpé en 6 sous-composants tabulaires isolés (`PersonalInfoTab`, `PreferencesTab`, `NotificationsTab`, `SecurityTab`, `WorkspacesTab`, `GdprTab`).
- **`InboxScreen.tsx` :** Découplé en sous-composants dédiés (`InboxQualityGateCard`, `InboxDraftList`, `InboxEditForm`, `InboxActionBar`, `InboxFeedbackModal`, `InboxShortcutsModal`) et un hook réutilisable `useHitlShortcuts.ts` qui protège la saisie textuelle contre le déclenchement intempestif des raccourcis clavier.
- **`CalendarScreen.tsx` :** Découpé en `CalendarSlotCard`, `CalendarListView` (avec bascule Mois/Semaine/Liste) et `CalendarRescheduleModal`.

### D. Authentification d'Entreprise et Isolation du Jeton Dev
- Création du point d'accès `POST /v1/auth/login` vérifiant l'empreinte de mot de passe par hachage Argon2id, créant une session traçable en base de données et émettant un jeton JWT d'accès.
- Isolation stricte du mode développeur (`POST /v1/auth/dev-token`) : l'interface ne présente l'accès jeton de test qu'en environnement de développement (`import.meta.env.DEV`), la production basculant sur l'authentification d'entreprise standard.

---

## 3. Garde-Fous Préservés

1. **Validation humaine obligatoire (HITL) :** Le flux d'approbation et les raccourcis clavier (J/K/A/R/X) restent strictement identiques.
2. **Publication au plus une fois (*At-Most-Once Delivery*) :** L'état `PUBLISHING` est scellé en base de données avant tout appel réseau ; en cas d'expiration ou d'interruption réseau, le statut passe en `PUBLISH_UNKNOWN` sans rejeu automatique.
3. **Mémoire volatile des jetons :** Aucun jeton JWT n'est persisté dans `localStorage` ou `sessionStorage`.

---

## 4. Conséquences et Validation

- **Couverture de tests :**  
  - Backend : 162/162 tests réussis (100% vert, incluant les tests de caractérisation de Liskov, l'authentification Argon2id et la résilience).
  - Frontend : 32/32 tests réussis en 1.0s (100% vert, incluant Vitest, React Testing Library, accessibilité et hook de raccourcis).
- **Extensibilité :** L'ajout d'une 3ème plateforme sociale ne nécessite désormais qu'une nouvelle classe héritant de `BaseSocialPublisher` et un composant de stratégie de prévisualisation enregistré dans le registre frontend.
