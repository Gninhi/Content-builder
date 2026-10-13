# Guide d'Hygiène de Dépôt et Gestion des Secrets (DevSecOps)

Ce document établit les politiques et procédures opérationnelles pour maintenir le dépôt ContentOps Harness (`Content-builder`) rigoureusement exempt de secrets, données sensibles et fuites d'informations.

---

## 1. Principes Fondamentaux de Sécurité du Dépôt

1. **Zero Secret in Code** :
   - Aucun token, clé d'API, mot de passe de base de données, certificat privé ni clé de chiffrement ne doit être commité dans Git.
   - Les variables sensibles sont injectées au runtime via des variables d'environnement (`.env` local exclu de Git) ou via les GitHub Actions Secrets.

2. **Défense en Profondeur** :
   - **Niveau 1 (Local)** : Crochets Git (`pre-commit`) avec Gitleaks et vérification des fichiers volumineux / clés privées.
   - **Niveau 2 (CI/CD)** : Job de sécurité automatisé `gitleaks detect` et `pip-audit` sur chaque Pull Request et Push.
   - **Niveau 3 (GitHub)** : Secret Scanning et Push Protection activés au niveau de l'organisation / dépôt.

---

## 2. Procédure de Rotation des Secrets et Fournisseurs

Lorsqu'un secret est exposé ou suspecté de compromission, sa simple suppression du code ne suffit pas : **il doit être révoqué et régénéré immédiatement chez le fournisseur**.

### 2.1 Checklist par Fournisseur

| Fournisseur | Emplacement Clé | Procédure de Révocation / Régénération | Contrôle d'Activité Récente |
| :--- | :--- | :--- | :--- |
| **NVIDIA API** | `NVIDIA_API_KEY` | 1. Portail NVIDIA Build (build.nvidia.com).<br>2. Onglet *API Keys* -> Supprimer la clé compromise.<br>3. Générer une nouvelle clé `nvapi-...`. | Vérifier le journal des requêtes et le décompte de crédits/tokens. |
| **Google Gemini** | `GOOGLE_API_KEY` | 1. Google AI Studio / GCP Console (console.cloud.google.com).<br>2. *APIs & Services* -> *Credentials*.<br>3. Supprimer la clé compromise -> Créer une nouvelle clé avec restriction d'API. | Consulter *Metrics* dans GCP Console pour détecter tout pic anormal. |
| **Langfuse** | `LANGFUSE_SECRET_KEY` | 1. Dashboard Langfuse -> *Project Settings* -> *API Keys*.<br>2. Révoquer la paire de clés publique/secrète compromise.<br>3. Générer une nouvelle paire. | Vérifier la liste des traces récentes et les adresses IP d'ingestion. |
| **LinkedIn Developer** | `LINKEDIN_CLIENT_SECRET` | 1. Developer Portal (linkedin.com/developers).<br>2. App -> *Auth* -> *OAuth 2.0 settings* -> Régénérer le Secret. | Vérifier la liste des applications autorisées et les webhooks. |
| **X (Twitter)** | `X_API_KEY`, `X_API_SECRET` | 1. X Developer Portal (developer.x.com).<br>2. Projet -> *Keys and Tokens* -> *Regenerate* pour API Key and Secret. | Consulter le tableau de bord d'usage de l'API v2 (Tweets publiés). |
| **Tavily Search** | `TAVILY_API_KEY` | 1. Dashboard Tavily (app.tavily.com).<br>2. Régénérer la clé d'API active. | Contrôler le compteur de requêtes mensuelles. |

### 2.2 Cas Particulier : Rotation de `SECRET_VAULT_KEY` (Chiffrement AES-GCM)

La variable `SECRET_VAULT_KEY` chiffre les tokens d'accès des réseaux sociaux dans la base de données. Modifier brutalement cette clé rendrait illisibles les tokens existants.

**Procédure de rotation sans interruption de service :**
1. Générer une nouvelle clé de 256 bits (32 octets hex/base64).
2. Définir un identifiant de clé (ex: `v2`).
3. Alimenter le trousseau de clés via `SECRET_VAULT_KEY_RING` au format JSON :
   ```json
   {"v1": "ancienne-cle-32-chars", "v2": "nouvelle-cle-32-chars"}
   ```
4. Définir `ACTIVE_VAULT_KEY_ID=v2`.
5. Exécuter le script de migration/rechiffrement :
   ```bash
   python -m packages.security.vault_rotate --from-kid v1 --to-kid v2
   ```
6. Une fois tous les enregistrements rechiffrés sous `v2`, supprimer `v1` du trousseau.

---

## 3. Plan de Réponse à Incident (Fuite de Secret Post-Publication)

Si un secret est commité ou poussé publiquement :

1. **Révocation immédiate** chez le fournisseur (priorité absolue).
2. **Évaluation de l'exposition** : inspecter les métriques et journaux d'accès du fournisseur pour déterminer si la clé a été exploitée.
3. **Purge de l'historique** :
   ```bash
   git filter-repo --replace-text <(echo "VALEUR_EXACTE==>REDACTED")
   ```
4. **Force-push contrôlé** sur la branche concernée.
5. **Contact du support GitHub** si l'historique a été cloné ou forké afin d'évacuer les caches internes.
6. **Rédaction d'un postmortem de sécurité** consignant l'origine, la durée d'exposition et les mesures préventives adoptées.
