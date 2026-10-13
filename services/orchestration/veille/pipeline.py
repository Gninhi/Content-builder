"""
Veille Technologique Ingestion & Qualification Pipeline.
Performs collection, sanitization, deduplication, scoring (0.0 to 5.0), and executive synthesis.
"""

from typing import List, Dict, Any, Optional
import logging

from infra.db.repository import ContentOpsRepository
from infra.db.models import SignalModel
from packages.security.prompt_injection import PromptInjectionGuard
from packages.tools.web_search import WebSearchTool
from packages.tools.data_connectors import OfficialDataConnectors
from packages.prompts.veille_queries import (
    SUPPORTED_AXES,
    AXIS_IA,
    AXIS_FRAMEWORKS,
    AXIS_METIERS,
    get_queries_for_axis,
    compute_qualification_score,
)

logger = logging.getLogger(__name__)


SYNTHETIC_DEMO_SIGNALS: List[Dict[str, Any]] = [
    # Axe IA
    {
        "axis": AXIS_IA,
        "title": "Régulation EU AI Act : Entrée en vigueur des standards de transparence pour les modèles GPAI",
        "canonical_url": "https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai",
        "trust_level": "A",
        "summary": "L'Union Européenne formalise les exigences d'audit et de transparence pour les modèles d'IA à usage général (GPAI). Les entreprises déployant des agents autonomes doivent documenter l'architecture de sécurité et le respect des droits fondamentaux.",
        "facts": [
            {
                "fact": "Obligation d'audit technique indépendant pour les modèles dépassant le seuil de 10^25 FLOPs",
                "source_url": "https://digital-strategy.ec.europa.eu",
                "quote": "Article 52 du règlement européen sur l'IA"
            },
            {
                "fact": "Sanctions financières maximales pouvant atteindre 35 millions d'euros ou 7% du CA mondial annuel",
                "source_url": "https://digital-strategy.ec.europa.eu",
                "quote": "Dispositions pénales Chapitre XI"
            }
        ],
        "executive_takeaway": "Les DSI et comités exécutifs doivent exiger un registre de conformité IA et cartographier les flux de données sortants vers les LLM tiers avant fin 2026.",
        "days_old": 2,
        "has_concrete_facts": True,
        "is_strategic": True,
        "is_exec_relevant": True,
    },
    {
        "axis": AXIS_IA,
        "title": "Optimisation des coûts d'inférence LLM : Le passage aux architectures de raisonnement hybrides",
        "canonical_url": "https://arxiv.org/abs/2602.04512",
        "trust_level": "A",
        "summary": "Une étude comparative sur plus de 100 000 requêtes d'entreprise démontre qu'associer un modèle de raisonnement flash pour le filtrage et un grand modèle uniquement sur les cas ambigus réduit la facture de 68%.",
        "facts": [
            {
                "fact": "Réduction de 68% du coût global de tokens sans perte mesurable de fidélité documentaire",
                "source_url": "https://arxiv.org",
                "quote": "Section 4 : Cost-Accuracy Pareto Frontiers in Enterprise Workloads"
            },
            {
                "fact": "Latence médiane P50 réduite de 4.2s à 850ms sur les tâches de triage et classification",
                "source_url": "https://arxiv.org",
                "quote": "Table 2 : Inference benchmarks"
            }
        ],
        "executive_takeaway": "L'architecture mono-modèle est obsolète : la gouvernance des coûts passe obligatoirement par un routeur adaptatif multi-modèles.",
        "days_old": 5,
        "has_concrete_facts": True,
        "is_strategic": True,
        "is_exec_relevant": True,
    },

    # Axe Frameworks & Outils
    {
        "axis": AXIS_FRAMEWORKS,
        "title": "LangGraph & Architectures Agentiques Gouvernées : Patterns de résilience pour environnements critiques",
        "canonical_url": "https://github.com/langchain-ai/langgraph/releases",
        "trust_level": "A",
        "summary": "Le paradigme du Human-in-the-Loop et du scellement d'état par hachage cryptographique s'impose comme le standard pour les workflows agentiques transactionnels et éditoriaux.",
        "facts": [
            {
                "fact": "92% des défaillances en production proviennent de l'absence de circuit breaker et d'états réversibles",
                "source_url": "https://github.com/langchain-ai/langgraph",
                "quote": "Enterprise Production Post-Mortems 2025-2026"
            },
            {
                "fact": "Standardisation du contrôle 'At-Most-Once' pour toute interaction avec les API tierces",
                "source_url": "https://github.com/langchain-ai/langgraph",
                "quote": "Release Notes Architecture Guidelines"
            }
        ],
        "executive_takeaway": "Ne jamais déployer un agent autonome sans scellement cryptographique préalable et confirmation humaine obligatoire sur les actions à impact externe.",
        "days_old": 3,
        "has_concrete_facts": True,
        "is_strategic": True,
        "is_exec_relevant": True,
    },
    {
        "axis": AXIS_FRAMEWORKS,
        "title": "vLLM et accélération GPU : Gains d'efficacité énergétique et passage à l'échelle sur clusters souverains",
        "canonical_url": "https://github.com/vllm-project/vllm/releases",
        "trust_level": "A",
        "summary": "Les avancées récentes sur le PagedAttention et le speculative decoding permettent de diviser par deux l'empreinte matérielle pour les déploiements d'IA sur serveurs privés européens.",
        "facts": [
            {
                "fact": "Débit d'inférence multiplié par 2.4 sur instances GPU NVIDIA de dernière génération",
                "source_url": "https://github.com/vllm-project/vllm",
                "quote": "Throughput benchmark v0.7.2"
            }
        ],
        "executive_takeaway": "L'hébergement souverain en Europe devient économiquement compétitif face aux API américaines grâce aux optimisations du runtime.",
        "days_old": 8,
        "has_concrete_facts": True,
        "is_strategic": False,
        "is_exec_relevant": True,
    },

    # Axe Évolution des Métiers (France & Europe)
    {
        "axis": AXIS_METIERS,
        "title": "Étude DARES & France Travail : Transformation des compétences des ingénieurs et cadres sous l'effet de l'IA",
        "canonical_url": "https://dares.travail-emploi.gouv.fr/etudes-et-statistiques",
        "trust_level": "A",
        "summary": "En France, 74% des équipes de développement logiciel intègrent quotidiennement des outils d'assistance au code, déplaçant la valeur du codage brut vers la spécification, l'architecture et la vérification formelle.",
        "facts": [
            {
                "fact": "Augmentation de 40% du temps alloué à la revue de code, la sécurité et les tests d'intégration",
                "source_url": "https://dares.travail-emploi.gouv.fr",
                "quote": "Rapport DARES 2026 : Métiers du numérique et technologies émergentes"
            },
            {
                "fact": "82% des DRH du secteur technologique privilégient désormais les compétences critiques en prompt architecture et prompt defense",
                "source_url": "https://dares.travail-emploi.gouv.fr",
                "quote": "Enquête compétences cadres tech"
            }
        ],
        "executive_takeaway": "La formation continue doit basculer immédiatement de la production de contenu/code vers la supervision rigoureuse et la gouvernance de la qualité.",
        "days_old": 4,
        "has_concrete_facts": True,
        "is_strategic": True,
        "is_exec_relevant": True,
    },
    {
        "axis": AXIS_METIERS,
        "title": "Adoption de l'IA dans les fonctions juridiques et conformité en France : De l'expérimentation à l'industrialisation",
        "canonical_url": "https://www.lesechos.fr/idees-debats/leadership-management",
        "trust_level": "B",
        "summary": "Les directions juridiques françaises adoptent des agents spécialisés pour l'audit contractuel et le tri jurisprudentiel, réduisant le temps de revue préliminaire de 60%.",
        "facts": [
            {
                "fact": "60% de gain de temps sur la phase de tri et d'analyse de conformité documentaire",
                "source_url": "https://www.lesechos.fr",
                "quote": "Baromètre annuel de la transformation des fonctions support"
            }
        ],
        "executive_takeaway": "L'automatisation ne supprime pas les juristes mais crée une prime massive aux équipes capables de maîtriser l'audit d'algorithmes et le droit européen du numérique.",
        "days_old": 6,
        "has_concrete_facts": True,
        "is_strategic": True,
        "is_exec_relevant": True,
    },
]


