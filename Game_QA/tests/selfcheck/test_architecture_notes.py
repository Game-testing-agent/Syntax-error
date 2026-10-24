"""
Test verifying that results/selfcheck/architecture_notes.md accurately describes:
1. The native path (tools/native_submit.py)
2. The actual prompt used per mode
3. The real cache key fields (all 8 fields)
"""
from pathlib import Path

def test_architecture_notes_content():
    root = Path(__file__).resolve().parent.parent.parent
    notes_file = root / "results" / "selfcheck" / "architecture_notes.md"
    assert notes_file.exists(), f"Missing {notes_file}"

    text = notes_file.read_text(encoding="utf-8")

    # 1. Native path
    assert "tools/native_submit.py" in text
    assert "_cache_put" in text
    assert "review_window" in text

    # 2. Prompt per mode
    assert "Native Agent Mode" in text
    assert ".agents/skills/game-qa/SKILL.md" in text
    assert "External API Mode" in text
    assert "prompts/review_v1.md" in text

    # 3. Real cache key fields
    expected_fields = [
        "version",
        "session_id",
        "window_id",
        "events_digest",
        "snaps_digest",
        "code_digest",
        "prompt_digest",
        "evaluator_mode",
    ]
    for field in expected_fields:
        assert f"`{field}`" in text or f'"{field}"' in text or field in text, f"Missing field in doc: {field}"

    print("PASS: test_architecture_notes_content passed.")

if __name__ == "__main__":
    test_architecture_notes_content()

