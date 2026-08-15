"""A verdict that binds an actor travels with grounds enough to act on.

Blindness upstream is deliberate — readers read cold, checks are independent —
but a bound actor (the proposer on a retry, the chair deciding) must see what
binds it. These are the cases where it did not.
"""
import json
import os
import shutil
import tempfile
import unittest

from hypelysis import cli, orchestrate, resources


class Study(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.study = os.path.join(self.dir, "study")
        cli.main([self.study, "init", os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "fixtures", "sprocket.md")])
        self.st = orchestrate.Study(self.study)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def log_decisions(self, *records):
        with open(os.path.join(self.study, "log", "decisions.jsonl"), "w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")


class TestChairSeesEveryObjection(unittest.TestCase):
    def verdicts(self, n_objections=2, text="the statement drops the consequence"):
        return {
            "rules": {"verdict": "ok", "objections": []},
            "skeptic": {"verdict": "no",
                        "sample_1": {"verdict": "no", "objections": [
                            {"defect": text, "failing_case": "a one-hop path",
                             "severity": "blocking"}]},
                        "sample_2_blind": {"verdict": "no", "objections": [
                            {"defect": text, "failing_case": "a one-hop path",
                             "severity": "blocking"},
                            {"defect": "the name promises more than the statement",
                             "failing_case": "widgets that never settle"}][:n_objections]}},
            "readers": {"verdict": "no", "flagged": 2, "restatements": [
                {"restatement": "a widget is a thing", "ambiguous": ["what individuates it"]}]},
        }

    def test_an_objection_in_both_blind_samples_is_marked_as_recurring(self):
        out = orchestrate.render_verdicts(self.verdicts())
        self.assertIn("[all samples]", out)
        self.assertIn("drops the consequence", out)

    def test_an_objection_in_one_sample_says_which(self):
        out = orchestrate.render_verdicts(self.verdicts())
        self.assertIn("[sample_2_blind]", out)
        self.assertIn("promises more", out)

    def test_the_labels_do_not_pretend_to_judge_recurrence(self):
        """Independent draws rarely word an objection identically, so matching
        text under-reports recurrence; the chair is told to judge substance."""
        out = orchestrate.render_verdicts(self.verdicts())
        self.assertIn("judge recurrence by substance", out)
        self.assertNotIn("only]", out)

    def test_readers_keep_their_restatements_and_ambiguities(self):
        out = orchestrate.render_verdicts(self.verdicts())
        self.assertIn("read as: a widget is a thing", out)
        self.assertIn("what individuates it", out)

    def test_the_digest_is_far_smaller_than_the_json_it_replaces(self):
        v = self.verdicts()
        self.assertLess(len(orchestrate.render_verdicts(v)),
                        len(json.dumps(v, indent=1)))

    def test_nothing_is_dropped_silently(self):
        v = {"skeptic": {"verdict": "no", "objections": [
            {"defect": f"objection number {i} " + "x" * 300} for i in range(40)]}}
        out = orchestrate.render_verdicts(v, limit=2000)
        self.assertIn("omitted for length", out)
        self.assertIn("ask for a revision rather than deciding without them", out)
        self.assertLessEqual(len(out), 2400)

    def test_a_verdict_that_fits_says_nothing_about_omissions(self):
        self.assertNotIn("omitted", orchestrate.render_verdicts(self.verdicts()))


class TestRejectedRevisionsAreVisible(Study):
    def test_a_revision_comes_back_as_a_diff(self):
        with open(os.path.join(self.study, "foundation.md"), "w") as f:
            f.write("### widget\nKind: base\nStatement: A widget is a thing.\n")
        r = {"proposal": {"move": "revision",
                          "payload": "### widget\nKind: base\n"
                                     "Statement: A widget is a gadget.\n"}}
        out = orchestrate.rejected_draft(self.st, r)
        self.assertIn("as a diff", out)
        self.assertIn("-Statement: A widget is a thing.", out)
        self.assertIn("+Statement: A widget is a gadget.", out)

    def test_a_revision_too_wide_to_review_is_refused_with_the_reason(self):
        with open(os.path.join(self.study, "foundation.md"), "w") as f:
            f.write("### a\nKind: base\n")
        r = {"proposal": {"move": "revision",
                          "payload": "\n".join(f"### t{i}\nKind: base\n"
                                               f"Statement: number {i}." for i in range(200))}}
        out = orchestrate.rejected_draft(self.st, r)
        self.assertIn("too large to quote back", out)
        self.assertIn("propose a smaller one", out)
        self.assertIn("Rule 5", out)

    def test_a_reorder_comes_back_as_the_moves_it_made(self):
        with open(os.path.join(self.study, "foundation.md"), "w") as f:
            f.write("### a\nKind: base\n### b\nKind: base\n### c\nKind: base\n")
        r = {"proposal": {"move": "reorder",
                          "payload": "### c\nKind: base\n### a\nKind: base\n"
                                     "### b\nKind: base\n"}}
        out = orchestrate.rejected_draft(self.st, r)
        self.assertIn("c: position 3 -> 1", out)


