import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIT = ROOT / "Game_QA_audit"
PRIVATE = ROOT / "Game_QA_private"

# Clean and recreate
if AUDIT.exists():
    shutil.rmtree(AUDIT)
if PRIVATE.exists():
    shutil.rmtree(PRIVATE)

AUDIT.mkdir(parents=True, exist_ok=True)
PRIVATE.mkdir(parents=True, exist_ok=True)

# 1. Populate Game_QA_audit
# Pipeline python files
for pyfile in ["loader.py", "code_loader.py", "checker.py", "llm.py", "eval.py", "report.py", "schemas.py"]:
    shutil.copy2(ROOT / pyfile, AUDIT / pyfile)

# Tools
(AUDIT / "tools").mkdir(parents=True, exist_ok=True)
shutil.copy2(ROOT / "tools" / "native_submit.py", AUDIT / "tools" / "native_submit.py")
shutil.copy2(ROOT / "tools" / "sanitize_source.py", AUDIT / "tools" / "sanitize_source.py")

# Sanitized game_src
shutil.copytree(ROOT / "game_src", AUDIT / "game_src")

# Telemetry copy
(AUDIT / "telemetry").mkdir(parents=True, exist_ok=True)
real_telem = ROOT.parent / "Syntax-error" / "game_events.jsonl"
real_sample = ROOT.parent / "Syntax-error" / "sample_game_events.jsonl"
if real_telem.exists():
    shutil.copy2(real_telem, AUDIT / "telemetry" / "game_events.jsonl")
if real_sample.exists():
    shutil.copy2(real_sample, AUDIT / "telemetry" / "sample_game_events.jsonl")

# Data (checks only, no truth.json)
(AUDIT / "data").mkdir(parents=True, exist_ok=True)
if (ROOT / "data" / "checks.json").exists():
    shutil.copy2(ROOT / "data" / "checks.json", AUDIT / "data" / "checks.json")
if (ROOT / "data" / "check.json").exists():
    shutil.copy2(ROOT / "data" / "check.json", AUDIT / "data" / "check.json")

# Prompts
if (ROOT / "prompts").exists():
    shutil.copytree(ROOT / "prompts", AUDIT / "prompts")

# Skill
(AUDIT / ".agents" / "skills" / "game-qa").mkdir(parents=True, exist_ok=True)
if (ROOT / ".agents" / "skills" / "game-qa").exists():
    shutil.copytree(ROOT / ".agents" / "skills" / "game-qa", AUDIT / ".agents" / "skills" / "game-qa", dirs_exist_ok=True)

# .env without keys
(AUDIT / ".env").write_text("# Game_QA environment\n", encoding="utf-8")

# Empty results directory
(AUDIT / "results").mkdir(parents=True, exist_ok=True)

# 2. Populate Game_QA_private
(PRIVATE / "data").mkdir(parents=True, exist_ok=True)
if (ROOT / "data" / "truth.json").exists():
    shutil.copy2(ROOT / "data" / "truth.json", PRIVATE / "data" / "truth.json")

if (ROOT / "_private").exists():
    shutil.copytree(ROOT / "_private", PRIVATE / "_private")

if (ROOT / "tests").exists():
    shutil.copytree(ROOT / "tests", PRIVATE / "tests")

print("Created Game_QA_audit and Game_QA_private workspaces successfully.")
