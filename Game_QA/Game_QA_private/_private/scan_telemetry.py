import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TELEMETRY = ROOT.parent / "Syntax-error" / "game_events.jsonl"
SAMPLE = ROOT.parent / "Syntax-error" / "sample_game_events.jsonl"

def check_telemetry(p: Path):
    if not p.exists():
        print(f"Telemetry file {p} does not exist.")
        return
    print(f"\nAnalyzing telemetry: {p.name}")
    event_names = set()
    bug_trigger_events = []
    anomaly_events = []
    has_flag_fields = []
    
    with open(p, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            if not line.strip():
                continue
            ev = json.loads(line)
            en = ev.get("event_name") or ev.get("event") or ""
            event_names.add(en)
            if "bug" in en.lower():
                bug_trigger_events.append((idx, ev.get("physics_frame"), en, ev.get("data") or ev.get("payload")))
            if ev.get("category") == "anomaly" or "anomaly" in en.lower():
                anomaly_events.append((idx, ev.get("physics_frame"), en, ev.get("data") or ev.get("payload")))
            
            # Check if any data/payload key or value mentions BugFlags or flag names
            s = json.dumps(ev)
            if any(k in s.lower() for k in ["bugflags", "bug_flags", "map1_", "map2_", "map3_", "map4_"]):
                has_flag_fields.append((idx, ev))

    print(f"Total distinct event types: {len(event_names)}")
    print(f"Distinct events: {sorted(list(event_names))}")
    print(f"Total 'bug' events (e.g. bug_trigger): {len(bug_trigger_events)}")
    if bug_trigger_events:
        print("Sample bug_trigger data:")
        for b in bug_trigger_events[:5]:
            print(f"  Line {b[0]} (frame {b[1]}): {b[2]} -> {b[3]}")
    print(f"Total events with flag field names: {len(has_flag_fields)}")

check_telemetry(TELEMETRY)
if SAMPLE.exists():
    check_telemetry(SAMPLE)

