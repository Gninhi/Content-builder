# Runbook : Gestion des Incidents LLM, Disjoncteur (Circuit Breaker) & Mode Dégradé

## Contexte
L'orchestrateur ContentOps Harness sollicite l'API Google AI Gemini 3.8 Flash (`gemini-3.8-flash`) via `langchain-google-genai`.
Pour garantir la disponibilité du service en cas d'indisponibilité de l'API externe (429 Rate Limit, 503 Service Unavailable, pannes réseau régionales), un disjoncteur déterministe (`packages/resilience/circuit_breaker.py`) protège le système :
- **État FERMÉ (CLOSED)** : Fonctionnement nominal.
- **État OUVERT (OPEN)** : Après 3 échecs consécutifs, les requêtes LLM sont immédiatement court-circuitées pour éviter l'épuisement des threads et l'accumulation de latence.
- **État SEMI-OUVERT (HALF-OPEN)** : Après un délai de récupération (60s), un appel sonde est autorisé pour vérifier le rétablissement du fournisseur.

## Comportement en Mode Dégradé (Degraded Mode)
Lorsque le disjoncteur est OUVERT ou en cas d'erreur LLM non recouvrable :
1. Le nœud de production bascule en **mode dégradé**.
2. Des variantes de repli sont générées à partir des faits bruts extraits et des modèles pré-approuvés de la marque.
3. Chaque variante dégradée reçoit explicitement le tag `degraded_mode: true`.
4. **RÈGLE CRITIQUE DE SÉCURITÉ** : Les variantes générées en mode dégradé sont **STRICTEMENT INTERDITES d'auto-publication**. Elles exigent obligatoirement une validation humaine explicite (`human_approval`) avant toute mise en file de publication.

## Procédure de Diagnostic en Production

### 1. Consulter les métriques du disjoncteur
Via l'endpoint `/health` et `/ready` :
```bash
curl -s http://localhost:8000/health | jq .
curl -s http://localhost:8000/ready | jq .
```
Vérifier l'état `circuit_breaker_state` (`CLOSED` ou `OPEN`).

### 2. Examiner les traces Langfuse et les logs JSON corrélés
Rechercher dans les journaux d'application :
```bash
docker logs contentops_api | grep -E "CircuitBreaker|GEMINI_RATE_LIMIT|LLM_OUTAGE"
```
Identifier les erreurs retournées par Google AI Studio (ex: 429 quota dépassé, 500 internal server error).

## Actions Correctives

### En cas de dépassement de quota (HTTP 429)
1. Vérifier la consommation de jetons et les plafonds mensuels FinOps configurés dans `config/pricing.json`.
2. Si un compte de secours Google AI est disponible, mettre à jour `GEMINI_API_KEY` sans interruption :
   ```bash
   export GEMINI_API_KEY="nouvelle_cle_google_ai"
   kill -HUP $(pgrep uvicorn)
   ```

### Forcer la réinitialisation manuelle du disjoncteur
Si l'incident externe est résolu et que l'équipe souhaite rétablir immédiatement le flux nominal sans attendre le TTL automatique :
```bash
python -c "
from packages.resilience.circuit_breaker import LLMCircuitBreaker
LLMCircuitBreaker.reset()
print('Disjoncteur LLM réinitialisé en état CLOSED.')
"
```

### Vérification de retour à la normale
1. Déclencher un cycle de génération de test sur un brief interne.
2. Vérifier dans Langfuse que les appels retournent un code 200 et que la latence est nominale (< 3 secondes).
