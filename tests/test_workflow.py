"""Tests for the workflow module — node logic without LLM calls."""

from unittest.mock import patch, MagicMock

import pytest

from app.models import ComfortState
from app.nodes.fetch_news import fetch_hot_news, _format_date_human_friendly
from app.nodes.generate_feeling import generate_feeling
from app.nodes.generate_comfort import generate_comfort
from app.nodes.generate_animation import generate_animation
from app.workflow import build_graph


class TestComfortState:
    """Tests for the ComfortState Pydantic model."""

    def test_default_state(self):
        state = ComfortState()
        assert state.hot_news == ""
        assert state.feeling == ""
        assert state.comfort == ""

    def test_state_with_values(self):
        state = ComfortState(
            hot_news="Test news",
            feeling="Test feeling",
            comfort="Test comfort",
            animation="/animation_12345.html",
        )
        assert state.hot_news == "Test news"
        assert state.feeling == "Test feeling"
        assert state.comfort == "Test comfort"
        assert state.animation == "/animation_12345.html"

    def test_state_default_animation_empty(self):
        """Default animation field should be empty string."""
        state = ComfortState()
        assert state.animation == ""


class TestFormatDateFriendly:
    """Tests for the _format_date_human_friendly helper function."""

    def test_standard_serpapi_format(self):
        """Standard SerpApi format 'Wed, 15 Jul 2026 10:01:40 GMT' should parse."""
        result = _format_date_human_friendly("Wed, 15 Jul 2026 10:01:40 GMT")
        assert result == "2026年7月15日 星期三"

    def test_us_date_with_am_pm(self):
        """US date format '07/13/2026, 08:08 AM, +0000 UTC' should parse."""
        result = _format_date_human_friendly("07/13/2026, 08:08 AM, +0000 UTC")
        assert result == "2026年7月13日 星期一"

    def test_us_date_with_pm(self):
        """US date with PM should parse correctly."""
        result = _format_date_human_friendly("07/13/2026, 02:30 PM, +0800 HKT")
        assert result == "2026年7月13日 星期一"

    def test_iso_date_format(self):
        """ISO format '2026-07-15' should parse."""
        result = _format_date_human_friendly("2026-07-15")
        assert result == "2026年7月15日 星期三"

    def test_iso_datetime_format(self):
        """ISO datetime '2026-07-15 10:01:40' should parse."""
        result = _format_date_human_friendly("2026-07-15 10:01:40")
        assert result == "2026年7月15日 星期三"

    def test_weekday_names_traditional_chinese(self):
        """Weekday names must be in Traditional Chinese."""
        assert "星期一" in _format_date_human_friendly("Mon, 01 Jan 2024 00:00:00 GMT")

    def test_empty_input(self):
        """Empty string should return '未知'."""
        assert _format_date_human_friendly("") == "未知"

    def test_unknown_input(self):
        """'Unknown' string should return '未知'."""
        assert _format_date_human_friendly("Unknown") == "未知"

    def test_unparseable_format(self):
        """Unparseable string should return the original string."""
        assert _format_date_human_friendly("not-a-date") == "not-a-date"

    def test_none_input(self):
        """None-like falsy input should return '未知'."""
        assert _format_date_human_friendly(None) == "未知"  # type: ignore[arg-type]


