# ADR 0006 : Apprentissage Propositionnel (Sans Mutation Autonome)

**Date :** 2026-10-02  
**Statut :** Accepté  
**Contexte :**  
Permettre à un système IA d'adapter automatiquement ses règles de marque ou ses prompts de production à partir des données d'engagement crée un risque de dérive vers du contenu putaclic ou controversé.

**Décision :**  
L'analyse des métriques fonctionne en mode propositionnel : l'agent `Strategy Insights` formule des constats factuels, émet des hypothèses causales avec un score de confiance, et soumet des recommandations d'action à un décideur humain (Owner / Analyst). Aucune règle de marque n'est altérée sans approbation humaine explicite.

**Conséquences :**  
- Protection absolue contre la dérive éditoriale.
- Transparence entre corrélation observée et hypothèse formulée.
