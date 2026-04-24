from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import urlparse
from typing import Any, Callable, Mapping, Sequence
from urllib import error, request


TAVILY_SEARCH_URL = "https://api.tavily.com/search"
TRUSTED_ROCM_DOMAINS = (
    "rocm.docs.amd.com",
    "rocmdocs.amd.com",
    "amd.com",
)
EXPLICIT_WEB_CUES = (
    "search the web",
    "search online",
    "look up",
    "browse",
    "on the web",
    "online",
    "internet",
)
FRESHNESS_CUES = (
    "latest",
    "today",
    "current",
    "currently",
    "recent",
    "recently",
    "up to date",
    "new today",
    "breaking",
    "news",
    "release notes",
    "released",
    "version",
    "price",
    "weather",
    "score",
    "scores",
    "who won",
    "election",
)
NEWS_CUES = (
    "today",
    "recent",
    "breaking",
    "news",
    "score",
    "scores",
    "who won",
    "weather",
)
RELEASE_CUES = (
    "release",
    "release notes",
    "version",
    "versions",
    "history",
)


class WebSearchError(RuntimeError):
    """Raised when the web search provider cannot return usable results."""


@dataclass(frozen=True)
class SearchHit:
    title: str
    url: str
    snippet: str


@dataclass(frozen=True)
class GroundingResult:
    status: str
    query: str | None
    citations: tuple[SearchHit, ...]
    grounded_prompt: str | None
    detail: str | None = None

    @property
    def used(self) -> bool:
        return self.status == "used"


class TavilySearchProvider:
    def __init__(
        self,
        *,
        api_key: str,
        timeout_seconds: float,
        max_results: int,
        urlopen: Callable[..., Any] = request.urlopen,
    ) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._max_results = max_results
        self._urlopen = urlopen

    def search(
        self,
        query: str,
        *,
        topic: str,
        include_domains: Sequence[str] = (),
    ) -> tuple[SearchHit, ...]:
        payload = {
            "query": query,
            "topic": topic,
            "search_depth": "basic",
            "max_results": self._max_results,
            "include_answer": False,
            "include_raw_content": False,
        }
        if include_domains:
            payload["include_domains"] = list(include_domains)
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            TAVILY_SEARCH_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with self._urlopen(req, timeout=self._timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore").strip()
            raise WebSearchError(
                f"Tavily request failed with HTTP {exc.code}"
                + (f": {detail[:200]}" if detail else "")
            ) from exc
        except error.URLError as exc:
            raise WebSearchError(f"Tavily request failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise WebSearchError("Tavily request timed out") from exc

        try:
            response_payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise WebSearchError("Tavily returned invalid JSON") from exc
        return parse_tavily_search_response(response_payload)


def should_ground_prompt(prompt: str, history: Sequence[Mapping[str, str]] | None = None) -> bool:
    del history
    normalized = " ".join(prompt.lower().split())
    if not normalized:
        return False
    return any(cue in normalized for cue in EXPLICIT_WEB_CUES + FRESHNESS_CUES)


def _normalized_prompt(prompt: str) -> str:
    return " ".join(prompt.lower().split())


def is_rocm_release_query(prompt: str) -> bool:
    normalized = _normalized_prompt(prompt)
    return "rocm" in normalized and any(cue in normalized for cue in RELEASE_CUES + ("latest",))


def select_tavily_topic(prompt: str) -> str:
    normalized = " ".join(prompt.lower().split())
    if is_rocm_release_query(prompt):
        return "general"
    if any(cue in normalized for cue in NEWS_CUES):
        return "news"
    return "general"


def rewrite_search_query(prompt: str) -> str:
    normalized = _normalized_prompt(prompt)
    if is_rocm_release_query(prompt):
        return "AMD ROCm latest release history version official documentation"
    if "release notes" in normalized and "version" not in normalized:
        return f"{prompt.strip()} official documentation"
    return prompt.strip()


def include_domains_for_prompt(prompt: str) -> tuple[str, ...]:
    if is_rocm_release_query(prompt):
        return TRUSTED_ROCM_DOMAINS
    return ()


def parse_tavily_search_response(payload: Mapping[str, Any]) -> tuple[SearchHit, ...]:
    results = payload.get("results")
    if not isinstance(results, list):
        return ()

    hits: list[SearchHit] = []
    for item in results:
        if not isinstance(item, Mapping):
            continue
        url = str(item.get("url") or "").strip()
        title = str(item.get("title") or "").strip() or url
        snippet = str(item.get("content") or "").strip()
        if not url or not snippet:
            continue
        hits.append(
            SearchHit(
                title=title,
                url=url,
                snippet=" ".join(snippet.split()),
            )
        )
    return tuple(hits)


def _hit_host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _is_trusted_rocm_hit(hit: SearchHit) -> bool:
    host = _hit_host(hit.url)
    return any(host == domain or host.endswith(f".{domain}") for domain in TRUSTED_ROCM_DOMAINS)


def filter_citations_for_prompt(
    prompt: str,
    citations: Sequence[SearchHit],
) -> tuple[SearchHit, ...]:
    if is_rocm_release_query(prompt):
        filtered = []
        for hit in citations:
            haystack = f"{hit.title} {hit.snippet} {hit.url}".lower()
            if "rocm" not in haystack and not _is_trusted_rocm_hit(hit):
                continue
            filtered.append(hit)
        return tuple(filtered)
    return tuple(citations)


def build_grounded_prompt(prompt: str, citations: Sequence[SearchHit]) -> str:
    source_lines = []
    for index, citation in enumerate(citations, start=1):
        source_lines.append(f"Source {index}: {citation.title}")
        source_lines.append(f"URL: {citation.url}")
        source_lines.append(f"Snippet: {citation.snippet}")
    joined_sources = "\n".join(source_lines)
    return (
        "Use the web search evidence below when it is relevant to the user's request. "
        "If the evidence is insufficient, say so plainly.\n\n"
        f"{joined_sources}\n\n"
        f"User question: {prompt}"
    )


def prepare_grounding(
    prompt: str,
    *,
    history: Sequence[Mapping[str, str]] | None,
    web_rag_mode: str,
    tavily_api_key: str | None,
    provider: TavilySearchProvider | None,
) -> GroundingResult:
    if web_rag_mode == "off":
        return GroundingResult(
            status="disabled",
            query=None,
            citations=(),
            grounded_prompt=None,
        )

    if not should_ground_prompt(prompt, history):
        return GroundingResult(
            status="not_needed",
            query=None,
            citations=(),
            grounded_prompt=None,
        )

    query = prompt.strip()
    if not tavily_api_key or provider is None:
        return GroundingResult(
            status="missing_api_key",
            query=query,
            citations=(),
            grounded_prompt=None,
        )

    try:
        search_query = rewrite_search_query(prompt)
        citations = provider.search(
            search_query,
            topic=select_tavily_topic(prompt),
            include_domains=include_domains_for_prompt(prompt),
        )
    except WebSearchError as exc:
        return GroundingResult(
            status="search_error",
            query=query,
            citations=(),
            grounded_prompt=None,
            detail=str(exc),
        )

    citations = filter_citations_for_prompt(prompt, citations)

    if not citations:
        return GroundingResult(
            status="no_results",
            query=query,
            citations=(),
            grounded_prompt=None,
        )

    return GroundingResult(
        status="used",
        query=query,
        citations=citations,
        grounded_prompt=build_grounded_prompt(prompt, citations),
    )
