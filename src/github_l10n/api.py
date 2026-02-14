"""GitHub REST API client with caching."""

import json
import os
import time
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Optional

CACHE_DIR = Path.home() / ".cache" / "github-l10n"
CACHE_TTL = 3600  # 1 hour

API_BASE = "https://api.github.com"

L10N_EXTENSIONS = [".po", ".ts", ".xliff", ".xlf", ".pot"]
L10N_PATTERNS = {
    "sv": ["sv.po", "sv_SE.po", "swedish.po", "sv.ts", "sv.xliff", "sv.xlf",
            "sv_SE.ts", "sv_SE.xliff", "sv_SE.xlf", "sv/", "sv-SE/", "swedish/"],
    "de": ["de.po", "de_DE.po", "german.po", "de.ts", "de.xliff", "de.xlf"],
    "fr": ["fr.po", "fr_FR.po", "french.po", "fr.ts", "fr.xliff", "fr.xlf"],
    "es": ["es.po", "es_ES.po", "spanish.po", "es.ts", "es.xliff", "es.xlf"],
    "ja": ["ja.po", "ja_JP.po", "japanese.po", "ja.ts", "ja.xliff", "ja.xlf"],
    "zh": ["zh.po", "zh_CN.po", "zh_TW.po", "chinese.po", "zh.ts", "zh.xliff"],
    "pt": ["pt.po", "pt_BR.po", "pt_PT.po", "portuguese.po", "pt.ts"],
    "ru": ["ru.po", "ru_RU.po", "russian.po", "ru.ts", "ru.xliff"],
    "ko": ["ko.po", "ko_KR.po", "korean.po", "ko.ts", "ko.xliff"],
    "it": ["it.po", "it_IT.po", "italian.po", "it.ts", "it.xliff"],
    "nl": ["nl.po", "nl_NL.po", "dutch.po", "nl.ts", "nl.xliff"],
    "pl": ["pl.po", "pl_PL.po", "polish.po", "pl.ts", "pl.xliff"],
    "da": ["da.po", "da_DK.po", "danish.po", "da.ts", "da.xliff"],
    "nb": ["nb.po", "nb_NO.po", "norwegian.po", "nb.ts", "nb.xliff"],
    "fi": ["fi.po", "fi_FI.po", "finnish.po", "fi.ts", "fi.xliff"],
}


def _get_cache_path(key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = urllib.parse.quote(key, safe="")
    return CACHE_DIR / f"{safe}.json"


def _get_cached(key: str) -> Optional[dict]:
    p = _get_cache_path(key)
    if p.exists():
        data = json.loads(p.read_text())
        if time.time() - data.get("_ts", 0) < CACHE_TTL:
            return data.get("_payload")
    return None


def _set_cache(key: str, payload):
    p = _get_cache_path(key)
    p.write_text(json.dumps({"_ts": time.time(), "_payload": payload}))


def _api_request(path: str, token: Optional[str] = None, params: Optional[dict] = None) -> dict:
    url = f"{API_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "github-l10n/0.1.0")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


class GitHubClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token

    def get_top_repos(self, count: int = 100, callback=None) -> list:
        """Fetch top repos by stars. Uses pagination (30 per page)."""
        cache_key = f"top_repos_{count}"
        cached = _get_cached(cache_key)
        if cached:
            return cached

        repos = []
        per_page = min(count, 100)
        pages = (count + per_page - 1) // per_page

        for page in range(1, pages + 1):
            try:
                data = _api_request(
                    "/search/repositories",
                    token=self.token,
                    params={
                        "q": "stars:>10000",
                        "sort": "stars",
                        "order": "desc",
                        "per_page": per_page,
                        "page": page,
                    },
                )
                for item in data.get("items", []):
                    repos.append({
                        "full_name": item["full_name"],
                        "name": item["name"],
                        "owner": item["owner"]["login"],
                        "stars": item["stargazers_count"],
                        "description": item.get("description", ""),
                        "html_url": item["html_url"],
                        "default_branch": item.get("default_branch", "main"),
                    })
                if callback:
                    callback(len(repos), count)
            except urllib.error.HTTPError as e:
                if e.code == 403:
                    break  # rate limited
                raise
            if len(repos) >= count:
                break

        repos = repos[:count]
        _set_cache(cache_key, repos)
        return repos

    def search_l10n_files(self, repo_full_name: str, lang: str = "sv") -> dict:
        """Search for l10n files in a repo for the given language."""
        cache_key = f"l10n_{repo_full_name}_{lang}"
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached

        result = {"status": "unknown", "files": [], "any_l10n": False}

        # Search for any l10n files first
        try:
            data = _api_request(
                "/search/code",
                token=self.token,
                params={
                    "q": f"repo:{repo_full_name} extension:po OR extension:ts OR extension:xliff OR extension:xlf OR extension:pot",
                    "per_page": 5,
                },
            )
            if data.get("total_count", 0) > 0:
                result["any_l10n"] = True
        except (urllib.error.HTTPError, urllib.error.URLError):
            pass

        # Search for specific language files
        patterns = L10N_PATTERNS.get(lang, [f"{lang}.po", f"{lang}.ts", f"{lang}.xliff"])
        found_files = []

        for pattern in patterns[:3]:  # limit queries
            try:
                q = f"repo:{repo_full_name} filename:{pattern}"
                data = _api_request(
                    "/search/code",
                    token=self.token,
                    params={"q": q, "per_page": 10},
                )
                for item in data.get("items", []):
                    file_info = {
                        "path": item["path"],
                        "name": item["name"],
                        "html_url": item["html_url"],
                    }
                    if file_info["path"] not in [f["path"] for f in found_files]:
                        found_files.append(file_info)
            except (urllib.error.HTTPError, urllib.error.URLError):
                pass

        result["files"] = found_files
        if found_files:
            result["status"] = "yes"
        elif result["any_l10n"]:
            result["status"] = "partial"
        else:
            result["status"] = "no"

        _set_cache(cache_key, result)
        return result

    def clear_cache(self):
        """Clear all cached data."""
        if CACHE_DIR.exists():
            for f in CACHE_DIR.glob("*.json"):
                f.unlink()

    def get_rate_limit(self) -> dict:
        """Get current rate limit status."""
        try:
            return _api_request("/rate_limit", token=self.token)
        except Exception:
            return {}
