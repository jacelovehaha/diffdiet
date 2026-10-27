"""Unit tests for diffdiet: parser, metrics, scoring, gate and CLI."""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent / "src")
)

from diffdiet.cli import main  # noqa: E402
from diffdiet.gate import DEFAULT_BUDGET, check_gate, load_config  # noqa: E402
from diffdiet.metrics import Metrics, compute_metrics  # noqa: E402
from diffdiet.parser import parse_diff  # noqa: E402
from diffdiet.scoring import diet_score  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

BASIC_DIFF = """\
diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,3 +1,4 @@
 import os
+import sys
 
-print("hi")
+print("hello")
"""

NEW_FILE_DIFF = """\
diff --git a/newmod.py b/newmod.py
new file mode 100644
--- /dev/null
+++ b/newmod.py
@@ -0,0 +1,2 @@
+def helper():
+    return 1
"""

DELETED_FILE_DIFF = """\
diff --git a/old.py b/old.py
deleted file mode 100644
--- a/old.py
+++ /dev/null
@@ -1,2 +0,0 @@
-def gone():
-    return 0
"""

MULTI_DIFF = """\
diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1,2 +1,2 @@
-x = 1
+x = 2
 y = 3
@@ -10,2 +10,3 @@
 p = 1
+q = 2
 r = 3
diff --git a/b.py b/b.py
--- a/b.py
+++ b/b.py
@@ -1,1 +1,1 @@
-old
+new
"""

PYPROJECT_DEP_DIFF = """\
diff --git a/pyproject.toml b/pyproject.toml
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -3,5 +3,6 @@
 [project]
 name = "demo"
 dependencies = [
     "click>=8",
+    "requests>=2.31",
 ]
"""

REQUIREMENTS_DEP_DIFF = """\
diff --git a/requirements.txt b/requirements.txt
new file mode 100644
--- /dev/null
+++ b/requirements.txt
@@ -0,0 +1,4 @@
+requests==2.31.0
+# a comment
+-r other.txt
+numpy>=1.26
"""

PACKAGE_JSON_DEP_DIFF = """\
diff --git a/package.json b/package.json
--- a/package.json
+++ b/package.json
@@ -2,6 +2,7 @@
   "name": "demo",
   "dependencies": {
     "react": "^18.2.0",
+    "lodash": "^4.17.21"
   },
   "scripts": {
"""

USED_TWICE_DIFF = """\
diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,3 +1,6 @@
 def main():
+    print(helper())
+
+def helper():
+    return 42
-    pass
"""


def metrics_of(text):
    return compute_metrics(parse_diff(text), text)


class ParserTests(unittest.TestCase):
    def test_basic_file_and_counts(self):
        files = parse_diff(BASIC_DIFF)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].path, "app.py")
        self.assertEqual(len(files[0].added_lines), 2)
        self.assertEqual(len(files[0].deleted_lines), 1)
        self.assertFalse(files[0].is_new)
        self.assertFalse(files[0].is_deleted)

    def test_new_file_detected(self):
        files = parse_diff(NEW_FILE_DIFF)
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].is_new)
        self.assertEqual(files[0].path, "newmod.py")
        self.assertEqual(len(files[0].added_lines), 2)

    def test_deleted_file_detected(self):
        files = parse_diff(DELETED_FILE_DIFF)
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].is_deleted)
        self.assertEqual(files[0].path, "old.py")
        self.assertEqual(len(files[0].deleted_lines), 2)

    def test_multiple_files_and_hunks(self):
        files = parse_diff(MULTI_DIFF)
        self.assertEqual(len(files), 2)
        self.assertEqual(len(files[0].hunks), 2)
        self.assertEqual(len(files[0].added_lines), 2)
        self.assertEqual(len(files[0].deleted_lines), 1)
        self.assertEqual(files[1].path, "b.py")

    def test_empty_diff(self):
        self.assertEqual(parse_diff(""), [])
        self.assertEqual(parse_diff("\n\n"), [])


class MetricsTests(unittest.TestCase):
    def test_line_and_file_metrics(self):
        m = metrics_of(BASIC_DIFF)
        self.assertEqual(m.added_lines, 2)
        self.assertEqual(m.deleted_lines, 1)
        self.assertEqual(m.net_lines, 1)
        self.assertEqual(m.files_touched, 1)
        self.assertEqual(m.new_files, 0)

    def test_churn_ratio(self):
        m = metrics_of(BASIC_DIFF)
        self.assertEqual(m.churn_ratio, 3.0)

    def test_pyproject_dependency_detected(self):
        m = metrics_of(PYPROJECT_DEP_DIFF)
        self.assertEqual(m.new_dependencies, ["requests"])

    def test_requirements_dependencies_detected(self):
        m = metrics_of(REQUIREMENTS_DEP_DIFF)
        self.assertEqual(m.new_dependencies, ["requests", "numpy"])

    def test_package_json_dependency_detected(self):
        m = metrics_of(PACKAGE_JSON_DEP_DIFF)
        self.assertEqual(m.new_dependencies, ["lodash"])

    def test_single_use_abstraction_is_suspect(self):
        m = metrics_of(NEW_FILE_DIFF)
        self.assertEqual(m.abstraction_suspects, ["helper"])

    def test_used_abstraction_is_not_suspect(self):
        m = metrics_of(USED_TWICE_DIFF)
        self.assertEqual(m.abstraction_suspects, [])


