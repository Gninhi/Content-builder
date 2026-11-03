from packages.domain.rendering import render_publishable_text, extract_publishable_media


def test_render_variant_combines_hook_body_cta_and_hashtags():
    """C2: render_publishable_text must combine hook, body, cta, and hashtags when not redundant."""
    variant = {
        "platform": "linkedin",
        "hook": "L'IA en 2026 : Réalité vs Fiction",
        "body": "Les systèmes multi-agents redéfinissent la productivité technique des entreprises modernes.",
        "cta": "Partagez votre retour d'expérience en commentaire !",
        "hashtags": ["#AgenticAI", "#TechLeadership"],
        "media_spec": {"urls": ["https://cdn.example.com/infographic.png"]}
    }

    rendered = render_publishable_text(variant)
    assert "L'IA en 2026 : Réalité vs Fiction" in rendered
    assert "Les systèmes multi-agents" in rendered
    assert "Partagez votre retour d'expérience" in rendered
    assert "#AgenticAI #TechLeadership" in rendered

    media = extract_publishable_media(variant)
    assert media == ["https://cdn.example.com/infographic.png"]


def test_render_variant_avoids_duplicating_hook_or_cta_if_already_present():
    """C2: Do not duplicate hook or cta if body already integrates them."""
    body = "Accroche intégrée.\n\nCorps du post complet avec argumentaire.\n\nCTA déjà présent."
    variant = {
        "platform": "linkedin",
        "hook": "Accroche intégrée.",
        "body": body,
        "cta": "CTA déjà présent.",
        "hashtags": ["#AI"],
    }
    rendered = render_publishable_text(variant)
    assert rendered.count("Accroche intégrée.") == 1
    assert rendered.count("CTA déjà présent.") == 1
    assert "#AI" in rendered


def test_render_variant_for_x_enforces_char_limit():
    """C2: For platform X, rendered text must strictly fit within 280 characters."""
    long_body = "A" * 300
    variant = {
        "platform": "x",
        "hook": "Accroche",
        "body": long_body,
        "cta": "Lien en bio",
        "hashtags": ["#AI"]
    }
    rendered = render_publishable_text(variant)
    assert len(rendered) <= 280
