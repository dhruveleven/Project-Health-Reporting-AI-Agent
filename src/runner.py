"""
runner.py
Orchestrates: parse -> compute features -> score -> narrate -> write output.
Produces one JSON + one markdown file per (project, as_of date) in
reports/weekly/. This is the file you actually run weekly (or on a cron).

Usage:
    python src/runner.py --file data/S2P_Project.xlsx
    python src/runner.py --file data/S2P_Project.xlsx --as-of 2026-06-01
    python src/runner.py --file data/S2P_Project.xlsx --skip-llm
"""

import argparse
import json
from pprint import pprint
import re
from pathlib import Path
from datetime import datetime
from pprint import pprint

import features
import insights
from parser import load_project
from features import compute_all_features
from scorer import compute_rag
from narrator import narrate
from insights import build_insights


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _json_default(o):
    if isinstance(o, datetime):
        return o.isoformat()
    return str(o)


def run(file_path: str, as_of: datetime = None, skip_llm: bool = False, out_dir: str = "reports/weekly"):
    project_data = load_project(file_path)
    features = compute_all_features(project_data, as_of=as_of)
    scored = compute_rag(features)
    insights = build_insights(
        features,
        scored
    )
    print("\n========== INSIGHTS ==========")
    pprint(insights)
    print("==============================\n")
    print("\n========== FEATURES ==========")
    pprint(features)
    print("==============================\n")

    if skip_llm:
        narration = {
            "official_rag": scored["rag"],
            "reasoning": "[LLM narration skipped --skip-llm flag]",
            "flagged_for_review": False,
            "flag_reason": None,
            "data_gaps": [],
            "top_risks": [],
        }
    else:
        narration = narrate(project_data, features, scored, insights)

    effective_as_of = as_of or project_data.summary.get("Today's Date") or datetime.now()

    report = {
        "project_name": project_data.project_name,
        "source_file": project_data.source_file,
        "as_of_date": effective_as_of,
        "as_of_is_simulated": as_of is not None,
        "official_rag": narration["official_rag"],
        "scorer_detail": scored,
        "features": features,
        "insights": insights,
        "narration": {k: v for k, v in narration.items() if k != "official_rag"},
        "data_quality_notes": project_data.data_quality_notes,
    }

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = _slugify(project_data.project_name)
    date_tag = effective_as_of.strftime("%Y-%m-%d") if hasattr(effective_as_of, "strftime") else str(effective_as_of)
    base_name = f"{slug}_{date_tag}"

    json_path = out_dir / f"{base_name}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=_json_default)

    md_path = out_dir / f"{base_name}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(_render_markdown(report))

    return report, json_path, md_path


def _render_markdown(report: dict) -> str:
    rag = report["official_rag"]
    n = report["narration"]
    sim_note = " *(simulated as-of date -- see note below)*" if report["as_of_is_simulated"] else ""

    lines = [
        f"# {report['project_name']}",
        f"**Status as of {report['as_of_date']}{sim_note}: {rag}**",
        "",
        "## Summary",
        n["reasoning"],
        "",
    ]

    if n["flagged_for_review"]:
        lines += ["## ⚑ Flagged for Review", n["flag_reason"], ""]

    lines += ["## Top Risks"]
    lines += [f"- {r}" for r in n["top_risks"]] if n["top_risks"] else ["- None identified"]
    lines += ["", "## Data Gaps"]
    lines += [f"- {g}" for g in n["data_gaps"] + report["data_quality_notes"]]

    if report["as_of_is_simulated"]:
        lines += [
            "",
            "---",
            "*Note: as-of date was manually set to simulate a past weekly run. Task completion "
            "status reflects the file's actual current data, not true historical status on that "
            "date -- only the schedule-slippage expected-vs-actual calculation is backdated. "
            "This project data does not contain a real historical time series.*",
        ]

    return "\n".join(lines)


if __name__ == "__main__":
    parser_args = argparse.ArgumentParser()
    parser_args.add_argument("--file", required=True, help="Path to the project plan xlsx")
    parser_args.add_argument("--as-of", default=None, help="Simulated as-of date, YYYY-MM-DD")
    parser_args.add_argument("--skip-llm", action="store_true", help="Skip the Gemini call (fast, deterministic-only run)")
    args = parser_args.parse_args()

    as_of_dt = datetime.strptime(args.as_of, "%Y-%m-%d") if args.as_of else None

    report, json_path, md_path = run(args.file, as_of=as_of_dt, skip_llm=args.skip_llm)
    print(f"Official RAG: {report['official_rag']}")
    print(f"Written: {json_path}")
    print(f"Written: {md_path}")