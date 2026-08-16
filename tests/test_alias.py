"""The alias move: a term that is only the document's other name for an entry.

The defect it answers, seen in a real run: a term whose content an accepted
entry already carries has no legal move. An entry of its own duplicates the
mechanism and the checks reject it; deferral is barred because other queued
terms presuppose it; the chair cannot amend a Statement into covering it. So a
correct chair diagnosis dies of budget poverty and escalates to the owner.

An alias is sugar over the existing revision path, and the tests below are
mostly about what it is NOT allowed to be: it buys no exemption from the rules
check, the reviewers, the chair, or rule 5. What it removes is the drafting,
not the checking — code builds the payload, so the proposer cannot lose an
entry while hand-copying the foundation.

    python -m unittest discover -s tests
"""
import json
import os
import shutil
import tempfile
import unittest

from hypelysis import cli, orchestrate, resources

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(HERE, "fixtures", "sprocket.md")

FOUNDATION = """### projection fabric
Kind: base
Statement: The fabric is rebuilt as entries land.
Because: the document treats rebuilding as primitive.
Finding: the document never says how long a rebuild takes.
Note: named for the weave metaphor in section 2.

### torque budget
Kind: defined
Statement: A torque budget is the load a sprocket may carry.
Uses: projection fabric
"""


class TestAliasPayload(unittest.TestCase):
    """The construction, on its own: what code builds from target + note."""

    def build(self, target="projection fabric", note="The document also calls this NeverStale.",
              finding=""):
        return orchestrate.alias_payload(FOUNDATION, target, note, finding)

    def test_the_note_lands_on_the_target(self):
        out = self.build()
        self.assertIn("weave metaphor in section 2. The document also calls this "
                      "NeverStale.", out)

    def test_a_finding_lands_on_the_targets_finding(self):
        out = self.build(finding="the guarantee appears only in the name.")
        self.assertIn("how long a rebuild takes. the guarantee appears only in the name.",
                      out)

    def test_everything_else_is_byte_identical(self):
        """The diff IS the claim: an alias that quietly rewrote a neighbouring
        entry would be a revision wearing an alias's clothes."""
        out = self.build()
        before = FOUNDATION.split("### torque budget")[1]
        after = out.split("### torque budget")[1]
        self.assertEqual(before, after)
        self.assertIn("Statement: The fabric is rebuilt as entries land.", out)
        self.assertIn("Because: the document treats rebuilding as primitive.", out)

    def test_the_result_passes_the_mechanical_checks(self):
        from hypelysis.check import check_text
        self.assertEqual(check_text(self.build(
            finding="the guarantee appears only in the name.")), [])

    def test_a_missing_target_builds_nothing(self):
        self.assertIsNone(self.build(target="nowhere"))

    def test_an_empty_note_builds_nothing(self):
        """An alias whose note is empty records no name, so it is not evidence
        about the document — it is a silent deletion of a candidate."""
        self.assertIsNone(self.build(note="   "))

    def test_fields_are_created_in_the_required_order(self):
        """A target with neither Finding nor Note: both must be inserted where
        the mechanical field order demands, or the checks reject the alias."""
        from hypelysis.check import check_text
        bare = ("### bare\nKind: base\nStatement: A bare entry.\n"
                "Because: it is primitive.\n")
        out = orchestrate.alias_payload(bare, "bare", "also called plain.",
                                        "the second name appears once.")
        self.assertEqual(check_text(out), [])
        self.assertLess(out.index("Finding:"), out.index("Note:"))
        self.assertLess(out.index("Because:"), out.index("Finding:"))

    def test_a_finding_is_inserted_before_an_existing_note(self):
        """The case that discriminates. Note is the LAST field, so simply
        appending new fields at the end of an entry produces the right order
        for almost every target — except one that already carries a Note and
        no Finding, where the Finding must be placed before it. Entries like
        that are common, and without this case an implementation that ignored
        field order entirely would pass."""
        from hypelysis.check import check_text
        noted = ("### noted\nKind: base\nStatement: A noted entry.\n"
                 "Because: it is primitive.\nNote: named in section 1.\n")
        out = orchestrate.alias_payload(noted, "noted", "also called plain.",
                                        "the second name appears once.")
        self.assertEqual(check_text(out), [])
        self.assertLess(out.index("Finding:"), out.index("Note:"))


