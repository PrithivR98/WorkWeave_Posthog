import math
import pandas as pd


def build_prs_df(raw: dict) -> pd.DataFrame:
    rows = []
    for pr in raw.get("pull_requests", []):
        author = (pr.get("author") or {}).get("login") or "unknown"
        created = pr.get("createdAt")
        merged = pr.get("mergedAt")

        additions = pr.get("additions") or 0
        deletions = pr.get("deletions") or 0
        changed_files = pr.get("changedFiles") or 0

        pr_size_raw = int(additions) + int(deletions)
        pr_size_log = math.log1p(pr_size_raw)

        rows.append(
            {
                "pr_number": pr.get("number"),
                "pr_title": pr.get("title"),
                "pr_url": pr.get("url"),
                "author_login": author,
                "created_at": pd.to_datetime(created, utc=True, errors="coerce"),
                "merged_at": pd.to_datetime(merged, utc=True, errors="coerce"),
                "additions": additions,
                "deletions": deletions,
                "changed_files": changed_files,
                "pr_size_raw": pr_size_raw,
                "pr_size_log": pr_size_log,
            }
        )

    prs_df = pd.DataFrame(rows)
    if not prs_df.empty:
        prs_df["cycle_time_hours"] = (prs_df["merged_at"] - prs_df["created_at"]).dt.total_seconds() / 3600.0
    else:
        prs_df["cycle_time_hours"] = []

    return prs_df


def build_reviews_df(raw: dict) -> pd.DataFrame:
    rows = []
    for pr in raw.get("pull_requests", []):
        pr_author = (pr.get("author") or {}).get("login") or "unknown"
        pr_number = pr.get("number")
        pr_url = pr.get("url")
        pr_merged_at = pd.to_datetime(pr.get("mergedAt"), utc=True, errors="coerce")

        review_nodes = ((pr.get("reviews") or {}).get("nodes") or [])
        for rv in review_nodes:
            reviewer = (rv.get("author") or {}).get("login") or "unknown"
            rows.append(
                {
                    "pr_number": pr_number,
                    "pr_url": pr_url,
                    "pr_author_login": pr_author,
                    "reviewer_login": reviewer,
                    "review_state": rv.get("state"),
                    "review_created_at": pd.to_datetime(rv.get("createdAt"), utc=True, errors="coerce"),
                    "pr_merged_at": pr_merged_at,
                    "is_merged_pr": pd.notna(pr_merged_at),
                }
            )

    return pd.DataFrame(rows)
