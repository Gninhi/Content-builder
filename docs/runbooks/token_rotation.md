# Runbook : Procédure de Rotation des Secrets et Tokens

## Fréquence
- Tous les 90 jours pour les clés d'API LLM et de recherche.
- Tous les 60 jours pour les jetons OAuth2 sociaux (LinkedIn, X).
- Immédiatement en cas de suspicion de fuite ou compromission.

## Règles de Sécurité
- Aucun token ou clé secrète ne doit figurer dans les commits Git, les prompts, les traces Langfuse ou les tables de la base de données.
- Utiliser le `PIIRedactor` pour vérifier la censure automatique.

## Procédure
1. Générer le nouveau secret sur la console plateforme (ex: Google AI Studio, Langfuse, Tavily, LinkedIn Developers).
2. Mettre à jour le fichier d'environnement ou le gestionnaire de secrets (ex: AWS Secrets Manager, Vault) :
   ```ini
   GOOGLE_API_KEY=AIzaSy-nouveau-secret...
   LANGFUSE_SECRET_KEY=sk-lf-nouveau-secret...
   TAVILY_API_KEY=tvly-nouveau-secret...
   ```
3. Redémarrer l'application avec rechargement sans interruption :
   ```bash
   kill -HUP $(pgrep uvicorn)
   ```
4. Exécuter un test de santé :
   ```bash
   curl -s http://localhost:8000/health
   ```