class AliasRound(unittest.TestCase):
    """A study whose foundation already holds the target, driven one round."""

    MOVE = {"move": "alias", "target": "projection fabric",
            "note": "The document also calls this NeverStale.",
            "finding": "the guarantee appears only in the name.",
            "reasoning": "the document uses NeverStale for the fabric it already defined"}

    class Scripted:
        def __init__(self, role, move, chair="accept", skeptic="ok"):
            self.role_name = role.split(":")[0]
            self.move = move
            self.chair_decision = chair
            self.skeptic_verdict = skeptic

        def spec(self):
            return {"provider": "scripted", "model": "scripted"}

        def complete(self, system, user, resume=None):
            if self.role_name == "proposer":
                out = dict(self.move)
            elif self.role_name == "reader":
                out = {"restatement": "the fabric, also called NeverStale", "ambiguous": []}
            elif self.role_name == "chair":
                out = {"decision": self.chair_decision, "feedback": "as reviewed"}
            elif self.role_name == "skeptic":
                out = {"verdict": self.skeptic_verdict,
                       "objections": ([] if self.skeptic_verdict == "ok" else
                                      [{"defect": "the name promises a guarantee the "
                                        "Statement does not carry",
                                        "failing_case": "a stale read after a failed rebuild",
                                        "severity": "blocking"}])}
            else:
                out = {"verdict": "ok", "objections": []}
            return json.dumps(out), {"cost_usd": 0.0}

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.study = os.path.join(self.dir, "study")
        cli.main([self.study, "init", DOC])
        with open(os.path.join(self.study, "foundation.md"), "w") as f:
            f.write(FOUNDATION)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def study_with(self, move=None, skeptic="ok"):
        st = orchestrate.Study(self.study)
        st.provider = lambda role: self.Scripted(
            role, move or self.MOVE, skeptic=skeptic)
        return st

    def log(self, name):
        p = os.path.join(self.study, "log", name)
        return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []

    def roles_called(self):
        return [r.get("role") for r in self.log("rounds.jsonl")]


class TestTheAliasGate(AliasRound):
    def test_an_unknown_target_is_refused_without_spending_a_check(self):
        """Mechanical, like the defer-gate: the proposer is the only worker
        that runs, and the objection names what it could have aliased."""
        st = self.study_with(dict(self.MOVE, target="a term with no entry"))
        r = orchestrate.entry_round(st, "NeverStale", "")
        self.assertEqual(r["decision"], "retry")
        self.assertEqual(r["failed"], ["alias-gate"])
        self.assertEqual(self.roles_called(), ["proposer"])
        objection = r["verdicts"]["alias-gate"]["objections"][0]
        self.assertIn("not an entry in the foundation", objection)
        self.assertIn("projection fabric", objection)

    def test_an_empty_note_is_refused_and_says_why(self):
        st = self.study_with(dict(self.MOVE, note=""))
        r = orchestrate.entry_round(st, "NeverStale", "")
        self.assertEqual(r["failed"], ["alias-gate"])
        self.assertIn("must record the name", r["verdicts"]["alias-gate"]["objections"][0])
        self.assertEqual(self.roles_called(), ["proposer"])

    def test_a_valid_alias_is_checked_like_any_revision(self):
        """The gate buys no exemption: rules, every AI check, and the readers
        all run on the constructed payload."""
        st = self.study_with()
        r = orchestrate.entry_round(st, "NeverStale", "")
        self.assertEqual(r["decision"], "accept")
        self.assertEqual(r["verdicts"]["rules"]["verdict"], "ok")
        for c in orchestrate.CHECKS:
            self.assertIn(c, r["verdicts"])
        self.assertEqual(r["verdicts"]["readers"]["flagged"], 0)
        self.assertEqual(len([x for x in self.roles_called() if x.startswith("reader:")]),
                         len(orchestrate.READER_PROFILES))

    def test_the_payload_the_checks_saw_was_built_by_code(self):
        """The proposer never drafts it, so it cannot lose an entry in
        transcription — both entries survive, with the note added."""
        st = self.study_with()
        r = orchestrate.entry_round(st, "NeverStale", "")
        payload = r["proposal"]["payload"]
        self.assertIn("### projection fabric", payload)
        self.assertIn("### torque budget", payload)
        self.assertIn("also calls this NeverStale", payload)

    def test_a_skeptic_can_still_refuse_an_alias(self):
        """The claim that the name adds nothing is a claim, and the checks
        attack it. A blocking objection sends the round to the chair like any
        other, and the alias does not land by virtue of being an alias."""
        st = self.study_with(skeptic="no")
        st.provider = lambda role: self.Scripted(role, self.MOVE, chair="revise",
                                                 skeptic="no")
        r = orchestrate.entry_round(st, "NeverStale", "")
        self.assertEqual(r["decision"], "retry")
        self.assertIn("skeptic", r["failed"])


