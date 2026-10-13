# Audit des Défauts de Données et Incohérences Métier (UI & Backend)

Ce document consigne l'ensemble des défauts de données, anomalies de calcul, métriques fictives et incohérences structurelles identifiés lors de la Phase 0 de la refonte de **ContentOps Harness**.
Conformément aux directives de conception, ces défauts **ne doivent pas être masqués par du design CSS**, mais faire l'objet de correctifs structurels dédiés.

---

## 1. Synthèse des Anomalies Recensées

| Réf | Anomalie constatée | Fichiers concernés | Cause racine technique | Impact utilisateur / Risque | Recommandation de correction |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DATA-01** | **Scores aberrants « 95 / 10 » et « 950% »** | `apps/web/src/screens/IdeationScreen.tsx`<br>`packages/contracts/schemas.py` | Le contrat Pydantic définit `novelty_score`, `relevance_score`, `effort_score` sur une échelle de `0.0` à `10.0`. L'UI supposait une échelle normalisée `[0.0, 1.0]` et appliquait `Math.round(score * 10)` et `Math.round(score * 100)%`. Un score de `9.5` devenait ainsi `95 / 10` ou `950%`. | Perte de crédibilité immédiate de l'outil d'idéation ; métriques absurdes. | Harmoniser l'échelle : normaliser à l'affichage (si `score > 1`, afficher directement `score.toFixed(1) / 10` ou calculer le pourcentage par `(score / 10) * 100`). |
| **DATA-02** | **Métriques fictives du Quality Gate HITL** | `apps/web/src/components/inbox/InboxQualityGateCard.tsx` | Les scores de la carte Quality Gate sont codés en dur dans le JSX : `95 / 100` (Alignement), `0 détecté` (Mots interdits), `Non dupliqué` (Doublons), `Conforme` (Mention IA). Aucune liaison avec le résultat réel du gate retourné par l'API. | Faux sentiment de sécurité ; l'utilisateur croit que les règles de marque sont vérifiées alors qu'il s'agit de texte statique. | Raccorder `InboxQualityGateCard` au payload réel du `QualityGateResult` stocké en base de données ou calculé par l'agent de validation. |
| **DATA-03** | **Statistiques inventées et insights non vides avec 0 donnée** | `apps/web/src/screens/InsightsScreen.tsx` | Les sections « Créneaux Optimaux » (+42% Engagement, +28% Clics) et « Répartition par Plateforme » (LinkedIn 65%, X 35%) sont codées en dur dans le template, même lorsque le workspace a 0 publication et 0 impression. | Rupture du principe d'honnêteté intellectuelle et de gouvernance déterministe. | Remplacer les valeurs statiques par un état vide explicite (« Échantillon insuffisant (< 5 publications) pour calculer les créneaux optimaux ») jusqu'à ce que des métriques réelles soient mesurées. |
| **DATA-04** | **Dépassement systématique de la limite X (818 / 280 caractères)** | `packages/prompts/registry.py`<br>`services/orchestration/nodes/generation.py`<br>`apps/web/src/screens/InboxScreen.tsx` | L'agent de rédaction génère pour X (Twitter) un texte identique ou quasi identique à la variante LinkedIn longue (780 à 820 caractères), sans respecter la contrainte stricte de 280 caractères imposée par la plateforme. | Tous les brouillons X arrivent en alerte rouge « Dépassement de la limite X » dans la boîte HITL, forçant une édition manuelle répétitive. | Renforcer le prompt système et la validation dans le nœud LangGraph pour tronquer ou réécrire en format concis micro-blogging (< 280 caractères) pour la variante X. |
| **DATA-05** | **Doublons d'idées non dédupliqués** | `apps/web/src/screens/IdeationScreen.tsx`<br>`apps/api/routers/ideas.py` | L'exécution successive de recherches sur des thèmes proches insère des idées similaires sans contrôle d'unicité sur le titre ou l'angle, provoquant l'accumulation de cartes quasi identiques. | Encombrement de la vue d'idéation ; dispersion de l'attention de l'équipe éditoriale. | Implémenter un filtre de déduplication par hachage sémantique ou similarité textuelle avant insertion dans la base. |
| **DATA-06** | **Affichage de l'identifiant technique `ws_demo_...` comme titre principal** | `apps/web/src/screens/DashboardScreen.tsx` (ligne 128) | L'UI affiche `session?.workspace_id || 'ws_default'` en titre h2 (« Espace Éditorial ws_demo_4e7834f4 ») au lieu d'afficher le nom lisible du workspace (`workspace.name`). | Expérience brute, non professionnelle ; sentiment d'outil interne inachevé. | Utiliser le nom officiel du workspace (`workspace.name`) avec repli propre, et reléguer l'identifiant technique en métadonnée secondaire discrète. |
| **DATA-07** | **Budget LLM fixe et plafond arbitraire en dur** | `apps/web/src/screens/DashboardScreen.tsx` (lignes 40-41) | `llmBudgetSpent` est initialisé à `0.42` et `llmLimit` à `10.0` en variable d'état locale si l'API `/v1/analytics/overview` ne retourne pas de montant consolidé. | Indicateur financier trompeur qui ne reflète pas la consommation réelle de jetons API. | Calculer la consommation exacte à partir des logs d'audit et de la table des appels LLM (`llm_audit_logs`). |

---

## 2. Plan d'Action pour le Chantier d'Audit & Backend

1. **Phase Immédiate (Design & UI - Phases 1 à 7) :**
   - Rendre les composants UI réceptifs à des états honnêtes (état vide avec mention « Données insuffisantes », skeletons pendant le calcul, affichage rigoureux des échelles).
   - Corriger les formules d'affichage dans les écrans React pour ne plus multiplier par 10 ou 100 des scores déjà sur 10.
   - Ne plus jamais coder en dur des pourcentages de performance dans les templates.

2. **Phase Suivante (Consolidation Backend) :**
   - Ajouter un contrôle de déduplication dans le router `ideas.py`.
   - Lier `InboxQualityGateCard` au modèle `QualityGateReport`.
   - Ajuster la contrainte de longueur dans le graphe LangGraph pour la variante X.
