# Guide de Configuration du Profil de Marque

Le profil de marque (`BrandProfile`) constitue le contrat éditorial appliqué par tous les agents et validé par le Quality Gate déterministe.

---

## Structure d'un Profil de Marque

```json
{
  "workspace_id": "ws_default",
  "audience": [
    "Tech Leads",
    "Architectes Logiciels",
    "CTOs",
    "Ingénieurs IA"
  ],
  "voice": "Direct, expert, pragmatique, orienté retour d'expérience et architecture sans jargon creux.",
  "pillars": [
    "IA générative & LLMs",
    "Systèmes multi-agents & LangGraph",
    "Automatisation d'entreprise & Gouvernance"
  ],
  "prohibited_topics": [
    "Spéculation crypto",
    "Rumeurs non vérifiées",
    "Dénigrement concurrent direct",
    "Promesses de gains financiers rapides"
  ],
  "cta_policy": {
    "allowed_ctas": [
      "Partagez votre avis en commentaire",
      "Visiter le dépôt GitHub",
      "S'inscrire à la veille technique"
    ],
    "max_per_post": 1
  }
}
```

---

## Règles d'Application
1. **Piliers éditoriaux :** Chaque idée produite doit obligatoirement correspondre à un des piliers déclarés.
2. **Interdits formels :** La présence d'un sujet interdit dans un brouillon entraîne l'échec immédiat au Quality Gate (`status = QA_FAILED`).
3. **Politique de CTA :** Tout post doit contenir exactement un CTA parmi ceux autorisés.
4. **Versionnage :** Toute mise à jour incrémente le numéro de version (`version=1, 2, ...`). Les contenus passés restent rattachés à la version sous laquelle ils ont été créés.
