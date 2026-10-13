# DESIGN.md — Système de Design & Architecture UX/UI

**Projet :** ContentOps Harness  
**Version :** 2.0 (Production Design System)  
**Conformité :** WCAG 2.2 Niveau AA (Rapports de contraste >= 4,5:1 pour le texte normal, >= 3:1 pour les composants d'interface)  

---

## 1. Architecture de l'Information & Layout Global

L'application repose sur un **AppShell** unifié composé d'une barre latérale persistante (`Sidebar`), d'une barre supérieure d'état (`Topbar`), et d'un conteneur de contenu principal responsive (`MainContent`) :

```text
+-----------------------------------------------------------------------------------------------+
| SIDEBAR (w-64)            | TOPBAR (h-16, sticky)                                            |
| - Logo & Titre ContentOps | - WorkspaceSwitcher (ws_default, etc.)                           |
| - Badge SANDBOX / LIVE    | - Indicateur Kill Switch (Actif / Normal)                        |
| - Navigation (9 Écrans)   | - Rôle effectif (Owner, Editor, Viewer)                          |
| - Boîte HITL avec Badge   | - Bascule Thème Sombre / Clair                                   |
| - Statut LangGraph        | - UserMenu (Déconnexion, session)                                |
|                           +-------------------------------------------------------------------+
|                           | MAIN CONTENT (max-w-7xl, p-6 ou p-8)                             |
|                           | - En-tête de vue (Titre, description, actions contextuelles)      |
|                           | - Filtres & barres d'outils                                       |
|                           | - Grilles réactives / Listes / Panneaux de révision              |
+---------------------------+-------------------------------------------------------------------+
```

### Plan de Navigation (9 Écrans & Routes) :
1. **`/auth`** : Authentification & Sélection de Rôle (mode Dev & Connexion standard).
2. **`/` ou `/dashboard`** : Vue d'ensemble (KPIs réels, état des connexions, activité récente).
3. **`/inbox`** : Revue HITL (Écran critique de validation humaine avec raccourcis clavier et aperçus fidèles).
4. **`/calendar`** : Calendrier éditorial (Mois & Semaine, créneaux, collisions, reprogrammation).
5. **`/ideation`** : Idéation & Veille (Formulaire dans vraie modale accessible, cartes scorées, statut Tavily).
6. **`/insights`** : Stratégie & Insights (Recommandations des agents, créneaux optimaux, performance plateformes).
7. **`/brand`** : Profil de Marque (Piliers éditoriaux, audience, mots interdits, historique des versions).
8. **`/connections`** : Connexions Réseaux (Cartes LinkedIn et X, statut OAuth, quotas, scopes).
9. **`/settings`** : Gouvernance & Paramètres (Kill switch global, plafonds horaires, audit logs, réservé rôle Owner).

---

## 2. Design Tokens & Thèmes

Les tokens sont définis sous forme de variables CSS standard dans le thème sombre (par défaut) et le thème clair.

### 2.1 Couleurs Sémantiques

| Token Sémantique | Thème Sombre (Défaut) | Thème Clair | Usage & Règle de Contraste |
| :--- | :--- | :--- | :--- |
| **Fond Application (`bg-app`)** | `#0b0f19` (Slate 950 profond) | `#f8fafc` (Slate 50) | Fond de base |
| **Fond Surface / Carte (`bg-surface`)** | `#111827` (Slate 900) | `#ffffff` (Blanc pur) | Cartes, conteneurs, modales |
| **Bordure Neutre (`border-subtle`)** | `#1f2937` (Slate 800) | `#e2e8f0` (Slate 200) | Séparateurs, bordures de cartes |
| **Texte Principal (`text-primary`)** | `#f9fafb` (Slate 50) | `#0f172a` (Slate 900) | Contraste >= 12:1 |
| **Texte Secondaire (`text-muted`)** | `#94a3b8` (Slate 400) | `#475569` (Slate 600) | Contraste >= 5.2:1 (Conforme AA) |
| **Accent Marque (`brand-accent`)** | `#0284c7` (Sky 600) | `#0284c7` (Sky 600) | Actions primaires, focus rings |
| **Succès (`status-success`)** | `#10b981` (Emerald 500) | `#059669` (Emerald 600) | PUBLISHED, APPROVED, Connexion active |
| **Avertissement (`status-warning`)**| `#f59e0b` (Amber 500) | `#d97706` (Amber 600) | PENDING_REVIEW, Quota > 80% |
| **Erreur (`status-error`)** | `#ef4444` (Red 500) | `#dc2626` (Red 600) | FAILED, Kill Switch actif, 401/500 |
| **Inconnu (`status-unknown`)** | `#8b5cf6` (Purple 500) | `#7c3aed` (Purple 600) | PUBLISH_UNKNOWN (Réconciliation) |
| **Dégradé (`status-degraded`)** | `#f97316` (Orange 500) | `#ea580c` (Orange 600) | Mode dégradé / Cache / Fallback |

### 2.2 Typographie (100% Auto-Hébergée, 0 CDN)

- **Police de corps & titres :** `Inter`, sans-serif (`@fontsource/inter`).
- **Police technique & métriques :** `JetBrains Mono`, monospace (`@fontsource/jetbrains-mono`) pour les hachages, compteurs, dates ISO, horodatages et identifiants.
- **Échelle typographique :**
  - Titre 1 (Page) : `text-2xl font-bold tracking-tight` (24px)
  - Titre 2 (Section) : `text-lg font-semibold` (18px)
  - Titre 3 (Carte) : `text-sm font-semibold` (14px)
  - Corps standard : `text-sm leading-relaxed` (14px)
  - Texte compact / métadonnées : `text-xs leading-normal` (12px)
  - Micro-texte / Badges : `text-[11px] font-mono` (11px)

### 2.3 Rayons, Ombres, Z-Index & Mouvement

- **Rayons de courbure (`border-radius`) :**
  - Boutons, entrées : `rounded-lg` (8px)
  - Cartes et panneaux : `rounded-xl` (12px)
  - Modales et conteneurs majeurs : `rounded-2xl` (16px)
  - Badges et pilules : `rounded-full` (9999px)
- **Z-Index hiérarchique :**
  - Fond décoratif : `z-0`
  - Contenu principal : `z-10`
  - Barres fixes (Sidebar, Topbar) : `z-20`
  - Tiroirs (`Drawer`) et menus déroulants : `z-30`
  - Modales et dialogues (`Dialog`) : `z-50`
  - Toasts et notifications : `z-60`
- **Mouvement & Accessibilité :**
  - Transitions : `duration-150 ease-out` pour les micro-interactions.
  - `@media (prefers-reduced-motion: reduce)` : désactivation stricte des animations et transitions pour les utilisateurs sensibles.

---

## 3. Matrice des Badges de Statut (Alignée sur la Machine à États)

Chaque badge visuel est strictement couplé aux valeurs de `packages/domain/state_machine.py:ContentStatus` :

| Valeur Statut | Libellé Affiché | Thème & Style Visuel | Signification Métier |
| :--- | :--- | :--- | :--- |
| `DRAFT` | **Brouillon** | Gris ardoise (`bg-slate-800 text-slate-300 border-slate-700`) | Idée transformée en contenu préliminaire |
| `PENDING_REVIEW` | **En attente de revue** | Ambre pulsant (`bg-amber-500/15 text-amber-300 border-amber-500/30`) | Dans la file HITL, validation humaine requise |
| `APPROVED` | **Approuvé** | Émeraude (`bg-emerald-500/15 text-emerald-300 border-emerald-500/30`) | Validé par un humain, prêt pour planification |
| `SCHEDULED` | **Planifié** | Bleu céleste (`bg-sky-500/15 text-sky-300 border-sky-500/30`) | Daté dans le calendrier, en attente de publication |
| `PUBLISHING` | **Publication en cours** | Cyan animé (`bg-cyan-500/15 text-cyan-300 border-cyan-500/30 animate-pulse`) | Verrou idempotence acquis par le worker |
| `PUBLISHED` | **Publié** | Vert succès (`bg-emerald-600/20 text-emerald-400 border-emerald-600/40`) | Confirmé sur LinkedIn ou X avec post ID |
| `FAILED` | **Échec** | Rouge alerte (`bg-rose-500/15 text-rose-300 border-rose-500/30`) | Erreur API réseau ou rejet irrémédiable |
| `PUBLISH_UNKNOWN` | **Statut Incertain** | Violet réconciliation (`bg-purple-500/15 text-purple-300 border-purple-500/30`) | Timeout worker, intervention manuelle requise |
| **`DEGRADED`** | **Mode Dégradé** | Orange avertissement (`bg-orange-500/20 text-orange-300 border-orange-500/40`) | Contenu généré sous LLM/Tavily fallback |

---

## 4. Bibliothèque des Composants Réutilisables

1. **`AppShell`** : Layout maître comprenant la navigation, la barre d'en-tête, la zone de notification et le conteneur principal.
2. **`Sidebar`** : Navigation latérale avec compteurs dynamiques en temps réel, indicateur de gouvernance et raccourcis.
3. **`Topbar`** : Espace de travail actif, badge SANDBOX/LIVE, statut du kill switch, bascule de thème, avatar et rôle RBAC.
4. **`WorkspaceSwitcher`** : Sélecteur d'espace de travail avec rechargement contextuel et affichage du tenant ID.
5. **`UserMenu`** : Affichage de l'identité connectée, du rôle effectif et bouton de déconnexion sécurisée.
6. **`Button` / `IconButton`** : Boutons d'action avec gestion native des états `loading` (spinner discret), `disabled`, variantes (primary, secondary, danger, ghost) et taille cible tactile >= 44px.
7. **`Input` / `Textarea` / `Select` / `Checkbox` / `Switch`** : Contrôles de formulaire avec libellés accessibles (`htmlFor`), messages d'erreur associés (`aria-describedby`) et anneau de focus `:focus-visible` à fort contraste.
8. **`Tabs`** : Navigation par onglets accessible au clavier (flèches droite/gauche, rôle `tablist`/`tabpanel`).
9. **`Dialog` (Modale Accessible)** : Primitive Radix UI avec piégeage de focus, fermeture via Échap ou clic externe, retour du focus et libellés d'en-tête.
10. **`ConfirmDialog`** : Boîte de dialogue de confirmation renforcée pour les actions critiques (Approbation en mode LIVE, Rejet, Activation du Kill Switch).
11. **`PlatformPreview` (LinkedIn & X)** : Composant double prévisualisant fidèlement le rendu final d'un post avec mise en page spécifique (avatar, nom, date, hashtags en bleu, média associé, compteurs de caractères précis : 3000 max pour LinkedIn, 280 max pour X).
12. **`QualityGateResults`** : Visualisation claire des métriques de validation (Score d'alignement marque, Détection de doublons, Mention de transparence IA obligatoire).
13. **`CharacterCounter`** : Jauge dynamique avec alerte visuelle en cas de dépassement des plafonds plateforme.
14. **`ToastContainer` / `Toast`** : Notifications non bloquantes avec annonces d'accessibilité (`role="status"`, `aria-live="polite"`).
15. **`Skeleton`** : Formes grises animées (`animate-pulse`) reflétant la structure exacte des cartes avant chargement.
16. **`EmptyState`** : Panneau informatif accueillant avec icône, titre, explication et bouton d'action contextuelle suggérée.
17. **`ErrorState`** : Panneau d'erreur avec message d'aide, code de corrélation pour le support et bouton "Réessayer".

---

## 5. Wireframes Textuels des 9 Écrans

### Écran 0 : Authentification (`/auth`)
```text
+-------------------------------------------------------------+
|                     CONTENTOPS HARNESS                      |
|           Système d'Exploitation Éditorial Agentique        |
+-------------------------------------------------------------+
|  [ Carte de Connexion ]                                     |
|                                                             |
|  Identifiant Utilisateur : [ dev_user                     ] |
|  Rôle RBAC              : [ Owner (Administrateur)      v] |
|  Espace de Travail      : [ ws_default                   v] |
|                                                             |
|  [ Se connecter avec le jeton de développement ]            |
|                                                             |
|  Note sécurité : Les jetons JWT sont maintenus en mémoire  |
|  protégée et ne sont jamais stockés dans le localStorage.   |
+-------------------------------------------------------------+
```

### Écran 1 : Vue d'ensemble (`/dashboard`)
```text
+-----------------------------------------------------------------------------------------------+
| VUE D'ENSEMBLE                     [ Badge : MODE SANDBOX ] [ Kill Switch : Normal ] [ws_default]
| Synthèse des opérations éditoriales et performance du cycle
+-----------------------------------------------------------------------------------------------+
| [ Cartes KPIs ]                                                                               |
| - À revoir (HITL) : 3      - Planifiés : 7       - Publiés (7j) : 12    - En erreur / Inconnu: 0|
| - Budget LLM : 4.20$ / 25$ - Contenus dégradés : 1 (Tavily fallback)                         |
+-----------------------------------------------------------------------------------------------+
| [ État des Connexions Sociales ]            | [ Prochaines Publications Planifiées ]          |
| - LinkedIn : Connecté (Expire dans 58j)     | - 08/10 14h00 [LinkedIn] "Systèmes Multi-Agents"|
| - X / Twitter : Connecté (38 / 100 publiés) | - 09/10 09h30 [X] "Benchmark LangGraph 2026"    |
+-----------------------------------------------------------------------------------------------+
| [ Activité Récente du Journal d'Audit ]                                                       |
| - Il y a 10 min : Approbation de la variante var_8192 par Owner (Martial G.)                   |
+-----------------------------------------------------------------------------------------------+
```

### Écran 2 : Revue HITL (`/inbox` — Écran Critique)
```text
+-----------------------------------------------------------------------------------------------+
| REVUE DE VALIDATION HUMAINE (HITL)    Filtres: [Toutes plateformes v] [Tous statuts v]        |
| Raccourcis clavier actifs : [J/K] Naviguer  [A] Approuver  [R] Réécrire  [X] Rejeter  [?] Aide|
+-----------------------------------------------------------------------------------------------+
| [ Liste des Brouillons (1/3 sélectionné) ]                                                    |
|                                                                                               |
| Post ID: var_a1b2  |  Plateforme: LinkedIn  |  Statut: PENDING_REVIEW  | Score Qualité: 94%   |
| Hook : "Pourquoi 73% des projets d'agents IA échouent sans garde-fous déterministes ?"        |
|                                                                                               |
| +-----------------------------------------+-------------------------------------------------+ |
| | APERÇU FIDÈLE LINKEDIN                  | APERÇU FIDÈLE X / TWITTER                       | |
| | [Avatar] ContentOps Harness             | [Avatar] ContentOps Harness @contentops         | |
| | Pourquoi 73% des projets d'agents IA    | 73% des projets d'agents IA échouent sans       | |
| | échouent sans garde-fous déterministes ?| garde-fous déterministes.                       | |
| |                                         |                                                 | |
| | 1. Validation humaine asynchrone...     | Le décalage entre prototype et production...    | |
| |                                         |                                                 | |
| | #IA #LangGraph #Architecture            | #AgenticAI #LangGraph                           | |
| | Compteur : 1 240 / 3 000 caractères     | Compteur : 210 / 280 caractères                 | |
| +-----------------------------------------+-------------------------------------------------+ |
|                                                                                               |
| [ Quality Gate ] : Ton de marque : 95% | Faits vérifiés : 2/2 | Mention IA : Conforme         |
|                                                                                               |
| Actions : [ Rejeter (X) ]   [ Demander Réécriture (R) ]   [ Approuver & Planifier (A) ]       |
+-----------------------------------------------------------------------------------------------+
```

### Écran 3 : Calendrier (`/calendar`)
```text
+-----------------------------------------------------------------------------------------------+
| CALENDRIER ÉDITORIAL               Vues : [ Semaine ] [ Mois ]       Fuseau : Europe/Paris    |
+-----------------------------------------------------------------------------------------------+
| LUNDI 06         | MARDI 07         | MERCREDI 08      | JEUDI 09         | VENDREDI 10       |
|                  |                  | 14:00 [LinkedIn] | 09:30 [X]        | 16:00 [LinkedIn]  |
|                  |                  | "Multi-Agents"   | "Benchmark"      | "Gouvernance"     |
|                  |                  | Statut: SCHEDULED| Statut: SCHEDULED| Statut: SCHEDULED |
+-----------------------------------------------------------------------------------------------+
| Détection de collision : Créneaux espacés d'au moins 2h par plateforme.                       |
+-----------------------------------------------------------------------------------------------+
```

### Écran 4 : Idéation & Veille (`/ideation`)
```text
+-----------------------------------------------------------------------------------------------+
| IDÉATION & RECHERCHE DE SUJETS                    [ + Lancer une session d'idéation (Modale) ]|
| Recherche de sources, scoring selon les piliers de marque et génération d'idées LangGraph    |
+-----------------------------------------------------------------------------------------------+
| [ Cartes d'Idées Scorées ]                                                                    |
|                                                                                               |
| Titre : "Architecture des Checkpointers Distribués pour LangGraph"                            |
| Angle : Technique, orienté résilience et reprise sur incident.                                |
| Scores : Pertinence : 96% | Timing : 88% | Effort : Moyen | Alignement Marque : 100%          |
| Source liée : "Benchmark Systèmes Agentiques 2026" (arXiv:2402.01234)                         |
| Actions : [ Transformer en brouillon ]      [ Écarter ]                                       |
+-----------------------------------------------------------------------------------------------+
```

### Écran 5 : Stratégie & Insights (`/insights`)
```text
+-----------------------------------------------------------------------------------------------+
| STRATÉGIE ÉDITORIALE & ANALYTICS                      Période : [ 30 derniers jours v ]       |
+-----------------------------------------------------------------------------------------------+
| [ Performance par Plateforme ]                        [ Meilleurs Créneaux d'Engagement ]     |
| - LinkedIn : Taux d'engagement 5.4% (+0.8%)           - Mardi 08h30 - 09h30                   |
| - X / Twitter : Impressions 42 000 (+12%)             - Jeudi 14h00 - 15h30                   |
+-----------------------------------------------------------------------------------------------+
| [ Recommandations de l'Agent Stratégie ]                                                      |
| Recommandation : "Augmenter la cadence des retours d'expérience techniques sur LinkedIn."     |
| Justification : Les posts avec citations factuelles ont généré 2.4x plus de partages.        |
+-----------------------------------------------------------------------------------------------+
```

### Écran 6 : Profil de Marque (`/brand`)
```text
+-----------------------------------------------------------------------------------------------+
| PROFIL ÉDITORIAL DE MARQUE                                       [ Enregistrer les modifications ]
| Guide de ton et garde-fous pour les agents de production                                      |
+-----------------------------------------------------------------------------------------------+
| Piliers Éditoriaux :  [ IA générative & LLMs, Systèmes multi-agents, Automatisation ]        |
| Ton & Voix :          [ Expert, pragmatique, direct, sans jargon creux.                     ] |
| Sujets Interdits :    [ Spéculation crypto, Rumeurs non vérifiées, Dénigrement concurrents  ] |
| Politique CTA :       [ 1 appel à l'action maximum par publication                          ] |
| Historique : Version v3 active (Modifiée le 07/10/2026) | [ Restaurer une version antérieure ]|
+-----------------------------------------------------------------------------------------------+
```

### Écran 7 : Connexions Réseaux (`/connections`)
```text
+-----------------------------------------------------------------------------------------------+
| CONNEXIONS SOCIALES & COMPTES AUTORISÉS                                                        |
+-----------------------------------------------------------------------------------------------+
| [ CARTE LINKEDIN ]                                  [ CARTE X / TWITTER ]                     |
| Statut : CONNECTÉ (Token valide)                   Statut : CONNECTÉ (OAuth 2.0 PKCE)        |
| Compte : Analyticatech Company Page                 Compte : @Analyticatech                   |
| Scopes : w_member_social, r_basicprofile            Scopes : tweet.read, tweet.write, users.read|
| Expiration : dans 58 jours                          Plafond : 38 / 100 tweets ce mois-ci      |
| Actions : [ Reconnecter ]  [ Déconnecter ]          Actions : [ Reconnecter ]  [ Déconnecter ]|
+-----------------------------------------------------------------------------------------------+
```

### Écran 8 : Gouvernance & Paramètres (`/settings` — Rôle Owner)
```text
+-----------------------------------------------------------------------------------------------+
| GOUVERNANCE ÉDITORIALE & CONTRÔLE SYSTÈME                                [ Rôle : Owner requis ]|
+-----------------------------------------------------------------------------------------------+
| [ KILL SWITCH GLOBAL D'URGENCE ]                                                              |
| État actuel : NORMAL (Désactivé)                                                              |
| [ ACTIVER LE KILL SWITCH D'URGENCE ] (Bloque instantanément toutes les publications)          |
+-----------------------------------------------------------------------------------------------+
| [ Plafonds & Limites de Débit ]                     [ Mode d'Exécution ]                      |
| Publications max par heure : [ 5 ] publications     Mode actuel : SANDBOX (Environnement dev) |
+-----------------------------------------------------------------------------------------------+
| [ Journal d'Audit des Validations ]                                                           |
| 07/10 22:30 | var_1092 | APPROVE  | Par: owner_martial | IP: 127.0.0.1                       |
+-----------------------------------------------------------------------------------------------+
```
