"""
narrator.py
The one LLM call in the pipeline. The LLM never decides or outputs a RAG
status -- that comes exclusively from scorer.py and is attached to the
result untouched. The LLM's only job is the plain-English narrative and an
optional review flag for cases the quantitative metrics can't see.
"""

import os
import json
from pydantic import BaseModel, Field
from typing import List, Optional
from google import genai
from dotenv import load_dotenv
from insights import build_insights
from prompt import build_prompt

load_dotenv()

MODEL = "gemini-2.5-flash"  # free tier, stable, supports structured output


class NarratorOutput(BaseModel):
    reasoning: str = Field(description="2-4 sentence plain-English explanation of why the official RAG makes sense, for a VP audience")
    flagged_for_review: bool = Field(description="True only if comments/signals reveal a concrete issue the metrics can't see")
    flag_reason: Optional[str] = Field(
        default=None,
        description="If flagged_for_review is true, the specific reason. Null otherwise."
    )
    data_gaps: List[str] = Field(description="Notable data quality issues or missing signals worth flagging")
    top_risks: List[str] = Field(description="1-3 specific, concrete risks surfaced from the comments or metrics")


def narrate(project_data, features: dict, scorer_result: dict, insights: dict) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY not set. Add it to your .env file and load it "
            "(e.g. `from dotenv import load_dotenv; load_dotenv()`) before calling narrate()."
        )

    client = genai.Client(api_key=api_key)
    prompt = build_prompt(project_data, features, scorer_result, insights)

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": NarratorOutput,
                "temperature": 0,
            },
        )
        parsed = NarratorOutput.model_validate_json(
            response.text
        )
        llm_result = parsed.model_dump()
    except Exception as e:
        # Graceful degradation: don't let an API hiccup kill the whole weekly run.
        llm_result = {
            "reasoning": f"[LLM narration unavailable: {e}] See computed metrics above for status.",
            "flagged_for_review": False,
            "flag_reason": None,
            "data_gaps": ["LLM narration call failed -- see error above"],
            "top_risks": [],
        }

    # official_rag is set here, from scorer_result only -- never from the
    # LLM response. This line is the entire enforcement of "the LLM doesn't decide."
    return {
        "official_rag": scorer_result["rag"],
        **llm_result,
    }


if __name__ == "__main__":

    import sys
    sys.path.insert(0, ".")
    from src.parser import load_project
    from src.features import compute_all_features
    from src.scorer import compute_rag

    for f in ["data/Project_Plan_B.xlsx", "data/S2P_Project.xlsx", "pseudo_data_check/Meridian_Project.xlsx"]:
        d = load_project(f)
        feats = compute_all_features(d)
        scored = compute_rag(feats)
        ins = build_insights(feats, scored)
        narration = narrate(d, feats, scored, ins)

        print(f"\n=== {d.project_name} ===")
        print(f"Official RAG: {narration['official_rag']}")
        print(f"Reasoning: {narration['reasoning']}")
        if narration["flagged_for_review"]:
            print(f"⚑ FLAGGED FOR REVIEW: {narration['flag_reason']}")
        print(f"Data gaps: {narration['data_gaps']}")
        print(f"Top risks: {narration['top_risks']}")