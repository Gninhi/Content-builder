# Runbook : Reconnexion d'un Compte Social & Gestion de l'Expiration des Jetons

## Contexte & Architecture des Jetons
ContentOps Harness s'interface avec LinkedIn et X via des jetons OAuth 2.0 sécurisés :
- **LinkedIn** : Jetons d'accès utilisateur à 3 volets d'une durée d'environ 60 jours. L'API standard LinkedIn n'émet pas de jeton de rafraîchissement (refresh token) pour les portées membres ; une reconnexion manuelle est requise avant expiration.
- **X (Twitter)** : Jetons d'accès à durée courte (~2 heures) accompagnés d'un `refresh_token` rotatif persistant. Si le rafraîchissement échoue (400/401 invalid_grant) ou si l'utilisateur a révoqué l'application, une reconnexion est requise.

## Seuil d'Alerte Préventive J-7
Pour LinkedIn, le connecteur `LinkedInSocialPublisher` applique une sécurité préventive intégrée (`TokenExpiringSoonError`) :
- Dès que `token_expires_at <= now + 7 jours`, toute tentative de publication est bloquée avec alerte explicite afin d'éviter les pannes silencieuses.
- Le statut du compte passe à `RECONNECT_REQUIRED` dans la base de données.

## Procédure de Reconnexion (Rôle OWNER Requis)

### 1. Identifier les comptes nécessitant une reconnexion
Interroger l'endpoint d'inventaire sécurisé :
```bash
curl -X GET "https://api.contentops.company.com/v1/oauth/accounts" \
  -H "Authorization: Bearer <OWNER_JWT_TOKEN>"
```
Vérifier les comptes dont le statut est `RECONNECT_REQUIRED` ou dont `expires_at` est proche de l'échéance.

### 2. Déclencher un nouveau flux OAuth
L'utilisateur OWNER du workspace initie une nouvelle autorisation :
```bash
curl -X GET "https://api.contentops.company.com/v1/oauth/start/linkedin" \
  -H "Authorization: Bearer <OWNER_JWT_TOKEN>"
```
Réponse :
```json
{
  "authorization_url": "https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=...&state=...",
  "state": "...",
  "provider": "linkedin",
  "status": "INITIATED"
}
```

### 3. Compléter l'accord dans le navigateur
1. Naviguer vers l'URL fournie.
2. Consentir aux autorisations (`openid`, `profile`, `w_member_social`).
3. Le navigateur est redirigé vers le callback configuré :
   `GET /v1/oauth/callback/linkedin?code=...&state=...`
4. Les nouveaux jetons sont chiffrés immédiatement en base de données et le statut repasse à `ACTIVE`.

### 4. Déconnexion Manuelle d'Urgence
Pour forcer la révocation et la suppression des jetons en base :
```bash
curl -X POST "https://api.contentops.company.com/v1/oauth/disconnect/linkedin" \
  -H "Authorization: Bearer <OWNER_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"account_id": "urn:li:person:sub_id"}'
```
Les clés et jetons sont purgés du coffre chiffré et le compte est marqué `REVOKED`.
