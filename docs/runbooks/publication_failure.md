# Runbook : Traitement des Échecs de Publication & Dead-Letter Queue

## Symptôme
Un job de publication passe au statut `PUBLISH_FAILED` ou atteint le nombre maximal de tentatives (`attempt_count >= max_retries`).

## Procédure de Diagnostic
1. Consulter la table `publication_jobs` et le champ `error_message`.
2. Vérifier les codes d'erreur retournés par le connecteur social (ex: 429 Too Many Requests, 401 Unauthorized, 400 Bad Payload).
3. Vérifier si le hash du payload a été altéré depuis l'approbation humaine.

## Actions Correctives
- **En cas de limite de taux (429) :**  
  Le dispatcher applique un backoff exponentiel. Aucune intervention manuelle requise sauf si la durée dépasse 2h.
- **En cas de token expiré (401) :**  
  Suivre le [Runbook de Rotation des Tokens](file:///Users/seansiehigninhi/Dossier_dev/apps/F-LangGraph/DeepAgent/docs/runbooks/token_rotation.md).
- **En cas de corruption ou altération de payload :**  
  Annuler le job via `POST /v1/publications/{job_id}/cancel`. Le contenu revient au statut `APPROVED` et doit faire l'objet d'une nouvelle validation.
