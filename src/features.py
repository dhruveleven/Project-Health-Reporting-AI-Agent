"""
features.py

Deterministic feature engineering layer.

All functions return:

{
    "value": ...,
    "confidence": ...,
    "notes": ...
}

The LLM never determines RAG.
The only LLM-assisted signal is comment analysis, which extracts structured
risk metadata. Scoring remains deterministic.
"""

import pandas as pd
from datetime import datetime

from comment_analyzer import analyze_comments


def _signal(value, confidence, notes=""):

    return {
        "value": value,
        "confidence": confidence,
        "notes": notes
    }


# ------------------------------------------------------------------
# Existing Features
# ------------------------------------------------------------------


def schedule_slippage(tasks: pd.DataFrame, summary: dict, as_of=None):

    as_of = as_of or summary.get("Today's Date")

    actual_pct = summary.get("% Complete")

    if not as_of or actual_pct is None:

        return _signal(
            None,
            "low",
            "Missing as-of date or % complete"
        )

    dated_tasks = tasks[
        tasks["end_date"].notna()
    ]

    if dated_tasks.empty:

        return _signal(
            None,
            "low",
            "No dated tasks available"
        )

    expected_pct = (
        dated_tasks["end_date"] <= as_of
    ).mean()

    slippage = expected_pct - actual_pct

    return _signal(
        round(slippage, 3),
        "high",
        (
            f"Expected {expected_pct:.0%} complete "
            f"vs actual {actual_pct:.0%}"
        )
    )


def milestone_health(tasks: pd.DataFrame, as_of=None):

    as_of = as_of or datetime.now()

    critical_tasks = tasks[
        tasks["critical"] == True
    ]

    if critical_tasks.empty:

        return _signal(
            None,
            "low",
            "No critical-path tasks available"
        )

    incomplete = critical_tasks[
        critical_tasks["status"] != "Completed"
    ]

    overdue = incomplete[
        incomplete["end_date"].notna()
        &
        (incomplete["end_date"] < as_of)
    ]

    ratio = len(overdue) / len(critical_tasks)

    coverage = (
        len(critical_tasks)
        / max(len(tasks), 1)
    )

    confidence = (
        "medium"
        if coverage < 0.20
        else "high"
    )

    return _signal(
        round(ratio, 3),
        confidence,
        (
            f"{len(overdue)}/{len(critical_tasks)} "
            "critical tasks overdue"
        )
    )


def blocker_density(tasks: pd.DataFrame):

    active = tasks[
        tasks["status"] != "Completed"
    ].copy()

    if active.empty:

        return _signal(
            None,
            "low",
            "No active tasks"
        )

    active["total_float"] = pd.to_numeric(
        active["total_float"],
        errors="coerce"
    )

    no_slack = active[
        active["total_float"] <= 0
    ]

    weight = (
        no_slack["critical"]
        .fillna(False)
        .astype(bool)
    )

    weighted_count = (
        (~weight).sum() * 1.0
        + weight.sum() * 1.5
    )

    density = (
        weighted_count
        / len(active)
    )

    return _signal(
        round(density, 3),
        "high",
        (
            f"{len(no_slack)}/{len(active)} "
            "active tasks have no float"
        )
    )


def budget_burn(tasks):

    return _signal(
        None,
        "unavailable",
        "No budget data supplied"
    )


# ------------------------------------------------------------------
# New Features
# ------------------------------------------------------------------


def variance_health(tasks: pd.DataFrame):

    active = tasks[
        tasks["status"] != "Completed"
    ]

    if active.empty:

        return _signal(
            None,
            "low",
            "No active tasks"
        )

    variances = pd.to_numeric(
        active["variance_days"],
        errors="coerce"
    )

    variances = variances.dropna()

    if variances.empty:

        return _signal(
            None,
            "low",
            "No variance data"
        )

    delayed = variances[variances > 0]

    if delayed.empty:

        avg_delay = 0

    else:

        avg_delay = delayed.mean()

    return _signal(
        round(avg_delay, 2),
        "high",
        (
            f"Average positive variance "
            f"{avg_delay:.2f} days"
        )
    )


