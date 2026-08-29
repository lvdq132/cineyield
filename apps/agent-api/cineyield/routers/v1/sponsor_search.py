"""Sponsor-side discovery across Gemini-analyzed scene inventory."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ...config import get_settings
from ...db import repository

router = APIRouter(prefix="/sponsor-search", tags=["sponsor-search"])

SUPPORTED_CATEGORIES = (
    "Consumer Audio",
    "Mobile Devices",
    "Home / Beverage",
    "Consumer Electronics",
    "Wearables",
)


def _rationale(result: dict, objective: str, budget: float) -> str:
    scene = result.get("scene_name") or "This scene"
    obj = result.get("object_label") or result.get("category") or "placement"
    mood = str(result.get("mood") or "contextual").lower()
    value = float(result.get("estimated_value_usd") or 0)
    affordability = (
        "within the working budget"
        if budget >= value
        else "above the working budget and worth a producer conversation"
    )
    return (
        f"{scene} presents {obj.lower()} in a {mood} story context with "
        f"{int(round(float(result.get('naturalness_score') or 0)))}% naturalness. "
        f"It supports the “{objective}” objective and is {affordability}."
    )


@router.get("")
async def sponsor_search(
    category: str = Query(default="Consumer Audio"),
    objective: str = Query(default="Launch a product", min_length=2, max_length=80),
    budget: float = Query(default=150_000, gt=0, le=10_000_000),
    territory: str = Query(default="US", min_length=2, max_length=8),
    limit: int = Query(default=8, ge=1, le=20),
) -> dict:
    settings = get_settings()
    if not settings.clickhouse_configured:
        raise HTTPException(503, detail="ClickHouse not configured")

    canonical_category = next(
        (item for item in SUPPORTED_CATEGORIES if item.casefold() == category.strip().casefold()),
        None,
    )
    if canonical_category is None:
        raise HTTPException(
            422,
            detail={
                "message": "Unsupported sponsor category",
                "supported_categories": list(SUPPORTED_CATEGORIES),
            },
        )

    rows = repository.search_sponsor_ready_scenes(
        category=canonical_category,
        working_budget_usd=budget,
        limit=limit,
    )
    results = [
        {
            **row,
            "fit_score": float(row.get("fit_score") or 0),
            "rationale": _rationale(row, objective, budget),
            "marketplace_path": f"/marketplace?opportunity_id={row['opportunity_id']}",
        }
        for row in rows
    ]
    return {
        "query": {
            "category": canonical_category,
            "objective": objective,
            "budget": budget,
            "territory": territory.upper(),
        },
        "total_scanned": len(results),
        "qualified_count": len(results),
        "results": results,
        "provenance": {
            "retrieval": "ClickHouse",
            "scene_intelligence": "Gemini-derived analysis",
            "ranking": "Deterministic commercial fit",
        },
    }
