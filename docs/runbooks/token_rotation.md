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

### 1. Rotation de la clé maîtresse OAuth Vault (`SECRET_VAULT_KEY`) avec Key ID (`kid`)
1. Générer une nouvelle clé aléatoire de 32 octets minimum :
   ```bash
   openssl rand -hex 32
   ```
2. Définir le porte-clé dans l'environnement avec le nouveau `ACTIVE_VAULT_KEY_ID` (ex: `v2`) et l'ancien conservé pour le déchiffrement transparent :
   ```bash
   export ACTIVE_VAULT_KEY_ID=v2
   export SECRET_VAULT_KEY_RING='{"v1": "<ancienne_cle>", "v2": "<nouvelle_cle>"}'
   ```
3. Ré-encrypter les enregistrements vers la clé active via le script de maintenance ou la méthode `vault.reencrypt_all(target_key_id="v2")`.
4. Une fois tous les comptes migrés vers `v2`, l'ancienne clé `v1` peut être révoquée du porte-clé.

### 2. Rotation du JWT Secret (`JWT_SECRET_KEY`) sans coupure
1. Générer un nouveau secret fort (>= 32 caractères) :
   ```bash
   openssl rand -base64 32
   ```
2. Configurer le porte-clé de transition dans `JWT_ROTATION_KEYS` :
   ```bash
   export JWT_KEY_ID=jwt_v2
   export JWT_SECRET_KEY="<nouveau_secret_jwt>"
   export JWT_ROTATION_KEYS="jwt_v1:<ancien_secret_jwt>"
   ```
3. Les nouveaux jetons sont signés avec l'en-tête `{"kid": "jwt_v2"}`. Les jetons émis avec `jwt_v1` continuent d'être validés sans interruption jusqu'à leur expiration (60 min).
4. Après 60 minutes, supprimer `JWT_ROTATION_KEYS`.


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
