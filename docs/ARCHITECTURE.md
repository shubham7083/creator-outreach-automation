# Architecture

The platform is organized around explicit boundaries:

- `models`: immutable typed data structures.
- `database`: SQLite connection, schema, migrations, and repository contracts.
- `api`: external service wrappers for Gmail, YouTube, Apollo, OpenAI/Codex, and HTTP.
- `browser`: Playwright browser automation primitives.
- `services`: orchestration boundaries where future business workflows will live.
- `utils`: small reusable helpers without domain ownership.
- `app`: Streamlit UI entrypoint.

## Creator Analysis

`CreatorAnalysisService` accepts a `CreatorAnalysisInput` with exactly one platform source:

- Instagram username
- YouTube URL

The service collects platform data through injectable collectors, caches raw snapshots and final
profiles under `cache/`, extracts reusable signals, and asks the Codex profile generator to produce
a validated `CreatorProfile`.

Collected and derived fields include subscriber/follower counts, views, latest YouTube videos,
Instagram post metadata, descriptions, titles, captions, hashtags, brand mentions, existing
sponsors, average engagement, topics, keywords, niche, audience summary, collaboration
opportunities, and estimated pricing.

## Similar Creator Discovery

`SimilarCreatorDiscoveryService` accepts an existing `CreatorProfile`, searches Google and YouTube
for similar creator candidates, deduplicates candidates by platform identity, analyzes each
candidate through `CreatorAnalysisService`, and ranks the resulting creator profiles.

Sponsor data is persisted in SQLite through `SponsorKnowledgeBase`:

- `creator_profiles`: normalized creator profile summaries.
- `sponsor_mentions`: existing sponsors, previous sponsors, brand mentions, and recurring brands.

Final discovery results are cached under `cache/similar_creator_discovery`.

## Brand Discovery

`BrandDiscoveryEngine` accepts a `CreatorProfile`, builds niche-aware search terms, discovers
brand candidates from provider boundaries, enriches company websites, deduplicates by normalized
domain or name, stores brands in SQLite, and returns `Brand` objects.

Default providers cover:

- Product Hunt
- Y Combinator companies
- Google Search
- startup directories
- company websites
- GitHub organizations
- AI directories

Brand data is persisted in:

- `brands`
- `brand_discovery_sources`

## Brand Scoring

`BrandScoringEngine` accepts a `CreatorProfile`, a `Brand`, and a website summary. It asks Codex
for structured JSON only, validates the response as `BrandScore`, caches the AI response, retries
transient/invalid AI responses, rejects brands below the configured threshold, ranks accepted
brands, and stores all scoring results in SQLite.

Brand scoring data is persisted in:

- `brand_scores`

## Outreach Engine

`OutreachEngine` accepts a creator profile, brand profile, campaign idea, and recipient email.
It generates structured outreach copy through Codex, validates the copy, creates Gmail drafts only,
and stores Gmail draft IDs locally.

Generated copy includes:

- subject
- initial email
- follow-up
- final follow-up

Each body is capped by `OUTREACH_MAX_WORDS`, defaulting to 150 words.

Outreach data is persisted in:

- `outreach_sequences`
- `outreach_drafts`

## Agent Architecture

The `creator_outreach_automation.agents` package provides a reusable agent framework:

- `Agent`: typed base class with input validation, output validation, memory, logging, tools, and retry logic.
- `AgentMemory`: in-memory run history for independent testing and future persistence.
- `AgentToolbox`: explicit tool descriptors per agent.
- `AgentRegistry`: runtime registration of agents by name.
- `WorkflowManager`: orchestration over registered agents without hardcoded agent dependencies.
- `WorkflowDefinition`: declarative ordered steps.
- input builders: translate workflow state into each agent's typed input.

Implemented agents:

- Creator Agent
- Brand Discovery Agent
- Scoring Agent
- Contact Agent
- Email Agent
- CRM Agent

Future agents can be added by creating a new `Agent` subclass, registering it with `AgentRegistry`,
and adding a workflow step. The manager itself does not need to change.

## Principles

- Configuration is environment-driven and loaded through Pydantic settings.
- Secrets belong in `.env`, never in source code.
- Service methods are async where they will perform I/O.
- External dependencies are isolated behind wrapper classes.
- Business logic is intentionally deferred until requirements are defined.
