# ADR 0010: Authentification JWT en Mémoire Volatile et Profil Utilisateur Multi-Tenant

## Statut
Accepté

## Date
10 Octobre 2026

## Contexte
ContentOps Harness fonctionne selon un modèle B2B multi-tenant strict avec séparation des données par Row-Level Security (RLS) et rôles RBAC (`owner`, `editor`, `viewer`).
La manipulation d'un jeton Bearer JWT dans une Single-Page Application (SPA) pose des risques de sécurité majeurs si stocké dans `localStorage` ou `sessionStorage` (vulnérabilités aux attaques Cross-Site Scripting - XSS).
Par ailleurs, les utilisateurs avaient besoin d'une interface complète pour consulter leur profil, auditer leurs droits RBAC sur les workspaces, exporter leurs données personnelles et renouveler leur mot de passe sans pouvoir altérer arbitrairement leur adresse e-mail côté client.

## Décision
1. **Stockage Strictement Volatile du JWT :**
   - Le jeton JWT (`access_token`) est conservé exclusivement dans l'état React en mémoire vive (`AuthContext`).
   - Aucun jeton d'accès n'est jamais écrit dans `localStorage` ni `sessionStorage`.
   - L'écran de connexion affiche explicitement cet engagement de sécurité.
   - En cas de rechargement de page ou d'expiration, l'utilisateur est invité à se ré-authentifier de manière transparente ou explicite.
2. **Cloisonnement du Mode Développeur :**
   - L'onglet de connexion rapide « Mode Dev (Jeton) » et les sélecteurs de profil mockés sont conditionnés au flag d'environnement `NODE_ENV === 'development'`.
   - L'environnement de production n'expose que le flux de connexion Enterprise (E-mail/Mot de passe ou SSO).
3. **Sécurisation du Profil Utilisateur :**
   - L'adresse e-mail utilisateur est immuable côté client (`disabled` et badge de verrouillage de sécurité) car elle sert d'ancrage d'identité cryptographique.
   - La mutation de rôle est strictement restreinte aux utilisateurs ayant le rôle `owner` du workspace via l'API backend.
   - Export de données personnelles au format JSON standardisé respectant les exigences de conformité et de portabilité des données.

## Conséquences
- **Positives :**
  - Immunité totale contre le vol de jetons par injection de scripts tiers dans le stockage local.
  - Respect strict des contrats de sécurité multi-tenant.
  - Profil utilisateur exhaustif avec traçabilité claire des permissions RBAC.
- **Négatives :**
  - La fermeture de l'onglet entraîne la déconnexion immédiate de la session (comportement de sécurité désiré pour un terminal de gouvernance).
