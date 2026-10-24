import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from schemas import Finding, Verdict, Severity
import eval as eval_module

# Check if dedupe_finding_key exists
has_func = hasattr(eval_module, "dedupe_finding_key")
print(f"eval.py has dedupe_finding_key: {has_func}")

if not has_func:
    print("F6 TEST RESULT: FAIL (dedupe_finding_key not implemented)")
    sys.exit(1)

