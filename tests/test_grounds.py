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

from hypelysis import cli, orchestrate, providers, resources


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


class TestWhatTheReviewersJudged(unittest.TestCase):
    """A chair may amend the entry it accepts; the reviewers judged the draft
    as proposed, and a record that keeps only the amendment cannot say
    afterwards what they read."""

    PROP = {"move": "entry", "payload": "### widget\nKind: base\nStatement: A widget.\n"}

    def test_an_amendment_keeps_both_texts(self):
        prop, reviewed = orchestrate.chair_amendment(
            self.PROP, {"payload": "### widget\nKind: base\nStatement: A widget, amended.\n"})
        self.assertIn("amended", prop["payload"])
        self.assertEqual(reviewed, self.PROP["payload"])

    def test_no_amendment_leaves_the_proposal_alone(self):
        prop, reviewed = orchestrate.chair_amendment(self.PROP, {})
        self.assertIs(prop, self.PROP)
        self.assertIsNone(reviewed)

    def test_an_identical_payload_is_not_an_amendment(self):
        prop, reviewed = orchestrate.chair_amendment(
            self.PROP, {"payload": self.PROP["payload"]})
        self.assertIsNone(reviewed)


class TestReconstructingWhatTheReadersRead(unittest.TestCase):
    """The point of keeping the reviewed draft: a finished study can say what
    its readers actually read.

    This drives the real accept path and checks the reconstruction against the
    digest **the run recorded in its own log**. Nothing here recomputes the
    digest it compares against — a test that hashes one string against itself
    passes whether or not the feature exists, which is how the first version of
    this test got through review.
    """

    PROPOSED = ("### widget\nKind: base\n"
                "Statement: A widget is a part that turns.\n"
                "Because: the document treats it as primitive.\n")
    AMENDED = ("### widget\nKind: base\n"
               "Statement: A widget is a part that turns under load.\n"
               "Because: the document treats it as primitive.\n")

    class Scripted:
        """One worker per role, answering well enough to reach the chair.

        `minimality` objects so that `bad` is non-empty — with every check
        clean the round accepts before a chair is ever called, and an
        amendment could not arise.
        """

        def __init__(self, role, proposed, amended):
            self.role = role.split(":")[0]
            self.proposed, self.amended = proposed, amended

        def spec(self):
            return {"provider": "scripted", "model": "scripted"}

        def complete(self, system, user, resume=None):
            if self.role == "proposer":
                out = {"move": "entry", "payload": self.proposed,
                       "reasoning": "the document uses it as a primitive"}
            elif self.role == "reader":
                out = {"restatement": "a part that turns", "ambiguous": []}
            elif self.role == "chair":
                out = {"decision": "accept", "payload": self.amended,
                       "feedback": "accepted with the load condition made explicit"}
            elif self.role == "minimality":
                out = {"verdict": "no", "objections": ["the Because could be tighter"]}
            else:
                out = {"verdict": "ok", "objections": []}
            return json.dumps(out), {"cost_usd": 0.0}

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.study = os.path.join(self.dir, "study")
        cli.main([self.study, "init", os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "fixtures", "sprocket.md")])
        st = orchestrate.Study(self.study)
        st.provider = lambda role: self.Scripted(role, self.PROPOSED, self.AMENDED)
        st.state["queue_lane1"] = ["widget"]
        orchestrate.phase_foundation(st, "lane1")
        self.st = st

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def log(self, name):
        p = os.path.join(self.study, "log", name)
        return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []

    def accepted(self):
        return [d for d in self.log("decisions.jsonl") if d["decision"] == "accept"][0]

    def recorded_reader_digests(self):
        """What the run logged for each reader call, straight from rounds.jsonl."""
        return {r["role"]: r["prompt_sha"] for r in self.log("rounds.jsonl")
                if r.get("role", "").startswith("reader:")}

    def test_the_round_was_accepted_over_an_amendment(self):
        """The fixture only means something if the chair really did amend."""
        acc = self.accepted()
        self.assertEqual(acc["proposal"]["payload"], self.AMENDED)
        self.assertNotEqual(self.PROPOSED, self.AMENDED)

    def test_the_log_keeps_the_draft_the_readers_judged(self):
        self.assertEqual(self.accepted()["reviewed_payload"], self.PROPOSED)

    def test_the_amendment_still_governs_the_foundation(self):
        """Keeping the reviewed draft must not cost the chair its amendment."""
        fnd = open(os.path.join(self.study, "foundation.md")).read()
        self.assertIn("under load", fnd)

    def test_the_reviewed_draft_reproduces_the_recorded_reader_digests(self):
        """Every reader call the run logged is reconstructible from the log
        alone: same role prompt, same profile, same ENTRY block."""
        reviewed = self.accepted()["reviewed_payload"]
        digests = self.recorded_reader_digests()
        self.assertEqual(len(digests), len(orchestrate.READER_PROFILES))
        for i, profile in enumerate(orchestrate.READER_PROFILES):
            system = self.st.role("reader", profile=profile)
            rebuilt = providers.prompt_sha(system, f"ENTRY:\n{reviewed}")
            self.assertEqual(rebuilt, digests[f"reader:{i}"],
                             f"reader:{i} is not reconstructible from the log")

    def test_the_approved_entry_does_not_reproduce_them(self):
        """The negative half, and the half that has teeth: reconstructing from
        the payload the chair approved must MISS every recorded digest. Without
        it, a prompt_sha that ignored its arguments would satisfy the positive
        test — which is exactly the hole in the version this replaces."""
        approved = self.accepted()["proposal"]["payload"]
        digests = self.recorded_reader_digests()
        for i, profile in enumerate(orchestrate.READER_PROFILES):
            system = self.st.role("reader", profile=profile)
            rebuilt = providers.prompt_sha(system, f"ENTRY:\n{approved}")
            self.assertNotEqual(rebuilt, digests[f"reader:{i}"],
                                f"reader:{i} matched the amended text — the digest "
                                "is not discriminating between the two drafts")
