# Runbook : Activation du Kill Switch Global

## Objectif
Interrompre immédiatement et sans délai toute publication publique sortante sur l'ensemble des réseaux sociaux connectés (ex: détection d'une compromission de clé ou d'une anomalie majeure de contenu).

## Procédure d'Activation Immédiate
1. **Bascule en mode Sandbox Forcé :**
   Définir la variable d'environnement :
   ```bash
   export SOCIAL_SANDBOX_MODE=true
   ```
2. **Arrêt du Dispatcher :**
   Si le service tourne via systemd ou Docker :
   ```bash
   docker stop contentops_api
   ```
3. **Mise à jour en base de données :**
   Suspendre tous les jobs en cours d'attente :
   ```sql
   UPDATE publication_jobs SET status = 'ARCHIVED', error_message = 'Kill-switch activated by administrator' WHERE status = 'SCHEDULED';
   ```

## Procédure de Réarmement
1. Audit des logs d'incidents et validation de l'intégrité de la base.
2. Réactivation sélective des publications depuis l'interface d'administration.
