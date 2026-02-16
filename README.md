# Engineering Impact Dashboard – PostHog

This project analyzes GitHub activity from the **PostHog/posthog** repository to identify the **most impactful engineers** over a recent time window and presents the results in an interactive dashboard.

The goal is not to measure “who writes the most code,” but to surface **meaningful engineering impact** in a way that is interpretable, transparent, and scoped appropriately for a short analysis.

---

## 1. What Does “Impact” Mean Here?

Engineering impact is a multidimensional concept. In this project, **impact is defined as the extent to which an engineer meaningfully contributes to progress, quality, and collaboration within the codebase**, rather than raw activity alone.

We intentionally avoid metrics like lines of code or commit counts, which often reward noise over value. Instead, we focus on three dimensions:

### a) Delivery Impact
Measures how much an engineer contributes to shipping work:
- Number of merged pull requests
- Recency and consistency of contributions

Merged PRs are used as a proxy for **work that made it into production**, filtering out abandoned or experimental changes.

### b) Collaboration & Review Impact
Captures how engineers unblock others and raise code quality:
- Pull request reviews
- Review comments

Reviews are a critical but often invisible part of engineering productivity. Engineers who consistently review PRs help teams scale and reduce bottlenecks.

### c) Scope & Ownership Signal
Approximates the **relative weight** of contributions:
- PR size (files changed, additions/deletions)
- Number of discussions/comments on PRs

Larger or more discussed PRs often indicate higher coordination cost, design complexity, or ownership of non-trivial changes.

> **Key principle:**  
> Impact is treated as a **signal**, not a perfect measure. The scoring is intentionally simple, explainable, and debuggable.

---

## 2. How Was the Data Gathered?

### Data Source
- GitHub repository: `PostHog/posthog`
- Time window: last **N days** (default: 90 days)
- API: GitHub **GraphQL API**

### Why GraphQL?
The GraphQL API allows us to:
- Fetch PRs, authors, reviews, and metadata in **fewer requests**
- Avoid multiple REST round-trips
- Control exactly which fields are retrieved (faster and cheaper)

### Extraction Approach

The extraction process focuses only on **merged pull requests**, since they represent accepted contributions.

At a high level:
1. Query merged PRs within the time window
2. For each PR, collect:
   - Author
   - Merge date
   - Additions / deletions
   - Number of files changed
   - Review count and comments
3. Normalize all data into tabular form for analysis

To keep the system **pragmatic and deployable**:
- The extracted data is saved as a **local snapshot (JSON)**
- Subsequent runs can operate in **offline mode**, avoiding repeated GitHub API calls
- This prevents rate-limit issues and ensures reproducibility

> This architecture allows the project to scale from a 1-hour prototype to a more robust system without redesign.

---

## 3. How Was the Data Analyzed?

Once extracted, the data goes through three stages:

### a) Transformation
Raw GitHub events are converted into **engineer-level aggregates**, such as:
- Total merged PRs per engineer
- Total reviews performed
- Average PR size
- Total discussion activity

All metrics are computed **per engineer**, not per PR, since the final goal is ranking people, not changes.

---

### b) Scoring Strategy

Each engineer receives an **impact score** computed as a weighted combination of normalized metrics.


#### Why normalization?
- Prevents any single metric (e.g., PR size) from dominating
- Allows fair comparison across different contribution styles
- Makes weights interpretable

#### Why weighted scoring instead of ML?
- Transparent and explainable
- Easy to tune and reason about
- Appropriate for small datasets and short timelines
- Aligns with the 1-hour scope constraint

Weights can be adjusted depending on what leadership values more:
- Shipping velocity
- Collaboration
- Technical ownership

---

### c) Ranking & Output

Engineers are ranked by their final impact score.
The dashboard highlights:
- Top 5 most impactful engineers
- Metric breakdowns per engineer
- Clear explanations of *why* someone ranks highly

This ensures the output is **actionable**, not just a leaderboard.

---

## 4. Project Structure

```text
.
├── app.py            # Streamlit dashboard
├── extract.py        # GitHub GraphQL extraction logic
├── transform.py     # Data cleaning and aggregation
├── scoring.py       # Impact scoring logic
├── data/             # Cached snapshots (JSON)
├── requirements.txt
└── README.md

