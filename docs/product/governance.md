# Gouvernance Éditoriale & Parcours Métier — ContentOps Harness

## 1. Vue d'Ensemble du Parcours Éditorial

ContentOps Harness est un système d'exploitation éditorial B2B multi-tenant conçu pour garantir qu'aucune publication publique n'intervienne sans une décision humaine explicite, vérifiée cryptographiquement.

```mermaid
graph TD
    START((Source / Veille)) --> Research[Recherche & Idéation]
    Research --> Brief[Création du Brief Éditorial]
    Brief --> Prod[Production Multi-Plateforme (LinkedIn, X)]
    Prod --> QA[Quality Gate Déterministe]
    QA --> Decision{QA Réussi ?}
    Decision -- Non --> QAFailed[QA_FAILED / Révision]
    Decision -- Oui --> Interrupt[Interruption Native LangGraph (HITL Inbox)]
    Interrupt --> Review{Décision Humaine (Rôle Owner)}
    Review -- Rejet --> REJECTED[Rejet Définitif]
    Review -- Réécriture --> REWRITE[Demande de Réécriture]
    REWRITE --> Prod
    Review -- Approbation --> APPROVED[Scellement SHA-256 & Horodatage]
    APPROVED --> Sched[Planification Temporelle]
    Sched --> Worker[Publisher Worker Découplé]
    Worker --> Receipt[Receipt Cryptographique & Publication]
    Receipt --> Analytics[Mesure des Performances & Insights]
```

---

## 2. Machine à États & Invariants Déterministes

Les transitions d'état du contenu respectent strictement le cycle suivant :

```text
IDEA ➔ BRIEFED ➔ DRAFT ➔ QA_FAILED / IN_REVIEW
IN_REVIEW ➔ REWRITE_REQUESTED ➔ DRAFT
IN_REVIEW ➔ REJECTED ➔ ARCHIVED
IN_REVIEW ➔ APPROVED ➔ SCHEDULED ➔ PUBLISHING
PUBLISHING ➔ PUBLISHED / PUBLISH_FAILED / PUBLISH_UNKNOWN
PUBLISHED ➔ MEASURED ➔ ARCHIVED
```

### Invariants Non Négociables :
1. **Validation Humaine Obligatoire (HITL)** : Aucun contenu ne peut passer à l'état `APPROVED` ou `SCHEDULED` sans validation explicite d'un utilisateur authentifié disposant du rôle `Owner`.
2. **Scellement SHA-256** : À l'approbation, le payload textuel complet (hook, body, cta, hashtags, media) est haché via SHA-256. Toute mutation ultérieure invalide l'approbation.
3. **Publication « Au Plus Une Fois » (At-Most-Once)** : Le statut passe à `PUBLISHING` *avant* l'appel réseau vers les APIs LinkedIn ou X. En cas de timeout ou déconnexion, l'état bascule vers `PUBLISH_UNKNOWN`. Aucun réessai automatique n'est autorisé depuis cet état afin d'exclure tout risque de publication en doublon.

---

## 3. Matrice des Rôles & Permissions (RBAC)

Le RBAC est appliqué strictement côté serveur sur toutes les routes API FastAPI (`require_roles(...)`) et reflété dans l'interface :

| Action / Écran | Owner | Editor | Viewer |
|---|:---:|:---:|:---:|
| Consultation des brouillons, calendrier, KPI | ✅ | ✅ | ✅ |
| Idéation, veille et conversion en briefs | ✅ | ✅ | ❌ |
| Édition de brouillons et soumission en revue | ✅ | ✅ | ❌ |
| Demande de réécriture (`REWRITE_REQUESTED`) | ✅ | ✅ | ❌ |
| **Approbation HITL (`APPROVED`)** | ✅ | ❌ | ❌ |
| **Rejet définitif (`REJECTED`)** | ✅ | ❌ | ❌ |
| **Publication immédiate (`Publish Now`)** | ✅ | ❌ | ❌ |
| Connexion et révocation OAuth des comptes sociaux | ✅ | ❌ | ❌ |
| Configuration des modèles LLM et clés API | ✅ | ❌ | ❌ |
| Activation / désactivation du Kill Switch d'urgence | ✅ | ❌ | ❌ |
| Export des données personnelles (RGPD Art. 20) | ✅ | ✅ | ✅ |
| Suppression de compte (RGPD Art. 17) | ✅ *(si pas unique owner)* | ✅ | ✅ |

---

## 4. Apprentissage Propositionnel (ADR 0006)

Le module de recommandation stratégique (Stratégie & Insights) est soumis au principe d'**apprentissage propositionnel** :
- Les retours de performance (taux d'engagement, impressions, partages) alimentent l'agent d'analyse.
- L'agent formule des **hypothèses** et des **recommandations d'actions** claires destinées à l'équipe éditoriale.
- **Aucune mutation autonome** : les directives du profil de marque (`BrandProfile`) ne sont jamais modifiées automatiquement par un agent IA. Toute mise à jour de la voix, des piliers ou des sujets interdits requiert une validation humaine explicite.
