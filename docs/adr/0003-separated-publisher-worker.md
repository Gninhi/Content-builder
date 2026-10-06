# ADR 0003 : Séparation Stricte du Worker de Publication

**Date :** 2026-10-02  
**Statut :** Accepté  
**Contexte :**  
Accorder des droits d'appel direct aux APIs de réseaux sociaux à des agents LLM expose l'entreprise à des publications accidentelles ou à des attaques par injection de prompt.

**Décision :**  
Le `PublisherWorker` est un service déterministe complètement isolé. Aucun LLM ne détient de clés d'API sociales. Le publisher n'accepte d'exécuter que des jobs dont le statut est `APPROVED`, vérifie que le hash SHA-256 du payload courant est rigoureusement identique à celui signé par l'humain, et enregistre un reçu (receipt) infalsifiable avec clé d'idempotence.

**Conséquences :**  
- Sécurité renforcée : un prompt hostile ne peut jamais déclencher une publication.
- Idempotence absolue et élimination des doublons de publication.
