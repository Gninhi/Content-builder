# Phase 0 — État des Lieux et Rapport d'Audit Complet

**Date d'audit :** 10 octobre 2026  
**Rôle :** Directeur de Conception Produit & Ingénieur Front-End Principal  
**Périmètre :** Système de design, accessibilité WCAG 2.2 AA, responsive, performance et architecture des thèmes de ContentOps Harness (`Content-builder`).

---

## 1. Cartographie du Système de Style Actuel

### 1.1 Emplacement des tokens
- **CSS (`apps/web/src/index.css`) :** Déclare seulement 8 variables CSS (`--bg-base`, `--bg-panel`, `--bg-sub`, `--border-titanium`, `--border-interactive`, `--text-primary`, `--text-secondary`, `--accent-brass`) avec une surcharge `.light`. **Ces variables sont presque totalement ignorées** dans les composants réels.
- **Tailwind (`apps/web/tailwind.config.js`) :** Déclare les échelles `obsidian` (950 à 800), `titanium` (900 à 100), `brass` (900 à 50), `brand` (50 à 900), des ombres `vault`, `brass`, `emerald`, `crimson`, et les polices `Inter` et `JetBrains Mono`.
- **Guide de Style (`apps/web/src/screens/StyleGuideScreen.tsx`) :** Liste statique en dur de 11 jetons étiquetés « Direction A — Obsidian & Brass ».

### 1.2 Valeurs en dur et styles non autorisés
- **Couleurs interdites identifiées :**
  - Cyan dans `apps/web/index.html` : `selection:bg-cyan-500/30 selection:text-cyan-200`.
  - Cyan dans `apps/web/src/components/profile/PreferencesTab.tsx` : `border-cyan-500 bg-cyan-500/10 text-cyan-400`.
  - Cyan dans `apps/web/src/components/common/Badge.tsx` (variante `info`).
  - Violet/purple dans `Badge.tsx` (variante `PUBLISH_UNKNOWN`) et `DashboardScreen.tsx` (KPI budget LLM).
- **Lueurs et effets décoratifs interdits :**
  - `.ambient-glow-brass` et `.ambient-glow-emerald` avec filtres `blur(80px)` dans `index.css`.
  - `blur-3xl` décoratif dans `DashboardScreen.tsx` et `StyleGuideScreen.tsx`.
- **Hexadécimaux en dur :**
  - `bg-[#0077b5]/20 text-[#0077b5]` (LinkedIn) dans `DashboardScreen.tsx` et `InsightsScreen.tsx`.
- **Chaînes en dur hors i18n :**
  - Textes système en français codés en dur dans `Button.tsx`, `Badge.tsx`, `InboxActionBar.tsx`, `InboxQualityGateCard.tsx`, `DashboardScreen.tsx`, `IdeationScreen.tsx`, `CalendarScreen.tsx`.

### 1.3 Doublons de composants
- **Boutons :** Multiplication de balises `<button>` avec classes utilitaires Tailwind ad-hoc au lieu de s'appuyer sur la source unique `Button.tsx`.
- **Badges :** Recréation inline de pastilles dans `Topbar.tsx`, `Sidebar.tsx`, `DashboardScreen.tsx`.
- **Dialogues :** 4 implémentations divergentes (`Dialog.tsx`, `ConfirmDialog.tsx`, `InboxFeedbackModal.tsx`, `CalendarRescheduleModal.tsx`).
- **Squelettes :** Duplication entre `Skeleton.tsx` et des blocs `<div className="h-8 w-64 bg-slate-800 rounded animate-pulse" />`.

### 1.4 Parité du thème clair
- **Rupture critique (1:1 de contraste / blanc-sur-blanc) :**
  - `index.html` et `AppShell.tsx` forcent un arrière-plan `bg-slate-950 text-slate-100`.
  - La classe `.panel-vault` en mode clair force un fond blanc (`rgba(255, 255, 255, 0.95)`), mais les composants enfants conservent `text-white` ou `text-slate-200`. Les titres et chiffres deviennent totalement invisibles.
  - La Sidebar et la Topbar restent sombres en mode clair (`bg-slate-900/95`).

### 1.5 Polices et poids des assets
- **34 fichiers de polices** individuels chargés depuis `@fontsource/inter` et `@fontsource/jetbrains-mono` couvrant toutes les graisses (100 à 900) en `.woff` et `.woff2`.
- **Poids total des polices : ~850 Ko**, aucun préchargement ciblé des fichiers critiques.
- **Bundle JS : 433.27 Ko** (gzip: 110.57 Ko) en un unique bloc non découpé (aucun lazy-loading de route).
- **Bundle CSS : 52.87 Ko** (gzip: 9.43 Ko).

### 1.6 Gestion actuelle du thème
- Stockage restreint à `localStorage.getItem('contentops_theme')`.
- Aucun cookie first-party, absence de script bloquant anti-flash dans `<head>`, ce qui génère un flash systématique (FOUC) au chargement.
- Aucune synchronisation serveur avec table de préférences, aucun schéma versionné.

---

## 2. Mesures de Référence

