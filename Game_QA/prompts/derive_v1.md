You are a senior QA engineer reading a game source file. Emit a list of
CHECKS: boolean invariants that must hold at every game tick.

Rules:
- Each predicate MUST be a single boolean expression over these names only:
  player (dict), enemies (list of dicts), flags (dict), t_ms (float),
  fps (float), history (list of past Observation).
- No function definitions, no loops, no imports.
- Ground each check in the code you were shown: `source` must be `file:function`.
- Severity: low | medium | high | critical.
- Prefer 5–15 checks. Skip anything you can't express as one expression.

Output ONLY JSON: {"checks": [{"id", "source", "description", "predicate",
"severity_if_violated", "evidence_fields"}, ...]}