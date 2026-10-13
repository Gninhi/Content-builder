# ADR 0005 : Versionnage Immuable des Prompts et des Profils de Marque

**Date :** 2026-10-02  
**Statut :** Accepté  
**Contexte :**  
Les tests A/B, la conformité réglementaire et la détection des régressions nécessitent de pouvoir reproduire exactement un contenu généré dans le passé.

**Décision :**  
Toute modification d'un prompt ou d'un profil de marque incrémente un numéro de version (`version=2, 3, ...`) sans écraser les versions précédentes. Chaque variante de contenu conserve la référence exacte de la version de prompt et de profil de marque utilisée.

**Conséquences :**  
- Reproductibilité intégrale des générations passées.
- Évaluations comparatives A/B fiables.
