"""Tests for POST /api/v1/deals/{deal_id}/approve.

Regression guards for two live-data bugs found via direct code review:

FIX 2: the proposal/opportunity join query had no ORDER BY and grouped by
`placement_fee_usd`. `proposals` is a plain MergeTree and upsert_proposal()
INSERTs rather than replaces, so re-composing the same proposal id (e.g.
DealAgent recomputing a fee) leaves two rows behind with different fees --
each fee value became its own GROUP BY bucket, and an unordered LIMIT 1
picked one arbitrarily. repository.get_proposal (what the deal page reads)
already used ORDER BY composed_at DESC LIMIT 1, so approve could record a
different, stale fee than the one shown on screen.

FIX 3: approve_deal had no idempotency check. A second approval of the same
deal wrote a second revenue_events row (fresh uuid4() event_id every time),
inflating approved_deals/approved_revenue_usd in /analytics/summary.
"""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _mock_settings(configured: bool) -> MagicMock:
    settings = MagicMock()
    settings.clickhouse_configured = configured
    return settings


def _fake_ch_client(row: tuple) -> MagicMock:
    """Fake ClickHouse client whose .query() returns one fixed proposal/opportunity row."""
    fake = MagicMock()
    result = MagicMock()
    result.column_names = ["id", "opportunity_id", "campaign_id", "placement_fee_usd", "asset_id"]
    result.result_rows = [row]
    fake.query.return_value = result
    return fake


def test_approve_returns_404_when_deal_not_found():
    fake = _fake_ch_client(())
    fake.query.return_value.result_rows = []
    with patch(
        "cineyield.routers.v1.deals.get_settings", return_value=_mock_settings(True)
    ), patch("cineyield.db.client.get_clickhouse_client", return_value=fake), patch(
        "cineyield.db.repository.get_proposal", return_value=None
    ):
        resp = client.post(
            "/api/v1/deals/does-not-exist/approve",
            json={"approved": True, "approver": "producer_1"},
        )
    assert resp.status_code == 404


def test_approve_query_does_not_group_by_fee_and_uses_argmax():
    """The specific FIX 2 bug pattern: fee must not be a GROUP BY key, and
    must be picked deterministically via argMax(..., composed_at) rather
    than an unordered LIMIT 1 over per-fee groups."""
    fake = _fake_ch_client(("prop_x", "opp_1", "camp_1", 92000.0, "horizons"))
    with patch(
        "cineyield.routers.v1.deals.get_settings", return_value=_mock_settings(True)
    ), patch("cineyield.db.client.get_clickhouse_client", return_value=fake), patch(
        "cineyield.db.repository.get_proposal", return_value={"is_approved": False}
    ), patch("cineyield.db.repository.approve_proposal") as mock_approve, patch(
        "cineyield.db.repository.write_revenue_event", return_value="rev_1"
    ) as mock_write_rev, patch("cineyield.db.repository.write_agent_event"):
        resp = client.post(
            "/api/v1/deals/prop_x/approve",
            json={"approved": True, "approver": "producer_1"},
        )

    assert resp.status_code == 200
    sql = fake.query.call_args[0][0]
    assert "argMax(p.placement_fee_usd, p.composed_at)" in sql
    assert "GROUP BY p.id" in sql
    # The old bug: placement_fee_usd (and opportunity_id/campaign_id) in the
    # GROUP BY clause. Only p.id may appear there now.
    group_by_clause = sql.split("GROUP BY", 1)[1].split("LIMIT", 1)[0]
    assert "placement_fee_usd" not in group_by_clause
    mock_approve.assert_called_once_with("prop_x")
    # The fee recorded as revenue must be the one the query returned --
    # i.e. wired straight through, not silently substituted.
    assert mock_write_rev.call_args.kwargs["amount_usd"] == 92000.0
    assert resp.json()["revenue_event_id"] == "rev_1"


