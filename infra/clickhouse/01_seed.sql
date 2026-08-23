-- CineYield Demo Seed Data
-- Fictional brands only. Based on frontend fixture data.
-- Run after 00_init_schema.sql.
--
-- Idempotent / re-runnable: every INSERT is wrapped as
--   INSERT INTO t SELECT ... FROM (VALUES...) WHERE id NOT IN (SELECT id FROM t)
-- so `make db-seed` can be run repeatedly against a live database without
-- creating duplicate rows (the tables are plain MergeTree and do not
-- deduplicate on their own).

-- ─────────────────────────────────────────────────────────────
-- Content catalog
-- ─────────────────────────────────────────────────────────────
INSERT INTO cineyield.content_assets
    (id, title, subtitle, format, status, scene_count, opportunity_count, estimated_value_usd)
SELECT id, title, subtitle, format, status, scene_count, opportunity_count, estimated_value_usd
FROM (
    SELECT 'horizons' AS id, 'HORIZONS' AS title, 'Sci-Fi Drama Series · S2' AS subtitle, 'tv_series' AS format, 'analyzed' AS status, 312 AS scene_count, 47 AS opportunity_count, 2840000.0 AS estimated_value_usd
    UNION ALL
    SELECT 'echoes',        'Echoes of Tomorrow',  'Feature Film',             'film',        'analyzed',  88, 12,  960000.0
    UNION ALL
    SELECT 'second-chapter','Second Chapter',      'Microdrama',               'microdrama',  'analyzing', 54,  0,       NULL
    UNION ALL
    SELECT 'frame-by-frame','Frame by Frame',      'Creator Series',           'youtube',     'analyzed',  31,  9,  120000.0
    UNION ALL
    SELECT 'urban-pulse',   'Urban Pulse',         'Social Clips',             'social',      'queued',     0,  0,       NULL
    UNION ALL
    SELECT 'north-line',    'North Line',          'TV Drama',                 'tv_series',   'analyzed', 120, 19,  780000.0
) AS v
WHERE id NOT IN (SELECT id FROM cineyield.content_assets);

-- ─────────────────────────────────────────────────────────────
-- Scenes
--
-- `horizons` carries the original flagship demo scene. The four other
-- catalogue entries marked status='analyzed' (echoes, frame-by-frame,
-- north-line) previously had ZERO scene rows despite claiming to be
-- analyzed — that contradiction is what made the Library look dead.
-- Each now carries 2-4 genuinely seeded analyzed scenes, in the same
-- style/quality as the horizons scene, so the catalogue is honestly
-- alive rather than fabricated.
--
-- `second-chapter` (status='analyzing') gets a couple of scenes that
-- have completed analysis so far, consistent with a pipeline still in
-- progress. `urban-pulse` (status='queued', scene_count=0) is
-- deliberately left untouched — it has not entered the pipeline yet,
-- so seeding "analyzed" scenes for it would be dishonest, not honest.
-- ─────────────────────────────────────────────────────────────
INSERT INTO cineyield.scenes
    (id, asset_id, episode, name, summary, brand_safety_score, narrative_weight, mood, duration_seconds)
