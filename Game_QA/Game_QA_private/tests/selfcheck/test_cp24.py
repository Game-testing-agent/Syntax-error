import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from schemas import Finding

test_inputs = [
    ("Valid JSON", '{"verdict": "bug", "severity": "high", "confidence": 0.9, "title": "Test Bug", "explanation": "Test explanation"}'),
    ("JSON in markdown fences", '```json\n{"verdict": "bug", "title": "Test", "explanation": "Test"}\n```'),
    ("JSON with prose before it", 'Here is the finding:\n{"verdict": "bug", "title": "Test", "explanation": "Test"}'),
    ("Missing required field", '{"severity": "high", "title": "Only Title"}'),  # missing explanation
    ("Wrong enum value", '{"verdict": "bug", "severity": "severe", "title": "Test", "explanation": "Test"}'),
    ("Confidence 1.5", '{"verdict": "bug", "confidence": 1.5, "title": "Test", "explanation": "Test"}'),
    ("Empty string", ''),
]

print(f"{'Input Case':<28} | {'Parsed OK':<10} | {'Behavior'}")
print("-" * 75)

for label, raw in test_inputs:
    try:
        # If it's valid json text
        obj = json.loads(raw)
        f = Finding.model_validate(obj)
        print(f"{label:<28} | {'True':<10} | Successfully parsed: title='{f.title}'")
    except Exception as e:
        err_msg = f"{type(e).__name__}: {str(e).splitlines()[0]}"
        print(f"{label:<28} | {'False':<10} | Rejected properly: {err_msg[:45]}")

