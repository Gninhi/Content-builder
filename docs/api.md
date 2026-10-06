# Documentation de l'API REST — ContentOps Harness

**Base URL :** `http://localhost:8000`  
**Spécification OpenAPI :** `/docs` ou `/redoc`

---

## Authentification & Contexte Tenant

Chaque requête doit inclure les en-têtes suivants :
```http
X-User-Id: <user_id>
X-User-Role: <Owner | Editor | Analyst | ServiceAgent>
X-Workspace-Id: <workspace_id>
```

---

## Endpoints Principaux

### 1. Espaces & Profils de Marque
- `POST /v1/workspaces` : Créer un workspace d'équipe.
- `POST /v1/brand-profiles` : Définir ou versionner un profil de marque.
- `GET /v1/brand-profiles/{workspace_id}` : Récupérer la dernière version du profil de marque.

### 2. Sources & Provenance
- `POST /v1/sources` : Ingérer une source (URL, texte brut, note), extraire les faits et calculer l'empreinte de provenance.
- `GET /v1/sources` : Lister les sources disponibles dans le workspace.

### 3. Idéation & Recherche
- `POST /v1/ideas/research` : Déclencher le workflow LangGraph `idea_research_graph` pour générer au moins 10 idées scorées.
- `GET /v1/ideas` : Lister le backlog d'idées avec scores de nouveauté, pertinence, effort et priorité.

### 4. Production de Contenu & Briefs
- `POST /v1/briefs` : Créer un brief éditorial lié ou non à une idée.
- `POST /v1/content/generate` : Déclencher `content_production_graph` et le Quality Gate déterministe pour générer les variantes par plateforme.
- `GET /v1/inbox` : Récupérer les brouillons soumis à validation humaine (`status: IN_REVIEW`).

### 5. Approbation Humaine (HITL)
- `POST /v1/content/{variant_id}/approve` :
  - **Décision :** `approve`, `edit`, `reject`, ou `request_rewrite`.
  - **Vérification cryptographique :** le hash du payload doit concorder exactement.

### 6. Planification & Publication
- `POST /v1/publications/schedule` : Programmer une variante approuvée en calculant sa clé d'idempotence.
- `POST /v1/publications/{job_id}/publish-now` : Déclencher l'exécution immédiate via le `PublisherWorker`.
- `POST /v1/publications/{job_id}/cancel` : Annuler un job programmé.
- `GET /v1/calendar` : Obtenir le calendrier éditorial unifié.

### 7. Analytics & Stratégie
- `GET /v1/analytics/overview` : Métriques globales consolidées.
- `POST /v1/analytics/snapshots` : Enregistrer un snapshot de métriques pour un post publié.
- `POST /v1/strategy/insights` : Exécuter l'agent `Strategy Insights` pour générer les hypothèses et recommandations.
