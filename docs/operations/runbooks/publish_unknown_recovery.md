# Runbook : Réconciliation et Reprise des Incidents PUBLISH_UNKNOWN

## Contexte & Garantie "Au Plus Une Fois" (At-Most-Once)
Ni LinkedIn ni X ne fournissent de clé d'idempotence réseau native pour la publication de posts.
Si une coupure réseau ou un dépassement de délai (timeout en lecture HTTP) survient *après* que la requête a été expédiée, le statut exact sur la plateforme distante est inconnu :
- Le post a peut-être été créé avec succès sur le profil.
- Ou le post a peut-être été abandonné avant d'être persisté.

Pour interdire formellement tout doublon (double publication publique) :
1. L'état `PUBLISHING` est persisté en base de données de manière atomique avant l'appel externe.
2. Tout incident de ce type lève une exception `SocialPublishUnknownError`.
3. Le job et la variante basculent dans l'état de sécurité **`PUBLISH_UNKNOWN`**.
4. **AUCUN retry automatique n'est exécuté aveuglément.**
5. Le score d'observabilité Langfuse `publication_unknown` (0.5) est émis.

## Procédure de Diagnostic

### 1. Identifier les jobs bloqués en PUBLISH_UNKNOWN
En base de données :
```sql
SELECT id, workspace_id, variant_id, scheduled_at, status, attempts_count, last_error
FROM publication_jobs
WHERE status = 'PUBLISH_UNKNOWN'
ORDER BY scheduled_at DESC;
```

### 2. Vérifier la plateforme externe
Consulter le compte officiel (LinkedIn ou X) ou utiliser l'API du provider pour déterminer si le contenu a réellement été publié :
- Rechercher le texte du post dans les publications récentes du compte.
- Vérifier l'heure de publication concordante (+/- 2 minutes).

## Procédure de Résolution

### Option A : Le post EST visible sur la plateforme (Succès confirmé)
Réconcilier le job en injectant l'identifiant distant et l'URL publique :
```bash
# Exemple via script ou appel direct de worker.reconcile_job()
python -c "
from infra.db.database import get_db_session
from services.publisher.worker import PublisherWorker

with get_db_session() as db:
    worker = PublisherWorker(db)
    worker.reconcile_job(
        job_id='<JOB_ID>',
        resolved_status='PUBLISHED',
        platform_post_id='<URN_OU_TWEET_ID>',
        permalink_url='https://linkedin.com/feed/update/<URN_OU_TWEET_ID>'
    )
print('Job réconcilié avec succès en PUBLISHED.')
"
```
Effet : Le job et la variante passent en `PUBLISHED`, un enregistrement `published_posts` est créé, et le flux éditorial reprend son cours.

### Option B : Le post N'EST PAS présent (Échec avéré)
Réconcilier le job en échec propre pour permettre une reprogrammation :
```bash
python -c "
from infra.db.database import get_db_session
from services.publisher.worker import PublisherWorker

with get_db_session() as db:
    worker = PublisherWorker(db)
    worker.reconcile_job(
        job_id='<JOB_ID>',
        resolved_status='PUBLISH_FAILED'
    )
print('Job réconcilié en PUBLISH_FAILED.')
"
```
Effet : La variante repasse en statut d'erreur, permettant au comité éditorial d'approuver ou de reprogrammer la publication sans risque de collision.

## Comportement au Redémarrage du Serveur
En cas de crash système imprévu ou redémarrage de conteneur, le cycle de démarrage (`lifespan` dans `apps/api/main.py`) scanne automatiquement la table `publication_jobs` et bascule tout job orphelin en état `PUBLISHING` vers `PUBLISH_UNKNOWN`.
Consultez ensuite le présent runbook pour finaliser la réconciliation.
