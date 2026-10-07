# Sources Officielles et Références Techniques

Ce document consigne les documentations officielles consultées, les versions d'API et les dates de vérification pour garantir que le code du ContentOps Harness s'appuie sur des spécifications réelles et actuelles.

---

## 1. Google Gemini & AI Studio

- **Source officielle :** [Google AI Pricing](https://ai.google.dev/pricing)
- **Date de vérification :** 2026-10-07
- **Modèle cible :** `gemini-3.8-flash`
- **Spécifications tarifaires (Tarifs en vigueur jusqu'au 31 décembre 2026) :**
  - **Input Tokens (prompt) :** $0.75 par million de tokens ($0.00075 par 1K tokens)
  - **Output Tokens (completion / thinking) :** $3.75 par million de tokens ($0.00375 par 1K tokens)
  - **Context Caching (Lecture) :** $0.075 par million de tokens
  - **Context Caching (Stockage) :** $0.50 par 1M tokens par heure
  - **Batch API :** Réduction de 50% sur les tarifs standards
  - **Search Grounding :** 5 000 requêtes gratuites/mois, puis $14 par 1 000 requêtes

---

## 2. LinkedIn API & Microsoft Learn

- **Sources officielles :**
  - [LinkedIn Share on LinkedIn](https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin)
  - [LinkedIn Sign In with LinkedIn using OpenID Connect](https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/sign-in-with-linkedin)
  - [LinkedIn Posts API Reference](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api)
- **Date de vérification :** 2026-10-07
- **Spécifications d'authentification :**
  - **Protocole :** OAuth 2.0 Authorization Code Flow
  - **Scopes requis :** `openid`, `profile`, `w_member_social`
  - **Scope obsolète (DEPRECATED) :** `r_liteprofile` (remplacé par OpenID Connect)
  - **Userinfo Endpoint :** `GET https://api.linkedin.com/v2/userinfo`
  - **Identifiant auteur :** `urn:li:person:{sub}` où `{sub}` est extrait de `userinfo`
- **Spécifications de publication :**
  - **Endpoint de publication :** `POST https://api.linkedin.com/rest/posts`
  - **En-têtes obligatoires :**
    - `LinkedIn-Version: 202601` (format YYYYMM, configurable via `LINKEDIN_API_VERSION`)
    - `X-Restli-Protocol-Version: 2.0.0`
    - `Authorization: Bearer {access_token}`
    - `Content-Type: application/json`
  - **Format Payload (Texte seul) :**
    ```json
    {
      "author": "urn:li:person:{sub}",
      "commentary": "Texte du post...",
      "visibility": "PUBLIC",
      "distribution": {
        "feedDistribution": "MAIN_FEED",
        "targetEntities": [],
        "thirdPartyDistributionChannels": []
      },
      "lifecycleState": "PUBLISHED",
      "isReshareDisabledByAuthor": false
    }
    ```
  - **En-tête de retour de création :** `x-restli-id: {urn:li:share:... ou urn:li:ugcPost:...}`
  - **Cycle de vie du jeton :** Durée de vie access token ~60 jours. Aucun refresh token disponible en libre-service classique pour les apps membres. Statut "reconnexion requise" à déclencher à J-7 de l'expiration.

---

## 3. X (Twitter) Developer Platform API v2

- **Sources officielles :**
  - [X API v2 Tweets Reference](https://developer.x.com/en/docs/x-api/tweets/manage-tweets/api-reference/post-tweets)
  - [X OAuth 2.0 Authorization Code Flow with PKCE](https://developer.x.com/en/docs/authentication/oauth-2-0/authorization-code-with-pkce)
  - [X Rate Limits and Usage](https://developer.x.com/en/docs/x-api/rate-limits)
- **Date de vérification :** 2026-10-07
- **Spécifications d'authentification :**
  - **Protocole :** OAuth 2.0 Authorization Code avec PKCE (S256), client confidentiel.
  - **Endpoint d'autorisation :** `https://x.com/i/oauth2/authorize`
  - **Endpoint de jetons :** `https://api.x.com/2/oauth2/token`
  - **Scopes requis :** `tweet.read`, `tweet.write`, `users.read`, `offline.access`
  - **Access Token TTL :** Courte durée (~2 heures).
  - **Refresh Token :** Utilise `offline.access`. Renouvellement avec rotation obligatoire : chaque utilisation de refresh token en délivre un nouveau qu'il faut persister immédiatement et de manière atomique.
- **Spécifications de publication :**
  - **Endpoint de création :** `POST https://api.x.com/2/tweets`
  - **Format Payload (Texte) :** `{"text": "Contenu du tweet..."}`
  - **Endpoint de suppression :** `DELETE https://api.x.com/2/tweets/{id}`
  - **Endpoint de métriques :** `GET https://api.x.com/2/tweets/{id}?tweet.fields=public_metrics`
  - **En-têtes de limitation :** `x-rate-limit-limit`, `x-rate-limit-remaining`, `x-rate-limit-reset`
  - **Gestion des erreurs spécifiques :**
    - `401 Unauthorized` : Déclenche refresh token atomique sous verrou.
    - `402 / 403 Forbidden` (Crédits ou accès) : Traité comme non réessayable, fail closed.
    - `429 Too Many Requests` : Respect strict du timestamp `x-rate-limit-reset`.

---

## 4. Langfuse Observability SDK

- **Source officielle :** [Langfuse Documentation](https://langfuse.com/docs)
- **Version installée :** `langfuse>=2.0.0`
- **Méthodes clés :**
  - Initialisation : `Langfuse(public_key=..., secret_key=..., host=...)`
  - Callback LangChain : `langfuse.langchain.CallbackHandler(public_key=...)`
  - Enregistrement de scores : `client.create_score(trace_id=..., name=..., value=..., comment=...)`
  - Flush asynchrone / fermeture propre : `client.flush()` et `client.shutdown()`

---

## 5. FastAPI, SlowAPI & SQLAlchemy

- **FastAPI / SlowAPI :** SlowAPI s'appuie sur `limits` qui nécessite `storage_uri="redis://..."` pour les environnements multi-workers.
- **SQLAlchemy 2.0 :** Utilisation de `with_for_update()` sur PostgreSQL pour garantir l'exclusion mutuelle (`SELECT ... FOR UPDATE`).