class TestAnAcceptedAliasSettlesTheTerm(AliasRound):
    def setUp(self):
        super().setUp()
        st = self.study_with()
        st.state["queue_lane1"] = ["NeverStale", "torque budget"]
        # 'torque budget' presupposes the alias term, so a deferral would have
        # been refused here — this is the situation the alias move exists for.
        with open(os.path.join(self.study, "candidates.json"), "w") as f:
            json.dump([{"term": "torque budget", "presupposes": ["NeverStale"]}], f)
        self.st = st
        try:
            orchestrate.phase_foundation(st, "lane1")
        except SystemExit:
            pass

    def test_the_term_settles_as_accepted(self):
        self.assertEqual(self.st.state["outcomes"]["NeverStale"], "accept")

    def test_the_decision_log_records_it_as_an_alias(self):
        acc = [d for d in self.log("decisions.jsonl")
               if d["term"] == "NeverStale" and d["decision"] == "accept"][0]
        self.assertEqual(acc["proposal"]["move"], "alias")
        self.assertEqual(acc["proposal"]["target"], "projection fabric")

    def test_the_foundation_gained_the_name_and_lost_nothing(self):
        fnd = open(os.path.join(self.study, "foundation.md")).read()
        self.assertIn("also calls this NeverStale", fnd)
        self.assertIn("### torque budget", fnd)
        self.assertIn("Statement: The fabric is rebuilt as entries land.", fnd)

    def test_no_entry_was_created_for_the_aliased_term(self):
        """The whole point: the term settles without a duplicate entry."""
        fnd = open(os.path.join(self.study, "foundation.md")).read()
        self.assertNotIn("### NeverStale", fnd)

    def test_a_dependent_term_is_no_longer_blocked(self):
        """`presupposed_by` is satisfied by settlement, not by an entry, so
        the term that presupposed the alias gets its round."""
        self.assertIn("torque budget", self.st.state.get("outcomes", {}))

    def test_the_report_counts_it_settled(self):
        from hypelysis import report
        self.assertIn("NeverStale", report.build(self.study))


class TestTheAliasInstructionsAreInstalled(unittest.TestCase):
    def test_the_proposer_is_told_when_to_alias_and_what_it_claims(self):
        role = resources.role("proposer")
        self.assertIn('"move": "alias"', role)
        self.assertIn("other NAME for something an existing entry", role)
        self.assertIn("is a CLAIM", role)
        self.assertIn("Do not draft a payload for it", role)

    def test_the_skeptic_is_told_to_attack_what_the_name_adds(self):
        role = resources.role("skeptic")
        self.assertIn("An alias deserves scrutiny of what the NAME asserts", role)
        self.assertIn("guarantee", role)
        self.assertIn("needs its own entry", role)


if __name__ == "__main__":
    unittest.main()