SELECT id, asset_id, episode, name, summary, brand_safety_score, narrative_weight, mood, duration_seconds
FROM (
    SELECT 'rooftop-reflection' AS id, 'horizons' AS asset_id, 'S2E3' AS episode, 'Rooftop Reflection' AS name,
           'A protagonist finishes a long day and looks over a futuristic city at dusk. Reflective, aspirational, premium and technology-forward.' AS summary,
           96.0 AS brand_safety_score, 'High' AS narrative_weight, 'Dusk' AS mood, 44 AS duration_seconds

    UNION ALL
    SELECT 'echoes-harbor-signal', 'echoes', NULL, 'Harbor Signal',
           'A courier waits at a fog-bound harbor terminal for an encrypted transmission, checking a wrist device as container ships idle in the background. Tense, atmospheric, near-future noir.',
           91.0, 'High', 'Tense', 52
    UNION ALL
    SELECT 'echoes-archive-vault', 'echoes', NULL, 'Archive Vault',
           'A researcher sifts through a holographic data archive late at night, a thermos of coffee cooling beside stacked monitors. Focused, intellectual, quietly aspirational.',
           94.0, 'Medium', 'Focused', 47
    UNION ALL
    SELECT 'echoes-final-broadcast', 'echoes', NULL, 'Final Broadcast',
           'A weary anchor delivers a closing transmission from a makeshift studio as the city loses power outside the window. Somber, cinematic, high narrative stakes.',
           89.0, 'High', 'Somber', 61

    UNION ALL
    SELECT 'second-chapter-opening-monologue', 'second-chapter', 'Ep1', 'Opening Monologue',
           'A young lead speaks directly to camera from a sunlit apartment kitchen, recapping the choice that opens the series. Intimate, vertical-native, conversational.',
           93.0, 'Medium', 'Intimate', 18
    UNION ALL
    SELECT 'second-chapter-kitchen-confession', 'second-chapter', 'Ep2', 'Kitchen Confession',
           'Two sisters argue quietly over a shared meal, a delivery bag still on the counter between them. Grounded, dialogue-driven, everyday realism.',
           85.0, 'Medium', 'Tense', 24

    UNION ALL
    SELECT 'frame-by-frame-studio-setup', 'frame-by-frame', 'Ep14', 'Studio Setup Morning',
           'A creator unboxes new gear and sets up a home studio for the day''s shoot, walking viewers through the process with practiced energy. Upbeat, instructional, product-forward.',
           97.0, 'Low', 'Upbeat', 36
    UNION ALL
    SELECT 'frame-by-frame-city-walk', 'frame-by-frame', 'Ep15', 'City Walk Vlog',
           'The creator narrates a handheld walk through a downtown market, pausing to grab a coffee from a street vendor. Candid, lifestyle, high-engagement segment.',
           95.0, 'Medium', 'Candid', 41
    UNION ALL
    SELECT 'frame-by-frame-editing-bay', 'frame-by-frame', 'Ep15', 'Editing Bay Night',
           'Late-night edit session with dual monitors and a mechanical keyboard clacking as the creator color-grades the day''s footage. Focused, technical, aspirational workspace.',
           96.0, 'Low', 'Focused', 33

    UNION ALL
    SELECT 'north-line-station-platform', 'north-line', 'S1E4', 'Station Platform',
           'A detective waits on a frost-lit train platform for a source who never shows, breath visible in the cold. Bleak, procedural, slow-burn tension.',
           90.0, 'High', 'Bleak', 48
    UNION ALL
    SELECT 'north-line-precinct-briefing', 'north-line', 'S1E4', 'Precinct Briefing',
           'The unit gathers around a case board for a pre-dawn briefing, coffee cups and case files scattered across the table. Procedural, ensemble, high narrative weight.',
           92.0, 'High', 'Focused', 55
    UNION ALL
    SELECT 'north-line-late-shift-diner', 'north-line', 'S1E5', 'Late Shift Diner',
           'Two off-duty officers unwind at an all-night diner, a jukebox glowing quietly in the corner booth. Quiet, character-driven, warm counterpoint to the case.',
           94.0, 'Medium', 'Warm', 39
) AS v
WHERE id NOT IN (SELECT id FROM cineyield.scenes);

-- ─────────────────────────────────────────────────────────────
-- Detected objects
-- ─────────────────────────────────────────────────────────────
INSERT INTO cineyield.detected_objects
    (scene_id, asset_id, label, category, confidence, is_primary)