def overdue_task_ratio(tasks: pd.DataFrame, as_of=None):

    as_of = as_of or datetime.now()

    active = tasks[
        tasks["status"] != "Completed"
    ]

    if active.empty:

        return _signal(
            None,
            "low",
            "No active tasks"
        )

    overdue = active[
        active["end_date"].notna()
        &
        (active["end_date"] < as_of)
    ]

    ratio = (
        len(overdue)
        / len(active)
    )

    return _signal(
        round(ratio, 3),
        "high",
        (
            f"{len(overdue)}/{len(active)} "
            "active tasks overdue"
        )
    )


def schedule_health_signal(tasks: pd.DataFrame):

    health_values = (
        tasks["schedule_health"]
        .dropna()
        .astype(str)
        .str.lower()
    )

    if health_values.empty:

        return _signal(
            None,
            "low",
            "No schedule health values"
        )

    mapping = {
        "green": 0,
        "yellow": 1,
        "amber": 1,
        "red": 2
    }

    scores = [
        mapping[h]
        for h in health_values
        if h in mapping
    ]

    if not scores:

        return _signal(
            None,
            "low",
            "Schedule health values unrecognized"
        )

    avg_score = sum(scores) / len(scores)

    return _signal(
        round(avg_score, 3),
        "high",
        (
            f"Average schedule health score "
            f"{avg_score:.2f}"
        )
    )


def comment_risk_signal(project_data):

    comment_analysis = analyze_comments(
        project_data.comments
    )

    return _signal(
        comment_analysis["risk_score"],
        comment_analysis["confidence"],
        comment_analysis["notes"]
    )


def data_quality_score(project_data):

    metrics = project_data.data_quality_metrics

    penalties = (
        metrics["missing_status_pct"] * 25
        + metrics["missing_dates_pct"] * 35
        + metrics["missing_schedule_health_pct"] * 20
        + metrics["missing_critical_pct"] * 20
    )

    score = max(
        0,
        round(100 - penalties)
    )

    return _signal(
        score,
        "high",
        f"Data quality score {score}/100"
    )


def confidence_score(feature_results, project_data):

    coverage = 0
    total = 0

    for value in feature_results.values():

        if not isinstance(value, dict):
            continue

        if "value" not in value:
            continue

        total += 1

        if value["value"] is not None:
            coverage += 1

    feature_coverage = (
        coverage / max(total, 1)
    )

    quality_score = (
        data_quality_score(project_data)["value"]
        / 100
    )

    confidence = (
        0.6 * feature_coverage
        + 0.4 * quality_score
    )

    return _signal(
        round(confidence, 3),
        "high",
        (
            f"Coverage={feature_coverage:.2f}, "
            f"quality={quality_score:.2f}"
        )
    )


# ------------------------------------------------------------------
# Master Feature Assembly
# ------------------------------------------------------------------


def compute_all_features(project_data, as_of=None):

    as_of = (
        as_of
        or project_data.summary.get("Today's Date")
    )

    features = {
        "schedule_slippage":
            schedule_slippage(
                project_data.tasks,
                project_data.summary,
                as_of
            ),

        "milestone_health":
            milestone_health(
                project_data.tasks,
                as_of
            ),

        "blocker_density":
            blocker_density(
                project_data.tasks
            ),

        "variance_health":
            variance_health(
                project_data.tasks
            ),

        "overdue_task_ratio":
            overdue_task_ratio(
                project_data.tasks,
                as_of
            ),

        "schedule_health_signal":
            schedule_health_signal(
                project_data.tasks
            ),

        "comment_risk_signal":
            comment_risk_signal(
                project_data
            ),

        "budget_burn":
            budget_burn(
                project_data.tasks
            ),

        "data_quality_score":
            data_quality_score(
                project_data
            ),

        "existing_project_signals": {
            "summary_schedule_health":
                project_data.summary.get(
                    "Schedule Health"
                ),

            "summary_at_risk":
                project_data.summary.get(
                    "At Risk"
                ),

            "pct_complete":
                project_data.summary.get(
                    "% Complete"
                )
        }
    }

    features["confidence_score"] = (
        confidence_score(
            features,
            project_data
        )
    )

    return features


if __name__ == "__main__":

    from parser import load_project

    for f in [
        "data/Project_Plan_B.xlsx",
        "data/S2P_Project.xlsx"
    ]:

        d = load_project(f)

        feats = compute_all_features(d)

        print(f"\n=== {d.project_name} ===")

        for k, v in feats.items():
            print(k, v)