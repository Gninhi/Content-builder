# ADR 0001 : Workflow Déterministe Avant Multi-Agent Libre

**Date :** 2026-10-02  
**Statut :** Accepté  
**Contexte :**  
Les systèmes multi-agents totalement autonomes ou basés sur des conversations libres entre agents présentent un risque élevé de dérive éditoriale, d'hallucination factuelle et de publication intempestive.

**Décision :**  
Nous adoptons un workflow déterministe sous forme de pipeline séquentiel strict codifié avec LangGraph. Les sous-agents ou appels LLM sont cantonnés à des nœuds isolés (Idéation, Rédaction, Validation QA) sans aucun pouvoir de décision sur le cycle de vie du contenu ni sur la publication.

**Conséquences :**  
- Robustesse et reproductibilité accrues.
- Impossibilité mathématique pour un modèle de contourner la revue humaine.
- Débogage simplifié grâce aux transitions d'états explicites.
