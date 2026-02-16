import streamlit as st
import pandas as pd
import altair as alt

from extract import fetch_prs_merged_last_90_days
from transform import build_prs_df, build_reviews_df
from scoring import build_engineers_df, top5_engineers

st.set_page_config(page_title="PostHog Engineer Impact", layout="wide")

st.title("PostHog Engineer Impact (GitHub-only)")
st.caption("PRs merged in last 90 days • shipping + reviews + cycle-time bonus")


# ---------------------------
# Stacked Weighted Chart
# ---------------------------
def impact_stacked_chart_weighted(engineers_df: pd.DataFrame, top_n: int = 10):
    top = engineers_df.head(top_n).copy()

    long = top.melt(
        id_vars=["engineer_login", "impact_score"],
        value_vars=["w_shipping", "w_collaboration", "w_speed"],
        var_name="component",
        value_name="score",
    )

    label_map = {
        "w_shipping": "Shipping (weighted)",
        "w_collaboration": "Collaboration (weighted)",
        "w_speed": "Speed (weighted)",
    }
    long["component"] = long["component"].map(label_map)

    bars = (
        alt.Chart(long)
        .mark_bar()
        .encode(
            x=alt.X("engineer_login:N", sort="-y", title="Engineer"),
            y=alt.Y("sum(score):Q", title="Impact Score"),
            color=alt.Color("component:N", title="Breakdown"),
            tooltip=[
                alt.Tooltip("engineer_login:N", title="Engineer"),
                alt.Tooltip("component:N", title="Component"),
                alt.Tooltip("score:Q", title="Weighted Contribution", format=".2f"),
            ],
        )
    )

    points = (
        alt.Chart(top)
        .mark_point(size=80)
        .encode(
            x=alt.X("engineer_login:N", sort="-y"),
            y=alt.Y("impact_score:Q"),
            tooltip=[
                alt.Tooltip("engineer_login:N", title="Engineer"),
                alt.Tooltip("impact_score:Q", title="Impact Score", format=".2f"),
            ],
        )
    )

    st.altair_chart((bars + points).properties(height=380), use_container_width=True)


# ---------------------------
# Sidebar Controls
# ---------------------------
with st.sidebar:
    st.header("Weights")

    w_ship = st.slider("Shipping weight", 0.0, 1.0, 0.55, 0.05)
    w_collab = st.slider("Collaboration weight", 0.0, 1.0, 0.30, 0.05)
    w_speed = st.slider("Speed weight", 0.0, 1.0, 0.15, 0.05)

    # Normalize to sum to 1
    total = w_ship + w_collab + w_speed
    if total == 0:
        w_ship, w_collab, w_speed = 0.55, 0.30, 0.15
    else:
        w_ship /= total
        w_collab /= total
        w_speed /= total


# ---------------------------
# Load Data (Always Uses Cache If Present)
# ---------------------------
raw = fetch_prs_merged_last_90_days(force_refresh=False)

st.info(
    f"Fetched **{raw['meta']['count_prs']} PRs** merged since "
    f"**{raw['meta']['merged_after']}**."
)

prs_df = build_prs_df(raw)
reviews_df = build_reviews_df(raw)
engineers_df = build_engineers_df(prs_df, reviews_df)

# ---------------------------
# Top KPIs
# ---------------------------
c1, c2, c3 = st.columns(3)
c1.metric("PRs analyzed", len(prs_df))
c2.metric("Unique PR authors", prs_df["author_login"].nunique() if not prs_df.empty else 0)
c3.metric("Unique reviewers", reviews_df["reviewer_login"].nunique() if not reviews_df.empty else 0)

if engineers_df.empty:
    st.warning("No data found in this window.")
    st.stop()

# ---------------------------
# Recompute Impact With Sidebar Weights
# ---------------------------
engineers_df["w_shipping"] = w_ship * engineers_df["shipping_score"]
engineers_df["w_collaboration"] = w_collab * engineers_df["collaboration_score"]
engineers_df["w_speed"] = w_speed * engineers_df["speed_score"]

engineers_df["impact_score"] = (
    engineers_df["w_shipping"]
    + engineers_df["w_collaboration"]
    + engineers_df["w_speed"]
)

engineers_df = engineers_df.sort_values("impact_score", ascending=False).reset_index(drop=True)
engineers_df["rank"] = range(1, len(engineers_df) + 1)

top5 = top5_engineers(engineers_df)

# ---------------------------
# Top 5 Table
# ---------------------------
st.subheader("Top 5 Most Impactful Engineers")
st.dataframe(top5, use_container_width=True)

# ---------------------------
# Combined Chart
# ---------------------------
st.subheader("Impact (Overall) + Breakdown (Stacked Weighted Components) — Top 10")
impact_stacked_chart_weighted(engineers_df, top_n=10)

# ---------------------------
# Engineer Summary
# ---------------------------
st.subheader("Engineer Summary")

selected = st.selectbox("Select engineer", engineers_df["engineer_login"].tolist())
row = engineers_df[engineers_df["engineer_login"] == selected].iloc[0]

k1, k2, k3, k4 = st.columns(4)
k1.metric("Impact Score", f"{row['impact_score']:.2f}")
k2.metric("Shipping Score", f"{row['shipping_score']:.2f}")
k3.metric("Collaboration Score", f"{row['collaboration_score']:.2f}")
k4.metric("Speed Score", f"{row['speed_score']:.2f}")

st.markdown("### Weighted Contributions")
w1, w2, w3 = st.columns(3)
w1.metric("Shipping (weighted)", f"{row['w_shipping']:.2f}")
w2.metric("Collaboration (weighted)", f"{row['w_collaboration']:.2f}")
w3.metric("Speed (weighted)", f"{row['w_speed']:.2f}")

st.markdown("### Raw Metrics (90 days)")
r1, r2, r3 = st.columns(3)
r1.metric("Merged PRs", int(row.get("merged_pr_count", 0)))
r2.metric("Reviews Authored", int(row.get("reviews_authored", 0)))
r3.metric("PRs Reviewed (Merged)", int(row.get("prs_reviewed_that_merged", 0)))

r4, r5, r6 = st.columns(3)
r4.metric("Avg PR Size (log)", f"{row.get('avg_pr_size_log', 0.0):.2f}")
r5.metric("Avg Files Changed", f"{row.get('avg_changed_files', 0.0):.2f}")

median_hours = row.get("median_cycle_time_hours", 0.0)
median_days = median_hours / 24 if median_hours else 0.0
r6.metric("Median Cycle Time", f"{median_days:.2f} days")

st.caption(f"Rank: #{row['rank']} out of {len(engineers_df)} engineers")
