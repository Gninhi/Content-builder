# Runbook : Procédure de Rotation des Secrets et Tokens

## Fréquence
- Tous les 90 jours pour les clés d'API LLM et de recherche.
- Tous les 60 jours pour le `JWT_SECRET_KEY` et les jetons OAuth2 sociaux.
- Immédiatement en cas de suspicion de fuite ou compromission.

## Règles de Sécurité
- Aucun token ou clé secrète ne doit figurer dans les commits Git, les prompts, les traces Langfuse ou les tables de la base de données.
- Utiliser le `PIIRedactor` et `StructuredJSONFormatter` pour la censure automatique des logs.
- Les tokens OAuth sociaux sont obligatoirement chiffrés au repos via `EncryptedOAuthTokenVault` avec chiffrement authentifié AES-GCM 256 bits et clé maîtresse `SECRET_VAULT_KEY`.

## Procédure

### 1. Rotation de la clé maîtresse OAuth Vault (`SECRET_VAULT_KEY`)
1. Générer une nouvelle clé aléatoire de 32 octets minimum :
   ```bash
   openssl rand -hex 32
   ```
2. Mettre à jour la variable `SECRET_VAULT_KEY` dans le gestionnaire de secrets sécurisé (Vault / AWS Secrets Manager).
3. Exécuter la rotation des jetons via la méthode `vault.rotate_token(...)`.

### 2. Rotation du JWT Secret (`JWT_SECRET_KEY`)
1. Générer une nouvelle chaîne aléatoire :
   ```bash
   openssl rand -base64 32
   ```
2. Remplacer `JWT_SECRET_KEY` dans l'environnement.
3. Les tokens précédents seront invalidés après leur période d'expiration naturelle (60 min).

### 3. Clés d'API Tiers (Google Gemini, Langfuse, Tavily)
1. Générer le nouveau secret sur la console plateforme (Google AI Studio, Langfuse, Tavily).
2. Déployer la variable d'environnement sur les conteneurs.
3. Redémarrer l'application avec rechargement sans interruption :
   ```bash
   kill -HUP $(pgrep uvicorn)
   ```
4. Exécuter un test de santé et de préparation :
   ```bash
   curl -s http://localhost:8000/health
   curl -s http://localhost:8000/ready
   ```
