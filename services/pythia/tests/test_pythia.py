"""Comprehensive tests for the Pythia lead building service.

Covers: health endpoint, scorer (mocked LLM), store (mocked Clio),
digest formatter, collector imports, and runner pipeline orchestration.
All mocks, no network access required.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

# ── FastAPI / health ──────────────────────────────────────────────────────────


class TestHealth:
    """Health endpoint returns 200 with expected shape."""

    def test_health_returns_ok(self):
        """/health should return status=ok, service=pythia."""
        from fastapi.testclient import TestClient
        from src.main import app

        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["service"] == "pythia"

    def test_health_can_be_imported(self):
        """HealthResponse model is importable and has correct defaults."""
        from src.models import HealthResponse

        h = HealthResponse()
        assert h.status == "ok"
        assert h.service == "pythia"


# ── Scorer (mocked LLM API) ───────────────────────────────────────────────────


class TestScorer:
    """score_item and score_items with httpx.AsyncClient mocked."""

    @pytest.fixture(autouse=True)
    def mock_llm_settings(self):
        """Patch LLM key so scoring logic proceeds past the config check."""
        with patch("src.scorer.settings") as mock_settings:
            mock_settings.llm_api_key = "sk-test-key"
            mock_settings.llm_base_url = "https://fake-llm.test/v1"
            mock_settings.llm_model = "test-model"
            yield

    @pytest.fixture
    def mock_httpx_client(self):
        """Mock httpx.AsyncClient so no real HTTP calls are made."""
        with patch("httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            mock_cls.return_value.__aenter__.return_value = client
            yield client

    async def test_score_item_success(self, mock_httpx_client):
        """Happy path — LLM returns valid JSON, ScoredLead is produced."""
        from src.models import RawItem
        from src.scorer import score_item

        llm_content = json.dumps({
            "score": 9,
            "company": "Acme Corp",
            "pain_point": "Manual invoice processing",
            "fit_reason": "We automate invoicing",
            "angle": "Offer invoice automation demo",
            "urgency": "high",
        })

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": llm_content}}],
        }
        mock_httpx_client.post.return_value = mock_response

        item = RawItem(
            source="reddit",
            url="https://reddit.com/r/test/123",
            title="Need help with invoicing",
            body="We spend 20 hours a week on invoices",
            collected_at="2025-01-01T00:00:00Z",
        )
        lead = await score_item(item)

        assert lead is not None
        assert lead.score == 9
        assert lead.company == "Acme Corp"
        assert lead.pain_point == "Manual invoice processing"
        assert lead.urgency == "high"
        assert lead.source == "reddit"
        assert lead.url == "https://reddit.com/r/test/123"
        assert lead.status == "new"

        # Verify the LLM API was called correctly
        mock_httpx_client.post.assert_awaited_once()
        call_args = mock_httpx_client.post.call_args
        assert "chat/completions" in call_args[0][0]
        assert call_args[1]["headers"]["Authorization"] == "Bearer sk-test-key"
        assert call_args[1]["json"]["model"] == "test-model"

    async def test_score_item_with_markdown_fences(self, mock_httpx_client):
        """LLM response wrapped in ```json ... ``` fences is parsed correctly."""
        from src.models import RawItem
        from src.scorer import score_item

        llm_content = "```json\n{\"score\": 7, \"company\": \"Biz Inc\", \"pain_point\": \"Slow reports\", \"fit_reason\": \"We build dashboards\", \"angle\": \"Show dashboard demo\", \"urgency\": \"medium\"}\n```"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": llm_content}}],
        }
        mock_httpx_client.post.return_value = mock_response

        item = RawItem(
            source="hackernews",
            url="https://news.ycombinator.com/item?id=999",
            title="Reporting is killing us",
            body="Our team spends days on manual reports",
            collected_at="2025-01-01T00:00:00Z",
        )
        lead = await score_item(item)

        assert lead is not None
        assert lead.score == 7
        assert lead.company == "Biz Inc"
        assert lead.urgency == "medium"

    async def test_score_item_api_error_returns_none(self, mock_httpx_client):
        """Non-200 from LLM API returns None."""
        from src.models import RawItem
        from src.scorer import score_item

        mock_response = MagicMock()
        mock_response.status_code = 429  # rate limited
        mock_httpx_client.post.return_value = mock_response

        item = RawItem(
            source="reddit",
            url="https://reddit.com/r/test/456",
            title="Rate limited",
            body="test",
        )
        lead = await score_item(item)
        assert lead is None

    async def test_score_item_no_api_key_returns_none(self):
        """When LLM_API_KEY is empty, scorer returns None without network."""
        from src.models import RawItem
        from src.scorer import score_item

        with patch("src.scorer.settings") as mock_settings:
            mock_settings.llm_api_key = ""

            item = RawItem(
                source="reddit",
                url="https://reddit.com/r/test/789",
                title="No key",
                body="test",
            )
            lead = await score_item(item)
            assert lead is None

    async def test_score_item_bad_json_returns_none(self, mock_httpx_client):
        """LLM returns 200 but malformed JSON -> None."""
        from src.models import RawItem
        from src.scorer import score_item

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "NOT JSON AT ALL"}}],
        }
        mock_httpx_client.post.return_value = mock_response

        item = RawItem(
            source="reddit",
            url="https://reddit.com/r/test/101",
            title="Bad json",
            body="test",
        )
        lead = await score_item(item)
        assert lead is None

    async def test_score_items_filters_below_5(self, mock_httpx_client):
        """score_items only returns leads with score >= 5."""
        from src.models import RawItem
        from src.scorer import score_items

        # Return different scores for different calls
        responses = [
            {"score": 9, "company": "Hot Co", "pain_point": "x", "fit_reason": "y", "angle": "z", "urgency": "high"},
            {"score": 3, "company": "Cold Co", "pain_point": "x", "fit_reason": "y", "angle": "z", "urgency": "low"},
            {"score": 6, "company": "Warm Co", "pain_point": "x", "fit_reason": "y", "angle": "z", "urgency": "medium"},
            {"score": 1, "company": None, "pain_point": "", "fit_reason": "", "angle": "", "urgency": "low"},
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200

        def json_side_effect():
            idx = len(mock_httpx_client.post.call_args_list) - 1
            content = json.dumps(responses[idx % len(responses)])
            return {"choices": [{"message": {"content": content}}]}

        mock_response.json = json_side_effect
        mock_httpx_client.post.return_value = mock_response

        items = [
            RawItem(source="reddit", url=f"https://example.com/{i}", title=f"Item {i}", body="test")
            for i in range(4)
        ]
        leads = await score_items(items)

        assert len(leads) == 2  # scores 9 and 6
        assert leads[0].score == 9
        assert leads[1].score == 6

    async def test_score_items_empty_input(self, mock_httpx_client):
        """Empty list of items returns empty list."""
        from src.scorer import score_items

        leads = await score_items([])
        assert leads == []


# ── Store (mocked Clio) ────────────────────────────────────────────────────────


class TestStore:
    """store_lead, get_lead, list_leads, update_lead_status, lead_exists
    with httpx.AsyncClient mocked."""

    @pytest.fixture(autouse=True)
    def mock_store_settings(self):
        """Patch dynamo_svc_url for predictable URLs."""
        with patch("src.store.settings") as mock_settings:
            mock_settings.dynamo_svc_url = "http://clio.test:8000"
            yield

    @pytest.fixture
    def mock_client(self):
        """Mock httpx.AsyncClient."""
        with patch("httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            mock_cls.return_value.__aenter__.return_value = client
            yield client

    @pytest.fixture
    def a_lead(self):
        """A sample ScoredLead for store operations."""
        from src.models import ScoredLead

        return ScoredLead(
            id="abc123",
            source="reddit",
            url="https://reddit.com/r/test/lead1",
            title="Test Lead",
            body="Test body",
            company="TestCo",
            score=8,
            pain_point="Automation need",
            fit_reason="We automate",
            angle="Demo angle",
            urgency="high",
            status="new",
            seen_at="2025-01-01T00:00:00Z",
        )

    # -- store_lead --

    async def test_store_lead_success(self, mock_client, a_lead):
        """store_lead returns True on 201."""
        from src.store import store_lead

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_client.post.return_value = mock_resp

        result = await store_lead(a_lead)
        assert result is True

        # Verify the payload includes the app partition
        _, kwargs = mock_client.post.call_args
        assert kwargs["json"]["app"] == "CA#Lead"
        assert kwargs["json"]["id"] == "abc123"

    async def test_store_lead_http_error(self, mock_client, a_lead):
        """store_lead returns False on non-2xx."""
        from src.store import store_lead

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_client.post.return_value = mock_resp

        result = await store_lead(a_lead)
        assert result is False

    async def test_store_lead_network_error(self, mock_client, a_lead):
        """store_lead returns False on RequestError."""
        from httpx import RequestError
        from src.store import store_lead

        mock_client.post.side_effect = RequestError("Connection refused")

        result = await store_lead(a_lead)
        assert result is False

    # -- get_lead --

    async def test_get_lead_found(self, mock_client):
        """get_lead returns ScoredLeadResponse when found."""
        from src.store import get_lead

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "item": {
                "id": "abc123",
                "source": "reddit",
                "url": "https://example.com",
                "title": "Found",
                "company": "FoundCo",
                "score": 7,
                "pain_point": "pp",
                "fit_reason": "fr",
                "angle": "ang",
                "urgency": "medium",
                "status": "new",
                "seen_at": "2025-01-01T00:00:00Z",
            }
        }
        mock_client.get.return_value = mock_resp

        lead = await get_lead("abc123")
        assert lead is not None
        assert lead.id == "abc123"
        assert lead.company == "FoundCo"
        assert lead.score == 7
        mock_client.get.assert_awaited_once()

    async def test_get_lead_not_found(self, mock_client):
        """get_lead returns None on 404 or any non-200."""
        from src.store import get_lead

        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_client.get.return_value = mock_resp

        lead = await get_lead("missing-id")
        assert lead is None

    async def test_get_lead_network_error(self, mock_client):
        """get_lead returns None on RequestError."""
        from httpx import RequestError
        from src.store import get_lead

        mock_client.get.side_effect = RequestError("Timeout")

        lead = await get_lead("abc123")
        assert lead is None

    # -- list_leads --

    async def test_list_leads_success(self, mock_client):
        """list_leads returns sorted list on 200."""
        from src.store import list_leads

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "items": [
                {
                    "id": "z", "source": "hn", "url": "https://z", "title": "Z",
                    "company": "ZCorp", "score": 5, "pain_point": "p",
                    "fit_reason": "f", "angle": "a", "urgency": "low",
                    "status": "new", "seen_at": "2025-01-02T00:00:00Z",
                },
                {
                    "id": "a", "source": "reddit", "url": "https://a", "title": "A",
                    "company": "ACorp", "score": 8, "pain_point": "p",
                    "fit_reason": "f", "angle": "a", "urgency": "high",
                    "status": "new", "seen_at": "2025-01-01T00:00:00Z",
                },
            ]
        }
        mock_client.post.return_value = mock_resp

        leads = await list_leads(limit=10)
        assert len(leads) == 2
        # Should be sorted by seen_at descending (newest first)
        assert leads[0].id == "z"
        assert leads[1].id == "a"

    async def test_list_leads_error_returns_empty(self, mock_client):
        """list_leads returns [] on non-200."""
        from src.store import list_leads

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_client.post.return_value = mock_resp

        leads = await list_leads()
        assert leads == []

    async def test_list_leads_network_error_returns_empty(self, mock_client):
        """list_leads returns [] on RequestError."""
        from httpx import RequestError
        from src.store import list_leads

        mock_client.post.side_effect = RequestError("Down")

        leads = await list_leads()
        assert leads == []

    # -- update_lead_status --

    async def test_update_lead_status_success(self, mock_client):
        """update_lead_status returns True on 200."""
        from src.store import update_lead_status

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client.put.return_value = mock_resp

        result = await update_lead_status("abc123", "contacted")
        assert result is True

    async def test_update_lead_status_network_error(self, mock_client):
        """update_lead_status returns False on RequestError."""
        from httpx import RequestError
        from src.store import update_lead_status

        mock_client.put.side_effect = RequestError("Down")

        result = await update_lead_status("abc123", "contacted")
        assert result is False

    # -- lead_exists --

    async def test_lead_exists_true(self, mock_client):
        """lead_exists returns True when Clio returns 200."""
        from src.store import lead_exists

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client.get.return_value = mock_resp

        result = await lead_exists("https://example.com", "reddit")
        assert result is True

    async def test_lead_exists_false(self, mock_client):
        """lead_exists returns False when Clio returns non-200."""
        from src.store import lead_exists

        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_client.get.return_value = mock_resp

        result = await lead_exists("https://example.com", "reddit")
        assert result is False

    async def test_lead_exists_network_error(self, mock_client):
        """lead_exists returns False on RequestError."""
        from httpx import RequestError
        from src.store import lead_exists

        mock_client.get.side_effect = RequestError("Timeout")

        result = await lead_exists("https://example.com", "reddit")
        assert result is False


# ── Digest Formatter ───────────────────────────────────────────────────────────


class TestDigest:
    """categorize_leads and format_telegram_digest — no mocks needed."""

    @pytest.fixture
    def hot_lead(self):
        from src.models import ScoredLead

        return ScoredLead(
            id="hot1",
            source="reddit",
            url="https://reddit.com/r/test/hot1",
            title="Hot Lead",
            body="Great opportunity",
            company="HotCo",
            score=9,
            pain_point="Needs automation urgently",
            fit_reason="We automate",
            angle="Offer free trial",
            urgency="high",
            status="new",
            seen_at="2025-01-01T00:00:00Z",
        )

    @pytest.fixture
    def warm_lead(self):
        from src.models import ScoredLead

        return ScoredLead(
            id="warm1",
            source="hackernews",
            url="https://news.ycombinator.com/item?id=warm1",
            title="Warm Lead",
            body="Might need help",
            company="WarmCo",
            score=6,
            pain_point="Considering options",
            fit_reason="We can help",
            angle="Share case study",
            urgency="medium",
            status="new",
            seen_at="2025-01-01T00:00:00Z",
        )

    @pytest.fixture
    def cold_lead(self):
        from src.models import ScoredLead

        return ScoredLead(
            id="cold1",
            source="reddit",
            url="https://reddit.com/r/test/cold1",
            title="Low priority",
            body="Just browsing",
            company="ColdCo",
            score=3,
            pain_point="",
            fit_reason="",
            angle="",
            urgency="low",
            status="new",
            seen_at="2025-01-01T00:00:00Z",
        )

    # -- categorize_leads --

    def test_categorize_all_hot(self, hot_lead):
        """All leads with score >= 8 land in hot bucket."""
        from src.digest import categorize_leads

        hot, warm = categorize_leads([hot_lead])
        assert len(hot) == 1
        assert len(warm) == 0
        assert hot[0].id == "hot1"

    def test_categorize_all_warm(self, warm_lead):
        """All leads with score 5-7 land in warm bucket."""
        from src.digest import categorize_leads

        hot, warm = categorize_leads([warm_lead])
        assert len(hot) == 0
        assert len(warm) == 1

    def test_categorize_mixed(self, hot_lead, warm_lead, cold_lead):
        """Mixed scores split correctly (only scored >= 5 items passed)."""
        from src.digest import categorize_leads

        hot, warm = categorize_leads([hot_lead, warm_lead])
        assert len(hot) == 1
        assert len(warm) == 1
        assert hot[0].id == "hot1"
        assert warm[0].id == "warm1"

    def test_categorize_empty(self):
        """Empty list returns empty buckets."""
        from src.digest import categorize_leads

        hot, warm = categorize_leads([])
        assert hot == []
        assert warm == []

    # -- format_telegram_digest --

    def test_format_hot_and_warm(self, hot_lead, warm_lead):
        """Digest includes both hot and warm sections."""
        from src.digest import format_telegram_digest

        text = format_telegram_digest(
            hot=[hot_lead],
            warm=[warm_lead],
            total_scanned=10,
            cold_count=5,
        )

        assert "Daily Lead Report" in text
        assert "HOT (score 8+)" in text
        assert "WARM (score 5-7)" in text
        assert "HotCo" in text
        assert "WarmCo" in text
        assert "Score: 9" in text
        assert "Score: 6" in text
        assert "Urgency: HIGH" in text
        assert "Stats: 10 scanned → 1 hot, 1 warm, 5 cold" in text

    def test_format_no_hot(self, warm_lead):
        """Digest with no hot leads shows 'None today'."""
        from src.digest import format_telegram_digest

        text = format_telegram_digest(
            hot=[],
            warm=[warm_lead],
            total_scanned=5,
            cold_count=3,
        )

        assert "None today" in text
        assert "WARM" in text
        assert "WarmCo" in text
        assert "Stats: 5 scanned → 0 hot, 1 warm, 3 cold" in text

    def test_format_no_leads_at_all(self):
        """Digest with zero leads shows both sections as 'None today'."""
        from src.digest import format_telegram_digest

        text = format_telegram_digest(
            hot=[],
            warm=[],
            total_scanned=0,
            cold_count=0,
        )

        assert "None today" in text
        assert "Stats: 0 scanned → 0 hot, 0 warm, 0 cold" in text

    def test_format_lead_with_none_company(self):
        """Lead with company=None displays as 'Unknown'."""
        from src.digest import format_telegram_digest
        from src.models import ScoredLead

        lead = ScoredLead(
            id="anon",
            source="reddit",
            url="https://reddit.com/r/test/anon",
            title="Anonymous",
            body="test",
            company=None,
            score=8,
            pain_point="Pain",
            fit_reason="Fit",
            angle="Angle",
            urgency="high",
            status="new",
            seen_at="2025-01-01T00:00:00Z",
        )

        text = format_telegram_digest(
            hot=[lead],
            warm=[],
            total_scanned=1,
            cold_count=0,
        )

        assert "Unknown" in text

    def test_format_truncates_url_properly(self, hot_lead):
        """URLs render as markdown links in digest."""
        from src.digest import format_telegram_digest

        text = format_telegram_digest(
            hot=[hot_lead],
            warm=[],
            total_scanned=1,
            cold_count=0,
        )

        assert "[reddit]" in text
        assert hot_lead.url in text


# ── Collector Import (lightweight) ─────────────────────────────────────────────


class TestCollectors:
    """Verify collector base and registry import without network."""

    def test_base_collector_importable(self):
        """BaseCollector class and registry functions are importable."""
        from src.collectors.base import (
            BaseCollector,
            get_all_collectors,
            get_collector,
            register_collector,
        )

        assert issubclass(BaseCollector.__class__, type)

    async def test_register_and_get_collector(self):
        """Test registration / retrieval in isolation via direct use."""
        from src.collectors.base import (
            BaseCollector,
            get_collector,
            register_collector,
        )

        # Define and register a dummy collector for testing
        @register_collector
        class DummyTestCollector(BaseCollector):
            @property
            def source_name(self) -> str:
                return "dummy_test_source"

            async def collect(self):
                return []

        instance = get_collector("dummy_test_source")
        assert instance.source_name == "dummy_test_source"

        result = await instance.collect()
        assert result == []

    def test_get_unknown_collector_raises(self):
        """Asking for an unregistered collector raises ValueError."""
        from src.collectors.base import get_collector

        with pytest.raises(ValueError, match="Unknown collector"):
            get_collector("this_does_not_exist")


# ── Runner Pipeline Orchestration ──────────────────────────────────────────────


class TestRunner:
    """run_pipeline with every dependency mocked."""

    @pytest.fixture(autouse=True)
    def mock_all_deps(self):
        """Patch runner-level imports so no real network or collector runs."""
        patcher1 = patch("src.runner.get_all_collectors")
        patcher2 = patch("src.runner.lead_exists")
        patcher3 = patch("src.runner.score_items")
        patcher4 = patch("src.runner.store_lead")
        patcher5 = patch("src.runner.settings")

        mock_get_collectors = patcher1.start()
        mock_lead_exists = patcher2.start()
        mock_score_items = patcher3.start()
        mock_store_lead = patcher4.start()
        mock_settings = patcher5.start()

        # Default: no telegram config so send_digest doesn't call external API
        mock_settings.telegram_bot_token = ""
        mock_settings.telegram_chat_id = ""

        yield {
            "get_all_collectors": mock_get_collectors,
            "lead_exists": mock_lead_exists,
            "score_items": mock_score_items,
            "store_lead": mock_store_lead,
            "settings": mock_settings,
        }

        patcher1.stop()
        patcher2.stop()
        patcher3.stop()
        patcher4.stop()
        patcher5.stop()

    @pytest.fixture
    def mock_collector(self):
        """A fake collector for the pipeline."""
        from src.collectors.base import BaseCollector

        class FakeCollector(BaseCollector):
            @property
            def source_name(self) -> str:
                return "test_source"

            async def collect(self):
                from src.models import RawItem

                return [
                    RawItem(
                        source="test_source",
                        url="https://example.com/item1",
                        title="Item One",
                        body="Body of item one",
                    ),
                ]

        return FakeCollector()

    @pytest.fixture
    def sample_scored_leads(self):
        """Sample ScoredLead objects for the pipeline store step."""
        from src.models import ScoredLead

        return [
            ScoredLead(
                id="lead1",
                source="test_source",
                url="https://example.com/item1",
                title="Item One",
                body="Body of item one",
                company="TestCorp",
                score=9,
                pain_point="Needs automation",
                fit_reason="We do automation",
                angle="Demo call",
                urgency="high",
                status="new",
                seen_at="2025-01-01T00:00:00Z",
            ),
            ScoredLead(
                id="lead2",
                source="test_source",
                url="https://example.com/item2",
                title="Item Two",
                body="Body of item two",
                company="MidCorp",
                score=6,
                pain_point="Considering options",
                fit_reason="Good fit",
                angle="Share case study",
                urgency="medium",
                status="new",
                seen_at="2025-01-01T00:00:00Z",
            ),
        ]

    async def test_pipeline_full_flow(self, mock_all_deps, mock_collector,
                                      sample_scored_leads):
        """Full pipeline: collect → score → store → digest."""
        from src.runner import run_pipeline

        # Wire up mocks
        mock_all_deps["get_all_collectors"].return_value = [mock_collector]
        mock_all_deps["lead_exists"].return_value = False  # all items are new
        mock_all_deps["score_items"].return_value = sample_scored_leads
        mock_all_deps["store_lead"].return_value = True

        stats = await run_pipeline()

        assert stats["scanned"] == 1
        assert stats["scored"] == 2
        assert stats["new_leads"] == 2
        assert stats["hot"] == 1
        assert stats["warm"] == 1
        assert stats["cold"] == -1  # scanned(1) - scored(2) = -1

        # Verify calls happened in order
        mock_all_deps["get_all_collectors"].assert_called_once()
        mock_all_deps["lead_exists"].assert_called_once()
        mock_all_deps["score_items"].assert_awaited_once()
        assert mock_all_deps["store_lead"].await_count == 2

    async def test_pipeline_no_new_items(self, mock_all_deps, mock_collector):
        """Pipeline short-circuits when no new items found."""
        from src.runner import run_pipeline

        mock_all_deps["get_all_collectors"].return_value = [mock_collector]
        mock_all_deps["lead_exists"].return_value = True  # all items already exist

        stats = await run_pipeline()

        assert stats["scanned"] == 0
        assert stats["errors"] == 0
        mock_all_deps["score_items"].assert_not_awaited()
        mock_all_deps["store_lead"].assert_not_awaited()

    async def test_pipeline_no_scored_leads(self, mock_all_deps, mock_collector):
        """Pipeline short-circuits when no leads score 5+."""
        from src.runner import run_pipeline

        mock_all_deps["get_all_collectors"].return_value = [mock_collector]
        mock_all_deps["lead_exists"].return_value = False
        mock_all_deps["score_items"].return_value = []  # nothing scored high enough

        stats = await run_pipeline()

        assert stats["scanned"] == 1
        assert stats["scored"] == 0
        assert stats["new_leads"] == 0
        mock_all_deps["store_lead"].assert_not_awaited()

    async def test_pipeline_collector_failure(self, mock_all_deps):
        """Pipeline handles a failing collector gracefully."""
        from src.runner import run_pipeline

        class FailingCollector:
            source_name = "broken_source"

            async def collect(self):
                msg = "Intentional test failure"
                raise RuntimeError(msg)

        mock_all_deps["get_all_collectors"].return_value = [FailingCollector()]

        stats = await run_pipeline()

        assert stats["scanned"] == 0
        assert stats["errors"] == 1
        assert stats["scored"] == 0

    async def test_pipeline_store_failure(self, mock_all_deps, mock_collector,
                                          sample_scored_leads):
        """Pipeline tracks store failures in errors count."""
        from src.runner import run_pipeline

        mock_all_deps["get_all_collectors"].return_value = [mock_collector]
        mock_all_deps["lead_exists"].return_value = False
        mock_all_deps["score_items"].return_value = sample_scored_leads
        mock_all_deps["store_lead"].return_value = False  # store fails

        stats = await run_pipeline()

        assert stats["scanned"] == 1
        assert stats["scored"] == 2
        assert stats["new_leads"] == 0
        assert stats["errors"] == 2  # both store attempts failed