class TestFetchHotNews:
    """Tests for the fetch_hot_news node (SerpApi Google News search)."""

    MOCK_SEARCH_RESPONSE = {
        "news_results": [
            {
                "title": "Hong Kong Weather Update",
                "source": {"name": "Reuters", "icon": ""},
                "date": "07/13/2026, 08:08 AM, +0000 UTC",
                "link": "http://example.com/article1",
            },
            {
                "title": "HK Economy Report",
                "source": {"name": "SCMP", "icon": ""},
                "date": "07/13/2026, 09:00 AM, +0000 UTC",
                "link": "http://example.com/article2",
            },
        ],
    }

    @patch("app.nodes.fetch_news.serpapi")
    def test_fetches_and_formats_news(self, mock_serpapi_mod):
        """Node should search SerpApi Google News, and format an HTML summary with clickable titles."""
        mock_client = MagicMock()
        mock_client.search.return_value = self.MOCK_SEARCH_RESPONSE
        mock_serpapi_mod.Client.return_value = mock_client

        result = fetch_hot_news(ComfortState())

        assert "hot_news" in result
        assert "Hong Kong Weather Update" in result["hot_news"]
        assert "HK Economy Report" in result["hot_news"]
        # News should be wrapped in a <ul> bullet list
        assert "<ul class=\"news-list\">" in result["hot_news"]
        assert "</ul>" in result["hot_news"]
        # Source names appear inside <span class="news-meta"> with bullet separator
        assert '<span class="news-meta">Reuters ·' in result["hot_news"]
        assert '<span class="news-meta">SCMP ·' in result["hot_news"]
        # Titles should be wrapped in <a> tags with href to the article
        assert '<a href="http://example.com/article1"' in result["hot_news"]
        assert '<a href="http://example.com/article2"' in result["hot_news"]
        # The Link: prefix should NOT be present (URL is in the href instead)
        assert "Link:" not in result["hot_news"]

    @patch("app.nodes.fetch_news.serpapi")
    def test_uses_correct_serpapi_parameters(self, mock_serpapi_mod):
        """Node should use engine=google_news with gl=hk and tbs=qdr:d."""
        mock_client = MagicMock()
        mock_client.search.return_value = self.MOCK_SEARCH_RESPONSE
        mock_serpapi_mod.Client.return_value = mock_client

        fetch_hot_news(ComfortState())

        call_kwargs = mock_client.search.call_args[0][0]
        assert call_kwargs["engine"] == "google_news"
        assert call_kwargs["q"] == "香港"
        assert call_kwargs["gl"] == "hk"
        assert call_kwargs["tbs"] == "qdr:d"
        # hl must NOT be present (zh-Hant is an unsupported SerpApi interface language)
        assert "hl" not in call_kwargs

    @patch("app.nodes.fetch_news.serpapi")
    def test_handles_no_search_results(self, mock_serpapi_mod):
        """Node should return a message when SerpApi returns no articles."""
        mock_client = MagicMock()
        mock_client.search.return_value = {"news_results": []}
        mock_serpapi_mod.Client.return_value = mock_client

        result = fetch_hot_news(ComfortState())
        assert "(No news articles found.)" in result["hot_news"]

    @patch("app.nodes.fetch_news.serpapi")
    def test_handles_serpapi_error(self, mock_serpapi_mod):
        """Node should return an error message when SerpApi search fails."""
        mock_client = MagicMock()
        mock_client.search.side_effect = Exception("API rate limited")
        mock_serpapi_mod.Client.return_value = mock_client

        result = fetch_hot_news(ComfortState())
        assert "Error fetching news" in result["hot_news"]

    @patch("app.nodes.fetch_news.serpapi")
    def test_skips_unfinished_articles(self, mock_serpapi_mod):
        """Node should skip articles with missing/empty titles (malformed responses)."""
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "news_results": [
                {
                    "title": "Valid Article",
                    "source": {"name": "Reuters"},
                    "date": "07/13/2026",
                    "link": "http://example.com/valid",
                },
                {
                    "title": "Untitled",
                    "source": {"name": "Unknown"},
                    "date": "07/13/2026",
                    "link": "http://example.com/untilted",
                },
                {
                    "title": "",
                    "source": {"name": "Unknown"},
                    "date": "07/13/2026",
                    "link": "http://example.com/empty",
                },
            ]
        }
        mock_serpapi_mod.Client.return_value = mock_client

        result = fetch_hot_news(ComfortState())
        assert "Valid Article" in result["hot_news"]
        assert "Untitled" not in result["hot_news"]
        # Empty-title articles should not appear either
        assert "http://example.com/empty" not in result["hot_news"]
        # "Valid Article" link should still be present
        assert '<a href="http://example.com/valid"' in result["hot_news"]

    @patch("app.nodes.fetch_news.serpapi")
    def test_returns_message_when_all_articles_skipped(self, mock_serpapi_mod):
        """Node should return a message when all articles have missing/invalid titles."""
        mock_client = MagicMock()
        mock_client.search.return_value = {
            "news_results": [
                {
                    "title": "Untitled",
                    "source": {"name": "Unknown"},
                    "date": "07/13/2026",
                    "link": "http://example.com/1",
                },
                {
                    "title": "",
                    "source": {"name": "Unknown"},
                    "date": "07/13/2026",
                    "link": "http://example.com/2",
                },
            ]
        }
        mock_serpapi_mod.Client.return_value = mock_client

        result = fetch_hot_news(ComfortState())
        assert "missing or invalid titles" in result["hot_news"]


class TestGenerateFeeling:
    """Tests for the generate_feeling node."""

    @pytest.mark.asyncio
    async def test_calls_llm_with_correct_prompt(self):
        """Node should invoke LLM with the Hong Kong resident prompt and news context.

        Uses model.astream() (async) so on_chat_model_stream events are emitted.
        """
        state = ComfortState(hot_news="Test news article here")

        with patch("app.nodes.generate_feeling.ChatOpenAI") as mock_llm_cls:
            mock_llm_instance = MagicMock()
            mock_llm_cls.return_value = mock_llm_instance

            # Mock astream() to return an async generator yielding token chunks
            async def mock_astream(messages):
                from unittest.mock import MagicMock
                mock_response = MagicMock()
                mock_response.content = "我好憂慮香港的前景。"
                yield mock_response

            mock_llm_instance.astream = mock_astream

            result = await generate_feeling(state)

            assert result["feeling"] == "我好憂慮香港的前景。"

    @pytest.mark.asyncio
    async def test_handles_llm_error(self):
        """Node should return an error message when the LLM call fails."""
        state = ComfortState(hot_news="Test news")

        with patch("app.nodes.generate_feeling.ChatOpenAI") as mock_llm_cls:
            mock_llm_instance = MagicMock()
            mock_llm_cls.return_value = mock_llm_instance

            async def mock_astream_error(messages):
                raise ConnectionError("Timeout")
                yield  # never reached

            mock_llm_instance.astream = mock_astream_error

            result = await generate_feeling(state)
            assert "Error generating feeling" in result["feeling"]


