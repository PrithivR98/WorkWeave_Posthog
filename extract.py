import os
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv


load_dotenv()

GITHUB_API = "https://api.github.com/graphql"
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)
OFFLINE_MODE = os.getenv("OFFLINE_MODE", "0") == "1"


OWNER = "PostHog"
REPO = "posthog"


def _iso_90_days_ago() -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=90)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _cache_path() -> Path:
    return CACHE_DIR / f"{OWNER}__{REPO}_prs_90d.json"


def _github_headers() -> dict:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("Missing GITHUB_TOKEN env var")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def fetch_prs_merged_last_90_days(force_refresh: bool = False, page_size: int = 50) -> dict:
    """
    Returns raw GraphQL JSON shaped for downstream transform.
    Uses disk cache unless force_refresh is True.
    """
    cache_file = _cache_path()
    if cache_file.exists() and not force_refresh:
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)
        
    if OFFLINE_MODE:
        raise RuntimeError("OFFLINE_MODE=1 but cache file not found. Commit the cache file or disable offline mode.")

    merged_after = _iso_90_days_ago()
    cursor = None
    all_pr_nodes = []

    query = """
    query($owner:String!, $name:String!, $pageSize:Int!, $cursor:String) {
      repository(owner: $owner, name: $name) {
        pullRequests(first: $pageSize, after: $cursor, states: MERGED, orderBy: {field: UPDATED_AT, direction: DESC}) {
          pageInfo { hasNextPage endCursor }
          nodes {
            number
            title
            url
            createdAt
            mergedAt
            additions
            deletions
            changedFiles
            author { login }
            reviews(first: 50) {
              nodes {
                author { login }
                state
                createdAt
              }
            }
          }
        }
      }
    }
    """

    session = requests.Session()
    session.headers.update(_github_headers())

    while True:
        variables = {
            "owner": OWNER,
            "name": REPO,
            "pageSize": page_size,
            "cursor": cursor,
        }

        resp = session.post(GITHUB_API, json={"query": query, "variables": variables}, timeout=45)
        resp.raise_for_status()
        payload = resp.json()

        if "errors" in payload:
            raise RuntimeError(payload["errors"])

        pr_conn = payload["data"]["repository"]["pullRequests"]
        nodes = pr_conn["nodes"]

        # Post-filter by mergedAt cutoff
        for pr in nodes:
            merged_at = pr.get("mergedAt") or ""
            if merged_at >= merged_after:
                all_pr_nodes.append(pr)

        # Stop early if the last PR in this page is older than cutoff
        if nodes:
            last_merged = nodes[-1].get("mergedAt") or ""
            if last_merged < merged_after:
                break

        page_info = pr_conn["pageInfo"]
        if not page_info["hasNextPage"]:
            break

        cursor = page_info["endCursor"]

    out = {
        "meta": {
            "owner": OWNER,
            "repo": REPO,
            "merged_after": merged_after,
            "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "count_prs": len(all_pr_nodes),
        },
        "pull_requests": all_pr_nodes,
    }

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(out, f)

    return out
