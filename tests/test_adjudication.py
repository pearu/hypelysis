"""Escalations that are not the owner's to make.

The chair escalates when a choice looks like the owner's. This stage tests the
options first: if the document itself refutes every rival, the run settles it
with reasons. If it does not, the choice stays the owner's — unless the run was
told to keep going, in which case it picks and says so, loudly and in writing.
"""
import json
import os
import shutil
import tempfile
import unittest

from hypelysis import cli, orchestrate

DOC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "sprocket.md")

ESCALATION = {"decision": "escalate", "failed": ["skeptic"],
              "proposal": {"move": "entry", "payload": "### widget\nKind: base\n"},
              "verdicts": {},
              "chair": {"decision": "escalate",
                        "choice": "Option A: a widget is one value. Option B: a widget "
                                  "is one attribute. Option C: declare the ambiguity."}}


class Adjudication(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.study = os.path.join(self.dir, "study")
        cli.main([self.study, "init", DOC])
        self.st = orchestrate.Study(self.study)
        self.calls = []

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    OPTIONS = ["one value", "one attribute", "declared ambiguity"]

    def fake(self, verdicts, pick=0, close=False):
        """A stand-in worker: option-lister, then one adjudicator per option,
        then the arbiter. The adjudicators run in parallel, so a verdict is
        matched to the option actually under test, never to call order."""

        def call(role, system, user, draw=0, resume=None, provider_as=None):
            self.calls.append(role)
            if role == "options":
                return {"options": list(self.OPTIONS)}
            if role == "adjudicator":
                option = user.split("OPTION UNDER TEST:\n")[1].strip()
                i = self.OPTIONS.index(option)
                return {"verdict": verdicts[i], "failing_case": f"case {i}"}
            if role == "arbiter":
                return {"pick": pick, "why": "the document's counts stay coherent",
                        "close": close}
            raise AssertionError(role)
        self.st.call = call

    def choices(self):
        return json.load(open(self.st.state_p)).get("machine_choices") or []


class TestAdjudicated(Adjudication):
    def test_one_survivor_settles_it_without_the_owner(self):
        self.fake(["refuted", "survives", "refuted"])
        out = orchestrate.adjudicate(self.st, "widget", ESCALATION)
        self.assertIn("ADJUDICATED", out)
        self.assertIn("one attribute", out)
        self.assertEqual(self.choices()[0]["mode"], "adjudicated")

    def test_the_reasons_are_written_down(self):
        self.fake(["refuted", "survives", "refuted"])
        orchestrate.adjudicate(self.st, "widget", ESCALATION)
        text = open(os.path.join(self.study, "adjudications.md")).read()
        self.assertIn("widget — adjudicated", text)
        self.assertIn("case 0", text)          # why the rivals fell

    def test_one_survivor_needs_no_arbiter(self):
        self.fake(["refuted", "survives", "refuted"])
        orchestrate.adjudicate(self.st, "widget", ESCALATION)
        self.assertNotIn("arbiter", self.calls)
        self.assertEqual(self.calls.count("adjudicator"), 3)


class TestStaysTheOwners(Adjudication):
    def test_several_survivors_are_left_to_the_owner(self):
        self.fake(["survives", "survives", "refuted"])
        self.assertIsNone(orchestrate.adjudicate(self.st, "widget", ESCALATION))
        self.assertEqual(self.choices(), [])

    def test_an_escalation_without_options_is_left_alone(self):
        self.fake(["survives"])
        bare = dict(ESCALATION, chair={"decision": "escalate", "choice": ""})
        self.assertIsNone(orchestrate.adjudicate(self.st, "widget", bare))
        self.assertEqual(self.calls, [])

    def test_a_single_option_is_no_choice_at_all(self):
        def call(role, system, user, draw=0, resume=None, provider_as=None):
            self.calls.append(role)
            return {"options": ["the only reading"]}
        self.st.call = call
        self.assertIsNone(orchestrate.adjudicate(self.st, "widget", ESCALATION))
        self.assertEqual(self.calls, ["options"])


class TestKeepGoing(Adjudication):
    def test_it_picks_and_says_the_owner_did_not(self):
        self.st.cfg["keep_going"] = "best"
        self.fake(["survives", "survives", "refuted"], pick=1)
        out = orchestrate.adjudicate(self.st, "widget", ESCALATION)
        self.assertIn("MACHINE-SELECTED WITHOUT OWNER APPROVAL", out)
        self.assertIn("one attribute", out)
        self.assertIn("Open clause", out)      # the entry must disclose it
        self.assertEqual(self.choices()[0]["mode"], "machine-selected")

    def test_it_picks_among_survivors_only(self):
        """The arbiter naming a refuted option does not get to choose it."""
        self.st.cfg["keep_going"] = "best"
        self.fake(["refuted", "survives", "survives"], pick=0)
        orchestrate.adjudicate(self.st, "widget", ESCALATION)
        self.assertIn(self.choices()[0]["chosen"], self.OPTIONS[1:])

    def test_when_everything_is_refuted_it_still_moves(self):
        self.st.cfg["keep_going"] = "best"
        self.fake(["refuted", "refuted", "refuted"], pick=2)
        out = orchestrate.adjudicate(self.st, "widget", ESCALATION)
        self.assertIn("MACHINE-SELECTED", out)
        self.assertIn("declared ambiguity", out)

    def test_random_is_arbitrary_but_reproducible(self):
        picks = set()
        for _ in range(3):
            self.setUp()
            self.st.cfg["keep_going"] = "random"
            self.fake(["survives", "survives", "survives"])
            picks.add(orchestrate.adjudicate(self.st, "widget", ESCALATION).split("\n")[0])
        self.assertEqual(len(picks), 1, "a replayed run must repeat its arbitrary pick")

    def test_status_and_report_disclose_unowned_choices(self):
        self.st.cfg["keep_going"] = "best"
        self.fake(["survives", "survives", "refuted"], pick=1)
        orchestrate.adjudicate(self.st, "widget", ESCALATION)
        shown = cli.report_mod.build(self.study)
        self.assertIn("owner-level choice", shown)
        self.assertIn("widget", shown)
        filed = open(os.path.join(self.study, "RUN-REPORT.md")).read()
        self.assertIn("made by the run, not by its owner", filed)


if __name__ == "__main__":
    unittest.main()
