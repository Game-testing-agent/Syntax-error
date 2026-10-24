#!/usr/bin/env python3
"""Check-only source integrity & forbidden token scanner for the audit workspace.

Verifies:
1. Manifest integrity of game_src/ (no drift, extra, or missing files).
2. Scan for generic forbidden defect tokens across game_src/ and telemetry.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN_PATTERNS = [
    r"\bbugflag\w*",
    r"\binject\w*",
    r"\bsynthetic\w*",
    r"\bbenchmark\w*",
    r"\bseeded\w*",
    r"\bplanted\w*",
    r"\bknown[_\s]+bug\b",
    r"\bknown[_\s]+defect\b",
    r"\bbug_trigger\b",
    r"\blog_bug\w*",
]
FORBIDDEN_REGEX = re.compile("|".join(FORBIDDEN_PATTERNS), re.IGNORECASE)

ALLOWED_EXTENSIONS = {".gd", ".tscn", ".tres"}
IGNORED_DIRS = {".godot", ".import", ".git", "__pycache__"}


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def check_sanitized_source(
    target_dir: Path,
    manifest_path: Path | None = None,
    telemetry_path: Path | None = None,
) -> bool:
    """Verifies manifest integrity and scans for forbidden tokens."""
    m_path = manifest_path or (target_dir / ".manifest.json")
    if not m_path.exists():
        print(f"[check] FAIL: Manifest file not found at {m_path}")
        return False

    manifest: dict[str, str] = json.loads(m_path.read_text(encoding="utf-8"))
    drift_detected = False

    # 1. Manifest file existence and hash verification
    for rel_path, expected_hash in sorted(manifest.items()):
        actual_file = target_dir / rel_path
        if not actual_file.exists():
            print(f"[check] FAIL: Missing file from manifest: {rel_path}")
            drift_detected = True
            continue
        actual_hash = compute_sha256(actual_file)
        if actual_hash != expected_hash:
            print(f"[check] FAIL: Hash mismatch for file: {rel_path}")
            drift_detected = True

    # 2. Check for unregistered files in target directory
    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for f in files:
            if f == ".manifest.json":
                continue
            curr = Path(root) / f
            if curr.suffix not in ALLOWED_EXTENSIONS and curr.name != "project.godot":
                continue
            rel = str(curr.relative_to(target_dir)).replace("\\", "/")
            if rel not in manifest:
                print(f"[check] FAIL: Unregistered file found in target: {rel}")
                drift_detected = True

    manifest_status = "FAIL" if drift_detected else "PASS"
    print(f"[check] Manifest Integrity Check: {manifest_status}")

    # 3. Forbidden tokens scan across game_src
    forbidden_hits: list[str] = []

    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for f in files:
            if f == ".manifest.json":
                continue
            fpath = Path(root) / f
            try:
                lines = fpath.read_text(encoding="utf-8", errors="ignore").splitlines()
            except Exception:
                continue
            for idx, line in enumerate(lines, start=1):
                if FORBIDDEN_REGEX.search(line):
                    rel = str(fpath.relative_to(target_dir)).replace("\\", "/")
                    forbidden_hits.append(f"{rel}:{idx}")

    # 4. Forbidden tokens scan across telemetry if provided
    if telemetry_path and telemetry_path.exists():
        try:
            with open(telemetry_path, "r", encoding="utf-8", errors="ignore") as tf:
                for idx, line in enumerate(tf, start=1):
                    if FORBIDDEN_REGEX.search(line):
                        forbidden_hits.append(f"{telemetry_path.name}:{idx}")
        except Exception:
            pass

    token_status = "PASS" if not forbidden_hits else "FAIL"
    print(f"[check] Forbidden Tokens Scan: {token_status} (hits: {len(forbidden_hits)})")

    if forbidden_hits:
        print("[check] Forbidden token location hits (file:line):")
        for hit in forbidden_hits[:20]:
            print(f"  {hit}")
        if len(forbidden_hits) > 20:
            print(f"  ... and {len(forbidden_hits) - 20} more hits")

    return not drift_detected and len(forbidden_hits) == 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Check game_src Integrity & Scan for Forbidden Tokens")
    parser.add_argument("--check", action="store_true", default=True, help="Run manifest verification and token scan")
    parser.add_argument("--target", type=str, default=str(ROOT / "game_src"), help="Target directory to check")
    parser.add_argument("--manifest", type=str, default=None, help="Manifest path")
    parser.add_argument("--telemetry", type=str, default=None, help="Telemetry path to scan")

    args = parser.parse_args()
    ok = check_sanitized_source(
        Path(args.target),
        Path(args.manifest) if args.manifest else None,
        Path(args.telemetry) if args.telemetry else None,
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
