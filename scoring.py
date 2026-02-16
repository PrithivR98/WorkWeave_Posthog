import numpy as np
import pandas as pd


def _zscore(s: pd.Series) -> pd.Series:
    s = s.astype(float)
    mu = s.mean()
    sigma = s.std(ddof=0)
    if sigma == 0 or np.isnan(sigma):
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - mu) / sigma


def build_engineers_df(prs_df: pd.DataFrame, reviews_df: pd.DataFrame) -> pd.DataFrame:
    if prs_df.empty:
        return pd.DataFrame(columns=["engineer_login", "impact_score"])

    ship = prs_df.groupby("author_login", as_index=False).agg(
        merged_pr_count=("pr_number", "count"),
        avg_pr_size_log=("pr_size_log", "mean"),
        avg_changed_files=("changed_files", "mean"),
        median_cycle_time_hours=("cycle_time_hours", "median"),
    ).rename(columns={"author_login": "engineer_login"})

    # Collaboration metrics chosen:
    # - Reviews Authored (count of review events)
    # - PRs Reviewed That Merged (distinct PRs reviewed that are merged)
    if reviews_df is None or reviews_df.empty:
        collab = pd.DataFrame({"engineer_login": ship["engineer_login"], "reviews_authored": 0, "prs_reviewed_that_merged": 0})
    else:
        reviews_authored = reviews_df.groupby("reviewer_login", as_index=False).agg(
            reviews_authored=("pr_number", "count"),
        ).rename(columns={"reviewer_login": "engineer_login"})

        prs_reviewed_that_merged = (
            reviews_df[reviews_df["is_merged_pr"]]
            .groupby("reviewer_login", as_index=False)
            .agg(prs_reviewed_that_merged=("pr_number", "nunique"))
            .rename(columns={"reviewer_login": "engineer_login"})
        )

        collab = reviews_authored.merge(prs_reviewed_that_merged, on="engineer_login", how="outer").fillna(0)

    eng = ship.merge(collab, on="engineer_login", how="left").fillna(0)

    # Normalize into scores
    eng["z_merged_pr_count"] = _zscore(eng["merged_pr_count"])
    eng["z_avg_pr_size_log"] = _zscore(eng["avg_pr_size_log"])
    eng["z_avg_changed_files"] = _zscore(eng["avg_changed_files"])

    eng["z_reviews_authored"] = _zscore(eng["reviews_authored"])
    eng["z_prs_reviewed_that_merged"] = _zscore(eng["prs_reviewed_that_merged"])

    # Speed: lower cycle time is better → negate z-score
    eng["z_speed"] = -_zscore(eng["median_cycle_time_hours"])

    # Simple weighted sum (can expose weights later in app)
    w_ship = 0.55
    w_collab = 0.30
    w_speed = 0.15

    ship_score = 0.5 * eng["z_merged_pr_count"] + 0.3 * eng["z_avg_pr_size_log"] + 0.2 * eng["z_avg_changed_files"]
    collab_score = 0.6 * eng["z_reviews_authored"] + 0.4 * eng["z_prs_reviewed_that_merged"]
    speed_score = eng["z_speed"]

    eng["shipping_score"] = ship_score
    eng["collaboration_score"] = collab_score
    eng["speed_score"] = speed_score

    eng["impact_score"] = w_ship * ship_score + w_collab * collab_score + w_speed * speed_score

    eng = eng.sort_values("impact_score", ascending=False).reset_index(drop=True)
    eng["rank"] = np.arange(1, len(eng) + 1)

    return eng


def top5_engineers(engineers_df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "rank",
        "engineer_login",
        "impact_score",
        "shipping_score",
        "collaboration_score",
        "speed_score",
        "merged_pr_count",
        "avg_pr_size_log",
        "avg_changed_files",
        "median_cycle_time_hours",
        "reviews_authored",
        "prs_reviewed_that_merged",
    ]
    cols = [c for c in cols if c in engineers_df.columns]
    return engineers_df[cols].head(5)
