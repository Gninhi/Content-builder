# ADR-005 : Migration de la Pile Frontend vers React, Vite, TypeScript et Radix UI

**Date :** 8 Octobre 2026  
**Statut :** Accepté  
**Décideurs :** Lead Product Designer & Senior Frontend Engineer  
**Consulté :** Équipe Backend & Sécurité  

---

## 1. Contexte et Problématique

L'implémentation initiale de l'interface utilisateur de ContentOps Harness résidait dans des fichiers statiques bruts (`apps/web/index.html`, `apps/web/app.js`, `apps/web/style.css`), sans gestionnaire de paquets, sans compilateur et sans typage statique.

Cette approche a entraîné des défaillances critiques :
1. **Incompatibilité totale avec la politique de sécurité (CSP) :** Le code s'appuyait sur des scripts et styles chargés via des CDN tiers (`cdn.tailwindcss.com`, `fonts.googleapis.com`, `unpkg.com`), bloqués immédiatement par l'en-tête `default-src 'self'`.
2. **Fragilité des données et régressions `undefined` :** En l'absence de validation de schéma et de typage à la frontière de l'API, les réponses HTTP (notamment 401 Unauthorized) provoquaient des plantages JavaScript en chaîne (`TypeError`).
3. **Absence d'accessibilité WAI-ARIA :** Les modales et composants interactifs étaient des balises `div` génériques sans focus trap, sans libellés accessibles et sans gestion du clavier.
4. **Impossibilité de tester unitairement :** Aucun outillage de test composant ou E2E automatisable.

---

## 2. Décision d'Architecture

Nous décidons de migrer l'interface vers une architecture moderne, compilée, typée et auto-hébergée :

- **Framework UI :** **React 18/19** avec **TypeScript** strict.
- **Bundler & Tooling :** **Vite**, assurant un build optimisé, du hot-reloading ultra-rapide et un hachage d'actifs pour la mise en cache longue durée.
- **Styling :** **Tailwind CSS** pré-compilé localement lors du build, sans CDN ni évaluation runtime dans le navigateur.
- **Design System & Primitives Accessibles :** **Radix UI** / primitives conformes WAI-ARIA (Dialog, DropdownMenu, Tooltip, Tabs, Switch, Slot) pour garantir une accessibilité WCAG 2.2 AA native (gestion du focus, Échap, lecteurs d'écran).
- **Gestion de l'État Serveur & Cache :** **TanStack Query (React Query)** pour la mise en cache des requêtes API, la revalidation automatique, l'invalidation optimisée et la gestion granulaire des états `loading`, `error`, `empty`.
- **Validation aux Frontières :** **Zod** pour valider et assainir rigoureusement toutes les charges utiles issues de l'API.
- **Typage OpenAPI :** Génération automatique des interfaces TypeScript depuis le schéma `openapi.json` de FastAPI.
- **Polices et Icônes :** Polices auto-hébergées via `@fontsource/inter` et `@fontsource/jetbrains-mono` ; icônes vectorielles via `lucide-react` embarquées directement dans le code source.

---

## 3. Modalités de Déploiement et Intégration Backend

- Le projet frontend est hébergé dans `apps/web/` avec son propre `package.json` et sa configuration Vite.
- Le build de production produit un dossier de distribution statique `apps/web/dist/`.
- FastAPI sert directement ces fichiers statiques via `app.mount("/ui", StaticFiles(directory="apps/web/dist", html=True))`.
- La politique de sécurité CSP `default-src 'self'; frame-ancestors 'none';` reste strictement préservée sans aucun assouplissement.

---

## 4. Conséquences et Bénéfices

### Positives :
- **Sécurité maximale :** Zéro dépendance CDN externe, respect strict de la CSP `default-src 'self'`.
- **Zéro valeur "undefined" :** Contrat de données strict et typé de bout en bout (OpenAPI ➔ Zod ➔ Composants React).
- **Accessibilité WCAG 2.2 AA garantie :** Raccourcis clavier (J/K, A, R, X), focus traps sur toutes les modales, lecteurs d'écran pris en charge nativement.
- **Auditabilité et Qualité :** Intégration de tests de composants (Vitest + Testing Library) et tests E2E Playwright automatisés dans la CI.

### Négatives / Contraintes :
- Nécessite une étape de compilation npm (`npm run build`) avant l'exécution en production ou dans le conteneur Docker. (Pris en compte via un build Docker multi-étapes).
