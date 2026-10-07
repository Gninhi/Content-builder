# ContentOps Harness — Frontend Web Interface

Interface web de gestion et de gouvernance de contenu éditorial pour réseaux sociaux piloté par agents autonomes avec validation humaine obligatoire (HITL - Human-In-The-Loop).

---

## 1. Vue d'Ensemble & Principes Directeurs

- **Sécurité Stricte :** Conforme à la politique de sécurité de contenu (CSP) `default-src 'self'`. Aucune ressource externe ou CDN n'est autorisée. Le jeton JWT est conservé strictement en mémoire volatile (aucun stockage dans `localStorage` ou `sessionStorage`).
- **Gouvernance Humaine Obligatoire :** Aucune publication directe sans passage par le Quality Gate et validation par un rôle habilité (`Owner`).
- **Accessibilité Universelle :** Conforme aux normes WCAG 2.2 AA (0 violation critique ou sérieuse sous `axe-core`). Raccourcis clavier (J/K, A, R, X, ?), contraste >= 4.5:1 sur les textes et composants.
- **Zéro Donnée Factice :** Toutes les données affichées proviennent exclusivement de l'API FastAPI backend ou sont présentées sous la forme d'états vides explicites (`EmptyState`).

---

## 2. Pile Technologique

- **Framework :** [React 18](https://react.dev) + [TypeScript 5](https://www.typescriptlang.org)
- **Bundler :** [Vite 5](https://vitejs.dev)
- **Styles :** [Tailwind CSS 3.4](https://tailwindcss.com) (compilé localement, sans runtime browser)
- **Typographie :** Polices `@fontsource/inter` et `@fontsource/jetbrains-mono` auto-hébergées
- **Icônes :** [Lucide React](https://lucide.dev)
- **Requêtes & Cache :** Client API natif avec typage OpenAPI et gestion de correlation-ID
- **Tests Unitaires & Composants :** [Vitest](https://vitest.dev) + [Testing Library](https://testing-library.com)
- **Tests E2E & Accessibilité :** [Playwright](https://playwright.dev) + [Axe-Core](https://github.com/dequelabs/axe-core)

---

## 3. Structure du Projet

```text
apps/web/
├── public/                 # Assets statiques locaux (favicon.svg)
├── src/
│   ├── __tests__/          # Tests unitaires et de composants Vitest
│   ├── components/
│   │   ├── common/         # Composants d'UI réutilisables (Button, Badge, Input, Dialog, etc.)
│   │   └── layout/         # AppShell, Sidebar, TopBar, MobileNavigation
│   ├── context/            # AuthContext (JWT en mémoire), LanguageContext, ThemeContext
│   ├── i18n/               # Dictionnaires bilingues FR & EN
│   ├── lib/                # Client API HTTP avec injection Bearer et gestion d'erreurs
│   ├── screens/            # Les 9 écrans de l'application (Auth à Settings)
│   ├── types/              # Définitions TypeScript issues d'OpenAPI
│   ├── App.tsx             # Routeur applicatif et gestionnaire d'état de session
│   ├── index.css           # Directives Tailwind et design tokens
│   └── main.tsx            # Point d'entrée React
├── index.html              # Gabarit HTML conforme CSP
├── package.json
├── tsconfig.json
└── vite.config.ts          # Configuration de compilation et proxy dev
```

---

## 4. Démarrage et Développement Local

### Prérequis
- Node.js >= 18
- Backend FastAPI démarré sur `http://127.0.0.1:8000`

### Commandes de base
```bash
# Installation des dépendances
npm install

# Démarrage du serveur de développement (port 3000 avec proxy vers l'API 8000)
npm run dev

# Exécution des tests unitaires (Vitest)
npm run test

# Compilation pour la production (génère apps/web/dist)
npm run build
```

Le build produit est servi directement par FastAPI à l'adresse suivante :
`http://127.0.0.1:8000/ui/`

---

## 5. Procédure de Mise à Jour du Contrat API (OpenAPI)

Pour synchroniser les types TypeScript avec le schéma OpenAPI de FastAPI :

1. Vérifier que le backend FastAPI est démarré sur `http://127.0.0.1:8000`.
2. Récupérer le schéma OpenAPI généré :
   ```bash
   curl http://127.0.0.1:8000/openapi.json -o docs/openapi.json
   ```
3. Utiliser `openapi-typescript` pour régénérer les interfaces :
   ```bash
   npx openapi-typescript docs/openapi.json -o apps/web/src/types/api_generated.d.ts
   ```
4. Vérifier les types dans `apps/web/src/types/api.ts` et lancer le typecheck :
   ```bash
   npm run build
   ```

---

## 6. Accessibilité & Vérification de Conformité

Le projet intègre un audit automatisé axe-core couvrant les 9 écrans :

```bash
# Lancement de l'audit d'accessibilité WCAG 2.2 AA
python scripts/verify_accessibility_axe.py

# Lancement des tests de régression visuelle et de console E2E
python scripts/verify_production_ui.py
```

### Règles d'or d'accessibilité :
- Tout élément cliquable sans texte explicite doit posséder un attribut `aria-label` descriptif.
- Le nom accessible des boutons textuels doit inclure le texte visible.
- Tous les boutons interactifs ont une surface tactile minimale de 44x44 px (`min-h-[44px]`).
- Les contrastes de couleur sont maintenus à un ratio supérieur à 4.5:1.
