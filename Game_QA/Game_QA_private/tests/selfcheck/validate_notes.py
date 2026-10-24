import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from schemas import Finding
from loader import resolve_log_path, load_sessions

log_path = resolve_log_path()
sessions = load_sessions(log_path, stride=1)

for sid in ['session_1792777856_45957', 'session_1792785118_99684']:
    f_path = Path(f'results/agent_notes/{sid}_findings.json')
    if not f_path.exists():
        print(f'Missing {f_path}')
        continue
    raw_findings = json.loads(f_path.read_text(encoding='utf-8'))
    print(f'Validating {sid}: {len(raw_findings)} findings')
    
    sess = sessions[sid]
    existing_frames = set([e.frame for e in sess.events] + [s.frame for s in sess.snapshots])
    
    for i, item in enumerate(raw_findings):
        # 1. Pydantic validation
        f = Finding(**item)
        
        # 2. Verdict
        assert f.verdict.value in ['bug', 'unsure'], f'Invalid verdict {f.verdict}'
        
        # 3. Evidence frames exist
        for ef in f.evidence_frames:
            assert ef in existing_frames, f'Evidence frame {ef} not in session {sid}'
            
        # 4. Title length
        assert len(f.title) <= 80, f'Title too long ({len(f.title)}): {f.title}'
        
        # 5. Path
        assert f.path == 'path2', f'Path must be path2, got {f.path}'
        
        print(f'  Finding {i+1} PASSED: "{f.title}"')

print('ALL FINDINGS PASSED VALIDATION!')