def test_second_approval_is_idempotent_and_does_not_double_count_revenue():
    """FIX 3: approving an already-APPROVED deal must not write a second
    revenue_events row -- it must return the original revenue_event_id."""
    fake = _fake_ch_client(("prop_y", "opp_2", "camp_2", 50000.0, "horizons"))
    with patch(
        "cineyield.routers.v1.deals.get_settings", return_value=_mock_settings(True)
    ), patch("cineyield.db.client.get_clickhouse_client", return_value=fake), patch(
        "cineyield.db.repository.get_proposal", return_value={"is_approved": True}
    ), patch("cineyield.db.repository.approve_proposal") as mock_approve, patch(
        "cineyield.db.repository.write_revenue_event"
    ) as mock_write_rev, patch(
        "cineyield.db.repository.get_revenue_event_for_proposal",
        return_value={"event_id": "rev_original", "amount_usd": 50000.0},
    ), patch("cineyield.db.repository.write_agent_event") as mock_agent_event:
        resp = client.post(
            "/api/v1/deals/prop_y/approve",
            json={"approved": True, "approver": "producer_2"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["already_approved"] is True
    assert body["revenue_event_id"] == "rev_original"
    assert body["status"] == "APPROVED"
    mock_approve.assert_not_called()
    mock_write_rev.assert_not_called()
    mock_agent_event.assert_not_called()


def test_rejection_writes_asset_id_on_agent_event():
    """FIX 6: the rejection branch used to omit asset_id from
    write_agent_event, leaving the "" the approval branch fixed."""
    fake = _fake_ch_client(("prop_z", "opp_3", "camp_3", 40000.0, "horizons"))
    with patch(
        "cineyield.routers.v1.deals.get_settings", return_value=_mock_settings(True)
    ), patch("cineyield.db.client.get_clickhouse_client", return_value=fake), patch(
        "cineyield.db.repository.write_agent_event"
    ) as mock_agent_event:
        resp = client.post(
            "/api/v1/deals/prop_z/approve",
            json={"approved": False, "approver": "producer_3", "note": "not a fit"},
        )

    assert resp.status_code == 200
    assert resp.json()["approved"] is False
    assert mock_agent_event.call_args.kwargs["asset_id"] == "horizons"


def test_canonical_alias_gets_latest_real_proposal():
    proposal = {
        "id": "prop_latest",
        "opportunity_id": "opp_horizons_rooftop_001",
        "campaign_id": "camp_aurelius_001",
        "workflow_state": "PRODUCER_REVIEW",
        "is_approved": False,
    }
    with patch(
        "cineyield.routers.v1.deals.get_settings", return_value=_mock_settings(True)
    ), patch(
        "cineyield.db.repository.get_latest_proposal_id", return_value="prop_latest"
    ) as mock_resolve, patch(
        "cineyield.db.repository.get_proposal", return_value=proposal
    ):
        resp = client.get("/api/v1/deals/aurelius-systems")

    assert resp.status_code == 200
    assert resp.json()["id"] == "prop_latest"
    assert resp.json()["canonical_alias"] == "aurelius-systems"
    mock_resolve.assert_called_once_with(
        opportunity_id="opp_horizons_rooftop_001",
        campaign_id="camp_aurelius_001",
    )


def test_canonical_alias_approval_writes_against_resolved_proposal():
    fake = _fake_ch_client(
        ("prop_latest", "opp_horizons_rooftop_001", "camp_aurelius_001", 219000.0, "horizons")
    )
    with patch(
        "cineyield.routers.v1.deals.get_settings", return_value=_mock_settings(True)
    ), patch(
        "cineyield.db.repository.get_latest_proposal_id", return_value="prop_latest"
    ), patch(
        "cineyield.db.client.get_clickhouse_client", return_value=fake
    ), patch(
        "cineyield.db.repository.get_proposal", return_value={"is_approved": False}
    ), patch("cineyield.db.repository.approve_proposal") as mock_approve, patch(
        "cineyield.db.repository.write_revenue_event", return_value="rev_alias"
    ), patch("cineyield.db.repository.write_agent_event"):
        resp = client.post(
            "/api/v1/deals/aurelius-systems/approve",
            json={"approved": True, "approver": "producer"},
        )

    assert resp.status_code == 200
    assert resp.json()["deal_id"] == "prop_latest"
    mock_approve.assert_called_once_with("prop_latest")


def test_counter_decision_persists_workflow_and_audit_event():
    proposal = {
        "id": "prop_counter",
        "opportunity_id": "opp_1",
        "campaign_id": "camp_1",
        "is_approved": False,
    }
    with patch(
        "cineyield.routers.v1.deals.get_settings", return_value=_mock_settings(True)
    ), patch(
        "cineyield.db.repository.get_proposal", return_value=proposal
    ), patch(
        "cineyield.db.repository.set_proposal_workflow_state"
    ) as mock_state, patch(
        "cineyield.db.repository.write_agent_event"
    ) as mock_event:
        resp = client.post(
            "/api/v1/deals/prop_counter/decision",
            json={
                "action": "counter",
                "approver": "producer",
                "note": "Raise fee to $225K",
            },
        )

    assert resp.status_code == 200
    assert resp.json()["workflow_state"] == "COUNTERED"
    mock_state.assert_called_once_with("prop_counter", "COUNTERED")
    assert mock_event.call_args.kwargs["kind"] == "counter"


def test_counter_requires_a_producer_note():
    with patch(
        "cineyield.routers.v1.deals.get_settings", return_value=_mock_settings(True)
    ), patch(
        "cineyield.db.repository.get_proposal",
        return_value={"id": "prop_counter", "opportunity_id": "opp_1", "campaign_id": "camp_1"},
    ):
        resp = client.post(
            "/api/v1/deals/prop_counter/decision",
            json={"action": "counter", "approver": "producer", "note": ""},
        )

    assert resp.status_code == 422
    assert "note" in resp.json()["detail"].lower()


def test_list_deals_uses_persisted_latest_proposals():
    items = [{"id": "prop_1", "status": "PRODUCER_REVIEW"}]
    with patch(
        "cineyield.routers.v1.deals.get_settings", return_value=_mock_settings(True)
    ), patch(
        "cineyield.db.repository.list_proposals", return_value=items
    ) as mock_list:
        resp = client.get("/api/v1/deals?limit=25")

    assert resp.status_code == 200
    assert resp.json() == {"items": items, "total": 1}
    mock_list.assert_called_once_with(limit=25)