class TestGenerateComfort:
    """Tests for the generate_comfort node."""

    @pytest.mark.asyncio
    async def test_calls_llm_with_correct_prompt(self):
        """Node should invoke LLM with the pastoral prompt and feeling context.

        Uses model.astream() (async) so on_chat_model_stream events are emitted.
        """
        state = ComfortState(feeling="我好憂慮香港的前景。")

        with patch("app.nodes.generate_comfort.ChatOpenAI") as mock_llm_cls:
            mock_llm_instance = MagicMock()
            mock_llm_cls.return_value = mock_llm_instance

            async def mock_astream(messages):
                from unittest.mock import MagicMock
                mock_response = MagicMock()
                mock_response.content = "不要怕，只要信。聖經說：'耶和華是我的牧者，我必不至缺乏。'"
                yield mock_response

            mock_llm_instance.astream = mock_astream

            result = await generate_comfort(state)

            assert result["comfort"] == "不要怕，只要信。聖經說：'耶和華是我的牧者，我必不至缺乏。'"

    @pytest.mark.asyncio
    async def test_handles_llm_error(self):
        """Node should return an error message when the LLM call fails."""
        state = ComfortState(feeling="Test feeling")

        with patch("app.nodes.generate_comfort.ChatOpenAI") as mock_llm_cls:
            mock_llm_instance = MagicMock()
            mock_llm_cls.return_value = mock_llm_instance

            async def mock_astream_error(messages):
                raise ValueError("Invalid model")
                yield  # never reached

            mock_llm_instance.astream = mock_astream_error

            result = await generate_comfort(state)
            assert "Error generating comfort" in result["comfort"]


class TestGenerateAnimation:
    """Tests for the generate_animation node."""

    @pytest.mark.asyncio
    async def test_calls_llm_with_comfort_context(self):
        """Node should invoke LLM with the comfort message context.

        Uses model.ainvoke() (async) — the animation node does not stream.
        """
        state = ComfortState(comfort="May you find peace in these difficult times.")

        with patch("app.nodes.generate_animation.ChatOpenAI") as mock_llm_cls:
            mock_llm_instance = MagicMock()
            mock_llm_cls.return_value = mock_llm_instance

            mock_response = MagicMock()
            mock_response.content = "<html><body>Animation</body></html>"

            async def mock_ainvoke(messages):
                return mock_response

            mock_llm_instance.ainvoke = mock_ainvoke

            result = await generate_animation(state)

            assert "animation" in result
            assert "Error" not in result["animation"]

    @pytest.mark.asyncio
    async def test_handles_llm_error(self):
        """Node should return an error message when the LLM call fails."""
        state = ComfortState(comfort="Test comfort")

        with patch("app.nodes.generate_animation.ChatOpenAI") as mock_llm_cls:
            mock_llm_instance = MagicMock()
            mock_llm_cls.return_value = mock_llm_instance

            async def mock_ainvoke_error(messages):
                raise ConnectionError("Timeout")
                return None  # never reached

            mock_llm_instance.ainvoke = mock_ainvoke_error

            result = await generate_animation(state)
            assert "Error generating animation" in result["animation"]


class TestSaveHtml:
    """Tests for the _save_html helper that saves animation HTML to disk."""

    def test_returns_url_with_static_prefix(self, tmp_path):
        """_save_html must return a URL prefixed with /static/ so FastAPI can serve it."""
        from app.nodes.generate_animation import _save_html

        result = _save_html("<html></html>", str(tmp_path), 1784077886)
        assert result == "/static/animation_1784077886.html"
        assert not result.startswith("/animation_")

    def test_saves_html_to_file(self, tmp_path):
        """_save_html must write the HTML content to the static directory."""
        from app.nodes.generate_animation import _save_html

        html_content = "<html><body>test</body></html>"
        result = _save_html(html_content, str(tmp_path), 1234567890)

        expected_path = tmp_path / "animation_1234567890.html"
        assert expected_path.exists()
        assert expected_path.read_text(encoding="utf-8") == html_content

    def test_url_matches_saved_filename(self, tmp_path):
        """The returned URL path must correspond to an actual file on disk."""
        from app.nodes.generate_animation import _save_html

        result = _save_html("<html></html>", str(tmp_path), 999999999)
        filename = result.replace("/static/", "")
        saved_path = tmp_path / filename
        assert saved_path.exists()


class TestBuildGraph:
    """Tests for the graph compilation."""

    def test_graph_is_compilable(self):
        """build_graph should return a compiled LangGraph Runnable."""
        graph = build_graph()
        assert graph is not None
        # Compiled graphs have an invoke method
        assert hasattr(graph, "invoke")

    def test_graph_topology_includes_animation(self):
        """build_graph should include the generate_animation node."""
        graph = build_graph()
        graph_def = graph.get_graph()
        node_ids = list(graph_def.nodes.keys())
        assert "fetch_hot_news" in node_ids
        assert "generate_feeling" in node_ids
        assert "generate_comfort" in node_ids
        assert "generate_animation" in node_ids
