"""
scorer.py

Deterministic RAG engine.

Converts engineered features into:

- Composite score
- RAG status
- Confidence score
- Data quality score

The LLM never participates in scoring.
"""


# ------------------------------------------------------------------
# Banding Functions
# ------------------------------------------------------------------


def _band_schedule_slippage(value):

    if value is None:
        return None

    if value <= 0.05:
        return 0

    if value <= 0.15:
        return 1

    return 2


def _band_milestone_health(value):

    if value is None:
        return None

    if value == 0:
        return 0

    if value <= 0.15:
        return 1

    return 2


def _band_blocker_density(value):

    if value is None:
        return None

    if value < 0.15:
        return 0

    if value < 0.30:
        return 1

    return 2


def _band_variance_health(value):

    if value is None:
        return None

    if value <= 2:
        return 0

    if value <= 7:
        return 1

    return 2


def _band_overdue_task_ratio(value):

    if value is None:
        return None

    if value < 0.10:
        return 0

    if value < 0.25:
        return 1

    return 2


def _band_schedule_health_signal(value):

    if value is None:
        return None

    if value < 0.50:
        return 0

    if value < 1.25:
        return 1

    return 2


def _band_comment_risk_signal(value):

    if value is None:
        return None

    if value < 0.5:
        return 0

    if value < 1.5:
        return 1

    return 2


# ------------------------------------------------------------------
# Weights
# ------------------------------------------------------------------

WEIGHTS = {

    # Core schedule metrics
    "schedule_slippage": 0.20,
    "variance_health": 0.15,
    "overdue_task_ratio": 0.15,

    # Delivery risk metrics
    "milestone_health": 0.20,
    "blocker_density": 0.15,

    # Human/project signals
    "schedule_health_signal": 0.05,
    "comment_risk_signal": 0.10
}


BAND_FUNCS = {

    "schedule_slippage":
        _band_schedule_slippage,

    "milestone_health":
        _band_milestone_health,

    "blocker_density":
        _band_blocker_density,

    "variance_health":
        _band_variance_health,

    "overdue_task_ratio":
        _band_overdue_task_ratio,

    "schedule_health_signal":
        _band_schedule_health_signal,

    "comment_risk_signal":
        _band_comment_risk_signal
}


RAG_LABELS = {
    0: "Green",
    1: "Amber",
    2: "Red"
}


# ------------------------------------------------------------------
# Main Scoring
# ------------------------------------------------------------------


def compute_rag(features):

    bands = {}

    weighted_sum = 0.0
    available_weight = 0.0

    for feature_name, weight in WEIGHTS.items():

        raw_value = features[feature_name]["value"]

        band = BAND_FUNCS[
            feature_name
        ](raw_value)

        bands[feature_name] = band

        if band is not None:

            weighted_sum += (
                band * weight
            )

            available_weight += weight

    if available_weight == 0:

        return {
            "rag": "Unknown",
            "composite_score": None,
            "signal_bands": bands,
            "overridden": False,
            "override_reason": None,
            "weight_coverage": 0.0,
            "confidence_score":
                features["confidence_score"]["value"],
            "data_quality_score":
                features["data_quality_score"]["value"],
            "notes":
                "No scorable signals available"
        }

    composite_score = (
        weighted_sum
        / available_weight
    )

    if composite_score < 0.60:

        rag = "Green"

    elif composite_score < 1.30:

        rag = "Amber"

    else:

        rag = "Red"

    overridden = False
    override_reason = None

    # ----------------------------------------------------------
    # Override Rule #1
    # Critical-path delays prevent Green
    # ----------------------------------------------------------

    milestone_val = (
        features["milestone_health"]["value"]
    )

    if (
        milestone_val is not None
        and milestone_val > 0
        and rag == "Green"
    ):

        rag = "Amber"

        overridden = True

        override_reason = (
            "Overdue critical-path tasks present"
        )

    # ----------------------------------------------------------
    # Override Rule #2
    # Severe blocker density forces Red
    # ----------------------------------------------------------

    blocker_val = (
        features["blocker_density"]["value"]
    )

    if (
        blocker_val is not None
        and blocker_val > 0.40
        and rag != "Red"
    ):

        rag = "Red"

        overridden = True

        override_reason = (
            (
                override_reason + "; "
            )
            if override_reason
            else ""
        ) + (
            "Blocker density exceeds 40%"
        )

    # ----------------------------------------------------------
    # Override Rule #3
    # Massive overdue ratio forces Red
    # ----------------------------------------------------------

    overdue_val = (
        features["overdue_task_ratio"]["value"]
    )

    if (
        overdue_val is not None
        and overdue_val > 0.50
        and rag != "Red"
    ):

        rag = "Red"

        overridden = True

        override_reason = (
            (
                override_reason + "; "
            )
            if override_reason
            else ""
        ) + (
            "More than 50% of active tasks overdue"
        )

    return {

        "rag": rag,

        "composite_score":
            round(
                composite_score,
                3
            ),

        "signal_bands": bands,

        "overridden":
            overridden,

        "override_reason":
            override_reason,

        "weight_coverage":
            round(
                available_weight,
                2
            ),

        "confidence_score":
            features[
                "confidence_score"
            ]["value"],

        "data_quality_score":
            features[
                "data_quality_score"
            ]["value"],

        "notes":
            (
                f"Scored on "
                f"{available_weight:.0%} "
                f"of intended signal weight. "
                f"Missing signals renormalized."
            )
    }


# ------------------------------------------------------------------
# Debug
# ------------------------------------------------------------------


if __name__ == "__main__":

    from parser import load_project
    from features import compute_all_features

    files = [
        "data/Project_Plan_B.xlsx",
        "data/S2P_Project.xlsx"
    ]

    for f in files:

        d = load_project(f)

        feats = compute_all_features(d)

        result = compute_rag(feats)

        print(
            f"\n=== {d.project_name} ==="
        )

        print(
            f"RAG: {result['rag']}"
        )

        print(
            f"Composite: "
            f"{result['composite_score']}"
        )

        print(
            f"Confidence: "
            f"{result['confidence_score']}"
        )

        print(
            f"Data Quality: "
            f"{result['data_quality_score']}"
        )

        if result["overridden"]:

            print(
                f"Override: "
                f"{result['override_reason']}"
            )

        print(
            result["signal_bands"]
        )