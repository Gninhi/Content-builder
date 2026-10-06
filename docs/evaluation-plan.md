# Plan d'Évaluation & Tests de Régression (80 Cas)

**Objectif :** Garantir que les agents respectent en permanence la gouvernance de contenu, la fidélité aux sources et les règles de sécurité.

---

## 1. Composition du Dataset Initial (80 Cas)

| Famille | Nombre de Cas | Objectif Clé |
|---|---:|---|
| **Fidélité source et citation** | 20 | Vérifier que chaque chiffre ou affirmation forte cite sa source exacte. |
| **Ton & profil de marque** | 15 | Détecter et rejeter le clickbait, le spam ou le dénigrement concurrent. |
| **Adaptation par plateforme** | 15 | Valider les contraintes de format (X < 280 car., LinkedIn aéré avec hook). |
| **Rejet des claims non vérifiés** | 10 | Rejeter toute affirmation non étayée par une source factuelle. |
| **Politique de sécurité/approbation** | 10 | Empêcher la publication sans approbation liée au hash exact du payload. |
| **Cas d'échec & résilience** | 10 | Vérifier le repli propre sans crash lors d'indisponibilité d'outils ou d'APIs. |
| **TOTAL** | **80** | **Seuil d'acceptation en CI : >= 95%** |

---

## 2. Exécution des Évaluations

Pour exécuter la suite complète d'évaluations automatisées :

```bash
PYTHONPATH=. python evals/evaluators/quality_evaluator.py
```

Le script produit un rapport JSON structuré avec le taux de passage global et le détail par famille de tests.
