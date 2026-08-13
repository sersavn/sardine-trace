from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def write_note(
    root: Path,
    name: str = "ex1",
    *,
    exercise: str = "1",
    include_attempt: bool = True,
) -> Path:
    exercise_dir = root / "exercises/probability/example/ch1"
    exercise_dir.mkdir(parents=True, exist_ok=True)
    (exercise_dir / f"{name}-problem.webp").write_bytes(b"webp problem")
    if include_attempt:
        (exercise_dir / f"{name}-attempt.webp").write_bytes(b"webp attempt")
    note = exercise_dir / f"{name}.md"
    note.write_text(
        f"""---
type: exercise
status: active
schema: tpl.pen-paper@0.2
created: 2026-08-13 10:00
source: example
subject: probability
topics: counting
chapter: "1"
exercise: "{exercise}"
attempt: 1
outcome: solved
time_spent_min: 12
problem_statement: {name}-problem.webp
solution_attempts:
  - {name}-attempt.webp
---
## LLM Comments
Correct.

## My Thoughts
Clear.
""",
        encoding="utf-8",
    )
    return note


def run_script(script: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / script)],
        cwd=cwd,
        text=True,
        capture_output=True,
    )


class PublicPipelineTests(unittest.TestCase):
    def test_valid_content_builds_all_indexes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(root)

            validation = run_script("validate.py", root)
            indexes = run_script("build_indexes.py", root)

            self.assertEqual(validation.returncode, 0, validation.stderr)
            self.assertEqual(indexes.returncode, 0, indexes.stderr)
            self.assertEqual(
                {path.name for path in (root / "generated").iterdir()},
                {"exercises.json", "activity.json", "topics.json", "analytics.json"},
            )
            analytics = json.loads((root / "generated/analytics.json").read_text())
            self.assertEqual(analytics["total_exercises"], 1)
            self.assertEqual(analytics["total_time_spent_min"], 12)

    def test_missing_solution_asset_fails_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(root, include_attempt=False)

            result = run_script("validate.py", root)

            self.assertEqual(result.returncode, 1)
            self.assertIn("referenced file does not exist", result.stdout)

    def test_duplicate_exercise_identity_fails_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_note(root, "first", exercise="1")
            write_note(root, "second", exercise="1")

            result = run_script("validate.py", root)

            self.assertEqual(result.returncode, 1)
            self.assertIn("duplicate exercise key", result.stdout)


if __name__ == "__main__":
    unittest.main()