SELECT scene_id, asset_id, label, category, confidence, is_primary
FROM (
    SELECT 'rooftop-reflection' AS scene_id, 'horizons' AS asset_id, 'Wireless Headphones' AS label, 'Consumer audio' AS category, 94.0 AS confidence, true AS is_primary
    UNION ALL SELECT 'rooftop-reflection', 'horizons', 'Smartphone',          'Mobile devices',  92.0, false
    UNION ALL SELECT 'rooftop-reflection', 'horizons', 'Coffee Mug',          'Home / beverage', 89.0, false
    UNION ALL SELECT 'rooftop-reflection', 'horizons', 'Smart Speaker',       'Smart home',      86.0, false
    UNION ALL SELECT 'rooftop-reflection', 'horizons', 'Table Lamp',          'Home / lighting', 83.0, false
    UNION ALL SELECT 'rooftop-reflection', 'horizons', 'Backpack',            'Accessories',     81.0, false

    UNION ALL SELECT 'echoes-harbor-signal',  'echoes', 'Smartwatch',            'Wearables',            90.0, true
    UNION ALL SELECT 'echoes-harbor-signal',  'echoes', 'Messenger Bag',         'Accessories',          80.0, false
    UNION ALL SELECT 'echoes-archive-vault',  'echoes', 'Insulated Thermos',     'Home / beverage',      87.0, true
    UNION ALL SELECT 'echoes-archive-vault',  'echoes', 'Desktop Monitor',       'Consumer electronics', 83.0, false
    UNION ALL SELECT 'echoes-final-broadcast','echoes', 'Studio Microphone',     'Consumer audio',       92.0, true
    UNION ALL SELECT 'echoes-final-broadcast','echoes', 'Backup Battery Pack',   'Consumer electronics', 78.0, false

    UNION ALL SELECT 'second-chapter-opening-monologue',  'second-chapter', 'Smartphone',    'Mobile devices',  91.0, true
    UNION ALL SELECT 'second-chapter-opening-monologue',  'second-chapter', 'Ceramic Mug',   'Home / beverage', 76.0, false
    UNION ALL SELECT 'second-chapter-kitchen-confession', 'second-chapter', 'Food Delivery Bag',       'Food',            82.0, true
    UNION ALL SELECT 'second-chapter-kitchen-confession', 'second-chapter', 'Wireless Earbuds Case',   'Consumer audio',  74.0, false

    UNION ALL SELECT 'frame-by-frame-studio-setup', 'frame-by-frame', 'Mirrorless Camera', 'Consumer electronics', 95.0, true
    UNION ALL SELECT 'frame-by-frame-studio-setup', 'frame-by-frame', 'Ring Light',         'Home / lighting',      85.0, false
    UNION ALL SELECT 'frame-by-frame-city-walk',    'frame-by-frame', 'Iced Coffee Cup',    'Home / beverage',      88.0, true
    UNION ALL SELECT 'frame-by-frame-city-walk',    'frame-by-frame', 'Crossbody Bag',      'Accessories',          79.0, false
    UNION ALL SELECT 'frame-by-frame-editing-bay',  'frame-by-frame', 'Mechanical Keyboard','Consumer electronics', 84.0, true
    UNION ALL SELECT 'frame-by-frame-editing-bay',  'frame-by-frame', 'Desk Lamp',          'Home / lighting',      77.0, false

    UNION ALL SELECT 'north-line-station-platform',  'north-line', 'Wool Overcoat',       'Apparel',              81.0, true
    UNION ALL SELECT 'north-line-station-platform',  'north-line', 'Two-Way Radio',       'Consumer electronics', 86.0, false
    UNION ALL SELECT 'north-line-precinct-briefing', 'north-line', 'Disposable Coffee Cup','Home / beverage',     83.0, true
    UNION ALL SELECT 'north-line-precinct-briefing', 'north-line', 'Tablet Device',       'Mobile devices',       80.0, false
    UNION ALL SELECT 'north-line-late-shift-diner',  'north-line', 'Diner Jukebox',       'Smart home',           72.0, true
    UNION ALL SELECT 'north-line-late-shift-diner',  'north-line', 'Smartphone',          'Mobile devices',       85.0, false
) AS v
WHERE (scene_id, label) NOT IN (SELECT scene_id, label FROM cineyield.detected_objects);

