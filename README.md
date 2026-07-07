# Creator Brand Outreach Automation

Production-oriented Python 3.12 creator brand outreach automation platform.

This repository contains modular workflows for creator analysis, brand discovery, brand scoring,
contact discovery, Gmail draft creation, workflow agents, Streamlit UI, persistence, caching,
logging, prompt templates, and documentation.

## Stack

- Python 3.12
- Streamlit UI
- SQLite persistence
- Async service and API boundaries
- Gmail API draft integration shell
- YouTube Data API shell
- Apollo API shell
- OpenAI/Codex task client shell
- Playwright browser automation shell
- BeautifulSoup parsing utilities
- Pydantic settings and models

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m creator_outreach_automation.database.migrations
streamlit run app/streamlit_app.py
```

On this workspace you can also use:

```powershell
.\scripts\run_streamlit.cmd
```

The local URL is `http://localhost:8501`.

## Deploy to Streamlit Community Cloud

This project is prepared for Streamlit Community Cloud with `runtime.txt`,
`.streamlit/config.toml`, and `.streamlit/secrets.toml.example`.

1. Push this folder to a GitHub repository.
2. Open [Streamlit Community Cloud](https://share.streamlit.io/).
3. Choose **New app** and select the GitHub repository and branch.
4. Set the main file path to `app/streamlit_app.py`.
5. Copy the keys from `.streamlit/secrets.toml.example` into the app secrets.
6. Add API keys for any live integrations you want enabled.
7. Deploy the app.

The app automatically creates and migrates its SQLite database at startup. Missing
API keys are shown as visible warnings in the UI instead of crashing the app.

This deployment intentionally does not install Debian Chromium through
`packages.txt`. Current Streamlit Cloud images can mix Debian releases during apt
resolution, which may make Chromium conflict with audio/system libraries. If a
browser executable is available in your hosted environment, set
`PLAYWRIGHT_CHROMIUM_EXECUTABLE` to its absolute path. Otherwise leave it blank.
Instagram browser automation will fail gracefully with a visible warning, while
YouTube/API-backed workflows remain available.

## Project Layout

```text
app/                              Streamlit app entrypoint
creator_outreach_automation/       Main Python package
  api/                             External API wrappers
  browser/                         Playwright automation shell
  database/                        SQLite connection, schema, repositories
  logging/                         Logging setup
  models/                          Typed domain and DTO models
  services/                        Reusable service boundaries
  utils/                           Reusable utility helpers
cache/                             Runtime cache files
docs/                              Documentation
outputs/                           Generated exports and reports
prompts/                           Prompt templates
tests/                             Test suite
```

## Configuration

Copy `.env.example` to `.env` and fill in secrets locally. Do not commit `.env`.

All runtime values should be accessed through `creator_outreach_automation.config.get_settings()`.

## Current Status

The platform is runnable locally. Features that require external API keys show warnings instead of
crashing when credentials are not configured.

## Creator Analysis Usage

```python
from creator_outreach_automation.models.creator_analysis import CreatorAnalysisInput
from creator_outreach_automation.services.factory import create_creator_analysis_service

service = create_creator_analysis_service()
profile = await service.analyze(
    CreatorAnalysisInput(youtube_url="https://www.youtube.com/@example")
)
```

Use `instagram_username="example"` instead of `youtube_url` for Instagram analysis.

## Similar Creator Discovery Usage

```python
from creator_outreach_automation.services.factory import create_similar_creator_discovery_service

discovery = create_similar_creator_discovery_service()
result = await discovery.discover(profile)
```

The result contains ranked similar creators and recurring sponsor/brand signals. Discovery stores
creator profiles and sponsor mentions in SQLite for the local Sponsor Knowledge Base.

## Brand Discovery Usage

```python
from creator_outreach_automation.services.factory import create_brand_discovery_engine

engine = create_brand_discovery_engine()
brands = await engine.discover(profile)
```

The engine searches Product Hunt, Y Combinator company pages, Google, startup directories, GitHub
organizations, AI directories, and company websites using the creator niche and content themes.
Brands are deduplicated and stored in SQLite.

## Brand Scoring Usage

```python
from creator_outreach_automation.services.factory import create_brand_scoring_engine

scoring = create_brand_scoring_engine()
result = await scoring.score_brands(
    creator_profile=profile,
    brand_summaries=[(brand, "Website summary goes here")],
)
```

Scores below `BRAND_SCORING_MIN_SCORE` are rejected. Accepted brands are ranked by score and all
scoring results are stored in SQLite.

## Outreach Engine Usage

```python
from creator_outreach_automation.models.outreach import OutreachGenerationInput
from creator_outreach_automation.services.factory import create_outreach_engine

engine = create_outreach_engine()
result = await engine.create_drafts(
    OutreachGenerationInput(
        creator_profile=profile,
        brand=brand,
        campaign_idea="A practical workflow integration",
        recipient_email="partnerships@example.com",
    )
)
```

The engine creates Gmail drafts only. It never sends email automatically.

## Agent Workflow Usage

```python
from creator_outreach_automation.agents.models import CreatorAgentInput
from creator_outreach_automation.agents.workflow import WorkflowState, default_workflow_definition
from creator_outreach_automation.models.creator_analysis import CreatorAnalysisInput
from creator_outreach_automation.services.factory import create_workflow_manager

manager = create_workflow_manager()
state = await manager.run(
    default_workflow_definition(),
    initial_state=WorkflowState(
        values={
            "creator_input": CreatorAgentInput(
                analysis_input=CreatorAnalysisInput(
                    youtube_url="https://www.youtube.com/@example"
                )
            )
        }
    ),
)
```

Agents are registry-based. New agents can be added by implementing `Agent`, registering it, and
optionally adding an input builder.
