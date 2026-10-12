# AUDIT_UI — Diagnostic Technique Exhaustif & Audit UX/UI

**Projet :** ContentOps Harness  
**Date :** 8 Octobre 2026  
**Branche :** `feat/ui-production`  
**Auteur :** Lead Product Designer & Senior Frontend Engineer  

---

## 1. Diagnostic Approfondi des 5 Symptômes Observés

Pour chacun des symptômes majeurs constatés sur l'interface initiale, voici l'établissement formel de la cause racine, les preuves factuelles issues du code et des mesures, et le correctif d'ingénierie requis.

---

### Symptôme 1 : Aucun style appliqué (Interface brute / non stylée)

- **Gravité :** Critique (Bloquant visuel).
- **Cause Racine :** 
  L'API FastAPI applique un en-tête `Content-Security-Policy: default-src 'self'; frame-ancestors 'none';`.
  Or, le fichier `apps/web/index.html` tente d'importer le compilateur Tailwind via CDN (`https://cdn.tailwindcss.com`), les polices Google Fonts via CDN (`https://fonts.googleapis.com`), et les icônes Lucide via CDN (`https://unpkg.com/lucide@latest`), en plus d'un script de configuration Tailwind inline sans nonce ni hash SHA-256.
  Le moteur de sécurité du navigateur applique strictement la directive `default-src 'self'` et bloque l'exécution de tous ces scripts et feuilles de style externes. Aucun CSS utilitaire Tailwind n'est compilé ou appliqué.
- **Preuves :**
  1. `apps/api/main.py:176` : `response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"`
  2. `apps/web/index.html:10-13` : Liens externes CDN et `<script>` inline.
  3. Journal console Playwright (`docs/ui/baseline/preflight_data.json`) :
     ```text
     Loading the stylesheet 'https://fonts.googleapis.com/...' violates Content Security Policy directive: "default-src 'self'". The action has been blocked.
     Loading the script 'https://cdn.tailwindcss.com/' violates Content Security Policy directive: "default-src 'self'". The action has been blocked.
     Executing inline script violates Content Security Policy directive 'default-src 'self''. The action has been blocked.
     ```
- **Correctif Requis :**
  Migration complète vers un pipeline de build statique pré-compilé (**Vite + Tailwind CSS v4 / v3 compilation locale**). Tous les assets CSS, JavaScript, polices de caractères (`@fontsource/inter`, `@fontsource/jetbrains-mono`) et icônes SVG intégrées doivent être compilés dans le bundle servi sous `/ui/` sous l'origine `'self'`, sans **aucun** appel CDN externe et sans script inline.

---

### Symptôme 2 : "Revue HITL undefined" et Données Cassées

- **Gravité :** Critique (Inopérant fonctionnel).
- **Cause Racine :**
  Toutes les routes de l'API requièrent une authentification via un jeton JWT dans l'en-tête `Authorization: Bearer <token>` validé par `packages/security/auth.py`.
  Le contrôleur front-end `apps/web/app.js` effectue ses requêtes `fetch(`${API_BASE}/v1/inbox`)` sans fournir le moindre jeton d'authentification.
  L'API FastAPI répond systématiquement par un statut **HTTP 401 Unauthorized** contenant l'objet JSON `{"error":"http_error","detail":"Authentication credentials were not provided"}`.
  Le code JavaScript dans `app.js` ne vérifie pas le code HTTP de la réponse, parse le JSON d'erreur comme s'il s'agissait de données métier, et tente d'itérer dessus (`inboxItems.map(...)` ou lecture de `item.hook`), provoquant des plantages JavaScript `TypeError` et des affichages de chaînes `"undefined"`.
