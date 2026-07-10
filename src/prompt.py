"""
prompt.py

Builds the Gemini prompt used for project-health narration.

IMPORTANT:
- LLM explains the RAG.
- LLM never determines the RAG.
- LLM must stay grounded in supplied facts.
"""


def build_prompt(project_data, features, scoring, insights):

    rag = scoring["rag"]

    confidence = insights["confidence_score"]

    quality = insights["data_quality_score"]

    positives = "\n".join(
        f"- {x}"
        for x in insights["positive_drivers"]
    )

    negatives = "\n".join(
        f"- {x}"
        for x in insights["negative_drivers"]
    )

    summary_signals = features.get(
        "existing_project_signals",
        {}
    )

    pct_complete = summary_signals.get(
        "pct_complete",
        "Unknown"
    )

    schedule_health = summary_signals.get(
        "summary_schedule_health",
        "Unknown"
    )

    at_risk = summary_signals.get(
        "summary_at_risk",
        "Unknown"
    )

    comments = []

    if (
        hasattr(project_data, "comments_df")
        and project_data.comments_df is not None
        and not project_data.comments_df.empty
    ):

        for _, row in (
            project_data.comments_df.head(10)
            .iterrows()
        ):

            text = str(
                row.get(
                    "comment",
                    row.get(
                        "comments",
                        ""
                    )
                )
            ).strip()

            if text:
                comments.append(text)

    comments_text = (
        "\n".join(
            f"- {c}"
            for c in comments
        )
        if comments
        else "No comments available."
    )

    data_gaps = (
        "\n".join(
            f"- {x}"
            for x in project_data.data_quality_notes
        )
        if project_data.data_quality_notes
        else "None"
    )

    prompt = f"""
You are a PMO Director preparing a weekly executive project health update.

Your job is NOT to determine project status.

Project status has already been determined by a deterministic scoring engine.

You must explain the result using only the evidence provided.

--------------------------------------------------
PROJECT
--------------------------------------------------

Project:
{project_data.project_name}

Official RAG:
{rag}

Confidence Score:
{confidence:.2f}

Data Quality Score:
{quality}/100

Percent Complete:
{pct_complete}

Summary Schedule Health:
{schedule_health}

Summary At Risk:
{at_risk}

--------------------------------------------------
POSITIVE DRIVERS
--------------------------------------------------

{positives if positives else "None"}

--------------------------------------------------
NEGATIVE DRIVERS
--------------------------------------------------

{negatives if negatives else "None"}

--------------------------------------------------
STAKEHOLDER COMMENTS
--------------------------------------------------

{comments_text}

--------------------------------------------------
DATA GAPS
--------------------------------------------------

{data_gaps}

--------------------------------------------------
INSTRUCTIONS
--------------------------------------------------

1. Do NOT change the RAG.
2. Do NOT invent schedule facts.
3. Do NOT invent risks.
4. Use only supplied evidence.
5. Write as an executive status update.
6. Keep reasoning concise and professional.
7. Mention confidence if data quality is weak.
8. If comments reveal risks, discuss them.
9. If data gaps exist, acknowledge them.

Return JSON only.

Required schema:

{{
  "official_rag": "{rag}",
  "reasoning": "2-4 paragraph executive summary",
  "flagged_for_review": true/false,
  "flag_reason": "string or null",
  "data_gaps": [
      "..."
  ],
  "top_risks": [
      "..."
  ]
}}

Review should be flagged when:
- confidence < 0.70
- data quality < 60
- contradictory signals exist
- major delivery uncertainty exists

Return valid JSON only.
"""

    return prompt