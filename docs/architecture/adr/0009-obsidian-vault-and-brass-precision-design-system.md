# ADR 0009: Direction Artistique « Obsidian Vault & Brass Precision » et Système de Design

## Statut
Accepté

## Date
10 Octobre 2026

## Contexte
L'interface initiale de ContentOps Harness souffrait de disparités visuelles :
- Teintes grises et bleues génériques non représentatives de l'exigence de sécurité d'un système éditorial B2B haute gouvernance.
- Utilisation excessive de la police monospace pour des libellés courants (fatigue visuelle).
- Cibles tactiles hétérogènes (< 38px sur certains boutons d'action), créant des risques de fausses manipulations.
- Superposition de la barre d'action HITL flottante sur le contenu des aperçus réseaux.
- Tronquage du texte et de l'en-tête sur mobile et tablettes.

## Décision
Adopter la **Direction Artistique A : « Obsidian Vault & Brass Precision »** et refondre tous les composants et écrans de l'application :
1. **Surfaces d'Instrument de Précision :**
   - Fond d'écran sombre profond : `--color-bg-base` (`#070A0F` / `obsidian-950`).
   - Panneaux de commande et cartes : `--color-bg-panel` (`#0D121D` / `obsidian-900`).
   - Bordures titane chirurgicales de 1px : `--color-border-titanium` (`#1E293B` / `titanium-800`).
2. **Points Focaux Laiton & Ambre Chaud :**
   - Accentuation réservée aux décisions critiques, à l'action principale HITL (« Approuver ») et aux statuts chauds : `--color-brass-primary` (`#D97706` / `brass-500`).
3. **Scellement Cryptographique & Kill Switch :**
   - Vert émeraude franc pour les validations et scellements SHA-256 (`#10B981` / `emerald-500`).
   - Rouge carmin haute visibilité pour l'arrêt d'urgence (`#E11D48` / `rose-600` / `shadow-crimson`).
4. **Typographie Hybride & Lisibilité :**
   - Corps de texte, titres et microcopy en police sans-serif moderne (`Inter`).
   - Police monospace (`JetBrains Mono`) strictement réservée aux empreintes de hachage SHA-256, horodatages UTC, identifiants techniques et compteurs tabulaires.
5. **Accessibilité & Cibles Tactiles WCAG 2.2 AA :**
   - Toutes les cibles interactives ont une dimension minimale de `min-h-[44px] min-w-[44px]`.
   - Les anneaux de focus sont visibles avec un contour contrasté double.
   - Les raccourcis clavier HITL (J/K/A/R/E/W/X/?) sont documentés et neutralisés dès que le focus est dans un champ de saisie (`INPUT`, `TEXTAREA`).

## Conséquences
- **Positives :**
  - Identité institutionnelle premium alignée avec le positionnement B2B critique du produit.
  - Suppression complète des débordements horizontaux de 320 px à 2560 px.
  - Zéro régression sur la machine à états de scellement et de publication.
  - Développeurs outillés d'un Guide de Style Vivant interactif (`/ui/#styleguide`).
- **Négatives :**
  - Nécessite de maintenir la discipline sur les tokens Tailwind sans réintroduire de valeurs hexadécimales en dur.