class VeillePipeline:
    """Orchestrates collection, sanitization, qualification, and storage of monitoring signals."""

    def __init__(self, repo: ContentOpsRepository):
        self.repo = repo
        self.search_tool = WebSearchTool()
        self.connectors = OfficialDataConnectors

    def run_collection_cycle(
        self,
        workspace_id: str,
        axis: Optional[str] = None,
        demo: bool = False,
        custom_query: Optional[str] = None,
        limit_per_axis: int = 3,
    ) -> List[SignalModel]:
        """
        Executes a targeted monitoring collection cycle.
        Returns the list of qualified signals persisted in the database.
        """
        target_axes = [axis.lower()] if (axis and axis.lower() in SUPPORTED_AXES) else SUPPORTED_AXES
        collected_signals: List[SignalModel] = []

        if demo:
            logger.info("Running Veille pipeline in DEMO mode (verified synthetic signals)")
            for item in SYNTHETIC_DEMO_SIGNALS:
                if item["axis"] not in target_axes:
                    continue
                q_res = compute_qualification_score(
                    trust_level=item["trust_level"],
                    days_old=item.get("days_old", 3),
                    has_concrete_facts=item.get("has_concrete_facts", True),
                    is_strategic=item.get("is_strategic", True),
                    is_exec_relevant=item.get("is_exec_relevant", True),
                )
                sig = self.repo.save_signal(
                    workspace_id=workspace_id,
                    title=item["title"],
                    summary=item["summary"],
                    axis=item["axis"],
                    trust_level=item["trust_level"],
                    qualification_score=q_res["score"],
                    qualification_criteria=q_res["breakdown"],
                    facts=item["facts"],
                    executive_takeaway=item["executive_takeaway"],
                    canonical_url=item["canonical_url"],
                    status="QUALIFIED" if q_res["is_qualified"] else "REJECTED",
                    is_synthetic=True,
                )
                collected_signals.append(sig)
            return collected_signals

        # Real Live Collection Mode
        logger.info(f"Running Veille pipeline in LIVE mode for axes {target_axes}")
        for ax in target_axes:
            # 1. Collect from Official Data Connectors (FND-03)
            connector_signals = self._collect_official_connectors(
                axis=ax,
                workspace_id=workspace_id,
                custom_query=custom_query
            )
            collected_signals.extend(connector_signals)

            # 2. General Web Search Collection (FND-01)
            queries = [
                {"query": custom_query, "lang": "fr", "trust_target": "B", "focus": "Requête personnalisée"}
            ] if custom_query else get_queries_for_axis(ax, count=limit_per_axis)

            for q_spec in queries:
                q_text = q_spec["query"]
                trust_target = q_spec.get("trust_target", "B")

                try:
                    search_resp = self.search_tool.search(
                        query=q_text,
                        max_results=3,
                        workspace_id=workspace_id
                    )
                    if search_resp.status in ("ERROR", "RATE_LIMITED"):
                        logger.warning(f"Search engine returned {search_resp.status} for query '{q_text}': {search_resp.error_message}")
                        continue

                    for item in search_resp.results:
                        # Sanitize untrusted web content
                        sanitized_title = PromptInjectionGuard.defang_text(item.title)
                        sanitized_snippet = PromptInjectionGuard.defang_text(item.snippet)

                        # Check if has concrete metrics/facts
                        has_metrics = any(char.isdigit() for char in sanitized_snippet)
                        q_res = compute_qualification_score(
                            trust_level=trust_target,
                            days_old=7,  # Default search freshness
                            has_concrete_facts=has_metrics,
                            is_strategic=True,
                            is_exec_relevant=True,
                        )

                        facts = [
                            {
                                "fact": sanitized_snippet[:200],
                                "source_url": item.url,
                                "quote": sanitized_title
                            }
                        ]
                        exec_takeaway = f"Signal identifié pour l'axe {ax.upper()} via {item.source_name} : impact potentiel sur la stratégie tech."

                        sig = self.repo.save_signal(
                            workspace_id=workspace_id,
                            title=sanitized_title,
                            summary=sanitized_snippet,
                            axis=ax,
                            trust_level=trust_target,
                            qualification_score=q_res["score"],
                            qualification_criteria=q_res["breakdown"],
                            facts=facts,
                            executive_takeaway=exec_takeaway,
                            canonical_url=item.url,
                            status="QUALIFIED" if q_res["is_qualified"] else "REJECTED",
                            is_synthetic=False,
                        )
                        collected_signals.append(sig)

                except Exception as e:
                    logger.warning(f"Error during search collection for query '{q_text}': {e}")
                    continue

        return collected_signals

    def _collect_official_connectors(
        self,
        axis: str,
        workspace_id: str,
        custom_query: Optional[str] = None
    ) -> List[SignalModel]:
        """Collects authoritative signals from official data connectors (arXiv, GitHub, HN, HuggingFace)."""
        raw_items = []
        try:
            if axis == AXIS_IA:
                raw_items.extend(self.connectors.fetch_arxiv_signals(
                    query=custom_query or "LLM deep reasoning MoE",
                    max_results=2
                ))
                raw_items.extend(self.connectors.fetch_huggingface_signals(
                    query=custom_query or "glm",
                    max_results=1
                ))
            elif axis == AXIS_FRAMEWORKS:
                raw_items.extend(self.connectors.fetch_github_releases(
                    repo="langchain-ai/langgraph",
                    max_results=2
                ))
                raw_items.extend(self.connectors.fetch_hackernews_signals(
                    query=custom_query or "LangGraph AI agent",
                    max_results=2
                ))
            elif axis == AXIS_METIERS:
                raw_items.extend(self.connectors.fetch_hackernews_signals(
                    query=custom_query or "AI software engineering productivity",
                    max_results=2
                ))
        except Exception as e:
            logger.warning(f"Error fetching official connector signals for axis '{axis}': {e}")

        saved_signals: List[SignalModel] = []
        for c_item in raw_items:
            sanitized_title = PromptInjectionGuard.defang_text(c_item.title)
            sanitized_summary = PromptInjectionGuard.defang_text(c_item.summary)
            trust_level = "A" if getattr(c_item.source_type, "value", c_item.source_type) in ("arxiv", "github", "rss") else "B"
            has_metrics = any(char.isdigit() for char in sanitized_summary)

            q_res = compute_qualification_score(
                trust_level=trust_level,
                days_old=3,
                has_concrete_facts=has_metrics,
                is_strategic=True,
                is_exec_relevant=True,
            )

            facts = [
                {
                    "fact": sanitized_summary[:200],
                    "source_url": c_item.url,
                    "quote": sanitized_title
                }
            ]
            exec_takeaway = f"Signal officiel ({getattr(c_item.source_type, 'value', c_item.source_type)}) pour l'axe {axis.upper()}."

            sig = self.repo.save_signal(
                workspace_id=workspace_id,
                title=sanitized_title,
                summary=sanitized_summary,
                axis=axis,
                trust_level=trust_level,
                qualification_score=q_res["score"],
                qualification_criteria=q_res["breakdown"],
                facts=facts,
                executive_takeaway=exec_takeaway,
                canonical_url=c_item.url,
                status="QUALIFIED" if q_res["is_qualified"] else "REJECTED",
                is_synthetic=False,
            )
            saved_signals.append(sig)

        return saved_signals
