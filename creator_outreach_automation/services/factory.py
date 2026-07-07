from __future__ import annotations

from creator_outreach_automation.api.brand_discovery import (
    CompanyWebsiteEnricher,
    create_default_brand_providers,
)
from creator_outreach_automation.api.gmail import GmailDraftClient
from creator_outreach_automation.api.google_search import GoogleCreatorSearchClient
from creator_outreach_automation.api.instagram_analysis import InstagramAnalysisClient
from creator_outreach_automation.api.openai_codex import CodexTaskClient
from creator_outreach_automation.api.youtube_analysis import YouTubeAnalysisClient
from creator_outreach_automation.api.youtube_search import YouTubeCreatorSearchClient
from creator_outreach_automation.agents.builders import default_input_builders
from creator_outreach_automation.agents.concrete import (
    BrandDiscoveryAgent,
    ContactAgent,
    CRMAgent,
    CreatorAgent,
    EmailAgent,
    ScoringAgent,
)
from creator_outreach_automation.agents.workflow import AgentRegistry, WorkflowManager
from creator_outreach_automation.browser.playwright_runner import PlaywrightBrowserRunner
from creator_outreach_automation.config import Settings, get_settings
from creator_outreach_automation.database.connection import SQLiteDatabase
from creator_outreach_automation.database.brand_repository import BrandRepository
from creator_outreach_automation.database.brand_score_repository import BrandScoreRepository
from creator_outreach_automation.database.contact_repository import ContactRepository
from creator_outreach_automation.database.outreach_repository import OutreachRepository
from creator_outreach_automation.database.sponsor_knowledge_base import SponsorKnowledgeBase
from creator_outreach_automation.services.brand_discovery import BrandDiscoveryEngine
from creator_outreach_automation.services.brand_scoring import BrandScoringEngine, CodexBrandScoreClient
from creator_outreach_automation.services.creator_analysis import CreatorAnalysisService
from creator_outreach_automation.services.creator_profile_generation import CreatorProfileGenerator
from creator_outreach_automation.services.contact_discovery import (
    ContactDiscoveryService,
    create_contact_providers,
)
from creator_outreach_automation.services.outreach_engine import (
    CodexOutreachContentGenerator,
    OutreachEngine,
)
from creator_outreach_automation.services.similar_creator_discovery import SimilarCreatorDiscoveryService


def create_creator_analysis_service(settings: Settings | None = None) -> CreatorAnalysisService:
    resolved_settings = settings or get_settings()
    browser_runner = PlaywrightBrowserRunner(resolved_settings.playwright)
    return CreatorAnalysisService(
        youtube_collector=YouTubeAnalysisClient(resolved_settings.google, resolved_settings.http),
        instagram_collector=InstagramAnalysisClient(browser_runner),
        profile_generator=CreatorProfileGenerator(CodexTaskClient(resolved_settings.openai)),
        settings=resolved_settings,
    )


def create_similar_creator_discovery_service(
    settings: Settings | None = None,
) -> SimilarCreatorDiscoveryService:
    resolved_settings = settings or get_settings()
    return SimilarCreatorDiscoveryService(
        google_search_client=GoogleCreatorSearchClient(resolved_settings.google, resolved_settings.http),
        youtube_search_client=YouTubeCreatorSearchClient(resolved_settings.google, resolved_settings.http),
        creator_analysis_service=create_creator_analysis_service(resolved_settings),
        sponsor_knowledge_base=SponsorKnowledgeBase(SQLiteDatabase(resolved_settings.database.sqlite_path)),
        settings=resolved_settings,
    )


def create_brand_discovery_engine(settings: Settings | None = None) -> BrandDiscoveryEngine:
    resolved_settings = settings or get_settings()
    return BrandDiscoveryEngine(
        providers=create_default_brand_providers(
            google_settings=resolved_settings.google,
            github_settings=resolved_settings.github,
            http_settings=resolved_settings.http,
        ),
        brand_repository=BrandRepository(SQLiteDatabase(resolved_settings.database.sqlite_path)),
        website_enricher=CompanyWebsiteEnricher(resolved_settings.http),
        settings=resolved_settings,
    )


def create_brand_scoring_engine(settings: Settings | None = None) -> BrandScoringEngine:
    resolved_settings = settings or get_settings()
    return BrandScoringEngine(
        score_client=CodexBrandScoreClient(
            CodexTaskClient(resolved_settings.openai),
            max_retries=resolved_settings.brand_scoring.max_retries,
        ),
        score_repository=BrandScoreRepository(SQLiteDatabase(resolved_settings.database.sqlite_path)),
        settings=resolved_settings,
    )


def create_outreach_engine(settings: Settings | None = None) -> OutreachEngine:
    resolved_settings = settings or get_settings()
    return OutreachEngine(
        content_generator=CodexOutreachContentGenerator(
            CodexTaskClient(resolved_settings.openai),
            max_words=resolved_settings.outreach.max_words,
        ),
        gmail_client=GmailDraftClient(resolved_settings.google),
        outreach_repository=OutreachRepository(SQLiteDatabase(resolved_settings.database.sqlite_path)),
        settings=resolved_settings,
    )


def create_contact_discovery_service(settings: Settings | None = None) -> ContactDiscoveryService:
    resolved_settings = settings or get_settings()
    return ContactDiscoveryService(
        providers=create_contact_providers(resolved_settings),
        repository=ContactRepository(SQLiteDatabase(resolved_settings.database.sqlite_path)),
        settings=resolved_settings,
    )


def create_workflow_manager(settings: Settings | None = None) -> WorkflowManager:
    resolved_settings = settings or get_settings()
    registry = AgentRegistry()
    registry.register(CreatorAgent(create_creator_analysis_service(resolved_settings)))
    registry.register(BrandDiscoveryAgent(create_brand_discovery_engine(resolved_settings)))
    registry.register(ScoringAgent(create_brand_scoring_engine(resolved_settings)))
    registry.register(ContactAgent(create_contact_discovery_service(resolved_settings)))
    registry.register(CRMAgent())
    registry.register(EmailAgent(create_outreach_engine(resolved_settings)))
    return WorkflowManager(registry=registry, input_builders=default_input_builders())