-- ─────────────────────────────────────────────────────────────
-- Placement opportunities
-- ─────────────────────────────────────────────────────────────
INSERT INTO cineyield.placement_opportunities
    (id, scene_id, asset_id, category, object_label, timecode_start, timecode_end,
     screen_time_seconds, naturalness_score, brand_safety_score, complexity, rights_status,
     estimated_value_usd, is_primary)
SELECT id, scene_id, asset_id, category, object_label, timecode_start, timecode_end,
       screen_time_seconds, naturalness_score, brand_safety_score, complexity, rights_status,
       estimated_value_usd, is_primary
FROM (
    SELECT 'opp_horizons_rooftop_001' AS id, 'rooftop-reflection' AS scene_id, 'horizons' AS asset_id,
           'Consumer Audio' AS category, 'Wireless Headphones' AS object_label, '00:12' AS timecode_start, '00:38' AS timecode_end,
           26 AS screen_time_seconds, 92.0 AS naturalness_score, 96.0 AS brand_safety_score, 'low' AS complexity, 'clear' AS rights_status,
           185000.0 AS estimated_value_usd, true AS is_primary
    UNION ALL
    SELECT 'opp_horizons_rooftop_002', 'rooftop-reflection', 'horizons',
           'Mobile Devices', 'Smartphone',          '00:20', '00:33', 13, 78.0, 95.0, 'low',  'clear',  74000.0, false
    UNION ALL
    SELECT 'opp_horizons_rooftop_003', 'rooftop-reflection', 'horizons',
           'Smart Home',     'Smart Speaker',       '00:05', '00:29', 20, 74.0, 93.0, 'medium','clear', 66000.0, false
    UNION ALL
    SELECT 'opp_horizons_rooftop_004', 'rooftop-reflection', 'horizons',
           'Home / Beverage','Coffee Mug',          '00:28', '00:41', 11, 71.0, 94.0, 'medium','review', 38000.0, false
    UNION ALL
    SELECT 'opp_horizons_rooftop_005', 'rooftop-reflection', 'horizons',
           'Home / Lighting','Table Lamp',          '00:02', '00:44', 34, 58.0, 97.0, 'high',  'clear', 22000.0, false

    UNION ALL
    SELECT 'opp_echoes_harbor_001', 'echoes-harbor-signal', 'echoes',
           'Wearables', 'Smartwatch', '00:04', '00:29', 25, 88.0, 91.0, 'low', 'clear', 64000.0, true
    UNION ALL
    SELECT 'opp_echoes_archive_001', 'echoes-archive-vault', 'echoes',
           'Home / Beverage', 'Insulated Thermos', '00:10', '00:33', 23, 81.0, 94.0, 'medium', 'clear', 28000.0, true
    UNION ALL
    SELECT 'opp_echoes_broadcast_001', 'echoes-final-broadcast', 'echoes',
           'Consumer Audio', 'Studio Microphone', '00:02', '00:40', 38, 85.0, 89.0, 'high', 'clear', 71000.0, true

    UNION ALL
    SELECT 'opp_secondchapter_opening_001', 'second-chapter-opening-monologue', 'second-chapter',
           'Mobile Devices', 'Smartphone', '00:00', '00:15', 15, 90.0, 93.0, 'low', 'clear', 21000.0, true
    UNION ALL
    SELECT 'opp_secondchapter_kitchen_001', 'second-chapter-kitchen-confession', 'second-chapter',
           'Food', 'Food Delivery Bag', '00:03', '00:19', 16, 77.0, 85.0, 'medium', 'review', 9000.0, true

    UNION ALL
    SELECT 'opp_framebyframe_studio_001', 'frame-by-frame-studio-setup', 'frame-by-frame',
           'Consumer Electronics', 'Mirrorless Camera', '00:01', '00:28', 27, 93.0, 97.0, 'low', 'clear', 58000.0, true
    UNION ALL
    SELECT 'opp_framebyframe_citywalk_001', 'frame-by-frame-city-walk', 'frame-by-frame',
           'Home / Beverage', 'Iced Coffee Cup', '00:05', '00:31', 26, 86.0, 95.0, 'low', 'clear', 19000.0, true
    UNION ALL
    SELECT 'opp_framebyframe_editingbay_001', 'frame-by-frame-editing-bay', 'frame-by-frame',
           'Consumer Electronics', 'Mechanical Keyboard', '00:00', '00:24', 24, 80.0, 96.0, 'medium', 'clear', 15000.0, true

    UNION ALL
    SELECT 'opp_northline_platform_001', 'north-line-station-platform', 'north-line',
           'Apparel', 'Wool Overcoat', '00:06', '00:34', 28, 79.0, 90.0, 'medium', 'clear', 24000.0, true
    UNION ALL
    SELECT 'opp_northline_briefing_001', 'north-line-precinct-briefing', 'north-line',
           'Home / Beverage', 'Disposable Coffee Cup', '00:00', '00:22', 22, 75.0, 92.0, 'low', 'clear', 17000.0, true
    UNION ALL
    SELECT 'opp_northline_diner_001', 'north-line-late-shift-diner', 'north-line',
           'Smart Home', 'Diner Jukebox', '00:08', '00:29', 21, 68.0, 94.0, 'high', 'review', 12000.0, true
) AS v
WHERE id NOT IN (SELECT id FROM cineyield.placement_opportunities);

