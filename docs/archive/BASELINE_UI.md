# BASELINE_UI — Rapport d'État Initial de l'Interface Utilisateur

**Projet :** ContentOps Harness  
**Date :** 8 Octobre 2026  
**Branche :** `feat/ui-production`  
**Auteur :** Lead Product Designer & Senior Frontend Engineer  

---

## 1. Protocole de Lancement & Environnement

### 1.1 Commande de démarrage exacte
L'application et son interface web sont servies conjointement par Uvicorn :
```bash
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```
- **Backend API :** `http://127.0.0.1:8000/`
- **Frontend UI :** `http://127.0.0.1:8000/ui/` (redirection automatique depuis `/`)
- **OpenAPI Schema :** `http://127.0.0.1:8000/openapi.json`
- **Documentation interactive :** `http://127.0.0.1:8000/docs`

---

## 2. Identification de la Pile Frontend Existante

| Élément | État Initial Détecté | Analyse & Impact |
| :--- | :--- | :--- |
| **Architecture** | Fichiers statiques bruts : `index.html`, `app.js` (786 lignes), `style.css` | Aucun framework, pas de composants réutilisables, logique monolithique. |
| **Bundler & Tooling** | Aucun (ni Vite, ni Webpack, ni Rollup) | Pas de minification, pas de tree-shaking, pas de source maps. |
| **Typage & Langage** | JavaScript ES6 non typé | Zéro sécurité de type, propension critique aux erreurs `undefined` / `null`. |
| **Dépendances CSS/JS** | CDNs externes (`cdn.tailwindcss.com`, `unpkg.com/lucide`, Google Fonts) | **Catastrophique** : Violations totales de la politique de sécurité CSP stricte. |
| **Mode de diffusion** | `app.mount("/ui", StaticFiles(directory="apps/web", html=True))` | FastAPI sert le dossier `apps/web` via Starlette `StaticFiles`. |

---

## 3. Mesures & Constats Techniques (Automatisés via Playwright)

Le script de capture et d'analyse Playwright (`scripts/capture_baseline.py`) a audité l'interface sur Chromium sous trois largeurs de viewport :
- **375px × 812px** (Mobile)
- **768px × 1024px** (Tablette)
- **1440px × 900px** (Desktop)

### 3.1 Synthèse Métrique

| Indicateur | Valeur Mesurée | Gravité |
| :--- | :---: | :--- |
| **Captures d'écran générées** | 21 captures | Fichiers stockés dans `docs/ui/baseline/` |
| **Erreurs console JavaScript** | 31 erreurs | **Critique** (blocage de rendu complet) |
| **Violations CSP** | 15 violations | **Bloquant** (aucun style externe ne charge) |
| **Requêtes réseau en échec (HTTP 401)** | 15 échecs (100% des appels API) | **Bloquant** (aucune donnée n'est récupérée) |
| **Problèmes structurels d'accessibilité (WCAG)** | 6 violations majeures | **Critique** (non conforme WCAG 2.2 AA) |

---

## 4. Relevé des Requêtes Réseau en Échec

Toutes les requêtes de chargement de données émises par `app.js` échouent avec un code **HTTP 401 Unauthorized** :

| Méthode | Route API Demandée | Code HTTP | Cause Relevée |
| :--- | :--- | :---: | :--- |
| `GET` | `/v1/analytics/overview` | **401** | Aucun jeton JWT passé (`Authorization: Bearer` absent). |
| `GET` | `/v1/inbox` | **401** | Aucun jeton JWT passé. |
| `GET` | `/v1/calendar` | **401** | Aucun jeton JWT passé. |
| `GET` | `/v1/brand-profiles/ws_default` | **401** | Aucun jeton JWT passé. |
| `POST` | `/v1/strategy/insights` | **401** | Aucun jeton JWT passé. |

---

## 5. Violations de Sécurité CSP (Content Security Policy)

L'API FastAPI applique l'en-tête de sécurité strict :
```http
Content-Security-Policy: default-src 'self'; frame-ancestors 'none';
```

Le front initial tente de charger :
1. `https://fonts.googleapis.com/css2?...` ➔ **BLOCKED by CSP**
2. `https://cdn.tailwindcss.com/` ➔ **BLOCKED by CSP**
3. `https://unpkg.com/lucide@latest` ➔ **BLOCKED by CSP**
4. `<script>tailwind.config = {...}</script>` (inline) ➔ **BLOCKED by CSP**
5. `<script>lucide.createIcons();</script>` (inline) ➔ **BLOCKED by CSP**

**Conséquence immédiate :** L'interface s'affiche en HTML brut non stylé, avec polices système par défaut, fond blanc par défaut ou non conforme, et icônes cassées.

---

## 6. Exceptions JavaScript à l'Exécution

Lorsque l'utilisateur navigue entre les onglets, le contrôleur monolithique `app.js` plante instantanément :
1. **Dashboard :**
   ```text
   TypeError: Cannot read properties of undefined (reading 'toLocaleString') at renderDashboard (app.js:97:89)
   ```
   *Raison :* `dashboardData` contient l'objet d'erreur 401 `{ error: "http_error", detail: "..." }` au lieu d'un objet statistiques.
2. **Revue HITL (Inbox) :**
   ```text
   TypeError: inboxItems.map is not a function at renderInbox (app.js:250:32)
   ```
   *Raison :* `inboxItems` est l'objet JSON d'erreur 401 et non un tableau.
3. **Profil de Marque :**
   ```text
   TypeError: Cannot read properties of undefined (reading 'map') at renderBrand (app.js:713:25)
   ```
   *Raison :* `brandData` est l'erreur 401.

---

## 7. Inventaire des Captures d'Écran Baseline

Les captures d'écran de l'état initial sont disponibles dans `docs/ui/baseline/` :
- `dashboard_375px.png`, `dashboard_768px.png`, `dashboard_1440px.png`
- `inbox_375px.png`, `inbox_768px.png`, `inbox_1440px.png`
- `calendar_375px.png`, `calendar_768px.png`, `calendar_1440px.png`
- `ideation_375px.png`, `ideation_768px.png`, `ideation_1440px.png`
- `insights_375px.png`, `insights_768px.png`, `insights_1440px.png`
- `brand_375px.png`, `brand_768px.png`, `brand_768px.png`
- `modal_research_375px.png`, `modal_research_768px.png`, `modal_research_1440px.png`

---

## 8. Conclusion du Préflight

L'interface actuelle souffre de défauts structurels majeurs :
1. Incompatibilité totale avec la politique de sécurité CSP en place (CDNs externes).
2. Absence de gestion d'authentification JWT côté client (tous les flux tombent en 401).
3. Contrôle d'erreurs inexistant conduisant à des plantages `TypeError` au premier clic.
4. Accessibilité et réactivité mobile non conformes.

La phase 1 détaillera le diagnostic exhaustif et l'audit UX/UI.
