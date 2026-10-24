#!/usr/bin/env python3
"""Ground Truth Scoring Engine for Game_QA (Private Side).

Enforces the F5 matching specification with three finding buckets:
1. MATCHED: Ground truth defects matched 1-to-1 to findings per F5 matching rules.
2. FALSE_POSITIVE: Unmatched findings that the reviewer has explicitly marked
   as 'false_positive' in Game_QA_private/data/adjudication.json.
3. NEEDS_REVIEW: All unmatched findings not yet adjudicated.
   Lists file:line, frames, and source label for review.

Reads Game_QA_audit/results strictly read-only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

FRAME_TOLERANCE_FRAMES = 120

# Aliases between ground truth specifications and sanitized codebase identifiers
FUNCTION_ALIASES: dict[str, str] = {
    "trigger_lava_contact": "handle_surface_hazard",
    "handle_surface_hazard": "trigger_lava_contact",
}


def normalize_code(code_str: Optional[str]) -> tuple[str, str]:
    """Extracts (canonical_file_basename, function_name) from code locator string."""
    if not code_str:
        return "", ""
    s = str(code_str).strip()
    s = re.sub(r":\d+$", "", s)
    s = re.sub(r"\s*\(.*?\)$", "", s)
    if ":" in s:
        parts = s.split(":", 1)
        file_part = Path(parts[0]).name
        func_part = parts[1].strip()
        return file_part, func_part
    if s.endswith((".gd", ".tscn")):
        return Path(s).name, ""
    return "", s


def load_truth(truth_path: Path) -> dict[str, dict]:
    """Loads ground truth from JSON file."""
    if not truth_path.exists():
        raise FileNotFoundError(f"Truth file not found: {truth_path}")
    raw = json.loads(truth_path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def load_adjudication(adjudication_path: Path) -> set[str]:
    """Loads set of finding identifiers or titles marked as false positives."""
    if not adjudication_path.exists():
        return set()
    try:
        raw = json.loads(adjudication_path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return set(str(x).strip().lower() for x in raw)
        elif isinstance(raw, dict):
            fps = set()
            # If formatted as {"false_positives": [...]}
            if "false_positives" in raw and isinstance(raw["false_positives"], list):
                for item in raw["false_positives"]:
                    if isinstance(item, str):
                        fps.add(item.strip().lower())
                    elif isinstance(item, dict) and "title" in item:
                        fps.add(str(item["title"]).strip().lower())
            # If formatted as {"finding_key": "false_positive"}
            for k, v in raw.items():
                if isinstance(v, str) and v.lower() == "false_positive":
                    fps.add(k.strip().lower())
            return fps
        return set()
    except Exception as exc:
        print(f"[score] Warning: could not parse adjudication file: {exc}", file=sys.stderr)
        return set()


def is_adjudicated_fp(finding: dict, adjudicated_fps: set[str]) -> bool:
    """Checks whether a finding matches any entry in the adjudication set."""
    if not adjudicated_fps:
        return False
    title = str(finding.get("title", "")).strip().lower()
    code = str(finding.get("suspected_code", "")).strip().lower()
    key = f"{title}|{code}"
    return title in adjudicated_fps or code in adjudicated_fps or key in adjudicated_fps


def score_session(findings: list[dict], truth: Optional[dict], adjudicated_fps: set[str]) -> dict:
    """Scores findings against ground truth using F5 one-to-one matching, bucketed into:
    - MATCHED
    - FALSE_POSITIVE (explicitly adjudicated)
    - NEEDS_REVIEW (unmatched, awaiting review)
    """
    if not truth:
        # No ground truth for this session
        needs_review = []
        false_positives = []
        for f in findings:
            if is_adjudicated_fp(f, adjudicated_fps):
                false_positives.append(f)
            else:
                needs_review.append(f)
        return {
            "matched": [],
            "needs_review": needs_review,
            "false_positives": false_positives,
            "n_expected": 0,
            "tp": 0,
            "fp": len(false_positives),
            "fn": 0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
        }

    sid = truth.get("session_id", "")
    expected_bugs = truth.get("expected_bugs", [])

    # Validate that truth entries have evidence grounding (frames or suspected code)
    for exp in expected_bugs:
        exp_title = exp.get("title", "")
        exp_frames = exp.get("evidence_frames") or ([exp.get("frame_approx")] if exp.get("frame_approx") is not None else [])
        exp_code = exp.get("suspected_code")
        if not exp_frames and not exp_code:
            raise ValueError(
                f"[score] Truth validation failed: entry '{exp_title}' in session '{sid}' "
                f"lacks both evidence_frames and suspected_code grounding."
            )

    matched = []
    used_finding_indices: set[int] = set()

    for exp in expected_bugs:
        exp_title = exp.get("title", "").strip()
        exp_cat = exp.get("category", "").strip().lower()
        exp_frames = exp.get("evidence_frames") or ([exp.get("frame_approx")] if exp.get("frame_approx") is not None else [])
        exp_code = exp.get("suspected_code")
        exp_file, exp_func = normalize_code(exp_code)

        matched_finding_idx: Optional[int] = None

        for idx, f in enumerate(findings):
            if idx in used_finding_indices:
                continue

            # Unsure or non-bug verdicts are never counted as hits
            verdict = f.get("verdict")
            if verdict not in ("bug", "Verdict.bug"):
                continue

            # 1. Title or category similarity check
            norm_exp_title = exp_title.lower()
            norm_f_title = f.get("title", "").lower()
            title_match = (
                norm_exp_title in norm_f_title
                or norm_f_title in norm_exp_title
                or (bool(exp_cat) and exp_cat in norm_f_title)
            )

            if not title_match:
                continue

            # 2. Evidence Grounding: frame proximity OR file+function match
            frame_match = False
            f_frames = f.get("evidence_frames") or []
            if exp_frames and f_frames:
                frame_match = any(
                    abs(ff - tf) <= FRAME_TOLERANCE_FRAMES
                    for ff in f_frames
                    for tf in exp_frames
                )

            code_match = False
            if exp_file:
                f_file, f_func = normalize_code(f.get("suspected_code"))
                if f_file and f_file == exp_file:
                    if not exp_func or not f_func or f_func == exp_func or FUNCTION_ALIASES.get(f_func) == exp_func:
                        code_match = True

            if frame_match or code_match:
                matched_finding_idx = idx
                break

        if matched_finding_idx is not None:
            used_finding_indices.add(matched_finding_idx)
            hit = findings[matched_finding_idx]
            matched.append({
                "expected": exp_title,
                "found": True,
                "finding_title": hit.get("title"),
                "path": hit.get("path"),
                "finding_idx": matched_finding_idx,
            })
        else:
            matched.append({
                "expected": exp_title,
                "found": False,
                "finding_title": None,
                "path": None,
                "finding_idx": None,
            })

    # Unmatched findings partition into FALSE_POSITIVE (adjudicated) vs NEEDS_REVIEW
    false_positives = []
    needs_review = []

    for i in range(len(findings)):
        if i in used_finding_indices:
            continue
        f = findings[i]
        if is_adjudicated_fp(f, adjudicated_fps):
            false_positives.append(f)
        else:
            needs_review.append(f)

    tp = sum(1 for m in matched if m["found"])
    fn = len(expected_bugs) - tp
    fp = len(false_positives)

    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

    return {
        "session_id": sid,
        "n_expected": len(expected_bugs),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "matched": matched,
        "needs_review": needs_review,
        "false_positives": false_positives,
    }


def score_all_results(
    results_path: Path,
    truth_path: Path,
    adjudication_path: Path,
    output_path: Optional[Path] = None,
) -> dict:
    """Reads results read-only, classifies findings into 3 buckets, and prints summary."""
    if not results_path.exists():
        raise FileNotFoundError(f"Results file not found at {results_path}")

    # Read strictly read-only
    with open(results_path, "r", encoding="utf-8") as rf:
        raw_results = json.load(rf)

    truth_map = load_truth(truth_path)
    adjudicated_fps = load_adjudication(adjudication_path)

    scored_sessions = []
    tot_matched = 0
    tot_needs_review = 0
    tot_false_positives = 0
    tot_expected = 0

    results_list = raw_results if isinstance(raw_results, list) else [raw_results]

    for item in results_list:
        sid = item.get("session_id", "")
        findings = item.get("findings", [])
        truth_entry = truth_map.get(sid)

        res = score_session(findings, truth_entry, adjudicated_fps)
        scored_sessions.append(res)

        tot_matched += res["tp"]
        tot_needs_review += len(res["needs_review"])
        tot_false_positives += len(res["false_positives"])
        tot_expected += res["n_expected"]

    summary = {
        "total_sessions": len(scored_sessions),
        "counts": {
            "MATCHED": tot_matched,
            "NEEDS_REVIEW": tot_needs_review,
            "FALSE_POSITIVE": tot_false_positives,
            "TOTAL_FINDINGS": tot_matched + tot_needs_review + tot_false_positives,
            "TOTAL_EXPECTED": tot_expected,
        },
        "sessions": scored_sessions,
    }

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"[score] Wrote score report to {output_path}")

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Game_QA Audit Results against Ground Truth (F5 Matching + 3-Bucket Classification)")
    parser.add_argument("--results", type=str, default="QA_audit_clean/results/eval_results.json", help="Path to eval_results.json (read-only)")
    parser.add_argument("--truth", type=str, default="Game_QA_private/data/truth.json", help="Path to truth.json")
    parser.add_argument("--adjudication", type=str, default="Game_QA_private/data/adjudication.json", help="Path to private adjudication.json")
    parser.add_argument("--out", type=str, default=None, help="Path to output scoring JSON")

    args = parser.parse_args()
    summary = score_all_results(
        results_path=Path(args.results),
        truth_path=Path(args.truth),
        adjudication_path=Path(args.adjudication),
        output_path=Path(args.out) if args.out else None,
    )

    counts = summary["counts"]
    print("=" * 70)
    print("GROUND TRUTH SCORING REPORT (F5 SPEC & 3-BUCKET CLASSIFICATION)")
    print("=" * 70)
    print(f"MATCHED:        {counts['MATCHED']}")
    print(f"NEEDS_REVIEW:   {counts['NEEDS_REVIEW']}")
    print(f"FALSE_POSITIVE: {counts['FALSE_POSITIVE']}")
    print(f"TOTAL FINDINGS: {counts['TOTAL_FINDINGS']} (Expected Ground Truth: {counts['TOTAL_EXPECTED']})")
    print("=" * 70)

    # List details for NEEDS_REVIEW findings across sessions
    has_needs_review = False
    for sess in summary["sessions"]:
        nr_list = sess.get("needs_review", [])
        if nr_list:
            if not has_needs_review:
                print("\n[NEEDS_REVIEW FINDINGS]")
                has_needs_review = True
            print(f"--- Session: {sess.get('session_id')} ({len(nr_list)} finding(s)) ---")
            for idx, f in enumerate(nr_list, 1):
                code = f.get("suspected_code") or "Unknown:0"
                frames = f.get("evidence_frames") or []
                source = f.get("path") or "unspecified"
                title = f.get("title") or "Untitled"
                print(f"  {idx}. file:line: {code:<35} | frames: {str(frames):<20} | source: {source:<6} | title: {title}")

    if not has_needs_review:
        print("\n[NEEDS_REVIEW]: None")
    print("=" * 70)


if __name__ == "__main__":
    main()