-- ─────────────────────────────────────────────────────────────
-- Brand campaign inventory
-- 27 total campaigns for a realistic Market Agent scan.
-- Fictional brands only.
-- ─────────────────────────────────────────────────────────────

-- Tier 1: Strong matches for Consumer Audio / headphones
INSERT INTO cineyield.brand_campaigns
    (id, brand, campaign_name, product_line, budget_min_usd, budget_max_usd,
     target_categories, excluded_contexts, territories,
     visibility_seconds_min, visibility_seconds_max, is_active)
SELECT id, brand, campaign_name, product_line, budget_min_usd, budget_max_usd,
       target_categories, excluded_contexts, territories,
       visibility_seconds_min, visibility_seconds_max, is_active
FROM (
    -- TOP MATCH
    SELECT 'camp_aurelius_001' AS id, 'Aurelius Systems' AS brand, 'Focus Without Limits' AS campaign_name,
           'Aurelius One Wireless Headphones' AS product_line, 150000 AS budget_min_usd, 250000 AS budget_max_usd,
           ['Consumer audio', 'Lifestyle tech', 'Wearables'] AS target_categories,
           ['violence', 'intoxication', 'ridicule'] AS excluded_contexts,
           ['US', 'CA', 'GB', 'AU'] AS territories,
           10 AS visibility_seconds_min, 30 AS visibility_seconds_max, true AS is_active

    -- Good match
    UNION ALL
    SELECT 'camp_aurora_001', 'Aurora Tech', 'Everyday Sound',
           'Aurora ANC Headphones', 90000, 160000,
           ['Consumer audio', 'Mobile devices'],
           ['violence', 'unsafe activity'],
           ['US', 'CA'],
           10, 35, true

    -- Good match
    UNION ALL
    SELECT 'camp_pinnacle_001', 'Pinnacle Performance', 'Move Free',
           'Pinnacle Sport Headset', 120000, 200000,
           ['Consumer audio', 'Wearables', 'Fitness'],
           ['violence'],
           ['US', 'GB'],
           12, 45, true

    -- Mid match (EU focused)
    UNION ALL
    SELECT 'camp_nexalife_001', 'NexaLife', 'Balance',
           'NexaLife Wellness Buds', 60000, 120000,
           ['Wearables', 'Wellness', 'Consumer audio'],
           ['violence', 'fast pace'],
           ['GB', 'DE', 'FR'],
           8, 30, true

    -- Weak match — audio but niche fitness
    UNION ALL
    SELECT 'camp_beatpulse_001', 'BeatPulse', 'Train Hard',
           'BeatPulse Workout Earbuds', 40000, 80000,
           ['Fitness', 'Consumer audio'],
           ['reflective', 'slow pace'],
           ['US'],
           5, 20, true

    -- BLOCKED: creative conflict (energy drink in reflective scene)
    UNION ALL
    SELECT 'camp_vortex_001', 'Vortex Energy', 'Unleash Everything',
           'Vortex Ultra Energy Drink', 200000, 350000,
           ['Beverages', 'Lifestyle'],
           ['reflective', 'melancholic', 'slow pace', 'aspirational quiet'],
           ['US', 'CA', 'GB', 'AU', 'DE'],
           5, 60, true

    -- BLOCKED: category mismatch (apparel, no audio connection)
    UNION ALL
    SELECT 'camp_stride_001', 'Stride Apparel', 'Own Your Run',
           'Stride Performance Gear', 80000, 140000,
           ['Apparel', 'Fitness apparel'],
           [],
           ['US', 'CA'],
           5, 30, true
) AS v
WHERE id NOT IN (SELECT id FROM cineyield.brand_campaigns);

