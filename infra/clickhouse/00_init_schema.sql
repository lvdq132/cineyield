-- CineYield ClickHouse Schema
-- Run once to initialize the database and all tables.
-- Safe to re-run: uses CREATE IF NOT EXISTS.

CREATE DATABASE IF NOT EXISTS cineyield;

-- ─────────────────────────────────────────────────────────────
-- Content catalog
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cineyield.content_assets
(
    id                   String,
    title                String,
    subtitle             String,
    format               LowCardinality(String),   -- tv_series, film, microdrama, youtube, social
    status               LowCardinality(String),   -- queued, analyzing, analyzed, failed
    scene_count          UInt32   DEFAULT 0,
    opportunity_count    UInt32   DEFAULT 0,
    estimated_value_usd  Nullable(Float64),
    gcs_uri              Nullable(String),
    updated_at           DateTime DEFAULT now()
)
ENGINE = MergeTree()
ORDER BY (id);

-- ─────────────────────────────────────────────────────────────
-- Scene intelligence (Gemini output)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cineyield.scenes
(
    id                   String,
    asset_id             String,
    episode              Nullable(String),
    name                 String,
    summary              String,
    brand_safety_score   Float32  DEFAULT 0.0,
    narrative_weight     LowCardinality(String),
    mood                 LowCardinality(String),
    duration_seconds     UInt32   DEFAULT 0,
    gemini_model_used    Nullable(String),
    analyzed_at          DateTime DEFAULT now()
)
ENGINE = MergeTree()
ORDER BY (asset_id, id);

-- ─────────────────────────────────────────────────────────────
-- Detected objects per scene
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cineyield.detected_objects
(
    scene_id        String,
    asset_id        String,
    label           String,
    category        String,
    confidence      Float32,
    is_primary      Bool    DEFAULT false,
    timecode_start  Nullable(String),
    timecode_end    Nullable(String),
    created_at      DateTime DEFAULT now()
)
ENGINE = MergeTree()
ORDER BY (scene_id, confidence);

-- ─────────────────────────────────────────────────────────────
-- Placement opportunities
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cineyield.placement_opportunities
(
    id                   String,
    scene_id             String,
    asset_id             String,
    category             String,
    object_label         String,
    timecode_start       String,
    timecode_end         String,
    screen_time_seconds  UInt32,
    naturalness_score    Float32,
    brand_safety_score   Float32,
    complexity           LowCardinality(String),  -- low, medium, high
    rights_status        LowCardinality(String),  -- clear, review, restricted
    estimated_value_usd  Nullable(Float64),
    is_primary           Bool    DEFAULT false,
    created_at           DateTime DEFAULT now()
)
ENGINE = MergeTree()
ORDER BY (scene_id, id);

-- ─────────────────────────────────────────────────────────────
-- Brand campaign inventory (queried by Market Agent via MCP)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cineyield.brand_campaigns
(
    id                      String,
    brand                   String,
    campaign_name           String,
    product_line            String,
    budget_min_usd          Float64,
    budget_max_usd          Float64,
    target_categories       Array(String),
    excluded_contexts       Array(String),
    territories             Array(String),
    visibility_seconds_min  UInt32  DEFAULT 0,
    visibility_seconds_max  UInt32  DEFAULT 60,
    is_active               Bool    DEFAULT true,
    created_at              DateTime DEFAULT now()
)
ENGINE = MergeTree()
ORDER BY (brand, id);

-- ─────────────────────────────────────────────────────────────
-- Territory rights rules (deterministic enforcement)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cineyield.rights_rules
(
    id                  String,
    category            String,
    territory           String,
    status              LowCardinality(String),  -- clear, review, restricted
    usage_window_months UInt8  DEFAULT 12,
    notes               Nullable(String),
    created_at          DateTime DEFAULT now()
)
ENGINE = MergeTree()
ORDER BY (category, territory);

-- ─────────────────────────────────────────────────────────────
-- Campaign/opportunity match events
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cineyield.match_events
(
    event_id          String,
    opportunity_id    String,
    campaign_id       String,
    brand             String,
    composite_score   Float32,
    context_fit       Float32,
    category_fit      Float32,
    visibility_score  Float32,
    brand_safety      Float32,
    territory_score   Float32,
    budget_score      Float32,
    is_blocked        Bool    DEFAULT false,
    blocked_reason    Nullable(String),
    occurred_at       DateTime DEFAULT now()
)
ENGINE = MergeTree()
ORDER BY (opportunity_id, occurred_at);

-- ─────────────────────────────────────────────────────────────
-- Proposals
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cineyield.proposals
(
    id                 String,
    opportunity_id     String,
    campaign_id        String,
    brand_name         String,
    campaign_name      String,
    placement_fee_usd  Float64,
    workflow_state     LowCardinality(String),
    composed_at        DateTime DEFAULT now()
)
ENGINE = MergeTree()
ORDER BY (id);

-- ─────────────────────────────────────────────────────────────
-- Agent execution events (sanitized — no secrets)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cineyield.agent_events
(
    event_id        String,
    correlation_id  String          DEFAULT '',
    agent_name      LowCardinality(String),
    kind            LowCardinality(String),  -- started, tool_call, tool_result, completed, failed
    asset_id        Nullable(String),
    scene_id        Nullable(String),
    opportunity_id  Nullable(String),
    campaign_id     Nullable(String),
    tool_name       Nullable(String),
    summary         String          DEFAULT '',
    latency_ms      Nullable(Int32),
    success         Bool            DEFAULT true,
    occurred_at     DateTime        DEFAULT now()
)
ENGINE = MergeTree()
ORDER BY (agent_name, occurred_at);

-- ─────────────────────────────────────────────────────────────
-- Revenue / approval events
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cineyield.revenue_events
(
    event_id      String,
    proposal_id   String,
    opportunity_id String,
    campaign_id   String,
    asset_id      String,
    amount_usd    Float64,
    revenue_type  LowCardinality(String)  DEFAULT 'placement_fee',
    territory     Nullable(String),
    occurred_at   DateTime DEFAULT now()
)
ENGINE = MergeTree()
ORDER BY (asset_id, occurred_at);
