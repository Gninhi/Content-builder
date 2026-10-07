# Runbook : Activation du Kill Switch Global

## Objectif
Interrompre immédiatement et sans délai toute publication publique sortante sur l'ensemble des réseaux sociaux connectés (ex: détection d'une compromission de clé, anomalie majeure de contenu ou hallucination en rafale).

## Procédure d'Activation Immédiate

### Option 1 : Variable d'environnement à chaud (Priorité 1)
Définir la variable d'environnement sur le conteneur ou serveur :
```bash
export KILL_SWITCH_GLOBAL=true
```
Le worker de publication et tous les nœuds de publication vérifient ce flag en temps réel à chaque cycle de tentative. Dès son activation, tout job de publication est immédiatement annulé avec le statut `FAILED` et la mention `"Publication blocked by global emergency kill-switch"`.

### Option 2 : Flag Workspace en Base de Données
Si l'incident ne concerne qu'un client ou workspace spécifique :
```sql
UPDATE workspaces 
SET settings = json_set(settings, '$.kill_switch_enabled', 1) 
WHERE id = 'ws_impacted';
```

### Option 3 : Suspension des jobs en cours
Suspendre tous les jobs en attente :
```sql
UPDATE publication_jobs 
SET status = 'FAILED', error_message = 'Emergency Kill-Switch triggered by ops team' 
WHERE status = 'SCHEDULED';
```

## Procédure de Réarmement
1. Audit des logs d'incidents via les Correlation IDs et traces Langfuse associées (`tag: degraded` ou `status: FAILED`).
2. Réinitialisation de la variable :
```bash
export KILL_SWITCH_GLOBAL=false
```
3. Reprise contrôlée du dispatching après validation humaine.