-- Tier 2: Moderate / adjacent campaigns
INSERT INTO cineyield.brand_campaigns
    (id, brand, campaign_name, product_line, budget_min_usd, budget_max_usd,
     target_categories, excluded_contexts, territories,
     visibility_seconds_min, visibility_seconds_max, is_active)
SELECT id, brand, campaign_name, product_line, budget_min_usd, budget_max_usd,
       target_categories, excluded_contexts, territories,
       visibility_seconds_min, visibility_seconds_max, is_active
FROM (
    SELECT 'camp_silvertech_001' AS id, 'SilverTech' AS brand, 'Precision by Design' AS campaign_name,
           'SilverTech Wireless Earbuds' AS product_line, 55000 AS budget_min_usd, 100000 AS budget_max_usd,
           ['Consumer audio', 'Lifestyle tech'] AS target_categories,
           [] AS excluded_contexts,
           ['DE', 'FR', 'IT'] AS territories,
           10 AS visibility_seconds_min, 30 AS visibility_seconds_max, true AS is_active

    UNION ALL
    SELECT 'camp_cloudform_001', 'CloudForm', 'Smart Space',
           'CloudForm Hub Speaker', 70000, 120000,
           ['Smart home', 'Lifestyle tech'],
           ['violence'],
           ['US', 'CA', 'GB'],
           10, 40, true

    UNION ALL
    SELECT 'camp_primewave_001', 'PrimeWave', 'Drive the Future',
           'PrimeWave CarAudio System', 100000, 180000,
           ['Automotive audio'],
           [],
           ['US'],
           15, 45, true

    UNION ALL
    SELECT 'camp_luminary_001', 'Luminary Labs', 'Think Ahead',
           'Luminary Smart Speaker', 90000, 150000,
           ['Smart home', 'Consumer audio'],
           ['distraction', 'noise'],
           ['US', 'CA', 'GB', 'AU'],
           20, 45, true

    UNION ALL
    SELECT 'camp_novascreen_001', 'NovaScreen', 'See More',
           'NovaScreen OLED Display', 200000, 400000,
           ['Consumer electronics'],
           [],
           ['US', 'CA'],
           10, 50, true

    UNION ALL
    SELECT 'camp_meridian_001', 'Meridian Coffee', 'Your Perfect Morning',
           'Meridian Premium Blend', 30000, 60000,
           ['Home / beverage', 'Lifestyle'],
           ['intoxication'],
           ['US', 'CA', 'GB'],
           5, 20, true

    UNION ALL
    SELECT 'camp_apex_001', 'Apex Wearables', 'Beyond Limits',
           'Apex Smart Watch', 80000, 160000,
           ['Wearables', 'Lifestyle tech'],
           [],
           ['US', 'CA', 'GB'],
           10, 40, true
) AS v
WHERE id NOT IN (SELECT id FROM cineyield.brand_campaigns);

