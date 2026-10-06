# ADR 0004 : PostgreSQL / Supabase comme Source Unique de Vérité

**Date :** 2026-10-02  
**Statut :** Accepté  
**Contexte :**  
L'état en mémoire ou dans des fichiers plats ne permet pas une isolation multitenant robuste, un audit légal pérenne ni l'application de verrous de concurrence.

**Décision :**  
PostgreSQL / Supabase est la source de vérité centrale pour toutes les entités métier (Workspaces, Brand Profiles, Sources, Idées, Briefs, Variantes, Approbations, Jobs, Posts, Métriques, Traces). L'isolation multi-tenant est garantie par le Row-Level Security (RLS) et l'injection du `workspace_id`.

**Conséquences :**  
- Intégrité référentielle garantie (clés étrangères avec suppression en cascade).
- Audit trail permanent et requêtable.
