from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from llm_gallery.config import DEFAULT_PROMPTS, RuntimeConfig
from llm_gallery.web_rag import (
    GroundingResult,
    SearchHit,
    TavilySearchProvider,
    WebSearchError,
    build_grounded_prompt,
    filter_citations_for_prompt,
    include_domains_for_prompt,
    parse_tavily_search_response,
    prepare_grounding,
    rewrite_search_query,
    should_ground_prompt,
)


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


class _RecordingUrlopen:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.calls: list[tuple[object, object]] = []

    def __call__(self, req, timeout=None):
        self.calls.append((req, timeout))
        return _FakeResponse(self.payload)


class _FakeProvider:
    def __init__(self, citations: tuple[SearchHit, ...] | None = None) -> None:
        self.citations = citations or ()
        self.calls: list[tuple[str, str]] = []

    def search(self, query: str, *, topic: str, include_domains=()) -> tuple[SearchHit, ...]:
        self.calls.append((query, topic, tuple(include_domains)))
        return self.citations


class _FailingProvider:
    def search(self, query: str, *, topic: str, include_domains=()) -> tuple[SearchHit, ...]:
        del query, topic, include_domains
        raise WebSearchError("network down")


class WebRagTests(unittest.TestCase):
    def test_runtime_config_disables_web_rag_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "example.gguf"
            model_path.touch()
            config = RuntimeConfig.from_sources(
                model=str(model_path),
                env={},
                cwd=None,
            )
        self.assertEqual(config.web_rag_mode, "off")

    def test_default_live_verifier_prompts_do_not_trigger_grounding(self) -> None:
        for prompt in DEFAULT_PROMPTS:
            self.assertFalse(should_ground_prompt(prompt))

    def test_fresh_prompt_triggers_grounding(self) -> None:
        self.assertTrue(
            should_ground_prompt("What is the latest ROCm release and what changed today?")
        )

    def test_parse_tavily_response_filters_invalid_results(self) -> None:
        hits = parse_tavily_search_response(
            {
                "results": [
                    {
                        "title": "Example",
                        "url": "https://example.com/a",
                        "content": " Example   snippet ",
                    },
                    {
                        "title": "Missing content",
                        "url": "https://example.com/b",
                    },
                    "not-a-dict",
                ]
            }
        )
        self.assertEqual(
            hits,
            (
                SearchHit(
                    title="Example",
                    url="https://example.com/a",
                    snippet="Example snippet",
                ),
            ),
        )

    def test_build_grounded_prompt_includes_sources_and_question(self) -> None:
        prompt = build_grounded_prompt(
            "What happened today?",
            (
                SearchHit(
                    title="Source Title",
                    url="https://example.com/source",
                    snippet="Fresh details here.",
                ),
            ),
        )
        self.assertIn("Source 1: Source Title", prompt)
        self.assertIn("URL: https://example.com/source", prompt)
        self.assertIn("User question: What happened today?", prompt)

    def test_rocm_release_query_is_rewritten_and_domain_scoped(self) -> None:
        prompt = "What is the latest ROCm release?"
        self.assertEqual(
            rewrite_search_query(prompt),
            "AMD ROCm latest release history version official documentation",
        )
        self.assertEqual(
            include_domains_for_prompt(prompt),
            ("rocm.docs.amd.com", "rocmdocs.amd.com", "amd.com"),
        )

    def test_prepare_grounding_reports_missing_api_key(self) -> None:
        result = prepare_grounding(
            "What is the latest ROCm release?",
            history=(),
            web_rag_mode="auto",
            tavily_api_key=None,
            provider=None,
        )
        self.assertEqual(
            result,
            GroundingResult(
                status="missing_api_key",
                query="What is the latest ROCm release?",
                citations=(),
                grounded_prompt=None,
                detail=None,
            ),
        )

    def test_prepare_grounding_uses_provider_and_builds_grounded_prompt(self) -> None:
        provider = _FakeProvider(
            citations=(
                SearchHit(
                    title="Release Notes",
                    url="https://example.com/release",
                    snippet="ROCm 7.0 released.",
                ),
            )
        )
        result = prepare_grounding(
            "What is the latest ROCm release?",
            history=(),
            web_rag_mode="auto",
            tavily_api_key="tvly-test",
            provider=provider,
        )
        self.assertEqual(result.status, "used")
        self.assertEqual(
            provider.calls,
            [
                (
                    "AMD ROCm latest release history version official documentation",
                    "general",
                    ("rocm.docs.amd.com", "rocmdocs.amd.com", "amd.com"),
                )
            ],
        )
        self.assertIsNotNone(result.grounded_prompt)
        self.assertIn("https://example.com/release", result.grounded_prompt or "")

    def test_prepare_grounding_reports_no_results(self) -> None:
        result = prepare_grounding(
            "What is the latest ROCm release?",
            history=(),
            web_rag_mode="auto",
            tavily_api_key="tvly-test",
            provider=_FakeProvider(),
        )
        self.assertEqual(result.status, "no_results")
        self.assertEqual(result.citations, ())

    def test_irrelevant_rocm_results_are_filtered_out(self) -> None:
        result = prepare_grounding(
            "What is the latest ROCm release?",
            history=(),
            web_rag_mode="auto",
            tavily_api_key="tvly-test",
            provider=_FakeProvider(
                citations=(
                    SearchHit(
                        title="Intel launches processor",
                        url="https://videocardz.com/article",
                        snippet="CPU launch coverage",
                    ),
                )
            ),
        )
        self.assertEqual(result.status, "no_results")

    def test_prepare_grounding_reports_search_error(self) -> None:
        result = prepare_grounding(
            "What is the latest ROCm release?",
            history=(),
            web_rag_mode="auto",
            tavily_api_key="tvly-test",
            provider=_FailingProvider(),
        )
        self.assertEqual(result.status, "search_error")
        self.assertEqual(result.detail, "network down")

    def test_filter_citations_for_rocm_prompt_keeps_relevant_hits(self) -> None:
        citations = filter_citations_for_prompt(
            "What is the latest ROCm release?",
            (
                SearchHit(
                    title="Intel article",
                    url="https://example.com/a",
                    snippet="Nothing about the target product.",
                ),
                SearchHit(
                    title="ROCm 7.2.1 release notes",
                    url="https://rocm.docs.amd.com/en/docs-7.2.1/about/release-notes.html",
                    snippet="ROCm 7.2.1 release notes.",
                ),
            ),
        )
        self.assertEqual(len(citations), 1)
        self.assertIn("rocm.docs.amd.com", citations[0].url)

    def test_tavily_provider_posts_json_request(self) -> None:
        recorder = _RecordingUrlopen(
            {
                "results": [
                    {
                        "title": "Example",
                        "url": "https://example.com/a",
                        "content": "Snippet",
                    }
                ]
            }
        )
        provider = TavilySearchProvider(
            api_key="tvly-test",
            timeout_seconds=4.0,
            max_results=2,
            urlopen=recorder,
        )
        hits = provider.search("latest ROCm release", topic="news")
        self.assertEqual(len(hits), 1)
        req, timeout = recorder.calls[0]
        self.assertEqual(timeout, 4.0)
        self.assertEqual(req.full_url, "https://api.tavily.com/search")
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.headers["Authorization"], "Bearer tvly-test")
        self.assertEqual(req.headers["Content-type"], "application/json")
        payload = json.loads(req.data.decode("utf-8"))
        self.assertEqual(payload["query"], "latest ROCm release")
        self.assertEqual(payload["topic"], "news")
        self.assertEqual(payload["max_results"], 2)

    def test_tavily_provider_includes_domains_when_requested(self) -> None:
        recorder = _RecordingUrlopen({"results": []})
        provider = TavilySearchProvider(
            api_key="tvly-test",
            timeout_seconds=4.0,
            max_results=2,
            urlopen=recorder,
        )
        provider.search(
            "AMD ROCm latest release history version official documentation",
            topic="general",
            include_domains=("rocm.docs.amd.com", "amd.com"),
        )
        req, _timeout = recorder.calls[0]
        payload = json.loads(req.data.decode("utf-8"))
        self.assertEqual(payload["include_domains"], ["rocm.docs.amd.com", "amd.com"])


if __name__ == "__main__":
    unittest.main()
