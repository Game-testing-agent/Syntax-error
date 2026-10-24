# Ground Truth Scoring Proposal

## 1. Current State of `data/truth.json`
- **Sessions Covered**: `session_1792580000_12345` (8 expected bugs) and `session_1792693950_44822` (0 expected bugs).
- **Available Fields**: `title` (str), `should_be_caught_by` (str).
- **Missing Fields**:
  - `frames` / `evidence_frames` (None)
  - `suspected_code` / `suspected_file` (None)
  - `category` (None)
  - `severity` (None)
- **Target Session**: `session_1792777856_45957` (currently has 0 entries in `data/truth.json`).

---

## 2. Proposed Matching Rule (for `eval.py:score_session`)

A candidate finding $F$ matches an expected truth bug $T$ if and only if **ALL** of the following conditions hold:

1. **Session Alignment**:
   - $F$ belongs to the exact same `session_id` as $T$.
2. **Semantic / Category Alignment**:
   - Either normalized title similarity matches:
     $$\text{similarity}(\text{norm}(F.\text{title}), \text{norm}(T.\text{title})) \ge 0.70$$
   - OR normalized title substring matches (without explanation substring matching):
     $$\text{norm}(T.\text{title}) \subseteq \text{norm}(F.\text{title}) \quad\text{or}\quad \text{norm}(F.\text{title}) \subseteq \text{norm}(T.\text{title})$$
   - OR $F.\text{category} == T.\text{category}$ (when category is provided).
3. **Evidence Grounding (At Least One Required)**:
   - **Temporal Frame Proximity**: At least one frame $f \in F.\text{evidence\_frames}$ falls within a tolerance window of a truth frame $t \in T.\text{evidence\_frames}$:
     $$\min_{f \in F, t \in T} |f - t| \le 120 \text{ physics frames (approx. } 2.0\text{s)}$$
   - **Code Attribution**: The normalized `suspected_code` file and symbol/function match:
     $$\text{file}(F.\text{suspected\_code}) == \text{file}(T.\text{suspected\_code})$$
     $$\text{and}\quad (\text{func}(F.\text{suspected\_code}) == \text{func}(T.\text{suspected\_code}) \text{ or } |\text{line}_F - \text{line}_T| \le 10)$$

### Elimination of Explanation Matching
The previous check `or exp.title.lower() in f["explanation"].lower()` is **completely removed**. Findings that casually mention a keyword in prose without meeting the criteria will not be counted as matches.

### False Positive Accounting
Any candidate finding produced by Path 1 or Path 2 that fails to match any expected truth bug is counted as a **false positive**.

---

## 3. Required Ground Truth Schema Enrichment

To implement this matching rule, each entry in `expected_bugs` in `data/truth.json` should have the following structure:
```json
{
  "title": "unexpected_score_change",
  "category": "anomaly",
  "should_be_caught_by": "path1",
  "evidence_frames": [578, 861, 964, 1714, 1887, 3805],
  "suspected_code": "PlayerData.gd:set_score",
  "severity": "medium"
}
```

