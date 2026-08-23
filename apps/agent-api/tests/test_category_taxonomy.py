"""Coverage test: every Gemini prompt category must resolve to at least one
unblocked campaign against the REAL seeded taxonomy, or be a documented,
deliberate exception.

FIX 4 (P0 review): scene_agent.py's Gemini prompt offers 13 category values.
Cross-referenced against every seeded campaign's target_categories
(infra/clickhouse/01_seed.sql), two of them matched nothing:

- "Home & living" had no substring relation, in either direction, with any
  of the seeded "Home ..." categories.
- "Other" -- also the default `_build_opportunities` falls back to when
  Gemini omits the category key -- matched nothing either.

category_taxonomy.normalize_category() fixes the first and deliberately
leaves the second fail-closed (see that module's docstring). This test
locks in both halves against the actual seeded campaign data so a taxonomy
change on either side (the Gemini prompt or the seed) cannot silently
reopen the dead end.

SEEDED_TARGET_CATEGORIES below is a snapshot of every `target_categories`
array in infra/clickhouse/01_seed.sql's 27-campaign brand_campaigns insert,
as of the "27 total campaigns for a realistic Market Agent scan" section. If
the seed changes, update this list.
"""
from cineyield.agents.category_taxonomy import PROMPT_CATEGORIES, normalize_category
from cineyield.agents.scoring import _score_category_fit

# One list per seeded campaign's target_categories (27 campaigns total).
SEEDED_TARGET_CATEGORIES: list[list[str]] = [
    ["Consumer audio", "Lifestyle tech", "Wearables"],
    ["Consumer audio", "Mobile devices"],
    ["Consumer audio", "Wearables", "Fitness"],
    ["Wearables", "Wellness", "Consumer audio"],
    ["Fitness", "Consumer audio"],
    ["Beverages", "Lifestyle"],
    ["Apparel", "Fitness apparel"],
    ["Consumer audio", "Lifestyle tech"],
    ["Smart home", "Lifestyle tech"],
    ["Automotive audio"],
    ["Smart home", "Consumer audio"],
    ["Consumer electronics"],
    ["Home / beverage", "Lifestyle"],
    ["Wearables", "Lifestyle tech"],
    ["Food", "Wellness"],
    ["Home improvement", "Tools"],
    ["Travel", "Accessories"],
    ["Finance", "Technology"],
    ["Transport", "Lifestyle"],
    ["Beauty", "Wellness"],
    ["Apparel", "Lifestyle"],
    ["Home security", "Technology"],
    ["Energy", "Technology"],
    ["Footwear", "Fitness apparel"],
    ["Wellness", "Health"],
    ["Real estate", "Lifestyle"],
    ["Home / beverage", "Lifestyle"],
]

# "Other" is the sole deliberate, documented exception -- see
# category_taxonomy.py's module docstring. Every other prompt category must
# resolve to at least one unblocked (category_fit == 100.0) campaign.
DELIBERATE_NO_MATCH_EXCEPTIONS = {"Other"}


def _unblocked_campaign_count(normalized_category: str) -> int:
    return sum(
        1
        for target_categories in SEEDED_TARGET_CATEGORIES
        if _score_category_fit(normalized_category, target_categories) == 100.0
    )


def test_seed_snapshot_has_27_campaigns():
    """Sanity check the fixture mirrors the seed's documented campaign count."""
    assert len(SEEDED_TARGET_CATEGORIES) == 27


def test_prompt_categories_list_has_all_13_values():
    """category_taxonomy.PROMPT_CATEGORIES must mirror the Gemini prompt exactly."""
    assert len(PROMPT_CATEGORIES) == 13
    from cineyield.agents.scene_agent import _SCENE_ANALYSIS_PROMPT

    for cat in PROMPT_CATEGORIES:
        assert cat in _SCENE_ANALYSIS_PROMPT, (
            f"{cat!r} is in category_taxonomy.PROMPT_CATEGORIES but not in "
            "the actual Gemini prompt -- the two have drifted apart"
        )


def test_every_prompt_category_resolves_to_a_real_campaign_or_is_a_documented_exception():
    """The core FIX 4 regression guard.

    Every one of the 13 prompt categories, after normalize_category(), must
    match at least one seeded campaign's target_categories -- except the
    categories explicitly listed in DELIBERATE_NO_MATCH_EXCEPTIONS, which
    must fail closed (0 matches) on purpose.
    """
    for raw_category in PROMPT_CATEGORIES:
        normalized = normalize_category(raw_category)
        matches = _unblocked_campaign_count(normalized)

        if raw_category in DELIBERATE_NO_MATCH_EXCEPTIONS:
            assert matches == 0, (
                f"{raw_category!r} is documented as a deliberate fail-closed "
                f"exception but now matches {matches} campaign(s) -- "
                "normalize_category must not turn 'no evidence' into a "
                "universal match"
            )
        else:
            assert matches >= 1, (
                f"{raw_category!r} (normalized to {normalized!r}) matches "
                "zero seeded campaigns -- this is the FIX 4 dead end "
                "regressing. Add a category_taxonomy.py override or a "
                "documented exception."
            )


def test_home_and_living_override_matches_the_home_family():
    """"Home" substring-matches every seeded category containing the word
    "home" -- the three "Home ..." categories plus "Smart home" (the
    substring matcher is symmetric: "home" in "smart home" too). All of
    them are a defensible candidate for a broad "Home & living" detection,
    which is the point of normalizing to the family prefix rather than
    picking one arbitrarily.
    """
    normalized = normalize_category("Home & living")
    assert normalized == "Home"
    matched = [
        set(target_categories)
        for target_categories in SEEDED_TARGET_CATEGORIES
        if _score_category_fit(normalized, target_categories) == 100.0
    ]
    assert len(matched) == 6
    assert {"Home improvement", "Tools"} in matched
    assert {"Home security", "Technology"} in matched
    assert {"Home / beverage", "Lifestyle"} in matched
    assert {"Smart home", "Lifestyle tech"} in matched
    assert {"Smart home", "Consumer audio"} in matched


def test_other_normalizes_to_blank_and_fails_closed():
    """Deliberate: "Other" means "no category evidence", same as blank.

    Must NOT be given a real category to universally match against --
    scoring.py's fail-closed rule for blank categories is intentional.
    """
    assert normalize_category("Other") == ""
    assert normalize_category("other") == ""
    assert _score_category_fit("", ["Consumer audio"]) == 0.0


def test_normalize_category_is_case_and_whitespace_insensitive():
    assert normalize_category("home & living") == "Home"
    assert normalize_category("  Home & Living  ") == "Home"
    assert normalize_category("OTHER") == ""


def test_normalize_category_passes_through_categories_that_already_match():
    """The 11 prompt categories with no override must be returned unchanged."""
    unchanged = [c for c in PROMPT_CATEGORIES if c not in ("Home & living", "Other")]
    assert len(unchanged) == 11
    for cat in unchanged:
        assert normalize_category(cat) == cat


def test_normalize_category_passthrough_for_unknown_value():
    """A category outside the 13 prompt values (or blank) is returned as-is."""
    assert normalize_category("Some Future Category") == "Some Future Category"
    assert normalize_category("") == ""
