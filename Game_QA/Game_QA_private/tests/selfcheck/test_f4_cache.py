import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from schemas import ReviewWindow, Event
import llm

# Check if window_cache_key exists
has_func = hasattr(llm, "window_cache_key")
print(f"llm.py has window_cache_key: {has_func}")

if not has_func:
    print("F4 TEST RESULT: FAIL (window_cache_key not implemented in llm.py)")
    sys.exit(1)