| Métrique | Valeur mesurée actuelle | Statut | Cible Phase 1-8 |
| :--- | :--- | :--- | :--- |
| **Lighthouse Accessibilité (Mobile)** | 96 (sombre) / Invalide (clair : blanc sur blanc) | ⚠️ Échec partiel | ≥ 90 vérifié sur TOUS les thèmes × modes |
| **Lighthouse Bonnes Pratiques** | 100 | ✅ Conforme | 100 |
| **Lighthouse SEO** | 100 | ✅ Conforme | 100 |
| **Poids total des polices** | ~850 Ko (34 fichiers) | ❌ Bloat critique | < 120 Ko (Geist Sans + Mono, 2 fichiers préchargés) |
| **Taille chunk JS principal** | 433.27 Ko (monolithique) | ⚠️ À optimiser | < 180 Ko initial via code splitting par route |
| **Taille CSS** | 52.87 Ko | ⚠️ Non standard | Structuré en tokens OKLCH 3 couches |
| **CLS (Cumulative Layout Shift)** | Dégradé par le bandeau démo (48px) | ⚠️ À corriger | ≈ 0.00 |
| **Tests Vitest** | 36 / 36 verts (100%) | ✅ Conforme | 100% verts à chaque commit |

---

## 3. Rapport Tabulaire Synthétique d'Audit

| Constat | Fichier(s) | Impact | Action corrective |
| :--- | :--- | :--- | :--- |
| **1. Contraste blanc-sur-blanc en mode clair** | `apps/web/src/index.css`<br>`apps/web/src/components/layout/AppShell.tsx` | Mode clair totalement illisible (ratio 1:1, violation WCAG 2.2 AA). | Remplacer les classes de couleurs en dur par des tokens sémantiques CSS variables (`var(--surface)`, `var(--text-primary)`). |
| **2. Barre d'action HITL collante recouvrant le contenu** | `apps/web/src/components/inbox/InboxActionBar.tsx`<br>`apps/web/src/screens/InboxScreen.tsx` | La barre flotte sur le post en cours de revue, masque les textes et empile les boutons sur mobile (320-390px). | Sortir l'action bar du flux chevauchant, réserver une zone d'espacement sûre (`padding-bottom` dédié) et layout adapté par container queries. |
| **3. Flash de thème au chargement (FOUC)** | `apps/web/index.html`<br>`apps/web/src/context/ThemeContext.tsx` | Écran blanc ou sombre violent avant hydratation React. | Script en ligne bloquant dans `<head>` lisant le cookie `co_prefs` et posant les attributs sur `<html>` avant le 1er rendu. |
| **4. Poids excessif des polices (850 Ko)** | `apps/web/src/index.css`<br>`apps/web/package.json` | 34 requêtes réseau `.woff2`/`.woff`, ralentit l'affichage initial et provoque du FOUT/FOIT. | Migrer vers Geist Sans + Geist Mono (OFL), auto-hébergées, latin/latin-ext, préchargement de 2 fichiers uniquement. |
| **5. Conflit sémantique accent ambre vs avertissement** | `apps/web/tailwind.config.js`<br>`apps/web/src/components/common/Button.tsx` | Impossible de distinguer une action interactive d'un statut d'alerte ou en attente. | Dissocier l'accent de marque des couleurs de statut (warning ambre séparé d'un accent laiton/doré/neutre distinct). |
| **6. Navigation à plat de 11 entrées désorganisée** | `apps/web/src/components/layout/Sidebar.tsx` | Charge cognitive excessive, mélange production, réglages et outils internes de développement. | Restructurer la navigation en sections cibles : Piloter, Produire, Valider, Diffuser, Apprendre, Configurer, Atelier. |
| **7. Abus de pastilles et mono majuscules** | `apps/web/src/components/common/Badge.tsx`<br>Multiples écrans | Esthétique surchargée, sentiment d'interface encombrée. | Remplacer les pastilles systématiques par des tags sobres (point + texte) et réserver la police mono aux hachages et IDs. |
| **8. Bandeau démo massif dégradant le CLS** | `apps/web/src/components/layout/AppShell.tsx` | Pousse brutalement le layout, consomme une hauteur précieuse sur mobile. | Remplacer par un bandeau fin d'une seule ligne sobre, non saturé, intégré sans décalage de mise en page. |
| **9. Couleurs interdites (cyan, purple)** | `index.html`<br>`Badge.tsx`<br>`PreferencesTab.tsx`<br>`DashboardScreen.tsx` | Violation des directives de direction artistique. | Éliminer tout cyan, bleu électrique, violet décoratif ; basculer sur les palettes réglementaires. |
| **10. Scores aberrants (« 95 / 10 », « 950% »)** | `apps/web/src/screens/IdeationScreen.tsx` | Perte de crédibilité de l'idéation IA. | Normaliser le calcul d'affichage par rapport à l'échelle [0.0, 10.0] du contrat backend (consigné dans `ui-data-issues.md`). |
| **11. Métriques Quality Gate et insights fictifs** | `apps/web/src/components/inbox/InboxQualityGateCard.tsx`<br>`apps/web/src/screens/InsightsScreen.tsx` | Données inventées affichées sur des workspaces neufs. | Raccorder aux payloads réels et afficher des états vides honnêtes en cas de données insuffisantes. |
| **12. Manque de découpage du bundle JS (433 Ko)** | `apps/web/src/App.tsx` | Tous les écrans sont chargés dès la page de connexion, allongeant le TTI. | Découpage du code par route via `React.lazy` et `Suspense`. |
