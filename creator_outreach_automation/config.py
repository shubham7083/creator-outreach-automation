from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


AppEnvironment = Literal["development", "test", "staging", "production"]


class LoggingSettings(BaseSettings):
    level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


class DatabaseSettings(BaseSettings):
    url: str = Field(default="sqlite+aiosqlite:///./data/outreach.sqlite3", alias="DATABASE_URL")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    @computed_field
    @property
    def safe_url(self) -> str:
        return self.url

    @computed_field
    @property
    def sqlite_path(self) -> Path:
        prefix = "sqlite+aiosqlite:///"
        if not self.url.startswith(prefix):
            raise ValueError("Only sqlite+aiosqlite database URLs are supported.")
        return Path(self.url.removeprefix(prefix)).resolve()


class PathSettings(BaseSettings):
    cache_dir: Path = Field(default=Path("./cache"), alias="CACHE_DIR")
    output_dir: Path = Field(default=Path("./outputs"), alias="OUTPUT_DIR")
    prompts_dir: Path = Field(default=Path("./prompts"), alias="PROMPTS_DIR")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


class HttpSettings(BaseSettings):
    timeout_seconds: float = Field(default=30.0, alias="HTTP_TIMEOUT_SECONDS")
    max_retries: int = Field(default=3, alias="HTTP_MAX_RETRIES")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


class OpenAISettings(BaseSettings):
    api_key: SecretStr | None = Field(default=None, alias="OPENAI_API_KEY")
    model: str = Field(default="gpt-4.1", alias="OPENAI_MODEL")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


class GoogleSettings(BaseSettings):
    client_id: SecretStr | None = Field(default=None, alias="GOOGLE_CLIENT_ID")
    client_secret: SecretStr | None = Field(default=None, alias="GOOGLE_CLIENT_SECRET")
    refresh_token: SecretStr | None = Field(default=None, alias="GOOGLE_REFRESH_TOKEN")
    gmail_sender_email: str | None = Field(default=None, alias="GMAIL_SENDER_EMAIL")
    youtube_api_key: SecretStr | None = Field(default=None, alias="YOUTUBE_API_KEY")
    search_api_key: SecretStr | None = Field(default=None, alias="GOOGLE_SEARCH_API_KEY")
    search_engine_id: str | None = Field(default=None, alias="GOOGLE_SEARCH_ENGINE_ID")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


class ApolloSettings(BaseSettings):
    api_key: SecretStr | None = Field(default=None, alias="APOLLO_API_KEY")
    base_url: str = Field(default="https://api.apollo.io", alias="APOLLO_BASE_URL")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


class GitHubSettings(BaseSettings):
    token: SecretStr | None = Field(default=None, alias="GITHUB_TOKEN")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


class PlaywrightSettings(BaseSettings):
    headless: bool = Field(default=True, alias="PLAYWRIGHT_HEADLESS")
    chromium_executable: Path | None = Field(default=None, alias="PLAYWRIGHT_CHROMIUM_EXECUTABLE")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


class CreatorAnalysisSettings(BaseSettings):
    cache_ttl_seconds: int = Field(default=86_400, alias="CREATOR_ANALYSIS_CACHE_TTL_SECONDS")
    youtube_video_count: int = Field(default=20, alias="CREATOR_ANALYSIS_YOUTUBE_VIDEO_COUNT")
    instagram_post_count: int = Field(default=12, alias="CREATOR_ANALYSIS_INSTAGRAM_POST_COUNT")
    keyword_limit: int = Field(default=30, alias="CREATOR_ANALYSIS_KEYWORD_LIMIT")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


class SimilarDiscoverySettings(BaseSettings):
    cache_ttl_seconds: int = Field(default=86_400, alias="SIMILAR_DISCOVERY_CACHE_TTL_SECONDS")
    google_result_limit: int = Field(default=10, alias="SIMILAR_DISCOVERY_GOOGLE_RESULT_LIMIT")
    youtube_result_limit: int = Field(default=10, alias="SIMILAR_DISCOVERY_YOUTUBE_RESULT_LIMIT")
    max_creators_to_analyze: int = Field(default=10, alias="SIMILAR_DISCOVERY_MAX_CREATORS_TO_ANALYZE")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


class BrandDiscoverySettings(BaseSettings):
    cache_ttl_seconds: int = Field(default=86_400, alias="BRAND_DISCOVERY_CACHE_TTL_SECONDS")
    results_per_source: int = Field(default=8, alias="BRAND_DISCOVERY_RESULTS_PER_SOURCE")
    max_brands: int = Field(default=40, alias="BRAND_DISCOVERY_MAX_BRANDS")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


class BrandScoringSettings(BaseSettings):
    cache_ttl_seconds: int = Field(default=86_400, alias="BRAND_SCORING_CACHE_TTL_SECONDS")
    min_score: float = Field(default=6.0, alias="BRAND_SCORING_MIN_SCORE")
    max_retries: int = Field(default=3, alias="BRAND_SCORING_MAX_RETRIES")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


class ContactDiscoverySettings(BaseSettings):
    cache_ttl_seconds: int = Field(default=86_400, alias="CONTACT_DISCOVERY_CACHE_TTL_SECONDS")
    max_contacts: int = Field(default=25, alias="CONTACT_DISCOVERY_MAX_CONTACTS")
    results_per_role: int = Field(default=5, alias="CONTACT_DISCOVERY_RESULTS_PER_ROLE")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


class OutreachSettings(BaseSettings):
    cache_ttl_seconds: int = Field(default=86_400, alias="OUTREACH_CACHE_TTL_SECONDS")
    max_words: int = Field(default=150, alias="OUTREACH_MAX_WORDS")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


class Settings(BaseSettings):
    app_name: str = Field(default="Creator Brand Outreach Automation", alias="APP_NAME")
    app_env: AppEnvironment = Field(default="development", alias="APP_ENV")
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    paths: PathSettings = Field(default_factory=PathSettings)
    http: HttpSettings = Field(default_factory=HttpSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    google: GoogleSettings = Field(default_factory=GoogleSettings)
    apollo: ApolloSettings = Field(default_factory=ApolloSettings)
    github: GitHubSettings = Field(default_factory=GitHubSettings)
    playwright: PlaywrightSettings = Field(default_factory=PlaywrightSettings)
    creator_analysis: CreatorAnalysisSettings = Field(default_factory=CreatorAnalysisSettings)
    similar_discovery: SimilarDiscoverySettings = Field(default_factory=SimilarDiscoverySettings)
    brand_discovery: BrandDiscoverySettings = Field(default_factory=BrandDiscoverySettings)
    brand_scoring: BrandScoringSettings = Field(default_factory=BrandScoringSettings)
    contact_discovery: ContactDiscoverySettings = Field(default_factory=ContactDiscoverySettings)
    outreach: OutreachSettings = Field(default_factory=OutreachSettings)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.paths.cache_dir.mkdir(parents=True, exist_ok=True)
    settings.paths.output_dir.mkdir(parents=True, exist_ok=True)
    settings.paths.prompts_dir.mkdir(parents=True, exist_ok=True)
    settings.database.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
