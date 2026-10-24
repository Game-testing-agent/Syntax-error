"""
Test that prompts/review_v1.md and llm.py contain zero leaked concrete values
identified in alignment_report.md (specific known bug frames, coordinates, exact line citations).
"""
import re
from pathlib import Path

def test_no_leaks_in_prompt_and_llm():
    root = Path(__file__).resolve().parent.parent.parent
    prompt_file = root / "prompts" / "review_v1.md"
    llm_file = root / "llm.py"

    assert prompt_file.exists(), f"Missing {prompt_file}"
    assert llm_file.exists(), f"Missing {llm_file}"

    prompt_text = prompt_file.read_text(encoding="utf-8")
    llm_text = llm_file.read_text(encoding="utf-8")

    forbidden_patterns = [
        r"Player\.gd:L76",
        r"Player\.gd:L176",
        r"Enemy\.gd:L30",
        r"Portal2D\.gd:L14",
        r"Enemy4",
        r"\b12722\b",
        r"\b13190\b",
        r"\b14140\b",
        r"\b14170\b",
        r"\b14200\b",
    ]

    errors = []
    for pattern in forbidden_patterns:
        if re.search(pattern, prompt_text):
            errors.append(f"prompts/review_v1.md contains leaked pattern: {pattern}")
        if re.search(pattern, llm_text):
            errors.append(f"llm.py contains leaked pattern: {pattern}")

    assert not errors, "\n".join(errors)
    print("PASS: test_no_leaks_in_prompt_and_llm passed without finding any leaked patterns.")

if __name__ == "__main__":
    test_no_leaks_in_prompt_and_llm()

