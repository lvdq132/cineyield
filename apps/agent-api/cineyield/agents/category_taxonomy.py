"""Taxonomy normalizer between Gemini's scene-analysis categories and the
seeded `brand_campaigns.target_categories` vocabulary that
`scoring._score_category_fit` matches against via case-insensitive substring
comparison.

Gemini (scene_agent.py's `_SCENE_ANALYSIS_PROMPT`) is prompted with a fixed
list of 13 category values. Cross-referenced against every seeded campaign's
`target_categories` (infra/clickhouse/01_seed.sql), 11 of the 13 already
overlap with at least one seeded campaign via that substring rule and need no
help. Two do not, and both silently blocked every one of the 27 seeded
campaigns (`category_fit` 0.0 -> hard block) whenever Gemini returned them:

- "Home & living" has no substring relation, in either direction, with any of
  the seeded "Home ..." categories (Home / beverage, Home improvement, Home
  security). Normalized here to "Home" so it substring-matches all three --
  the deterministic scorer's other criteria (context fit, budget, territory,
  brand safety) still decide ranking and blocking from there. This is a
  best-effort family match, not a precise one: nothing in the seed is a
  clean semantic fit for "kitchen appliance" or "living-room decor", so
  matching the whole Home family is the honest compromise between "give up"
  and "invent a category that doesn't exist in the data".

- "Other" is also the *default* `scene_agent._build_opportunities` falls
  back to whenever Gemini omits the category key entirely -- i.e. it means
  "no positive category evidence", the same thing a blank category means.
  scoring.py's fail-closed rule for a blank category (0.0 fit, hard block,
  see `_score_category_fit`) is deliberately correct and must NOT be
  bypassed here: mapping "Other" onto some real category would turn "no
  evidence" into "universal match", which is the dishonest failure mode
  this module exists to avoid. "Other" is therefore normalized to "" so it
  hits that same fail-closed path. This is a deliberate, documented
  exception to "every prompt category should resolve to a match" -- not a
  gap.
"""
from __future__ import annotations

# The 13 category values Gemini is prompted to choose from in
# scene_agent.py's _SCENE_ANALYSIS_PROMPT. Kept here (rather than parsed out
# of the prompt string) so tests can assert full coverage explicitly.
PROMPT_CATEGORIES: list[str] = [
    "Consumer audio",
    "Mobile devices",
    "Automotive",
    "Apparel",
    "Beverages",
    "Food & dining",
    "Home & living",
    "Sports & fitness",
    "Beauty & wellness",
    "Technology",
    "Jewelry & accessories",
    "Travel & luggage",
    "Other",
]

# Explicit mapping for all 13 prompt categories onto the value handed to
# scoring.py. Most map to themselves -- they already overlap with seeded
# target_categories via the substring rule. Only "home & living" and "other"
# are real overrides; see the module docstring for why.
_CATEGORY_MAP: dict[str, str] = {
    "consumer audio": "Consumer audio",
    "mobile devices": "Mobile devices",
    "automotive": "Automotive",
    "apparel": "Apparel",
    "beverages": "Beverages",
    "food & dining": "Food & dining",
    "home & living": "Home",  # override -- see module docstring
    "sports & fitness": "Sports & fitness",
    "beauty & wellness": "Beauty & wellness",
    "technology": "Technology",
    "jewelry & accessories": "Jewelry & accessories",
    "travel & luggage": "Travel & luggage",
    "other": "",  # override, deliberate -- see module docstring
}


def normalize_category(raw: str) -> str:
    """Map a Gemini-detected category onto the seeded campaign taxonomy.

    Returns the value scoring.py's substring matcher should be given instead
    of the raw Gemini string. A category outside the 13 prompted values (or
    already blank) passes through unchanged -- there is nothing to normalize
    it against.
    """
    if not raw:
        return raw
    key = raw.strip().lower()
    if key in _CATEGORY_MAP:
        return _CATEGORY_MAP[key]
    return raw
