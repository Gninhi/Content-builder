import re
import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone, timedelta

from services.orchestration.nodes.research import _clean_title, _normalize_score_100
from infra.db.repository import ContentOpsRepository
from infra.db.models import SignalModel


def test_t10_editorial_scoring_and_title_prefix_sanitization():
    """
    T10 AUDIT TEST: Qualité éditoriale des idées.
    Vérifie la suppression systématique des préfixes de catégorie dans les titres
    et la normalisation stricte des scores sur l'échelle 0-100.
    """
    pillars = ["IA générative", "Systèmes multi-agents", "Gouvernance & Conformité"]

    # 1. Nettoyage des préfixes de piliers
    raw_titles = [
        ("IA générative : Comment réduire les coûts d'inférence en production", "Comment réduire les coûts d'inférence en production"),
        ("Systèmes multi-agents: Architecture de supervision", "Architecture de supervision"),
        ("Gouvernance & Conformité : Préparer l'audit EU AI Act", "Préparer l'audit EU AI Act"),
        ("Titre sans aucun préfixe", "Titre sans aucun préfixe")
    ]
    for raw, expected in raw_titles:
        assert _clean_title(raw, pillars) == expected

    # 2. Normalisation des scores 0-100 (Correction du défaut historique "95 / 10" ou "950%")
    # Un score fourni sur base 10 (ex: 9.2) doit être converti en 92.0
    assert _normalize_score_100(9.2) == 92.0
    # Un score fourni directement sur base 100 (ex: 88.0) doit rester 88.0
    assert _normalize_score_100(88.0) == 88.0
    # Clamping aux bornes 0.0 et 100.0
    assert _normalize_score_100(120.0) == 100.0
    assert _normalize_score_100(-5.0) == 0.0


def test_t11_temporal_deduplication_90_days():
    """
    T11 AUDIT TEST: Déduplication temporelle exacte sur fenêtre glissante de 90 jours (REQ-11).
    Vérifie qu'un signal identique publié dans les 90 jours ne produit aucun doublon en base.
    """
    mock_db = MagicMock()
    repo = ContentOpsRepository(db=mock_db)

    # Simulation d'un signal existant enregistré il y a 10 jours
    now = datetime.now(timezone.utc)
    existing_signal = MagicMock(spec=SignalModel)
    existing_signal.id = "sig_existing_123"
    existing_signal.title = "Sortie de GLM-5.3 par Z.ai"
    existing_signal.qualification_score = 4.0
    existing_signal.created_at = now - timedelta(days=10)

    # Le mock DB renvoie le signal existant lors du filtre
    mock_db.query.return_value.filter.return_value.first.return_value = existing_signal

    # Tentative d'insertion du même signal
    res = repo.save_signal(
        workspace_id="ws_audit_t11",
        title="Sortie de GLM-5.3 par Z.ai",
        summary="Nouveau modèle",
        axis="ia",
        trust_level="A",
        qualification_score=4.2,
        qualification_criteria={},
        facts=[],
        executive_takeaway="Impact stratégique",
        canonical_url="https://z-ai.org/blog/glm-5-3",
        max_dedup_days=90
    )

    # Le repository doit renvoyer l'existant sans ajouter de nouvel objet
    assert res == existing_signal
    assert mock_db.add.call_count == 0, "Doublon inséré : add() ne doit pas être appelé pour un signal existant !"