-- Tier 3: Low/no match campaigns (pad count to 27)
INSERT INTO cineyield.brand_campaigns
    (id, brand, campaign_name, product_line, budget_min_usd, budget_max_usd,
     target_categories, excluded_contexts, territories,
     visibility_seconds_min, visibility_seconds_max, is_active)
SELECT id, brand, campaign_name, product_line, budget_min_usd, budget_max_usd,
       target_categories, excluded_contexts, territories,
       visibility_seconds_min, visibility_seconds_max, is_active
FROM (
    SELECT 'camp_greenfield_001' AS id, 'Greenfield Foods' AS brand, 'Eat Well' AS campaign_name,
           'Greenfield Protein Bars' AS product_line, 20000 AS budget_min_usd, 40000 AS budget_max_usd,
           ['Food', 'Wellness'] AS target_categories,
           [] AS excluded_contexts,
           ['US'] AS territories,
           5 AS visibility_seconds_min, 15 AS visibility_seconds_max, true AS is_active

    UNION ALL
    SELECT 'camp_urbancraft_001', 'UrbanCraft Tools', 'Build Something',
           'UrbanCraft Power Drill Set', 15000, 30000,
           ['Home improvement', 'Tools'],
           [],
           ['US', 'CA'],
           5, 20, true

    UNION ALL
    SELECT 'camp_coralwave_001', 'CoralWave Travel', 'Go Anywhere',
           'CoralWave Travel Essentials', 50000, 90000,
           ['Travel', 'Accessories'],
           [],
           ['US', 'CA', 'GB'],
           5, 25, true

    UNION ALL
    SELECT 'camp_titanfinance_001', 'Titan Finance', 'Your Future Now',
           'Titan Investment Platform', 100000, 200000,
           ['Finance', 'Technology'],
           ['controversy', 'negativity'],
           ['US'],
           10, 30, true

    UNION ALL
    SELECT 'camp_skymotion_001', 'SkyMotion', 'Always Moving',
           'SkyMotion Scooter', 40000, 70000,
           ['Transport', 'Lifestyle'],
           [],
           ['US', 'GB'],
           5, 20, true

    UNION ALL
    SELECT 'camp_rootsorg_001', 'Roots Organics', 'Back to Nature',
           'Roots Organic Skincare', 25000, 50000,
           ['Beauty', 'Wellness'],
           ['synthetic', 'industrial'],
           ['US', 'CA', 'GB'],
           5, 15, true

    UNION ALL
    SELECT 'camp_zephyr_001', 'Zephyr Apparel', 'Light as Air',
           'Zephyr Summer Collection', 35000, 65000,
           ['Apparel', 'Lifestyle'],
           [],
           ['US', 'CA'],
           5, 20, true

    UNION ALL
    SELECT 'camp_ironclad_001', 'Ironclad Security', 'Protect What Matters',
           'Ironclad Home Security', 60000, 110000,
           ['Home security', 'Technology'],
           ['unsafe environment'],
           ['US', 'CA'],
           10, 30, true

    UNION ALL
    SELECT 'camp_solarflow_001', 'SolarFlow', 'Clean Power',
           'SolarFlow Residential Panel', 80000, 150000,
           ['Energy', 'Technology'],
           [],
           ['US', 'AU'],
           10, 40, true

    UNION ALL
    SELECT 'camp_freshstep_001', 'FreshStep', 'Every Step Counts',
           'FreshStep Running Shoes', 45000, 85000,
           ['Footwear', 'Fitness apparel'],
           [],
           ['US', 'CA', 'GB'],
           5, 20, true

    UNION ALL
    SELECT 'camp_vivantis_001', 'Vivantis Pharma', 'Feel Your Best',
           'Vivantis Wellness Supplements', 55000, 95000,
           ['Wellness', 'Health'],
           ['violence', 'unsafe activity'],
           ['US'],
           5, 20, true

    UNION ALL
    SELECT 'camp_harborpoint_001', 'HarborPoint Realty', 'Find Your Place',
           'HarborPoint Luxury Properties', 120000, 220000,
           ['Real estate', 'Lifestyle'],
           [],
           ['US', 'CA'],
           10, 40, true

    UNION ALL
    SELECT 'camp_dawnrise_001', 'DawnRise Coffee', 'Rise with the Day',
           'DawnRise Single Origin', 18000, 35000,
           ['Home / beverage', 'Lifestyle'],
           [],
           ['US', 'CA'],
           5, 15, true
) AS v
WHERE id NOT IN (SELECT id FROM cineyield.brand_campaigns);

