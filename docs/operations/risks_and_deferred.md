# Matrice des Risques Résiduels & Éléments Reportés

**Date :** 10 Octobre 2026  
**Système :** ContentOps Harness (Content-builder)  
**Auteur :** Directeur de Conception Produit & Ingénieur Full-Stack Senior  

---

## 1. Risques Résiduels Analysés & Mitigations

| # | Risque Résiduel | Impact | Probabilité | Niveau | Mesures de Mitigation en Place |
|---|---|---|---|---|---|
| **R-01** | **Révocation / Expiration de session en mémoire volatile** | Faible | Moyenne | **Faible** | Le jeton JWT n'étant pas persisté dans `localStorage`, un rafraîchissement complet (`F5`) par l'utilisateur réinitialise la session. Un message clair avertit l'utilisateur et un bandeau d'expiration propose une reconnexion immédiate sans perte de données saisies (formulaires locaux protégés). |
| **R-02** | **Publication au statut `PUBLISH_UNKNOWN` lors d'un timeout réseau externe** | Moyen | Faible | **Moyen** | Si l'appel réseau vers l'API LinkedIn ou X dépasse 5000ms ou subit une rupture de socket après l'envoi, le statut bascule en `PUBLISH_UNKNOWN`. **Aucun retry automatique n'est déclenché** (invariant au-plus-une-fois). Une procédure de réconciliation manuelle assistée est documentée dans [`docs/operations/runbooks/publish_unknown_recovery.md`](runbooks/publish_unknown_recovery.md). |
| **R-03** | **Débit de requêtes et quota d'appels LLM (Gemini / NVIDIA)** | Moyen | Moyenne | **Moyen** | Disjoncteur automatique (`CircuitBreaker`) actif côté backend avec bascule en mode dégradé déterministe (fallback sans IA ou arrêt temporaire de l'enrichissement sans impacter la validation humaine). Runbook : [`docs/operations/runbooks/llm_circuit_breaker.md`](runbooks/llm_circuit_breaker.md). |
| **R-04** | **Conflit de permissions lors de la rotation de rôle en temps réel** | Faible | Faible | **Faible** | Le backend réévalue systématiquement le rôle dans la base de données et dans les dépendances FastAPI (`get_current_user`, `require_role`) à chaque requête protégée. Même si l'UI affichait un état désynchronisé, aucune action non autorisée ne peut franchir le serveur. |

---

## 2. Éléments Reportés & Justifications Techniques

| Réf | Fonctionnalité Reportée | Justification du Report | Plan d'Exécution Futur |
|---|---|---|---|
| **DEF-01** | **Authentification WebAuthn / FIDO2 (Passkeys matérielles)** | Non requis pour la refonte actuelle ; l'authentification Bearer JWT avec coffre OAuth chiffré (AES-GCM 256) et conformité multi-tenant couvre 100% des exigences actuelles. | Évalué pour la Roadmap Q1 2027 dans le cadre de l'extension de gouvernance bancaire. |
| **DEF-02** | **Éditeur Rich-Text WYSIWYG complexe (Canvas/TipTap)** | Volontairement écarté au profit d'un composant de saisie `Textarea` haute fidélité avec compteur en temps réel et simulateur d'aperçu réseau direct (`PlatformPreview`). Les réseaux cibles (LinkedIn, X) traitent du texte brut ou du markdown allégé, ce qui évite les décalages de rendu entre l'éditeur et l'aperçu réel. | Prévu uniquement si de nouveaux canaux à formatage étendu (ex: blogs internes, substack) sont intégrés. |
| **DEF-03** | **Driver Navigateur Playwright Cloud pour tests E2E automatisés headless** | Le miroir de téléchargement officiel Playwright pour architecture ARM64 Mac renvoie un code HTTP 404 temporaire (`azureedge.net/playwright-1.57.0-mac-arm64.zip`). La suite de 32 tests unitaires et d'intégration Vitest (`happy-dom`) et 162 tests Pytest fournissent une couverture complète de régression. | À réactiver dès résolution du CDN Playwright externe ou via conteneur Docker Linux standardisé. |
