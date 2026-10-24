import sys
import json
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from loader import resolve_log_path, load_sessions

log_path = resolve_log_path()
sessions = load_sessions(log_path, stride=1)

with open("results/eval_results.json", "r", encoding="utf-8") as f:
    eval_results = json.load(f)

total_citations = 0
valid_citations = 0
citation_details = []

for session_entry in eval_results:
    sid = session_entry.get("session_id")
    sess = sessions.get(sid)
    session_frames = set()
    if sess:
        session_frames = {e.frame for e in sess.events} | {s.frame for s in sess.snapshots}
    
    findings = session_entry.get("findings", [])
    for f in findings:
        title = f.get("title", "")
        frames = f.get("evidence_frames", [])
        code = f.get("suspected_code", "")
        
        # 1. Validate frames
        for fr in frames:
            total_citations += 1
            is_valid = fr in session_frames
            if is_valid:
                valid_citations += 1
            else:
                citation_details.append(f"INVALID FRAME: {fr} in '{title}' (not in session {sid})")
                
        # 2. Validate suspected code
        total_citations += 1
        # Extract filename and line number if present
        m = re.search(r"(\w+\.gd)(?::L?(\d+))?", code or "")
        if m:
            fname = m.group(1)
            line_no = int(m.group(2)) if m.group(2) else None
            matching_files = list(Path("game_src").rglob(fname))
            if matching_files:
                file_path = matching_files[0]
                with open(file_path, "r", encoding="utf-8") as gf:
                    lines = gf.readlines()
                if line_no is not None:
                    if 1 <= line_no <= len(lines):
                        valid_citations += 1
                    else:
                        citation_details.append(f"INVALID LINE: {code} in '{title}' (file has only {len(lines)} lines)")
                else:
                    valid_citations += 1  # File exists, no line specified
            else:
                citation_details.append(f"INVALID FILE: {fname} in '{title}' (file not found in game_src)")
        elif code and ("res://" in code or "GameLogger.gd" in code):
            # Known architectural reference
            valid_citations += 1
        else:
            citation_details.append(f"UNRECOGNIZED CODE FORMAT: {code} in '{title}'")

print(f"Total citations checked: {total_citations}")
print(f"Valid citations: {valid_citations}")
print(f"Invalid citations count: {len(citation_details)}")
for d in citation_details:
    print(f"  {d}")

pct = (valid_citations / total_citations * 100) if total_citations > 0 else 0
print(f"Validity percentage: {pct:.1f}%")
print("CP-35 RESULT:", "PASS" if valid_citations == total_citations else "FAIL")
