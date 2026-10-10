"""Tests for yo_cleaner. Run: python3 -m unittest -v test_yo_cleaner"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import yo_cleaner as yc


class GuardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.guard = yc.Guard(allowed_roots=(self.tmp,))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_allows_path_inside_root(self):
        target = self.tmp / "cache"
        self.assertIsNone(self.guard.check(target))
        self.assertTrue(self.guard.is_allowed(target))

    def test_refuses_path_outside_root(self):
        with self.assertRaises(yc.SafetyRefusal) as ctx:
            self.guard.check(Path("/etc/passwd"))
        self.assertIn("outside the allowed roots", str(ctx.exception))

    def test_refuses_protected_directory_component(self):
        target = self.tmp / ".git" / "objects"
        with self.assertRaises(yc.SafetyRefusal) as ctx:
            self.guard.check(target)
        self.assertIn("protected directory", str(ctx.exception))

    def test_refuses_protected_extension(self):
        target = self.tmp / "app.exe"
        with self.assertRaises(yc.SafetyRefusal):
            self.guard.check(target)

    def test_refuses_system_root_even_if_allowed(self):
        # A user pointing the tool at C:\ must still not be able to eat Windows.
        guard = yc.Guard(allowed_roots=(Path("/"),))
        with self.assertRaises(yc.SafetyRefusal):
            guard.check(Path("/") / "Windows" / "System32" / "kernel32.dll")


class CandidateScanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.guard = yc.Guard(allowed_roots=(self.tmp,))
        (self.tmp / "__pycache__").mkdir()
        (self.tmp / "__pycache__" / "mod.cpython-311.pyc").write_bytes(b"x" * 100)
        (self.tmp / "keep.txt").write_text("important")
        (self.tmp / ".git").mkdir()
        (self.tmp / ".git" / "HEAD").write_text("ref")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_finds_pycache_and_measures_bytes(self):
        stats = yc.Stats()
        found = yc.find_candidates([self.tmp], ["__pycache__", "*.pyc"], self.guard, stats)
        paths = [c.path.name for c in found]
        self.assertIn("__pycache__", paths)
        cache = next(c for c in found if c.path.name == "__pycache__")
        self.assertEqual(cache.kind, "dir")
        self.assertEqual(cache.bytes, 100)
        self.assertEqual(stats.bytes_reclaimable, 100)

    def test_scan_leaves_everything_on_disk(self):
        before = sorted(p.name for p in self.tmp.iterdir())
        stats = yc.Stats()
        yc.find_candidates([self.tmp], ["__pycache__"], self.guard, stats)
        after = sorted(p.name for p in self.tmp.iterdir())
        self.assertEqual(before, after)

    def test_protected_dir_is_refused_at_execution(self):
        stats = yc.Stats()
        found = yc.find_candidates([self.tmp], [".git"], self.guard, stats)
        result = yc.execute(found, self.guard, apply=True, confirm_token="DELETE",
                            log_dir=self.tmp / "logs")
        self.assertEqual(result.stats.deleted, 0)
        self.assertEqual(result.stats.skipped, 1)
        self.assertTrue((self.tmp / ".git" / "HEAD").exists())
        self.assertIn("protected directory", result.refusals[0])


class ExecuteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.guard = yc.Guard(allowed_roots=(self.tmp,))
        self.junk = self.tmp / "node_modules"
        (self.junk / "pkg").mkdir(parents=True)
        (self.junk / "pkg" / "index.js").write_text("module.exports = 1;\n")
        self.keep = self.tmp / "src.py"
        self.keep.write_text("print('keep')\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _candidates(self):
        stats = yc.Stats()
        return yc.find_candidates([self.tmp], ["node_modules"], self.guard, stats)

    def test_dry_run_deletes_nothing(self):
        result = yc.execute(self._candidates(), self.guard, apply=False,
                            confirm_token=None, log_dir=self.tmp / "logs")
        self.assertFalse(result.armed)
        self.assertEqual(result.stats.deleted, 0)
        self.assertTrue(self.junk.exists())

    def test_apply_without_confirm_token_is_refused(self):
        with self.assertRaises(yc.SafetyRefusal) as ctx:
            yc.execute(self._candidates(), self.guard, apply=True,
                       confirm_token="yes", log_dir=self.tmp / "logs")
        self.assertIn("--confirm DELETE", str(ctx.exception))
        self.assertTrue(self.junk.exists())

    def test_apply_deletes_writes_log_and_keeps_other_files(self):
        result = yc.execute(self._candidates(), self.guard, apply=True,
                            confirm_token="DELETE", log_dir=self.tmp / "logs")
        self.assertEqual(result.stats.deleted, 1)
        self.assertFalse(self.junk.exists())
        self.assertTrue(self.keep.exists())
        self.assertIsNotNone(result.log_path)
        self.assertTrue(Path(result.log_path).exists())
        payload = json.loads(Path(result.log_path).read_text(encoding="utf-8"))
        self.assertEqual(payload["mode"], "clean")
        self.assertTrue(payload["armed"])
        self.assertEqual(payload["deletions"][0]["kind"], "dir")

    def test_undo_restores_deleted_files(self):
        result = yc.execute(self._candidates(), self.guard, apply=True,
                            confirm_token="DELETE", log_dir=self.tmp / "logs")
        self.assertFalse((self.junk / "pkg" / "index.js").exists())
        outcome = yc.undo(Path(result.log_path))
        self.assertEqual(outcome["restored"], 1)
        self.assertEqual(outcome["failed"], 0)
        restored = self.junk / "pkg" / "index.js"
        self.assertTrue(restored.exists())
        self.assertEqual(restored.read_text(), "module.exports = 1;\n")

    def test_file_deletion_and_undo_round_trip(self):
        stray = self.tmp / "debug.swp"
        stray.write_bytes(b"binary\x00data")
        stats = yc.Stats()
        found = yc.find_candidates([self.tmp], ["*.swp"], self.guard, stats)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].kind, "file")
        result = yc.execute(found, self.guard, apply=True, confirm_token="DELETE",
                            log_dir=self.tmp / "logs")
        self.assertFalse(stray.exists())
        yc.undo(Path(result.log_path))
        self.assertEqual(stray.read_bytes(), b"binary\x00data")


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "__pycache__").mkdir()
        (self.tmp / "__pycache__" / "a.pyc").write_bytes(b"z" * 10)
        self.old_home = os.environ.get("HOME")
        os.environ["HOME"] = str(self.tmp)

    def tearDown(self):
        if self.old_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self.old_home
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_scan_exits_zero_and_deletes_nothing(self):
        code = yc.main(["scan", "--root", str(self.tmp)])
        self.assertEqual(code, 0)
        self.assertTrue((self.tmp / "__pycache__" / "a.pyc").exists())

    def test_scan_json_reports_reclaimable_bytes(self):
        import io
        import contextlib

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = yc.main(["scan", "--root", str(self.tmp), "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertEqual(payload["mode"], "scan")
        self.assertEqual(payload["stats"]["bytes_reclaimable"], 10)

    def test_clean_without_apply_is_dry_run(self):
        code = yc.main(["clean", "--root", str(self.tmp)])
        self.assertEqual(code, 0)
        self.assertTrue((self.tmp / "__pycache__" / "a.pyc").exists())

    def test_protected_dir_is_skipped_not_failed(self):
        code = yc.main(
            ["scan", "--root", str(self.tmp), "--pattern", ".git"]
        )
        # No .git in the fixture, so nothing matches and the run still succeeds.
        self.assertEqual(code, 0)
        (self.tmp / ".git").mkdir()
        (self.tmp / ".git" / "config").write_text("[core]")
        code = yc.main(
            ["clean", "--root", str(self.tmp), "--pattern", ".git",
             "--apply", "--confirm", "DELETE"]
        )
        self.assertEqual(code, 0)  # skipped, not failed
        self.assertTrue((self.tmp / ".git" / "config").exists())

    def test_cli_undo_restores_after_armed_clean(self):
        """Regression: `undo` has no --root flag; main() used to crash on it."""
        import io
        import contextlib

        log_dir = self.tmp / "logs"
        code = yc.main(
            ["clean", "--root", str(self.tmp), "--apply", "--confirm", "DELETE",
             "--log-dir", str(log_dir)]
        )
        self.assertEqual(code, 0)
        self.assertFalse((self.tmp / "__pycache__" / "a.pyc").exists())
        log = sorted(log_dir.glob("run-*.json"))[-1]

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = yc.main(["undo", str(log)])
        self.assertEqual(code, 0)
        self.assertIn("restored 1 file(s)", buffer.getvalue())
        self.assertEqual(
            (self.tmp / "__pycache__" / "a.pyc").read_bytes(), b"z" * 10
        )

    def test_cli_undo_missing_log_returns_error_code(self):
        code = yc.main(["undo", str(self.tmp / "nope.json")])
        self.assertEqual(code, 3)

    def test_human_sizes(self):
        self.assertEqual(yc.human(512), "512 B")
        self.assertEqual(yc.human(2048), "2.0 KiB")
        self.assertEqual(yc.human(5 * 1024 * 1024), "5.0 MiB")


if __name__ == "__main__":
    unittest.main(verbosity=2)