class TestChairSeesTheTrajectory(Study):
    HISTORY = [
        {"term": "widget", "attempt": 0, "decision": "retry", "failed": ["rules"],
         "verdicts": {"rules": {"objections": ["widget: Statement exceeds three sentences"]}}},
        {"term": "widget", "attempt": 1, "decision": "retry", "failed": ["skeptic"],
         "verdicts": {"skeptic": {"objections": [{"defect": "the name overpromises"}]}},
         "chair": {"feedback": "shorten the statement and declare the openness"}},
        {"term": "gadget", "attempt": 0, "decision": "accept", "failed": []},
    ]

    def test_only_this_term_s_attempts_are_shown(self):
        self.log_decisions(*self.HISTORY)
        got = orchestrate.attempt_history(self.st, "widget")
        self.assertEqual([d["attempt"] for d in got], [0, 1])

    def test_the_trajectory_names_what_failed_and_what_the_chair_said(self):
        out = orchestrate.render_trajectory(self.HISTORY[:2])
        self.assertIn("attempt 0: retry (failed: rules)", out)
        self.assertIn("Statement exceeds three sentences", out)
        self.assertIn("you told the proposer: shorten the statement", out)

    def test_a_first_attempt_has_no_trajectory(self):
        self.assertEqual(orchestrate.render_trajectory([]), "")


class TestTheSameMechanicalFailureTwice(Study):
    """A rules failure is cheap to redraft, so it short-circuits — until it
    repeats, which means the proposer cannot see something."""

    OBJ = ["widget: Statement exceeds three sentences"]

    def promoted(self, previous_failed, previous_objections):
        self.log_decisions({"term": "widget", "attempt": 0,
                            "decision": "retry", "failed": previous_failed,
                            "verdicts": {"rules": {"objections": previous_objections}}})
        history = orchestrate.attempt_history(self.st, "widget")
        return bool(history and history[-1].get("failed") == ["rules"]
                    and ((history[-1].get("verdicts") or {}).get("rules") or {}
                         ).get("objections") == self.OBJ)

    def test_the_same_objection_twice_promotes_the_round(self):
        self.assertTrue(self.promoted(["rules"], self.OBJ))

    def test_a_different_mechanical_objection_does_not(self):
        self.assertFalse(self.promoted(["rules"], ["widget: field order [...]"]))

    def test_a_semantic_failure_before_it_does_not(self):
        self.assertFalse(self.promoted(["skeptic"], []))


class TestDecisionsBindReadings(unittest.TestCase):
    def test_the_binding_text_says_a_reading_is_settled_not_its_wording(self):
        text = orchestrate.DECISION_BINDS_THE_READING
        self.assertIn("fixes the READING", text)
        self.assertIn("does not fix any wording", text)
        self.assertIn("not text to transcribe", text)

    def test_it_does_not_instruct_the_proposer_on_length(self):
        """Telling a proposer to fit prose into a cap invites clause-stuffing;
        the cap is a speed bump and the skeptic is the guard."""
        text = orchestrate.DECISION_BINDS_THE_READING.lower()
        for trick in ("three sentences", "sentence limit", "shorten", "concise"):
            self.assertNotIn(trick, text)

    def test_the_option_lister_is_told_to_strip_drafting_instructions(self):
        role = resources.role("options")
        self.assertIn("states what is TRUE under that reading", role)
        self.assertIn("Drafting instructions", role)
        self.assertIn("The proposer, not the option, decides", role)


if __name__ == "__main__":
    unittest.main()
