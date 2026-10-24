#!/usr/bin/env python3
"""Unit tests for tools/sanitize_source.py.

Verifies:
1. A clean tree matching manifest passes.
2. A planted forbidden token fails.
3. An edited file (hash mismatch) fails.
4. An extra unmanifested file fails.
5. A missing file fails.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

# Add repo root to path
ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT))

from tools.sanitize_source import check_sanitized_source, compute_sha256


class TestSanitizeSource(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_sanitize_"))
        self.clean_file = self.test_dir / "Actors" / "TestActor.gd"
        self.clean_file.parent.mkdir(parents=True, exist_ok=True)
        self.clean_file.write_text("extends Node\nfunc _ready():\n\tpass\n", encoding="utf-8")

        # Generate manifest
        self.manifest = {
            "Actors/TestActor.gd": compute_sha256(self.clean_file)
        }
        self.manifest_file = self.test_dir / ".manifest.json"
        self.manifest_file.write_text(json.dumps(self.manifest), encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_clean_tree_passes(self):
        """A clean tree matching the manifest must pass with 0 hits."""
        ok = check_sanitized_source(self.test_dir, self.manifest_file)
        self.assertTrue(ok, "Clean tree should pass manifest and token scan")

    def test_planted_forbidden_token_fails(self):
        """A file with a forbidden token (e.g. bugflag) must fail token scan."""
        # Plant forbidden token while keeping hash valid by updating manifest
        self.clean_file.write_text("extends Node\n# This is a synthetic bugflag test\n", encoding="utf-8")
        self.manifest["Actors/TestActor.gd"] = compute_sha256(self.clean_file)
        self.manifest_file.write_text(json.dumps(self.manifest), encoding="utf-8")

        ok = check_sanitized_source(self.test_dir, self.manifest_file)
        self.assertFalse(ok, "Tree with forbidden token must fail")

    def test_edited_file_fails_manifest(self):
        """A file modified after manifest generation must fail hash check."""
        # Modify file without updating manifest
        self.clean_file.write_text("extends Node\n# benign modification\n", encoding="utf-8")
        ok = check_sanitized_source(self.test_dir, self.manifest_file)
        self.assertFalse(ok, "Tree with hash drift must fail manifest check")

    def test_extra_file_fails_manifest(self):
        """An extra unregistered file must fail manifest check."""
        extra = self.test_dir / "Unregistered.gd"
        extra.write_text("extends Node\n", encoding="utf-8")
        ok = check_sanitized_source(self.test_dir, self.manifest_file)
        self.assertFalse(ok, "Tree with unmanifested file must fail")

    def test_missing_file_fails_manifest(self):
        """A missing manifested file must fail manifest check."""
        self.clean_file.unlink()
        ok = check_sanitized_source(self.test_dir, self.manifest_file)
        self.assertFalse(ok, "Tree with missing manifested file must fail")


if __name__ == "__main__":
    unittest.main()

