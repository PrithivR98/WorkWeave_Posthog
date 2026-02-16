# Engineering Impact Dashboard – PostHog

This project analyzes recent GitHub activity from the **PostHog/posthog** repository to identify the **most impactful engineers** and present the results in a simple, interactive dashboard.

The goal is not to measure raw output (e.g., lines of code), but to surface **meaningful engineering impact** in a transparent and interpretable way, scoped for a short analysis.

---

## 1. What Does “Impact” Mean?

Impact is defined as an engineer’s contribution to **shipping work, improving quality, and enabling collaboration**.

Rather than using noisy metrics like commit count, we focus on three signals:

- **Delivery Impact** – merged pull requests (work that reached production)
- **Collaboration Impact** – PR reviews and review comments
- **Scope & Ownership** – PR size and discussion activity

Impact is treated as a **signal, not a perfect measure**, and is intentionally simple and explainable.

---

## 2. Data Collection

- **Source:** PostHog GitHub repository  
- **Time window:** Last 90 days  
- **API:** GitHub GraphQL API

GraphQL was used to efficiently fetch PRs, authors, reviews, and metadata in fewer requests than REST.

Only **merged pull requests** were analyzed, since they represent accepted contributions.  
The extracted data is cached locally as a JSON snapshot to:
- Avoid repeated API calls
- Prevent rate-limit issues
- Ensure reproducibility and fast iteration

---

## 3. Analysis & Scoring

GitHub events are aggregated at the **engineer level**, including:
- Number of merged PRs
- Number of reviews
- Average PR size
- Discussion activity

Each engineer receives an **impact score** computed as a weighted sum of **normalized metrics**.

**Why this approach?**
- Normalization prevents any single metric from dominating
- Weighted scoring is transparent and easy to reason about
- Avoids over-engineering (no ML) given the dataset size and time constraint

Engineers are ranked by final score, and the dashboard highlights the **top 5 most impactful engineers** with metric breakdowns.

---

## 4. Deployment & Pragmatic Scoping

Given the **1-hour time constraint**, several deliberate tradeoffs were made:

- Limited analysis to **90 days** of data
- Used **cached snapshots** instead of real-time GitHub extraction
- Designed the pipeline to support both **online (API-based)** and **offline** modes
- Prioritized clarity, reproducibility, and deployability over completeness

This allows the project to work reliably within the time limit while remaining easy to extend.

---

## 5. Project Structure

```text
.
├── app.py        # Streamlit dashboard
├── extract.py    # GitHub GraphQL extraction
├── transform.py  # Aggregation & feature engineering
├── scoring.py    # Impact scoring logic
├── data/         # Cached JSON snapshots
├── requirements.txt
└── README.md
