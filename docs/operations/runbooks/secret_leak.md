# Runbook : Réponse à Incident en Cas de Fuite de Secret (secret_leak.md)

Ce runbook détaille les mesures immédiates et obligatoires à appliquer si un secret ou une clé d'API venait à atteindre le dépôt GitHub distant.

---

## ⚠️ Règle Fondamentale

> **TOUT SECRET PUBLIÉ SUR UN DÉPÔT (MÊME PRIVÉ, MÊME SUPPRIMÉ RAPIDEMENT) DOIT ÊTRE CONSIDÉRÉ COMME IMMÉDIATEMENT COMPROMIS.**  
> Les clones, forks et caches GitHub peuvent conserver l'empreinte du secret. La réécriture d'historique ne remplace JAMAIS la révocation immédiate.

---

## Procédure en 6 Étapes

### Étape 1 : Notification & Mobilisation Immédiate
- Informer le propriétaire du dépôt (`@Gninhi`).
- Créer un canal d'incident sécurisé hors ligne.
- Ne pas commenter publiquement la valeur ou la nature exacte du secret sur des issues publiques.

### Étape 2 : Révocation & Rotation Immédiate (AVANT toute manipulation Git)
Régénérer et révoquer immédiatement la clé auprès du fournisseur concerné :

1. **Clé Google Gemini** :
   - Accéder à la [Google Cloud Console / Google AI Studio](https://aistudio.google.com/app/apikey).
   - Supprimer immédiatement la clé compromise.
   - Générer une nouvelle clé restreinte et mettre à jour le fichier `.env` local ou GitHub Secrets.
2. **Langfuse (Public / Secret Key)** :
   - Se connecter à [cloud.langfuse.com](https://cloud.langfuse.com).
   - Créer un nouveau jeu d'API keys dans les paramètres de projet.
   - Révoquer l'ancien jeu de clés.
3. **Jetons & Secrets OAuth (LinkedIn / X)** :
   - Révoquer les jetons clients sur les portails développeurs [LinkedIn Developer Portal](https://www.linkedin.com/developers/) et [X Developer Portal](https://developer.x.com/).
   - Purger les tokens chiffrés du coffre SQLite/PostgreSQL si applicable.
4. **Secret Maître du Coffre (`SECRET_VAULT_KEY`) & Secret JWT (`JWT_SECRET_KEY`)** :
   - Suivre la procédure de rotation sans coupure documentée dans [token_rotation.md](token_rotation.md).

### Étape 3 : Audit d'Usage Anormal Côté Fournisseur
- Consulter les journaux d'accès et métriques d'utilisation (Google Cloud Audit Logs, Langfuse traces, Twitter API usage) pour détecter toute consommation anormale, surcoût ou requête suspecte survenue entre le moment de la fuite et la révocation.

### Étape 4 : Nettoyage de l'Historique Git
- **Sur une copie locale propre** (après vérification d'un clone miroir de sauvegarde hors dépôt) :
  ```bash
  # Exemple avec git-filter-repo
  git filter-repo --replace-text <(echo "SECRET_VALUE==>REDACTED")
  ```
- Vérifier avec `gitleaks detect` et `trufflehog git file://$(pwd)`.

### Étape 5 : Purge des Vues en Cache GitHub
- Contacter le support GitHub ou ouvrir une demande de purge des commits orphelins (GitHub ref cache purge) si le secret a été indexé.
- Forcer la mise à jour des branches avec l'accord explicite écrit du propriétaire.

### Étape 6 : Post-Mortem & Amélioration Continue
- Rédiger un compte-rendu d'incident consignant :
  - La cause racine de l'introduction du secret (hook manquant, ajout manuel forcé, etc.).
  - Le délai de détection et le délai de révocation (MTTR).
  - Les actions préventives (renforcement du hook `.pre-commit-config.yaml` et activation de GitHub Push Protection).
