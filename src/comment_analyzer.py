"""
comment_analyzer.py

Uses Gemini to convert unstructured PM comments into structured project-risk
signals. The LLM never determines project health or RAG status.

It extracts:

- risk_type
- severity
- root_cause
- dependency_mentioned

Deterministic code then aggregates all extracted risks into a single
comment-derived risk signal for scoring.
"""

import json
import os
from collections import Counter
from typing import List, Optional

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field

load_dotenv()

MODEL = "gemini-2.5-flash"


class CommentRisk(BaseModel):
    risk_type: str = Field(
        description="One of: Schedule Risk, Dependency Risk, Resource Risk, Scope Risk, Client Risk, Other"
    )
    severity: str = Field(
        description="One of: Low, Medium, High"
    )
    root_cause: Optional[str] = Field(
        default=None,
        description="Short root cause if identifiable"
    )
    dependency_mentioned: bool = Field(
        description="Whether the comment references a dependency or waiting on another party"
    )


def _severity_to_score(severity: str) -> int:
    mapping = {
        "low": 0,
        "medium": 1,
        "high": 2
    }
    return mapping.get(str(severity).lower(), 0)


def analyze_comments(comments_df):
    """
    Parameters
    ----------
    comments_df : pd.DataFrame

    Returns
    -------
    dict
    """

    if comments_df.empty:
        return {
            "risk_score": None,
            "overall_risk_level": None,
            "risk_types": [],
            "root_causes": [],
            "dependency_mentions": 0,
            "confidence": "low",
            "notes": "No comments available"
        }

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        return {
            "risk_score": None,
            "overall_risk_level": None,
            "risk_types": [],
            "root_causes": [],
            "dependency_mentions": 0,
            "confidence": "low",
            "notes": "GEMINI_API_KEY not configured"
        }

    client = genai.Client(api_key=api_key)

    extracted = []

    for comment in comments_df["comment_text"].dropna().tolist():

        prompt = f"""
You are a PMO risk analyst.

Analyze the project comment below.

Extract:

- risk_type
- severity
- root_cause
- dependency_mentioned

Do NOT determine project health.
Do NOT mention Red/Amber/Green.

Comment:

{comment}
"""

        try:

            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": CommentRisk,
                    "temperature": 0
                }
            )

            extracted.append(json.loads(response.text))

        except Exception:
            continue

    if not extracted:
        return {
            "risk_score": None,
            "overall_risk_level": None,
            "risk_types": [],
            "root_causes": [],
            "dependency_mentions": 0,
            "confidence": "low",
            "notes": "No comments could be parsed"
        }

    severities = [
        _severity_to_score(x["severity"])
        for x in extracted
    ]

    avg_score = sum(severities) / len(severities)

    if avg_score < 0.5:
        overall = "Low"
    elif avg_score < 1.5:
        overall = "Medium"
    else:
        overall = "High"

    risk_types = Counter(
        x["risk_type"]
        for x in extracted
        if x.get("risk_type")
    )

    root_causes = Counter(
        x["root_cause"]
        for x in extracted
        if x.get("root_cause")
    )

    dependency_mentions = sum(
        1
        for x in extracted
        if x.get("dependency_mentioned")
    )

    return {
        "risk_score": round(avg_score, 2),
        "overall_risk_level": overall,
        "risk_types": [
            r[0]
            for r in risk_types.most_common(5)
        ],
        "root_causes": [
            r[0]
            for r in root_causes.most_common(5)
        ],
        "dependency_mentions": dependency_mentions,
        "confidence": "medium" if len(extracted) < 3 else "high",
        "notes": f"Analyzed {len(extracted)} comments"
    }