"""Every command that mutates a study records the code that did it."""
import json
import os
import shutil
import tempfile
import unittest

from hypelysis import cli, orchestrate, provenance
from hypelysis.providers import Replay

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")
DOC = os.path.join(FIXTURES, "sprocket.md")
EXTRACTION = os.path.join(FIXTURES, "sprocket-extraction.jsonl")


class TestCode(unittest.TestCase):
    def test_code_names_the_package_and_interpreter(self):
        info = provenance.code()
        self.assertTrue(info["hypelysis"])
        self.assertTrue(info["python"])

    def test_a_git_checkout_also_reports_its_commit(self):
        """An editable install runs from a checkout and can name its commit; an
        installed wheel cannot, and says nothing rather than guessing."""
        info = provenance.code()
        if "git_sha" in info:
            self.assertRegex(info["git_sha"], r"^[0-9a-f]{7,}$")
            self.assertIn("git_dirty", info)

    def test_describe_admits_when_nothing_was_recorded(self):
        self.assertIn("unrecorded", provenance.describe({}))
        self.assertIn("unrecorded", provenance.describe(None))

    def test_describe_flags_a_dirty_checkout(self):
        clean = provenance.describe({"hypelysis": "0.1.0", "git_sha": "abc1234"})
        dirty = provenance.describe({"hypelysis": "0.1.0", "git_sha": "abc1234",
                                     "git_dirty": True})
        self.assertNotIn("DIRTY", clean)
        self.assertIn("DIRTY", dirty)


class TestSettings(unittest.TestCase):
    def test_the_settings_that_shape_a_run_are_kept(self):
        s = provenance.settings({"prompt_packaging": "session-primer",
                                 "foundation_view": "lean", "note_cap": 4,
                                 "extractors": 3, "irrelevant": "plumbing"})
        self.assertEqual(s["foundation_view"], "lean")
        self.assertEqual(s["note_cap"], 4)
        self.assertNotIn("irrelevant", s)

    def test_only_roles_that_differ_from_the_default_model_are_listed(self):
        s = provenance.settings({"default": {"model": "sonnet"},
                                 "roles": {"skeptic": {"model": "opus"},
                                           "reader": {"model": "sonnet"},
                                           "_example": {"model": "llama"}}})
        self.assertEqual(s["models"], {"default": "sonnet", "skeptic": "opus"})


class TestStamping(unittest.TestCase):
    def setUp(self):
        Replay.reset()
        self.dir = tempfile.mkdtemp()
        self.study = os.path.join(self.dir, "study")

    def tearDown(self):
        Replay.reset()
        shutil.rmtree(self.dir, ignore_errors=True)

    def invocations(self):
        p = os.path.join(self.study, "log", "invocations.jsonl")
        return [json.loads(l) for l in open(p) if l.strip()]

    def test_init_records_itself(self):
        cli.main([self.study, "init", DOC, "--view", "lean"])
        recs = self.invocations()
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["command"], "init")
        self.assertEqual(recs[0]["settings"]["foundation_view"], "lean")
        self.assertTrue(recs[0]["at"])
        state = json.load(open(os.path.join(self.study, "state.json")))
        self.assertEqual(state["provenance"]["command"], "init")

    def test_a_run_is_stamped_before_it_spends_anything(self):
        cli.main([self.study, "init", DOC,
                  "--set", "default.provider=replay",
                  "--set", f"default.fixture={EXTRACTION}"])
        with self.assertRaises(SystemExit):
            cli.main([self.study, "run"])
        commands = [r["command"] for r in self.invocations()]
        self.assertEqual(commands, ["init", "run"])
        state = json.load(open(os.path.join(self.study, "state.json")))
        self.assertEqual(state["provenance"]["command"], "run")
        self.assertIn("retry_budget", state["provenance"]["settings"])
        self.assertEqual(state["provenance"]["argv"][-1], "run")

    def test_owner_decisions_are_stamped_too(self):
        cli.main([self.study, "init", DOC])
        cli.main([self.study, "resolve", "widget", "adopt the plain reading"])
        cli.main([self.study, "approve"])
        self.assertEqual([r["command"] for r in self.invocations()],
                         ["init", "resolve", "approve"])

    def test_reading_a_study_leaves_no_record(self):
        cli.main([self.study, "init", DOC])
        cli.main([self.study, "status"])
        cli.main([self.study, "report"])
        self.assertEqual([r["command"] for r in self.invocations()], ["init"])

    def test_status_and_report_name_the_code(self):
        cli.main([self.study, "init", DOC])
        shown = cli.report_mod.build(self.study)          # terminal rendering
        self.assertIn("code      hypelysis", shown)
        filed = open(os.path.join(self.study, "RUN-REPORT.md")).read()
        self.assertIn("Code: hypelysis", filed)           # the file is the record

    def test_a_study_advanced_by_two_versions_says_so(self):
        cli.main([self.study, "init", DOC])
        p = os.path.join(self.study, "log", "invocations.jsonl")
        with open(p, "a") as f:
            f.write(json.dumps({"command": "run", "hypelysis": "0.1.0",
                                "git_sha": "aaaaaaa"}) + "\n")
            f.write(json.dumps({"command": "run", "hypelysis": "0.2.0",
                                "git_sha": "bbbbbbb"}) + "\n")
        text = cli.report_mod.build(self.study)
        self.assertIn("2 different versions", text)


if __name__ == "__main__":
    unittest.main()
