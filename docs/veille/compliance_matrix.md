# Matrice de Conformité des Connecteurs Sociaux (LinkedIn & X)

Cette matrice formalise l'audit et l'alignement des connecteurs sociaux de **ContentOps Harness** par rapport aux spécifications officielles des API des plateformes en vigueur en 2026.

---

## 1. LinkedIn (API Microsoft Learn & Community Management)

| Exigence Officielle | État Antérieur du Code | Écart Constaté | Correction Apportée & Statut |
| :--- | :--- | :--- | :--- |
| **OAuth 2.0 OpenID Connect**<br>Scopes : `openid profile w_member_social`<br>(`r_liteprofile` déprécié) | Implémenté sur `openid profile w_member_social` | Aucun | Conforme. Résolution de l'auteur via `GET https://api.linkedin.com/v2/userinfo` (`urn:li:person:{sub}`). |
| **Endpoint de Publication**<br>`POST https://api.linkedin.com/rest/posts` | Implémenté avec headers `LinkedIn-Version` et `X-Restli-Protocol-Version: 2.0.0` | Aucun | Conforme. Version par défaut `202601`. |
| **Pages Entreprise (Community Management API)**<br>Support de `urn:li:organization:{id}` et scope `w_organization_social` | Seuls les profils membres (`urn:li:person:...`) étaient ciblés | Impossibilité de publier au nom d'une page entreprise | **Corrigé :** Ajout du support de `organization_urn` dans le constructeur et les options de `publish()`. Résolution automatique vers `urn:li:organization:{id}`. |
| **Plafond de Longueur du Contenu**<br>Entre 10 et 3 000 caractères | Validation `len(body) in [10, 3000]` | Aucun | Conforme. Erreur `ValueError` explicite levée avant tout appel réseau. |
| **Politique At-Most-Once**<br>Interdiction de rejeu aveugle en cas de timeout | Gestion timeout via `SocialPublishUnknownError` | Aucun | Conforme. En cas de timeout réseau, le statut passe en `PUBLISH_UNKNOWN` nécessitant réconciliation manuelle sans rejeu automatique. |
| **Surveillance Expiration Token**<br>Alerte proactive à J-7 avant péremption (~60 jours) | Exception levée si `now + 7j >= token_expires_at` | Aucun | Conforme. `TokenExpiringSoonError` levée pour déclencher la reconnexion avant coupure. |

---

## 2. X / Twitter (X Developer API v2)

| Exigence Officielle | État Antérieur du Code | Écart Constaté | Correction Apportée & Statut |
| :--- | :--- | :--- | :--- |
| **OAuth 2.0 PKCE (S256)**<br>Scopes : `tweet.read tweet.write users.read offline.access` | Implémenté avec PKCE et rotation de refresh token | Aucun | Conforme. Lock thread-safe (`threading.Lock`) sur la rotation atomique du refresh token. |
| **Endpoint de Publication**<br>`POST https://api.x.com/2/tweets` | Implémenté sur l'URL officielle v2 | Aucun | Conforme. Charge utile `{"text": ...}` avec extraction de l'ID publié. |
| **Pondération t.co des URL (23 caractères)**<br>Toute URL compte pour 23 caractères quel que soit son nombre réel de caractères | Mesure brute de `len(body)` sans pondération t.co | Rejet à tort de posts avec URLs longues (ou sous-estimation de courtes URLs) | **Corrigé :** Implémentation de `compute_weighted_length()` avec regex `https?://\S+` appliquant le poids fixe officiel de 23 caractères par URL. |
| **Contrôle Budgétaire & Plafonds d'Usage**<br>Quotas mensuels stricts et surveillance financière | `monthly_limit` et `current_month_publications` vérifiés | Aucun | Conforme. Bloquage fail-closed (`SocialBillingError`) dès que le plafond mensuel est atteint. |
| **Gestion du Rate Limit (429)**<br>Prise en compte de `x-rate-limit-reset` | Extraction du header epoch et calcul du délai `retry_after` | Aucun | Conforme. `SocialRateLimitError` alimente le RateLimiter / CircuitBreaker. |
| **Politique At-Most-Once**<br>Gestion des timeouts | `SocialPublishUnknownError` levée sur timeout | Aucun | Conforme. Zéro risque de double publication de tweet en cas de socket timeout. |

---

## 3. Synthèse d'Audit et Règles Communes
1. **Zéro Scraping :** Les plateformes LinkedIn et X sont accédées exclusivement par les API REST officielles sous jetons OAuth 2.0. Aucun scraping HTML direct n'est autorisé.
2. **Scellement Cryptographique SHA-256 :** Tout contenu destiné à être publié est scellé par une empreinte SHA-256 calculée sur son payload canonique. Toute modification ultérieure sans repassage par le Quality Gate annule la validation (`QA_FAILED`).
3. **Validation Humaine HITL Obligatoire :** Aucun agent ne peut appeler les connecteurs sociaux sans une approbation humaine enregistrée en base (`ContentStatus.APPROVED`).
