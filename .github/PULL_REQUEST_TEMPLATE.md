## Description des modifications
Une vue d'ensemble des changements apportés et de leur contexte métier/technique.

## Type de modification
- [ ] Correction de bogue (Bug fix)
- [ ] Nouvelle fonctionnalité (Feature)
- [ ] Refactorisation / Amélioration de performance
- [ ] Sécurité / Durcissement d'infrastructure
- [ ] Documentation / Spécification

---

## Checklist de Sécurité & Qualité (Obligatoire)
Avant de soumettre cette Pull Request, assurez-vous que tous les critères suivants sont validés :

- [ ] **Zéro Secret Commité** : Aucun fichier `.env`, clé d'API, mot de passe ou jeton OAuth n'est présent dans les commits (`gitleaks detect` passe à 100%).
- [ ] **Tests Unitaires & Contrats** : La suite complète `pytest` (backend) et `vitest` (frontend) s'exécute avec succès.
- [ ] **Validation Humaine (HITL)** : Les garanties anti-publication autonome et de garde-fous éthiques sont strictement préservées.
- [ ] **Sécurité des Données** : Aucune donnée personnelle (PII) n'est consignée en clair dans les logs JSON ou traces Langfuse.
- [ ] **Typage & Linter** : `ruff check` et `mypy` ne rapportent aucune erreur bloquante.
- [ ] **Aucun Chemin Absolu Local** : Les fichiers ne contiennent aucun chemin absolu vers des répertoires locaux de machine hôte.
