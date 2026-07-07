CREATE TABLE IF NOT EXISTS creators (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    handle TEXT,
    channel_url TEXT,
    email TEXT,
    niche TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS brands (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    website TEXT,
    normalized_domain TEXT,
    description TEXT,
    industry TEXT,
    location TEXT,
    socials_json TEXT NOT NULL DEFAULT '{}',
    discovery_sources_json TEXT NOT NULL DEFAULT '[]',
    discovered_for_creator_identity TEXT,
    contact_email TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    UNIQUE(normalized_domain)
);

CREATE TABLE IF NOT EXISTS campaigns (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    brand_id TEXT,
    status TEXT NOT NULL,
    starts_on TEXT,
    ends_on TEXT,
    objective TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY (brand_id) REFERENCES brands(id)
);

CREATE TABLE IF NOT EXISTS outreach_messages (
    id TEXT PRIMARY KEY,
    creator_id TEXT NOT NULL,
    brand_id TEXT NOT NULL,
    campaign_id TEXT,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL,
    provider_draft_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY (creator_id) REFERENCES creators(id),
    FOREIGN KEY (brand_id) REFERENCES brands(id),
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
);

CREATE TABLE IF NOT EXISTS creator_profiles (
    identity TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    handle TEXT NOT NULL,
    display_name TEXT,
    source_url TEXT,
    niche TEXT NOT NULL,
    audience_summary TEXT NOT NULL,
    keywords_json TEXT NOT NULL,
    topics_json TEXT NOT NULL,
    sponsors_json TEXT NOT NULL,
    brand_mentions_json TEXT NOT NULL,
    follower_count INTEGER,
    subscriber_count INTEGER,
    average_engagement REAL,
    engagement_rate REAL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sponsor_mentions (
    id TEXT PRIMARY KEY,
    sponsor_name TEXT NOT NULL,
    creator_identity TEXT NOT NULL,
    source_platform TEXT NOT NULL,
    mention_type TEXT NOT NULL,
    context TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (sponsor_name, creator_identity, mention_type),
    FOREIGN KEY (creator_identity) REFERENCES creator_profiles(identity)
);

CREATE INDEX IF NOT EXISTS idx_sponsor_mentions_name ON sponsor_mentions(sponsor_name);
CREATE INDEX IF NOT EXISTS idx_sponsor_mentions_creator ON sponsor_mentions(creator_identity);

CREATE TABLE IF NOT EXISTS brand_discovery_sources (
    id TEXT PRIMARY KEY,
    brand_id TEXT NOT NULL,
    source TEXT NOT NULL,
    source_url TEXT,
    creator_identity TEXT NOT NULL,
    confidence REAL NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(brand_id, source, creator_identity),
    FOREIGN KEY (brand_id) REFERENCES brands(id)
);

CREATE INDEX IF NOT EXISTS idx_brands_domain ON brands(normalized_domain);
CREATE INDEX IF NOT EXISTS idx_brand_sources_creator ON brand_discovery_sources(creator_identity);

CREATE TABLE IF NOT EXISTS brand_scores (
    id TEXT PRIMARY KEY,
    creator_identity TEXT NOT NULL,
    brand_id TEXT NOT NULL,
    brand_name TEXT NOT NULL,
    score REAL NOT NULL,
    accepted INTEGER NOT NULL,
    reason TEXT NOT NULL,
    campaign_idea TEXT NOT NULL,
    estimated_pricing TEXT NOT NULL,
    email_hook TEXT NOT NULL,
    website_summary TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(creator_identity, brand_id),
    FOREIGN KEY (brand_id) REFERENCES brands(id)
);

CREATE INDEX IF NOT EXISTS idx_brand_scores_creator ON brand_scores(creator_identity);
CREATE INDEX IF NOT EXISTS idx_brand_scores_score ON brand_scores(score);

CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    brand_id TEXT NOT NULL,
    brand_name TEXT NOT NULL,
    dedupe_key TEXT NOT NULL,
    name TEXT,
    title TEXT,
    email TEXT,
    linkedin TEXT,
    role TEXT,
    confidence_score REAL NOT NULL,
    sources_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(brand_id, dedupe_key),
    FOREIGN KEY (brand_id) REFERENCES brands(id)
);

CREATE INDEX IF NOT EXISTS idx_contacts_brand ON contacts(brand_id);
CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email);

CREATE TABLE IF NOT EXISTS outreach_sequences (
    id TEXT PRIMARY KEY,
    creator_identity TEXT NOT NULL,
    brand_id TEXT NOT NULL,
    brand_name TEXT NOT NULL,
    recipient_email TEXT NOT NULL,
    campaign_idea TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outreach_drafts (
    id TEXT PRIMARY KEY,
    sequence_id TEXT NOT NULL,
    draft_kind TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    gmail_draft_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(sequence_id, draft_kind),
    FOREIGN KEY (sequence_id) REFERENCES outreach_sequences(id)
);

CREATE INDEX IF NOT EXISTS idx_outreach_sequences_creator ON outreach_sequences(creator_identity);
CREATE INDEX IF NOT EXISTS idx_outreach_drafts_gmail ON outreach_drafts(gmail_draft_id);
