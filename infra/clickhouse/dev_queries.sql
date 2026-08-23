-- CineYield development / debug queries
-- Run against your ClickHouse instance to verify state.

-- Verify schema
SHOW TABLES IN cineyield;

-- Campaign count
SELECT count() AS total_campaigns FROM cineyield.brand_campaigns WHERE is_active = true;

-- Canonical Market Agent query: Consumer Audio compatible campaigns for rooftop opp
SELECT
    id,
    brand,
    campaign_name,
    product_line,
    budget_min_usd,
    budget_max_usd,
    target_categories,
    excluded_contexts,
    territories,
    visibility_seconds_min,
    visibility_seconds_max
FROM cineyield.brand_campaigns
WHERE is_active = true
  AND has(target_categories, 'Consumer audio')
  AND budget_max_usd >= 150000
  AND visibility_seconds_max >= 15
  AND NOT hasAny(excluded_contexts, ['reflective', 'aspirational quiet', 'slow pace'])
ORDER BY budget_max_usd DESC;

-- All active campaigns
SELECT id, brand, campaign_name, target_categories, territories
FROM cineyield.brand_campaigns
WHERE is_active = true
ORDER BY brand;

-- Scene intelligence
SELECT id, name, brand_safety_score, mood, narrative_weight
FROM cineyield.scenes
ORDER BY asset_id;

-- Opportunities for rooftop scene
SELECT id, object_label, category, naturalness_score, brand_safety_score, rights_status, estimated_value_usd
FROM cineyield.placement_opportunities
WHERE scene_id = 'rooftop-reflection'
ORDER BY naturalness_score DESC;

-- Recent agent events
SELECT agent_name, kind, tool_name, summary, latency_ms, success, occurred_at
FROM cineyield.agent_events
ORDER BY occurred_at DESC
LIMIT 20;

-- Revenue summary
SELECT
    asset_id,
    sum(amount_usd) AS total_revenue,
    count() AS deal_count
FROM cineyield.revenue_events
GROUP BY asset_id
ORDER BY total_revenue DESC;
