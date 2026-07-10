#!/usr/bin/env python3
"""Small stdlib checks for the central SuperGoal model-profile synchronizer."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from sync_model_profile import (
    ASSETS,
    load_profile,
    main,
    planned_updates,
    validate_local_model_catalog,
    write_updates,
)


PROFILE = """\
[controller]
model = "controller-model"
reasoning_effort = "high"
[researcher]
model = "research-model"
reasoning_effort = "xhigh"
[executor]
model = "executor-model"
reasoning_effort = "max"
[reviewer]
model = "review-model"
reasoning_effort = "medium"
"""


class ModelProfileTests(unittest.TestCase):
    def _root(self, directory):
        root = Path(directory)
        for relative, _ in ASSETS:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('model = "old"\nmodel_reasoning_effort = "low"\n', encoding="utf-8")
        profile_path = root / "config" / "model-profile.toml"
        profile_path.write_text(PROFILE, encoding="utf-8")
        return root, profile_path

    def test_profile_updates_every_generated_asset_then_converges(self):
        with tempfile.TemporaryDirectory() as directory:
            root, profile_path = self._root(directory)
            updates = planned_updates(root, load_profile(profile_path))
            self.assertEqual(len(updates), len(ASSETS))
            write_updates(updates)
            self.assertEqual(planned_updates(root, load_profile(profile_path)), {})
            self.assertIn('model = "executor-model"', (root / "config/supergoal_luna_executor.toml").read_text())
            self.assertIn('model_reasoning_effort = "medium"', (root / "config/supergoal_reviewer.toml").read_text())

    def test_invalid_effort_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root, profile_path = self._root(directory)
            profile_path.write_text(PROFILE.replace('reasoning_effort = "high"', 'reasoning_effort = "very-high"', 1), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "reasoning_effort"):
                load_profile(profile_path)

    def test_catalog_rejects_unsupported_luna_ultra_pair(self):
        with tempfile.TemporaryDirectory() as directory:
            root, profile_path = self._root(directory)
            profile_path.write_text(
                PROFILE.replace('model = "executor-model"', 'model = "gpt-5.6-luna"').replace(
                    'reasoning_effort = "max"', 'reasoning_effort = "ultra"'
                ),
                encoding="utf-8",
            )
            catalog = {
                "controller-model": {"high"},
                "research-model": {"xhigh"},
                "gpt-5.6-luna": {"low", "medium", "high", "xhigh", "max"},
                "review-model": {"medium"},
            }
            problems = validate_local_model_catalog(load_profile(profile_path), catalog)
            self.assertEqual(len(problems), 1)
            self.assertIn("[executor].reasoning_effort 'ultra'", problems[0])

    def test_unknown_profile_sections_and_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root, profile_path = self._root(directory)
            profile_path.write_text(PROFILE + '\n[discussor]\nmodel = "unused"\nreasoning_effort = "high"\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "discussor.*reviewer"):
                load_profile(profile_path)
            profile_path.write_text(PROFILE + 'unused = "value"\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsupported key"):
                load_profile(profile_path)

    def test_write_and_check_are_mutually_exclusive(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                main(["--write", "--check"])
        self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