-- ─────────────────────────────────────────────────────────────
-- Rights rules (deterministic enforcement)
-- ─────────────────────────────────────────────────────────────
INSERT INTO cineyield.rights_rules
    (id, category, territory, status, usage_window_months, notes)
SELECT id, category, territory, status, usage_window_months, notes
FROM (
    SELECT 'rr_001' AS id, 'Consumer audio' AS category, 'US' AS territory, 'clear' AS status, 12 AS usage_window_months, NULL AS notes
    UNION ALL SELECT 'rr_002', 'Consumer audio',  'CA',  'clear',      12, NULL
    UNION ALL SELECT 'rr_003', 'Consumer audio',  'GB',  'clear',      12, NULL
    UNION ALL SELECT 'rr_004', 'Consumer audio',  'DE',  'restricted',  0, 'Usage window not cleared for this category'
    UNION ALL SELECT 'rr_005', 'Consumer audio',  'AU',  'clear',      12, NULL
    UNION ALL SELECT 'rr_006', 'Mobile devices',  'US',  'clear',      12, NULL
    UNION ALL SELECT 'rr_007', 'Mobile devices',  'CA',  'clear',      12, NULL
    UNION ALL SELECT 'rr_008', 'Mobile devices',  'GB',  'clear',      12, NULL
    UNION ALL SELECT 'rr_009', 'Smart home',      'US',  'clear',      12, NULL
    UNION ALL SELECT 'rr_010', 'Smart home',      'CA',  'clear',      12, NULL
    UNION ALL SELECT 'rr_011', 'Smart home',      'GB',  'review',      6, 'Territory review in progress'
    UNION ALL SELECT 'rr_012', 'Home / beverage', 'US',  'review',     12, 'Category pending approval'
    UNION ALL SELECT 'rr_013', 'Home / beverage', 'CA',  'clear',      12, NULL
    UNION ALL SELECT 'rr_014', 'Lifestyle tech',  'US',  'clear',      12, NULL
    UNION ALL SELECT 'rr_015', 'Lifestyle tech',  'CA',  'clear',      12, NULL
    UNION ALL SELECT 'rr_016', 'Lifestyle tech',  'GB',  'clear',      12, NULL
    UNION ALL SELECT 'rr_017', 'Wearables',       'US',  'clear',      12, NULL
    UNION ALL SELECT 'rr_018', 'Wearables',       'CA',  'clear',      12, NULL
    UNION ALL SELECT 'rr_019', 'Wearables',       'GB',  'clear',      12, NULL
    UNION ALL SELECT 'rr_020', 'Wearables',       'DE',  'review',      6, 'Territory review pending'
) AS v
WHERE id NOT IN (SELECT id FROM cineyield.rights_rules);
