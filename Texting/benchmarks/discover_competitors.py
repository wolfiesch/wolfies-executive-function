#!/usr/bin/env python3
"""
Discover potential iMessage-related competitors across ecosystems.

This script is intentionally conservative: it finds candidates and ranks them,
but it does not install anything or run benchmarks.

Data sources:
- PyPI XML-RPC search + PyPI JSON metadata
- GitHub repository search (public API; optional GITHUB_TOKEN)
- npm registry search
- crates.io search
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional


PYPI_SIMPLE = "https://pypi.org/simple/"
PYPI_JSON = "https://pypi.org/pypi/{name}/json"
GITHUB_SEARCH_REPOS = "https://api.github.com/search/repositories?q={q}&per_page={per_page}&page={page}"
NPM_SEARCH = "https://registry.npmjs.org/-/v1/search?text={q}&size={size}&from={from_}"
CRATES_SEARCH = "https://crates.io/api/v1/crates?q={q}&per_page={per_page}&page={page}"


DEFAULT_QUERIES = {
    # PyPI removed XML-RPC search and the HTML search endpoint is behind bot protection.
    # The only robust unauthenticated discovery path is name-based matching via /simple/.
    "pypi_substrings": [
        "imessage",
        "imessagedb",
        "imessage-",
        "imessage_",
        "imessage.",
        "mcp-imessage",
        "imessage-mcp",
        "mac_messages",
        "mac-messages",
        "messages-mcp",
    ],
    "github": [
        "imessage mcp",
        "imessage mcp server",
        "imessage fastmcp",
        "imessage modelcontextprotocol",
        "chat.db mcp",
        "macos messages mcp",
        "chat.db imessage",
        "macOS Messages chat.db",
        "imessage cli",
        "imessage exporter",
        "imessage sqlite",
        "messages.app sqlite",
        "Messages chat.db exporter",
        "apple messages database",
        "imessage applescript mcp",
        "imessage swift chat.db",
        "imessage rust chat.db",
    ],
    "npm": [
        "imessage",
        "imessage mcp",
        "macos messages",
        "mcp imessage",
        "messages chat.db",
    ],
    "crates": [
        "imessage",
        "macos messages",
        "chat.db",
        "messages",
    ],
}


def _http_get_json(
    url: str, headers: Optional[Dict[str, str]] = None, timeout_s: int = 30
) -> Any:
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        raw = response.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def _http_get_text(url: str, headers: Optional[Dict[str, str]] = None, timeout_s: int = 30) -> str:
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        return response.read().decode("utf-8", errors="replace")


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _contains_any(haystack: str, needles: Iterable[str]) -> bool:
    h = (haystack or "").lower()
    return any(n.lower() in h for n in needles)


def _score_candidate(name: str, description: str, extra: str = "", stars: int = 0) -> int:
    text = " ".join([name or "", description or "", extra or ""]).lower()
    score = 0

    if "imessage" in text or "iMessage".lower() in text:
        score += 10
    if "messages.app" in text or "messages app" in text:
        score += 6
    if "chat.db" in text:
        score += 8
    if "mcp" in text:
        score += 8
    if "claude" in text:
        score += 6
    if "export" in text or "exporter" in text:
        score += 3
    if "sqlite" in text:
        score += 2
    if "macos" in text or "osx" in text:
        score += 2

    if stars >= 1000:
        score += 6
    elif stars >= 200:
        score += 4
    elif stars >= 50:
        score += 2

    return score


@dataclass(frozen=True)
class PyPiProject:
    name: str
    version: str
    summary: str
    home_page: str
    project_url: str
    requires_dist: List[str]
    score: int


@dataclass(frozen=True)
class GitHubRepo:
    full_name: str
    html_url: str
    description: str
    stargazers_count: int
    language: str
    score: int


@dataclass(frozen=True)
class NpmPackage:
    name: str
    version: str
    description: str
    links: Dict[str, str]
    score: int


@dataclass(frozen=True)
class Crate:
    name: str
    max_version: str
    description: str
    crates_io_url: str
    score: int


def search_pypi(queries: List[str], limit_per_query: int) -> List[PyPiProject]:
    # PyPI's search APIs are deprecated or bot-protected. We fall back to name matching
    # against the canonical /simple/ index, which is accessible and authoritative.
    #
    # Note: this can only find packages whose NAMES match the provided substrings.
    substrings = [q for q in queries if q]
    substrings_lc = [s.lower() for s in substrings]
    candidates: List[str] = []
    seen: set[str] = set()

    try:
        request = urllib.request.Request(
            PYPI_SIMPLE,
            headers={"User-Agent": "wolfies-imessage-gateway-competitor-discovery"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace")
                # Lines look like: <a href="/simple/<name>/">name</a>
                m = re.search(r'href=\"/simple/([^/]+)/\"', line)
                if not m:
                    continue
                name = m.group(1).strip()
                name_lc = name.lower()
                if name in seen:
                    continue
                if any(s in name_lc for s in substrings_lc):
                    seen.add(name)
                    candidates.append(name)
                    if len(candidates) >= limit_per_query:
                        break
    except Exception:
        candidates = []

    projects: List[PyPiProject] = []
    for name in candidates:
        try:
            meta = _http_get_json(PYPI_JSON.format(name=urllib.parse.quote(name)))
            info = meta.get("info") or {}
            summary = _clean_text(info.get("summary") or "")
            home_page = _clean_text(info.get("home_page") or "")
            project_url = _clean_text(info.get("project_url") or "")
            version = _clean_text(info.get("version") or "")
            requires_dist = info.get("requires_dist") or []
            requires_dist = [str(x) for x in requires_dist if x]
            score = _score_candidate(
                name=name,
                description=summary,
                extra=" ".join(requires_dist + [home_page, project_url]),
            )
            projects.append(
                PyPiProject(
                    name=name,
                    version=version,
                    summary=summary,
                    home_page=home_page,
                    project_url=project_url,
                    requires_dist=requires_dist,
                    score=score,
                )
            )
        except Exception:
            continue

    projects.sort(key=lambda p: (p.score, p.name.lower()), reverse=True)
    return projects


def search_github(queries: List[str], per_page: int, pages: int) -> List[GitHubRepo]:
    token = os.environ.get("GITHUB_TOKEN") or ""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "wolfies-imessage-gateway-competitor-discovery",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    seen: set[str] = set()
    repos: List[GitHubRepo] = []

    for q in queries:
        for page in range(1, pages + 1):
            url = GITHUB_SEARCH_REPOS.format(
                q=urllib.parse.quote(q),
                per_page=min(per_page, 100),
                page=page,
            )
            try:
                payload = _http_get_json(url, headers=headers)
            except Exception:
                break

            items = payload.get("items") or []
            if not items:
                break

            for it in items:
                full_name = _clean_text(it.get("full_name") or "")
                if not full_name or full_name in seen:
                    continue
                seen.add(full_name)

                description = _clean_text(it.get("description") or "")
                html_url = _clean_text(it.get("html_url") or "")
                stars = int(it.get("stargazers_count") or 0)
                language = _clean_text(it.get("language") or "")
                score = _score_candidate(
                    name=full_name,
                    description=description,
                    extra=q,
                    stars=stars,
                )
                repos.append(
                    GitHubRepo(
                        full_name=full_name,
                        html_url=html_url,
                        description=description,
                        stargazers_count=stars,
                        language=language,
                        score=score,
                    )
                )

            time.sleep(0.2)

    repos.sort(key=lambda r: (r.score, r.stargazers_count, r.full_name.lower()), reverse=True)
    return repos


def search_npm(queries: List[str], size: int) -> List[NpmPackage]:
    seen: set[str] = set()
    packages: List[NpmPackage] = []

    # npm search endpoint returns capped results; we query with multiple terms.
    for q in queries:
        url = NPM_SEARCH.format(q=urllib.parse.quote(q), size=min(size, 250), from_=0)
        try:
            payload = _http_get_json(url, headers={"User-Agent": "wolfies-imessage-gateway-competitor-discovery"})
        except Exception:
            continue

        objects = payload.get("objects") or []
        for obj in objects:
            pkg = obj.get("package") or {}
            name = _clean_text(pkg.get("name") or "")
            if not name or name in seen:
                continue
            seen.add(name)
            version = _clean_text(pkg.get("version") or "")
            description = _clean_text(pkg.get("description") or "")
            links = pkg.get("links") or {}
            score = _score_candidate(name=name, description=description, extra=q)
            packages.append(
                NpmPackage(
                    name=name,
                    version=version,
                    description=description,
                    links={k: str(v) for k, v in links.items() if v},
                    score=score,
                )
            )

    packages.sort(key=lambda p: (p.score, p.name.lower()), reverse=True)
    return packages


def search_crates(queries: List[str], per_page: int, pages: int) -> List[Crate]:
    seen: set[str] = set()
    crates: List[Crate] = []
    headers = {"User-Agent": "wolfies-imessage-gateway-competitor-discovery"}

    for q in queries:
        for page in range(1, pages + 1):
            url = CRATES_SEARCH.format(
                q=urllib.parse.quote(q),
                per_page=min(per_page, 100),
                page=page,
            )
            try:
                payload = _http_get_json(url, headers=headers)
            except Exception:
                break

            items = payload.get("crates") or []
            if not items:
                break

            for it in items:
                name = _clean_text(it.get("id") or "")
                if not name or name in seen:
                    continue
                seen.add(name)

                description = _clean_text(it.get("description") or "")
                max_version = _clean_text(it.get("max_version") or "")
                crates_io_url = f"https://crates.io/crates/{urllib.parse.quote(name)}"
                score = _score_candidate(name=name, description=description, extra=q)
                crates.append(
                    Crate(
                        name=name,
                        max_version=max_version,
                        description=description,
                        crates_io_url=crates_io_url,
                        score=score,
                    )
                )

            time.sleep(0.2)

    crates.sort(key=lambda c: (c.score, c.name.lower()), reverse=True)
    return crates


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover iMessage-related tooling across ecosystems")
    parser.add_argument("--out", required=True, help="Output JSON path")
    parser.add_argument(
        "--limit-pypi",
        type=int,
        default=200,
        help="Max PyPI candidates from name-based matching against /simple/",
    )
    parser.add_argument("--github-per-page", type=int, default=30, help="GitHub results per page (max 100)")
    parser.add_argument("--github-pages", type=int, default=2, help="Pages to fetch per GitHub query")
    parser.add_argument("--npm-size", type=int, default=100, help="Max npm results per query (max 250)")
    parser.add_argument("--crates-per-page", type=int, default=50, help="Crates results per page (max 100)")
    parser.add_argument("--crates-pages", type=int, default=2, help="Pages to fetch per crates query")
    args = parser.parse_args()

    generated_at = time.strftime("%Y-%m-%d %H:%M:%S")
    pypi = search_pypi(DEFAULT_QUERIES["pypi_substrings"], limit_per_query=args.limit_pypi)
    github = search_github(DEFAULT_QUERIES["github"], per_page=args.github_per_page, pages=args.github_pages)
    npm = search_npm(DEFAULT_QUERIES["npm"], size=args.npm_size)
    crates = search_crates(DEFAULT_QUERIES["crates"], per_page=args.crates_per_page, pages=args.crates_pages)

    payload = {
        "generated_at": generated_at,
        "env": {
            "github_token_present": bool(os.environ.get("GITHUB_TOKEN")),
        },
        "queries": DEFAULT_QUERIES,
        "results": {
            "pypi": [asdict(x) for x in pypi],
            "github": [asdict(x) for x in github],
            "npm": [asdict(x) for x in npm],
            "crates": [asdict(x) for x in crates],
        },
        "notes": [
            "This is discovery only; candidates may be false positives.",
            "GitHub API results are rate-limited; set GITHUB_TOKEN to improve coverage.",
        ],
    }

    out_path = os.fspath(args.out)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    # Small human-readable summary to stdout
    print(f"Wrote {out_path}")
    print(f"PyPI candidates: {len(pypi)}")
    print(f"GitHub repos:    {len(github)}")
    print(f"npm packages:    {len(npm)}")
    print(f"crates:          {len(crates)}")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
