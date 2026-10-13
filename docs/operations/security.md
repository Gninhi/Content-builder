# Politique de Sécurité (Security Policy)

ContentOps Harness prend la sécurité très au sérieux. Ce document décrit notre politique de sécurité, les versions supportées et la procédure de signalement responsable des vulnérabilités.

---

## 1. Versions Supportées

Seules les versions suivantes reçoivent actuellement des correctifs de sécurité :

| Version | Supportée | Statut |
| :--- | :--- | :--- |
| `2.0.x` (main) | :white_check_mark: Oui | Version active de production |
| `< 2.0.0` | :x: Non | Obsolète |

---

## 2. Signalement d'une Vulnérabilité

Si vous découvrez une faille de sécurité ou une vulnérabilité dans ContentOps Harness :

> **IMPORTANT : NE DIVULGUEZ JAMAIS UNE VULNÉRABILITÉ DE MANIÈRE PUBLIQUE (ISSUES, DISCUSSIONS, PULL REQUESTS PUBLIQUES).**

### Canal Privé de Signalement
1. **GitHub Private Vulnerability Reporting** (Recommandé) :
   - Rendez-vous sur l'onglet **Security** du dépôt GitHub.
   - Cliquez sur **Report a vulnerability** pour soumettre un rapport chiffré directement aux mainteneurs.
2. **Contact Direct** :
   - Si le signalement via GitHub n'est pas disponible, contactez directement l'équipe de sécurité à l'adresse du propriétaire du projet sur GitHub (`Gninhi`).

### Contenu Attendu dans le Rapport
- Une description claire du problème de sécurité (type de vulnérabilité, CWE / OWASP le cas échéant).
- Les étapes reproductibles (Proof of Concept sans impact destructeur).
- L'évaluation de l'impact potentiel (BOLA/IDOR, fuite d'informations, contournement d'authentification).
- Toute proposition de remédiation ou de patch.

---

## 3. Délais de Réponse et Traitement

- **Accusé de réception** : sous 48 heures ouvrées.
- **Évaluation et confirmation du triage** : sous 5 jours ouvrés.
- **Mise à disposition d'un correctif (Security Advisory)** : sous 14 jours ouvrés.

---

## 4. Politique Relative aux Secrets et Clés d'API

- **Aucun secret dans le dépôt** : Aucun jeton d'API réel, secret OAuth ou mot de passe ne doit être commité dans ce dépôt.
- Des scans pré-commit (`gitleaks`, `trufflehog`) et l'analyse continue par GitHub Secret Scanning sont activés.
- Tout secret accidentellement commité doit être considéré comme immédiatement **compromis** et faire l'objet d'une rotation immédiate par son émetteur.
