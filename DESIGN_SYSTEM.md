# ContentOps Harness — Design System
## Direction Artistique : « Obsidian Vault & Brass Precision »

### 1. Philosophie & Identité Visuelle
ContentOps Harness est un système d'exploitation éditorial B2B haute gouvernance avec validation humaine obligatoire (HITL), scellement cryptographique SHA-256 et publication « au plus une fois ».

L'univers visuel **« Obsidian Vault & Brass Precision »** s'inspire des interfaces de terminaux financiers (Bloomberg, Palantir Gotham) et des coffres-forts cryptographiques matériels :
- **Rigueur institutionnelle :** Les surfaces sont denses, sombres, nettes, sans fioritures superflues ni dégradés néon IA génériques.
- **Précision mécanique :** Les bordures titane (1px), les séparateurs nets et les compteurs mono-espacés renforcent la sensation d'instrumentation de précision.
- **Accents laiton & ambre chaud :** Utilisés avec parcimonie pour les points d'ancrage décisionnels, les actions critiques et l'état de revue humaine.
- **Scellement émeraude :** Les validations cryptographiques et publications scellées sont marquées par un vert émeraude franc et sans ambiguïté.

---

## 2. Palette de Couleurs & Tokens Sémantiques

### Thème Sombre (Obsidian Vault — Référence de base)
| Token Sémantique | Variable CSS / Classe Tailwind | Valeur Hex | Usage |
| :--- | :--- | :--- | :--- |
| **Surface Base** | `--color-bg-base` / `bg-obsidian-950` | `#070A0F` | Fond principal de l'application |
| **Surface Panel** | `--color-bg-panel` / `bg-obsidian-900` | `#0D121D` | Cartes, sidebars, panneaux |
| **Surface Elevated** | `--color-bg-elevated` / `bg-obsidian-850` | `#111827` | Menus déroulants, modales, popovers |
| **Surface Sub** | `--color-bg-sub` / `bg-obsidian-800` | `#162032` | Champs de formulaire, zones imbriquées |
| **Bordure Titanium** | `--color-border-titanium` / `border-titanium-800`| `#1E293B` | Bordures structurelles par défaut |
| **Bordure Interactive**| `--color-border-interactive` / `border-titanium-700`| `#2E3A52` | Bordures au survol et états focus |
| **Accent Laiton (Brass)**| `--color-accent-brass` / `text-brass-400` | `#F59E0B` | Points focaux, revue HITL, état chaud |
| **Bouton Laiton Fort** | `--color-brass-primary` / `bg-brass-500` | `#D97706` | Actions principales de gouvernance |
| **Cryptographic Emerald**| `--color-emerald-vault` / `text-emerald-400` | `#10B981` | Scellement cryptographique, succès |
| **Kill-Switch Crimson** | `--color-crimson-danger` / `text-rose-400` | `#F43F5E` | Arrêt d'urgence, rejet, alerte |

### Thème Clair (Architectural Precision)
| Token Sémantique | Variable CSS / Classe Tailwind | Valeur Hex | Usage |
| :--- | :--- | :--- | :--- |
| **Surface Base** | `--color-bg-base` | `#F8FAFC` | Fond lumineux architectural |
| **Surface Panel** | `--color-bg-panel` | `#FFFFFF` | Cartes blanches pures |
| **Surface Sub** | `--color-bg-sub` | `#F1F5F9` | Champs de formulaire et zones neutres |
| **Bordure Titanium** | `--color-border-titanium` | `#E2E8F0` | Bordures nettes haute lisibilité |
| **Texte Primaire** | `--color-text-primary` | `#0F172A` | Contraste supérieur à 10:1 (WCAG AAA) |
| **Texte Secondaire**| `--color-text-secondary` | `#475569` | Métadonnées et labels |
| **Accent Laiton Bruni**| `--color-accent-brass` | `#B45309` | Lisibilité maximale sur fond blanc |

---

## 3. Typographie

- **Police Principale :** `Inter`, sans-serif.  
  - Corps de texte : `text-xs` (12px) et `text-sm` (14px) pour optimiser la densité d'information.  
  - Titres de section : `text-lg` à `text-2xl` avec `tracking-tight font-bold`.
- **Police Technique & Métriques :** `JetBrains Mono`, monospace.  
  - Empreintes SHA-256 (`font-mono text-xs text-amber-400/90`).  
  - Horodatages UTC, compteurs de caractères, identifiants `job_id`, `variant_id`.  
  - Statistiques de performance et métriques d'engagement.

---

## 4. Règles d'Accessibilité (WCAG 2.2 AA)

1. **Ratios de Contraste :**
   - Texte normal (<= 18px) : au minimum **4.5:1** contre son arrière-plan.
   - Éléments graphiques et bordures interactives : au minimum **3:1**.
2. **Cibles Tactiles et de Clic :**
   - Tous les boutons et éléments cliquables ont une zone tactile minimale de **44 × 44 px** (`min-h-[44px] min-w-[44px]`).
3. **Focus Visible :**
   - `:focus-visible` universel avec contour contrasté double (`outline: 2px solid`, `outline-offset: 2px`).
4. **Réduction du Mouvement :**
   - Respect strict de `prefers-reduced-motion` : toutes les animations et transitions sont immédiatement désactivées pour les utilisateurs sensibles.

---

## 5. Composants Communs Normalisés

- **`Button` :** Variantes `primary`, `secondary`, `danger`, `vault`, `ghost`, `outline`. Prise en charge des états `isLoading` et `disabled`.
- **`Badge` & `StatusBadge` :** Variantes `brass`, `success`, `danger`, `warning`, `info`, `neutral`. Affichage déterministe des statuts du cycle éditorial.
- **`Dialog` & `ConfirmDialog` :** Modales avec piège de focus WAI-ARIA, fermeture Échap, panneau `obsidian` flouté et boutons contrastés.
- **`Input` & `Textarea` :** Surfaces haute densité, bordures titane, anneaux de focus laiton, compteurs de caractères temps réel.
- **`EmptyState` & `ErrorState` :** Écrans d'état zéro résilients avec actions de relance et diagnostics clairs.
- **`Skeleton` :** Effet de pulsation atténué adapté aux interfaces de commande professionnelle.