class ScoringTests(unittest.TestCase):
    def test_tiny_diff_scores_100(self):
        score, breakdown = diet_score(Metrics(added_lines=6))
        self.assertEqual(score, 100)
        self.assertEqual(breakdown, [])

    def test_bloated_metrics_score(self):
        m = Metrics(
            added_lines=57,
            new_files=1,
            new_dependencies=["fancylib"],
            abstraction_suspects=["a", "b", "c", "d"],
        )
        score, breakdown = diet_score(m)
        # 100 - 5 (lines) - 8 (new file) - 10 (dep) - 20 (suspects)
        self.assertEqual(score, 57)
        self.assertEqual(len(breakdown), 4)

    def test_score_floor_is_zero(self):
        m = Metrics(
            added_lines=100_000,
            new_files=50,
            new_dependencies=[f"dep{i}" for i in range(10)],
            abstraction_suspects=[f"s{i}" for i in range(10)],
            deleted_files=10,
        )
        score, _ = diet_score(m)
        self.assertEqual(score, 0)


class GateTests(unittest.TestCase):
    def test_defaults(self):
        config = dict(DEFAULT_BUDGET)
        self.assertEqual(config["max_new_deps"], 0)
        self.assertEqual(config["min_score"], 60)
        self.assertEqual(config["max_added_lines"], 300)

    def test_config_file_overrides_and_merges(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cfg.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"max_added_lines": 5}, fh)
            config = load_config(path)
        self.assertEqual(config["max_added_lines"], 5)
        self.assertEqual(config["max_new_files"], DEFAULT_BUDGET["max_new_files"])

    def test_gate_passes_within_budget(self):
        m = Metrics(added_lines=10, new_files=1)
        self.assertEqual(check_gate(m, 95, dict(DEFAULT_BUDGET)), [])

    def test_gate_fails_over_budget(self):
        m = Metrics(added_lines=10, new_dependencies=["requests"])
        violations = check_gate(m, 50, dict(DEFAULT_BUDGET))
        # new dep over 0 budget + score 50 below 60 minimum
        self.assertEqual(len(violations), 2)


class CliTests(unittest.TestCase):
    def run_cli(self, argv, stdin_text=None):
        out = io.StringIO()
        old_stdin = sys.stdin
        if stdin_text is not None:
            sys.stdin = io.StringIO(stdin_text)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                old_cwd = os.getcwd()
                os.chdir(tmp)  # isolate from any local .diffdiet.json
                try:
                    with contextlib.redirect_stdout(out):
                        code = main(argv)
                finally:
                    os.chdir(old_cwd)
        finally:
            sys.stdin = old_stdin
        return code, out.getvalue()

    def test_check_lean_example_passes(self):
        code, out = self.run_cli(["check", "--diff", str(EXAMPLES / "lean.diff")])
        self.assertEqual(code, 0)
        self.assertIn("Diet score: 100/100", out)
        self.assertIn("Gate: PASSED", out)

    def test_check_bloated_example_fails(self):
        code, out = self.run_cli(
            ["check", "--diff", str(EXAMPLES / "bloated.diff")]
        )
        self.assertEqual(code, 1)
        self.assertIn("Gate: FAILED", out)
        self.assertIn("fancylib", out)

    def test_score_command_always_exits_zero(self):
        code, out = self.run_cli(
            ["score", "--diff", str(EXAMPLES / "bloated.diff")]
        )
        self.assertEqual(code, 0)
        self.assertIn("57", out)

    def test_score_json_format(self):
        code, out = self.run_cli(
            ["check", "--diff", str(EXAMPLES / "lean.diff"),
             "--format", "json"]
        )
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["score"], 100)
        self.assertTrue(payload["gate"]["passed"])
        self.assertEqual(payload["metrics"]["added_lines"], 6)

    def test_reads_diff_from_stdin(self):
        lean_text = (EXAMPLES / "lean.diff").read_text(encoding="utf-8")
        code, out = self.run_cli(["score"], stdin_text=lean_text)
        self.assertEqual(code, 0)
        self.assertIn("100", out)


if __name__ == "__main__":
    unittest.main()