- **Preuves :**
  1. `apps/api/routers/content.py:177` : `user: UserContext = Depends(require_roles("Owner", "Editor", "Viewer", "ServiceAgent"))`
  2. `apps/web/app.js:25` : `fetch(`${API_BASE}/v1/inbox`).then(r => r.json())` (aucun en-tête d'autorisation).
  3. Rapport Playwright (`docs/ui/baseline/preflight_data.json`) :
     ```text
     URL: http://127.0.0.1:8000/v1/inbox -> Status: 401 Unauthorized
     Console Error: TypeError: inboxItems.map is not a function at renderInbox (app.js:250:32)
     ```
- **Correctif Requis :**
  Implémentation d'un module d'authentification complet :
  - Client API typé avec intercepteur injectant automatiquement le token JWT.
  - Gestion sécurisée de la session (stockage sécurisé en mémoire avec mécanisme de rafraîchissement, jamais en `localStorage`).
  - Écran de connexion (avec support du jeton dev en `ENV=dev`).
  - Validation des schémas d'entrée/sortie via Zod à la frontière de l'API pour garantir qu'aucune donnée corrompue n'atteint les composants.

---

### Symptôme 3 : Fausse modale "Rechercher de nouvelles idées" et élément "—" orphelin

- **Gravité :** Majeure (Rupture ergonomique et accessibilité).
- **Cause Racine :**
  La modale d'idéation dans `apps/web/index.html` est une simple balise `<div>` non accessible sans attributs WAI-ARIA (`role="dialog"`, `aria-modal="true"`, `aria-labelledby`), manipulée de manière rudimentaire via l'ajout/retrait de classes CSS (`hidden` / `flex`). Elle ne piège pas le focus clavier, ne se ferme pas avec la touche Échap, et ne restitue pas le focus au bouton déclencheur.
  L'élément `" — "` orphelin découle d'un séparateur statique inséré dans le titre ou les en-têtes sans conteneur flex/grid fonctionnel (en raison de l'absence de CSS Tailwind).
  De plus, la fonction `executeResearch()` dans `app.js:766` envoie l'en-tête obsolète `'X-User-Role': 'Owner'` (strictement ignoré et rejeté par FastAPI) et échoue en HTTP 401.
- **Preuves :**
  1. `apps/web/index.html:142` : `<div id="modal-research" class="fixed inset-0 bg-black/70 backdrop-blur-sm hidden ...">`
  2. Audit A11y (`docs/ui/baseline/a11y_data.json`) :
     ```json
     {"type": "wcag-dialog-role-missing", "selector": "#modal-research"}
     {"type": "wcag-aria-modal-missing", "selector": "#modal-research"}
     ```
  3. `apps/web/app.js:766` : Envoi de `'X-User-Role': 'Owner'` sans jeton Bearer.
- **Correctif Requis :**
  Remplacement de la modale par une primitive accessible (Radix Dialog / shadcn Dialog) avec gestion native du focus trap, fermeture par touche Échap, retour du focus, libellés ARIA stricts, et formulaire connecté via React Hook Form / TanStack Query avec suivi de progression temps réel de l'exécution LangGraph.

---

### Symptôme 4 : Carte utilisateur en dur et "LangGraph v0.2" concaténé au workspace

- **Gravité :** Majeure (Données factices / Violation du principe de vérité).
- **Cause Racine :**
  L'identité de l'utilisateur (`Martial Gninhi`, initiales `MG`, rôle `Owner`) ainsi que le nom du workspace (`AI & Multi-Agents`) et la mention `LangGraph v0.2` sont codés en dur dans le balisage HTML statique (`apps/web/index.html`).
  Aucune requête n'est effectuée vers les informations de session ou le endpoint de profil, masquant la véritable identité du tenant et violant la règle d'intégrité "Zéro donnée factice".
- **Preuves :**
  1. `apps/web/index.html:103-108` :
     ```html
     <p class="font-medium text-slate-200">Martial Gninhi</p>
     <p class="text-slate-400">Rôle : <span class="text-cyan-400 font-semibold">Owner</span></p>
     ```
  2. `apps/web/index.html:120-124` :
     ```html
     Workspace : <strong class="text-cyan-300" id="ws-label">AI & Multi-Agents</strong>
     <span class="..."><i data-lucide="cpu" class="w-3.5 h-3.5"></i> LangGraph v0.2</span>
     ```
- **Correctif Requis :**
  Composants dynamiques `UserMenu` et `WorkspaceSwitcher` alimentés exclusivement par les revendications du jeton JWT (`sub`, `role`, `workspace_id`) et par les requêtes API `/v1/workspaces`. Affichage clair du rôle effectif avec gestion RBAC (Owner, Editor, Viewer).

---

### Symptôme 5 : Dépendance Tavily (Gestion des clés, indisponibilité et UI)

- **Gravité :** Moyenne à Majeure (Résilience et transparence).
- **Cause Racine :**
  Le connecteur Tavily (`packages/connectors/search/tavily.py`) intercepte silencieusement toutes les exceptions (`except Exception: pass`) et bascule sur un mock statique de repli lorsque la clé est absente, invalide ou que le quota est dépassé. L'API ne renvoie pas d'indicateur explicite sur la source réelle des données, et l'interface n'affiche aucun avertissement si la recherche s'effectue en mode dégradé ou hors ligne.
- **Preuves :**
  1. `packages/connectors/search/tavily.py:37-40` : Exception masquée sans journalisation structurée côté contrat.
  2. `apps/web/app.js:774-780` : Aucune distinction entre données Tavily réelles et données de repli ; `alert(err.message)` archaïque.
- **Correctif Requis :**
  Intégration d'un badge explicite et d'un indicateur de source dans l'écran d'Idéation :
  - Détection de l'état du service de recherche web via `/ready`.
  - Notification pédagogique si Tavily est inactif ou en quota dépassé (avec mention explicite de l'utilisation des sources locales existantes).
  - Gestion d'état d'erreur et de repli transparente, sans `alert()` JavaScript.

---

## 2. Audit UX/UI Systématique selon les Heuristiques de Nielsen

| Heuristique de Nielsen | Constat Initial sur ContentOps | Sévérité | Correctif Prévu |
| :--- | :--- | :---: | :--- |
| **H1 : Visibilité du statut système** | Zéro indicateur de chargement (skeletons), zéro badge SANDBOX/LIVE, aucun retour visuel lors des appels asynchrones. | Critique | Skeletons animés par composant, badge permanent d'environnement (`SANDBOX` vs `LIVE`), toasts de progression. |
| **H2 : Correspondance avec le monde réel** | Hachages cryptographiques bruts exposés (`item.payload_hash.substring(0, 16)`), manque d'aperçus fidèles des réseaux sociaux. | Majeure | Aperçus WYSIWYG fidèles pour LinkedIn et X (mise en page, compteur de caractères, avatars, médias). |
| **H3 : Contrôle utilisateur et liberté** | Pas d'annulation, pas de confirmation lors des actions critiques (approbation, rejet, kill switch). | Critique | Modales de confirmation accessibles (`ConfirmDialog`) avec garde-fous stricts avant toute action en mode LIVE. |
| **H4 : Cohérence et standards** | Styles disparates, aucune convention de composants, absence totale de tokens de design documentés. | Majeure | Système de design complet sous Tailwind + Radix UI avec tokens sémantiques stricts. |
| **H5 : Prévention des erreurs** | Validation directe sans vérification des prérequis ou des politiques de marque (mots interdits, mention IA). | Critique | Quality Gate visuel interactif affichant clairement les règles échouées, doublons et mentions d'IA. |
| **H6 : Reconnaissance plutôt que rappel** | L'utilisateur doit deviner l'état d'un brouillon sans légende ni guide sur la machine à états. | Moyenne | Badges de statut conformes aux 8 états du cycle de vie + infobulles explicatives des transitions autorisées. |
| **H7 : Efficacité et raccourcis** | Aucune navigation au clavier dans la boîte de révision HITL. | Majeure | Raccourcis clavier pro : `J`/`K` (navigation), `A` (approuver), `R` (réécrire), `X` (rejeter), `?` (aide). |
| **H8 : Esthétique et design minimaliste** | En l'absence de CSS, disposition brute brisée ; en cas de CSS partiel, surcharge visuelle sans hiérarchie. | Majeure | Layout moderne épuré, typographie hiérarchisée, thème sombre soigné et thème clair contrasté. |
| **H9 : Aide et gestion des erreurs** | `alert()` natifs intrusifs, plantages silencieux `TypeError` dans la console. | Critique | Système de Toasts non bloquants, composants `ErrorState` dédiés avec bouton "Réessayer" et identifiant de corrélation. |
| **H10 : Aide et documentation** | Aucune aide contextuelle sur les politiques éditoriales, le kill switch ou les scopes OAuth. | Moyenne | Infobulles accessibles (`Tooltip`) et panneaux d'aide intégrés dans chaque écran. |

---

## 3. Audit d'Accessibilité (WCAG 2.2 AA)

L'audit automatisé et manuel relève 6 défaillances critiques :

1. **Absence de balises `<label>` associées aux contrôles de formulaire (Critère WCAG 1.3.1 & 4.1.2) :**
   Les champs d'idéation (`input-research-topic`, `input-research-count`) utilisent des `<label>` sans attribut `for`, ni `aria-label`.
2. **Boutons sans nom accessible (Critère WCAG 4.1.2) :**
   Le bouton de fermeture de la modale contient uniquement une balise SVG `<i data-lucide="x"></i>` sans texte ni `aria-label="Fermer"`.
3. **Absence de rôles de dialogue WAI-ARIA (Critère WCAG 4.1.2) :**
   La modale ne possède ni `role="dialog"` ni `aria-modal="true"` ni `aria-labelledby`.
4. **Contraste insuffisant et absence de focus visible (Critère WCAG 1.4.3 & 2.4.7) :**
   En l'absence de CSS, les états `:focus-visible` par défaut sont difficilement perceptibles ; les couleurs texte/fond ne respectent pas le ratio 4,5:1.
5. **Cibles tactiles inférieures à 44×44 px (Critère WCAG 2.5.8) :**
   Sur viewport mobile 375px, les boutons d'action mesurent moins de 32px de hauteur sans marge d'espacement suffisante.
6. **Absence de région vivante pour les annonces d'état (Critère WCAG 4.1.3) :**
   Les changements de vue et les chargements ne sont pas annoncés aux technologies d'assistance (`aria-live="polite"`).

---

## 4. Matrice Synthétique des Findings

| ID | Domaine | Problème Constaté | Sévérité | Preuve | Solution Validée |
| :--- | :--- | :--- | :---: | :--- | :--- |
| **AUD-01** | Sécurité / CSS | Tailwind CDN bloqué par la CSP | **Bloquant** | Log console CSP | Bundle local auto-hébergé avec Vite |
| **AUD-02** | Sécurité / Auth | Requêtes API sans Bearer JWT (401) | **Bloquant** | HTTP 401 sur `/v1/*` | Client API typé avec intercepteur auth |
| **AUD-03** | Robustesse JS | `TypeError` en chaîne sur données non vérifiées | **Critique** | Exceptions `map`/`toLocaleString` | Schémas de validation Zod front |
| **AUD-04** | Composant | Modale non accessible sans focus trap | **Majeure** | Audit A11y DOM | Dialogue Radix UI accessible |
| **AUD-05** | Données | Identité utilisateur & Workspace codés en dur | **Majeure** | Code HTML statique | Composants branchés sur claims JWT & API |
| **AUD-06** | A11y | Formulaires sans labels accessibles | **Majeure** | `a11y_data.json` | Association stricte `htmlFor` + ARIA |
| **AUD-07** | A11y | Cibles tactiles trop petites sur mobile | **Moyenne** | Mesure 375px | Cibles tactiles >= 44×44 px |
| **AUD-08** | UX | Raccourcis clavier absents sur la revue HITL | **Majeure** | Spécification métier | Gestionnaire global d'événements clavier |
| **AUD-09** | Architecture | Absence de bundler, linter, tests front | **Critique** | Absence de package.json | Mise en place de Vite + React + TS + Vitest |
