"""
insights.py

Translate engineered features and scoring output
into executive-friendly project drivers.

LLM should narrate these insights,
not invent its own conclusions.
"""


def build_insights(features, scoring):

    positive = []
    negative = []

    # ----------------------------------
    # Schedule Slippage
    # ----------------------------------

    slippage = features["schedule_slippage"]["value"]

    if slippage is not None:

        if slippage < -0.05:

            positive.append(
                "Project completion is ahead of expected schedule"
            )

        elif slippage > 0.05:

            negative.append(
                "Project progress is lagging behind expected schedule"
            )

    # ----------------------------------
    # Critical Milestones
    # ----------------------------------

    milestone = features["milestone_health"]["value"]

    if milestone is not None:

        if milestone == 0:

            positive.append(
                "No overdue critical-path activities detected"
            )

        else:

            negative.append(
                "Critical-path activities are overdue"
            )

    # ----------------------------------
    # Blockers
    # ----------------------------------

    blocker = features["blocker_density"]["value"]

    if blocker is not None:

        if blocker < 0.15:

            positive.append(
                "Low critical-path blocker density"
            )

        elif blocker > 0.25:

            negative.append(
                "High concentration of critical-path blockers"
            )

    # ----------------------------------
    # Variance
    # ----------------------------------

    variance = features["variance_health"]["value"]

    if variance is not None:

        if variance > 7:

            negative.append(
                f"Average task variance is {variance:.0f} days"
            )

    # ----------------------------------
    # Overdue Tasks
    # ----------------------------------

    overdue = features["overdue_task_ratio"]["value"]

    if overdue is not None:

        if overdue > 0.20:

            negative.append(
                "Large share of active tasks are overdue"
            )

    # ----------------------------------
    # Comment Risks
    # ----------------------------------

    comment_risk = features[
        "comment_risk_signal"
    ]["value"]

    if comment_risk is not None:

        if comment_risk >= 0.5:

            negative.append(
                "Stakeholder comments indicate delivery risks"
            )

    # ----------------------------------
    # Confidence
    # ----------------------------------

    confidence = features[
        "confidence_score"
    ]["value"]

    if confidence is not None:

        if confidence >= 0.80:

            positive.append(
                "Assessment confidence is high"
            )

    return {

        "positive_drivers": positive,

        "negative_drivers": negative,

        "confidence_score":
            confidence,

        "data_quality_score":
            features[
                "data_quality_score"
            ]["value"],

        "rag":
            scoring["rag"]
    }