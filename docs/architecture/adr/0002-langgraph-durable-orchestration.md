# ADR 0002 : LangGraph pour Orchestration Durable et Validation Asynchrone

**Date :** 2026-10-02  
**Statut :** Accepté  
**Contexte :**  
La validation humaine d'un brouillon éditorial peut prendre de quelques minutes à plusieurs jours. Le système doit pouvoir suspendre son exécution sans bloquer de thread réseau, persister l'état complet, et reprendre immédiatement dès que l'approbation humaine est soumise.

**Décision :**  
Utilisation de LangGraph avec checkpointer (`MemorySaver` en local/test, PostgreSQL en production) et configuration d'interruptions natives (`interrupt_before=["human_review"]`).

**Conséquences :**  
- Gestion asynchrone native de la boucle humaine (HITL).
- Reprise sur incident transparente sans perte de données.
- Observabilité unifiée avec les traces Langfuse.
