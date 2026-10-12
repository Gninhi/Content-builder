# Crédits & Licences du Design System

Ce document consigne les licences, auteurs et adaptations de l'ensemble des bibliothèques, polices, composants et motifs intégrés dans le système de conception de **ContentOps Harness**.

---

## 1. Typographie & Polices

| Ressource | Auteur / Fonderie | Licence | Usage dans l'application | Adaptations / Optimisations |
| :--- | :--- | :--- | :--- | :--- |
| **Geist Sans** | Vercel Inc. | [SIL Open Font License 1.1 (OFL)](https://scripts.sil.org/OFL) | Police d'interface par défaut (texte courant, titres, boutons, formulaires) | Auto-hébergée via Fontsource, sous-ensembles latin & latin-ext uniquement, `font-display: swap`, 2 fichiers critiques préchargés (`latin-400.woff2` et `latin-600.woff2`). |
| **Geist Mono** | Vercel Inc. | [SIL Open Font License 1.1 (OFL)](https://scripts.sil.org/OFL) | Hachages cryptographiques SHA-256, identifiants techniques, blocs de code, chiffres tabulaires des métriques | Auto-hébergée, sous-ensembles latin, `font-display: swap`. Jamais utilisée sur les libellés de texte courant. |

---

## 2. Primitives et Patterns de Composants

| Composant / Motif | Source d'inspiration / Auteur | Licence | Fichiers d'implémentation | Adaptations effectuées |
| :--- | :--- | :--- | :--- | :--- |
| **Radix Color System (12 steps)** | WorkOS / Radix Team | MIT | `src/styles/tokens.css`<br>`src/styles/palettes/*.css` | Transcription en espace colorimétrique moderne **OKLCH**, génération des variantes alpha, application via attributs `data-palette` et `data-mode`. |
| **shadcn/ui Primitives Pattern** | shadcn (shadcn.com) | MIT | `src/components/ui/*` | Typage strict TypeScript, suppression des variantes pill/rounded-full excessives, adaptation aux tokens CSS purs sans classes arbitraires, intégration i18n native. |
| **Command Palette (⌘K)** | Pacocoursey / cmdk & Linear patterns | MIT | `src/components/ui/CommandMenu.tsx` | Navigation contextuelle accessible, gestion des raccourcis J/K et touches de fonction, mode dégradé sans animation superflue. |
| **Lucide Icons** | Lucide Contributors | ISC | Tout le projet (`lucide-react`) | Standardisation sur une taille de 16px/18px (stroke 1.75px) avec `aria-hidden="true"` systématique et labels textuels associés. |

---

## 3. Règle de Non-Régression & Propriété Intellectuelle

* Aucun code minifié propriétaire ou non documenté n'est injecté.
* Tous les composants retenus depuis l'écosystème open-source (21st.dev / shadcn) sont adaptés pour être strictement propriétaires du dépôt (`apps/web/src/components/ui/`), garantissant l'indépendance technologique et l'absence d'appels réseau externes (0 CDN tiers).
