# 📚 Documentation & Carte du Projet — ContentOps Harness

Bienvenue dans la documentation officielle consolidée de **ContentOps Harness** (Content-builder). Ce répertoire constitue la source unique de vérité technique, produit et opérationnelle.

---

## 🗺️ Carte de la Documentation

```
docs/
├── README.md                               # Index général et carte du projet (ce fichier)
├── CHANGELOG_CONSOLIDATION.md              # Historique exhaustif de consolidation et métriques
│
├── architecture/                           # Architecture technique, composants & décisions
│   ├── overview.md                         # Architecture globale, graphes LangGraph & persistance
│   ├── llm-providers.md                    # Architecture multi-provider (Gemini, NVIDIA, etc.)
│   ├── references.md                       # Sources officielles, versions et APIs tierces
│   └── adr/                                # Décisions d'Architecture Enregistrées (ADRs)
│       ├── 0001-workflow-first.md          # Workflow déterministe avant multi-agent libre
│       ├── 0002-langgraph-durable...       # LangGraph pour orchestration durable et interruptions
│       ├── 0003-separated-publisher...     # Séparation stricte du worker de publication
│       ├── 0004-postgres-source-of...      # PostgreSQL / Supabase comme source de vérité
│       ├── 0005-versioned-prompts...       # Versionnage immuable des prompts et profils
│       ├── 0006-propositional-learning.md  # Apprentissage propositionnel sans mutation autonome
│       ├── 0007-react-vite-ui-stack.md     # Pile UI moderne React 18, Vite & Tailwind
│       ├── 0008-social-connectors-and-p... # Connecteurs sociaux isolés et registre d'aperçus
│       ├── 0009-obsidian-vault-and-bras... # Direction A « Obsidian Vault & Brass Precision »
│       ├── 0010-volatile-jwt-auth-and-m... # Authentification JWT volatile et profil multi-tenant
│       └── 0011-langgraph-orchestrati...   # Consolidation LangGraph et séparation des rôles
│
├── veille/                                 # Pipeline de veille & idéation autonome
│   ├── architecture.md                     # Architecture de collecte, déduplication et scoring
│   ├── sources_catalog.md                  # Catalogue officiel des sources (Niveaux A à D)
│   ├── query_bank.md                       # Banque de requêtes spécialisées et prompts
│   └── compliance_matrix.md                # Matrice de conformité et règles de qualification
│
├── product/                                # Règles métier, gouvernance et contrats
│   ├── governance.md                       # Parcours éditorial, machine à états HITL & RBAC
│   ├── brand-governance.md                 # Spécification et règles du profil de marque
│   └── api-contracts.md                    # Spécification des endpoints REST et contrats
│
├── design-system/                          # Écosystème de design, tokens et composants
│   ├── overview.md                         # Vue d'ensemble « Obsidian Vault & Brass Precision »
│   ├── principles.md                       # Principes directeurs et accessibilité WCAG 2.2 AA
│   ├── tokens.md                           # Architecture des tokens sémantiques OKLCH
│   └── audit-final.md                      # Validation et conformité de l'interface
│
├── operations/                             # Déploiement, sécurité, tests et runbooks
│   ├── security.md                         # Politique de sécurité et signalement des failles
│   ├── contributing.md                     # Guide des contributions et standards de code
│   ├── evaluation-plan.md                  # Plan d'évaluation et jeu de régression 80 cas
│   ├── risks_and_deferred.md               # Matrice des risques résiduels et éléments reportés
│   └── runbooks/                           # Procédures opérationnelles de production
│       ├── kill_switch.md                  # Activation du coupe-circuit d'urgence
│       ├── llm_circuit_breaker.md          # Disjoncteur LLM et bascule en mode dégradé
│       ├── publication_failure.md          # Gestion des échecs de diffusion (Dead-Letter)
│       ├── publish_unknown_recovery.md     # Réconciliation des états PUBLISH_UNKNOWN
│       ├── reconnection_guide.md           # Renouvellement des jetons OAuth sociaux
│       ├── secret_leak.md                  # Procédure de réponse à fuite de secret
│       └── token_rotation.md               # Rotation périodique des clés API
│
├── audits/                                 # Rapports d'audits techniques et matrices de preuve
│   ├── audit_exhaustif_severe_2026.md      # Audit complet du dépôt (backend, frontend, graphes)
│   ├── audit_veille_industrialisation_2... # Audit du pipeline de veille et idéation
│   ├── remediation_veille_industrialis...  # Validation des remédiations du pipeline de veille
│   ├── pipeline.mmd                        # Diagramme Mermaid de flux de veille et d'idéation
│   ├── coverage-matrix.csv                 # Matrice de couverture détaillée des contrôles
│   ├── findings.csv                        # Inventaire exhaustif des constats et remédiations
│   └── traceability-matrix.csv             # Matrice de traçabilité des exigences produit
│
└── archive/                                # Rapports d'audits et jalons historiques (lecture seule)
    ├── FINAL_REPORT_REFONTE.md             # Clôture du chantier de refonte globale (10/10)
    ├── AUDIT.md                            # Audit initial sécurité & architecture (06/10)
    ├── AUDIT_V2.md                         # Audit indépendant V2 (07/10)
    ├── AUDIT_UI.md                         # Diagnostic UI initial (08/10)
    ├── BASELINE.md                         # Métriques de référence initiales backend
    ├── BASELINE_UI.md                      # Métriques de référence initiales frontend
    ├── DIAGNOSTIC_LLM_PROVIDERS.md         # Diagnostic préliminaire des providers LLM
    ├── FINAL_REPORT.md                     # Rapport de livraison jalon V1
    ├── FINAL_REPORT_GH.md                  # Rapport de livraison jalon GitHub
    ├── FINAL_REPORT_UI.md                  # Rapport de livraison jalon UI V1
    ├── INVENTORY_GH.md                     # Inventaire de reconnaissance git pré-push
    ├── POSTPUSH_REPORT.md                  # Rapport de vérification post-push
    ├── PROGRESS.md                         # Journal de reprise jalon V1
    ├── PROGRESS_GH.md                      # Journal de reprise déploiement GitHub
    ├── PROGRESS_UI.md                      # Journal de reprise frontend V1
    ├── REMEDIATION.md                      # Matrice de remédiation jalon V1
    ├── REMEDIATION_V2.md                   # Matrice de remédiation jalon V2
    └── SECURITY_PREPUSH_REPORT.md          # Audit de sécurité pré-push DevSecOps
```

---

## 🎯 Accès Rapide par Profil

* **Développeur Full-Stack / Débutant sur le projet** : Commencez par [`operations/contributing.md`](operations/contributing.md) puis [`architecture/overview.md`](architecture/overview.md).
* **Ingénieur Produit / Rédacteur** : Consultez [`product/governance.md`](product/governance.md) et [`product/brand-governance.md`](product/brand-governance.md).
* **Designer / Développeur Frontend** : Consultez [`design-system/principles.md`](design-system/principles.md).
* **Équipe SRE / On-call** : Référez-vous directement aux [`operations/runbooks/`](operations/runbooks/).
