# Références de Design et Analyse Comparée

Ce document compile les fiches d'analyse des références de design de premier plan dans l'écosystème SaaS B2B, conformément à la Phase 1 de la refonte de **ContentOps Harness**.

---

## 1. Fiches de Référence

### 1.1 Geist Design System (Vercel)
* **Ce que l'on retient :**
  * La rigueur géométrique et le minimalisme monochrome absolu.
  * Les ombres utilisées comme des micro-bordures intérieures ou superposées (« border-as-shadow »), extrêmement nettes sur écrans Retina.
  * Les polices **Geist Sans** et **Geist Mono** : lisibilité exceptionnelle en petite taille, chiffres tabulaires parfaits pour les tableaux de bord et métriques.
  * L'absence totale de fioritures décoratives (pas de néons, pas de dégradés gratuits).
* **Pourquoi :** Vercel a défini le standard du design pour développeurs et outils d'infrastructure critique : sobre, rapide, sans bruit visuel.
* **Ce que l'on ne copie pas :** Le côté parfois trop austère et clinique ("tout en noir et blanc") qui nuit à la hiérarchie dans un outil éditorial métier où l'action humaine (HITL) doit ressortir avec chaleur et clarté.

---

### 1.2 Radix Colors & Radix Themes (WorkOS)
* **Ce que l'on retient :**
  * Le modèle d'échelle à **12 niveaux de couleurs sémantiques** :
    * Niveaux 1-2 : Fonds de page et surfaces d'application
    * Niveaux 3-5 : États interactifs de surface (défaut, survol, actif)
    * Niveaux 6-8 : Bordures (subtiles, interactives, focus)
    * Niveaux 9-10 : Couleurs pleines / actions primaires et survols
    * Niveaux 11-12 : Textes à contraste faible (atténués) et élevé (titres)
  * Les échelles alpha transparentes associées (ex. `slate-a3`) garantissant une superposition naturelle sur tous les fonds.
  * La séparation stricte entre les teintes d'accent et les couleurs d'état (succès, avertissement, danger, information).
* **Pourquoi :** C'est le système de tokens le plus mathématiquement rigoureux du web moderne, garantissant les ratios WCAG par conception.
* **Ce que l'on ne copie pas :** Les rayons de courbure par défaut trop ronds dans Radix Themes et les palettes pastel qui manquent de densité pour un environnement de gouvernance d'entreprise.

---

### 1.3 Linear
* **Ce que l'on retient :**
  * La densité d'information maîtrisée : interfaces compactes, navigation au clavier omniprésente (raccourcis universels, palette ⌘K).
  * L'absence quasi totale de pastilles décoratives : les statuts sont indiqués par une icône précise de 14px ou un point coloré de 6px + libellé clair.
  * Les transitions de surface ultra-fluides (transform/opacity exclusivement, sous 150ms).
  * La hiérarchie typographique : une seule graisse forte pour le titre actif, tout le reste en graisses 400/500 finement contrastées.
* **Pourquoi :** Linear est la référence mondiale de fluidité et de productivité bureautique.
* **Ce que l'on ne copie pas :** Les textes en très petit corps (11px) et contrastes parfois limites (< 4.5:1) dans certains états inactifs de Linear, incompatibles avec la norme WCAG 2.2 AA.

---

### 1.4 Stripe Dashboard
* **Ce que l'on retient :**
  * La gestion exemplaire des tableaux de données : en-têtes collants discrets, alignement parfait des valeurs numériques à droite en chiffres tabulaires.
  * Les états de sécurité et d'audit : messages d'autorité rassurants sans être anxiogènes.
  * Le système de navigation à double niveau : section métier à gauche, sous-filtres contextuels en haut.
* **Pourquoi :** Stripe gère des flux financiers critiques avec une clarté et une robustesse inégalées.
* **Ce que l'on ne copie pas :** Les dégradés violets/indigos historiques de la marque Stripe (formellement proscrits ici) et la lourdeur du bundle de composants propriétaires.

---

### 1.5 Attio & Raycast
* **Ce que l'on retient :**
  * **Attio :** La modularité des cartes et la personnalisation de la densité (confortable vs compacte). L'utilisation d'une palette ardoise neutre qui met en valeur le contenu utilisateur.
  * **Raycast :** L'excellence de la palette de commandes (⌘K), la clarté des raccourcis affichés entre crochets et la hiérarchie immédiate de l'action principale.
* **Pourquoi :** Ce sont les deux outils qui réconcilient le mieux la puissance des raccourcis claviers avec une interface visuelle épurée.
* **Ce que l'on ne copie pas :** Les effets de transparence floue trop prononcés (glassmorphism) qui nuisent aux performances et au contraste sur écrans non calibrés.

---

### 1.6 Resend & Notion
* **Ce que l'on retient :**
  * **Resend :** L'approche éditoriale "noir & blanc avec un seul accent de précision". La mise en valeur des logs et des métadonnées avec une police mono réservée aux valeurs techniques.
  * **Notion :** La palette "Papier & Encre" : des fonds chauds, une typographie posée, un sentiment d'artisanat numérique et de réflexion.
* **Pourquoi :** ContentOps Harness est un système éditorial. Il doit respirer la confiance et la qualité littéraire autant que la rigueur technique.
* **Ce que l'on ne copie pas :** La lenteur de rendu et le manque de structure stricte de Notion ; nous restons dans une application de gouvernance déterministe avec contraintes strictes.

---

### 1.7 21st.dev & shadcn/ui
* **Ce que l'on retient :**
  * L'architecture de composants non-empaquetés (code possédé directement dans le dépôt, personnalisable sans dépendance opaque).
  * Les patterns d'accessibilité basés sur Radix UI primitives : focus trapping automatique, rôles ARIA natifs, gestion des flèches directionnelles.
  * Les cartes avec bordures subtiles (`border-border/50`) et arrière-plans `bg-card`.
* **Pourquoi :** Garantit la pérennité du code, l'absence de lock-in et l'extensibilité totale.
* **Ce que l'on ne copie pas :** Les composants "tape-à-l'œil" de 21st.dev utilisant des dégradés animés, des lueurs néon ou du glassmorphism non conforme.
