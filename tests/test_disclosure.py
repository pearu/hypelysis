"""A choice the run made for the owner has to say so, and not on trust.

`--keep-going` lets an unattended run settle a reading no owner chose. The
resolution instructs the proposer to declare that in the entry's Open field.
An instruction is not a guarantee, and a disclosure that exists only when a
worker remembers it is not a disclosure — so the run verifies it before the
accept lands.

Adjudicated choices are exempt on purpose: there every rival reading was
refuted with grounds, so the run owes the owner nothing to declare.

    python -m unittest discover -s tests
"""
import json
import os
import shutil
import tempfile
import unittest

from hypelysis import cli, orchestrate, report

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(HERE, "fixtures", "sprocket.md")
MARKER = orchestrate.DISCLOSURE_MARKER

CLEAN = ("### widget\nKind: base\nStatement: A widget is a part that turns.\n"
         "Because: the document treats it as primitive.\n")
DISCLOSED = ("### widget\nKind: base\nStatement: A widget is a part that turns.\n"
             "Because: the document treats it as primitive.\n"
             f"Open: {MARKER}; whether it turns under load is unsettled.\n")
IN_NOTE = ("### widget\nKind: base\nStatement: A widget is a part that turns.\n"
           "Because: the document treats it as primitive.\n"
           f"Note: {MARKER}.\n")


class Round(unittest.TestCase):
    """One round driven with scripted workers; no AI, no fixture."""

    class Scripted:
        def __init__(self, role, payload, chair=None):
            self.role_name = role.split(":")[0]
            self.payload, self.chair = payload, chair

        def spec(self):
            return {"provider": "scripted", "model": "scripted"}

        def complete(self, system, user, resume=None):
            if self.role_name == "proposer":
                out = {"move": "entry", "payload": self.payload, "reasoning": "as decided"}
            elif self.role_name == "reader":
                out = {"restatement": "a part that turns", "ambiguous": []}
            elif self.role_name == "chair":
                out = {"decision": "accept", "feedback": "ok",
                       **({"payload": self.chair} if self.chair else {})}
            elif self.role_name == "minimality" and self.chair is not None:
                out = {"verdict": "no", "objections": ["forces the chair to run"]}
            else:
                out = {"verdict": "ok", "objections": []}
            return json.dumps(out), {"cost_usd": 0.0}

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.study = os.path.join(self.dir, "study")
        cli.main([self.study, "init", DOC])

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def study_with(self, payload, mode="machine-selected", term="widget", chair=None):
        st = orchestrate.Study(self.study)
        if mode:
            st.state["machine_choices"] = [
                {"term": term, "mode": mode, "chosen": "a reading", "why": "kept going"}]
        st.provider = lambda role: self.Scripted(role, payload, chair)
        return st

    def calls(self):
        p = os.path.join(self.study, "log", "rounds.jsonl")
        return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []


class TestTheDisclosureGate(Round):
    def test_an_undisclosed_machine_choice_is_refused(self):
        r = orchestrate.entry_round(self.study_with(CLEAN), "widget", "")
        self.assertEqual(r["decision"], "retry")
        self.assertEqual(r["failed"], ["disclosure-gate"])

    def test_the_refusal_quotes_the_exact_clause_and_where_it_goes(self):
        """A retry the proposer cannot act on is the defect this project keeps
        finding; the objection carries the literal string and the field."""
        r = orchestrate.entry_round(self.study_with(CLEAN), "widget", "")
        obj = r["verdicts"]["disclosure-gate"]["objections"][0]
        self.assertIn(MARKER, obj)
        self.assertIn("Open", obj)
        self.assertIn("widget", obj)

    def test_a_disclosed_entry_passes(self):
        r = orchestrate.entry_round(self.study_with(DISCLOSED), "widget", "")
        self.assertEqual(r["decision"], "accept")

    def test_an_adjudicated_choice_needs_no_disclosure(self):
        """Every rival was refuted with grounds, so there is no owner debt."""
        r = orchestrate.entry_round(
            self.study_with(CLEAN, mode="adjudicated"), "widget", "")
        self.assertEqual(r["decision"], "accept")

    def test_a_term_with_no_machine_choice_is_untouched(self):
        r = orchestrate.entry_round(self.study_with(CLEAN, mode=None), "widget", "")
        self.assertEqual(r["decision"], "accept")

    def test_a_choice_for_another_term_does_not_bind_this_one(self):
        r = orchestrate.entry_round(
            self.study_with(CLEAN, term="sprocket"), "widget", "")
        self.assertEqual(r["decision"], "accept")

    def test_the_marker_must_be_in_open_not_note(self):
        """A disclosure parked in Note is commentary. Open binds the reader."""
        r = orchestrate.entry_round(self.study_with(IN_NOTE), "widget", "")
        self.assertEqual(r["failed"], ["disclosure-gate"])

    def test_the_gate_spends_no_ai_on_its_own_verdict(self):
        """Mechanical, like the defer- and alias-gates: the refusal itself
        costs nothing beyond the round that was already running."""
        st = self.study_with(CLEAN)
        before = len(self.calls())
        orchestrate.entry_round(st, "widget", "")
        roles = [c["role"] for c in self.calls()[before:]]
        self.assertNotIn("disclosure-gate", roles)


class TestTheGateReadsWhatTheRunAccepts(Round):
    def test_a_chair_amendment_that_adds_the_marker_satisfies_it(self):
        """The check runs after the amendment, never before: what must carry
        the disclosure is the text that lands in the foundation."""
        r = orchestrate.entry_round(
            self.study_with(CLEAN, chair=DISCLOSED), "widget", "")
        self.assertEqual(r["decision"], "accept")
        self.assertIn(MARKER, r["proposal"]["payload"])

    def test_a_chair_amendment_that_drops_the_marker_is_caught(self):
        """And the converse: a proposer that disclosed does not save an
        amendment that removes it."""
        r = orchestrate.entry_round(
            self.study_with(DISCLOSED, chair=CLEAN), "widget", "")
        self.assertEqual(r["failed"], ["disclosure-gate"])


class TestTheChairIsAChoiceSourceToo(Round):
    """A chair that amends a reading onto its own authority has made an
    owner-level choice. Measured across two completed arms: of nine entries
    claiming a run-selected reading with no backing record, six were written
    by the chair, not the proposer. Recording that is what lets the gate
    refuse an unbacked claim without refusing the chair's own candour."""

    def test_a_chair_added_disclosure_becomes_a_record(self):
        st = self.study_with(CLEAN, mode=None, chair=DISCLOSED)
        r = orchestrate.entry_round(st, "widget", "")
        self.assertEqual(r["decision"], "accept")
        rec = [m for m in st.state["machine_choices"] if m["mode"] == "chair-amended"]
        self.assertEqual(len(rec), 1)
        self.assertEqual(rec[0]["term"], "widget")
        self.assertIn(MARKER, rec[0]["chosen"])
        self.assertIn("attempt", rec[0])

    def test_the_record_is_what_stops_the_oscillation(self):
        """This is the whole point. Before the record existed, a chair-added
        clause was unbacked, so the gate refused it and the retry went to the
        proposer — who never wrote it, would not reproduce it, and would watch
        the chair add it again. The record legitimises the clause in the same
        round that creates it, so the round accepts."""
        st = self.study_with(CLEAN, mode=None, chair=DISCLOSED)
        r = orchestrate.entry_round(st, "widget", "")
        self.assertNotEqual(r["failed"], ["disclosure-gate"])
        self.assertEqual(r["decision"], "accept")

    def test_a_proposers_own_disclosure_is_not_credited_to_the_chair(self):
        """The chair must really amend for this to test anything — an
        identical payload is no amendment, so `reviewed` would be None and the
        credit check would never be reached. Here the chair changes the
        Statement while leaving the proposer's disclosure standing: an
        amendment did happen, and it is still not the chair's disclosure."""
        amended = DISCLOSED.replace("turns.", "turns under load.")
        self.assertNotEqual(amended, DISCLOSED)
        st = self.study_with(DISCLOSED, mode="machine-selected", chair=amended)
        r = orchestrate.entry_round(st, "widget", "")
        self.assertEqual(r["decision"], "accept")
        self.assertEqual(r["reviewed_payload"], DISCLOSED)   # it really amended
        self.assertEqual([m["mode"] for m in st.state["machine_choices"]],
                         ["machine-selected"])

    def test_an_amendment_that_adds_no_disclosure_records_nothing(self):
        amended = CLEAN.replace("turns.", "turns under load.")
        st = self.study_with(CLEAN, mode=None, chair=amended)
        orchestrate.entry_round(st, "widget", "")
        self.assertEqual(st.state.get("machine_choices", []), [])


class TestAnUnbackedClaimIsRefused(Round):
    """The direction neither side specced, and the one the evidence found:
    nine claims with no backing record across two arms, against zero
    omissions."""

    def test_a_claim_with_no_record_at_all_is_refused(self):
        r = orchestrate.entry_round(self.study_with(DISCLOSED, mode=None), "widget", "")
        self.assertEqual(r["decision"], "retry")
        self.assertEqual(r["failed"], ["disclosure-gate"])

    def test_the_refusal_says_to_remove_it_or_argue_the_reading(self):
        r = orchestrate.entry_round(self.study_with(DISCLOSED, mode=None), "widget", "")
        obj = r["verdicts"]["disclosure-gate"]["objections"][0]
        self.assertIn("no such choice", obj)
        self.assertIn("Remove", obj)
        self.assertIn("ground the reading in the document", obj)

    def test_an_adjudicated_record_permits_the_clause_without_requiring_it(self):
        """Adjudicated choices owe the owner nothing — every rival was refuted
        — so the marker is neither required nor a lie."""
        for payload in (CLEAN, DISCLOSED):
            r = orchestrate.entry_round(
                self.study_with(payload, mode="adjudicated"), "widget", "")
            self.assertEqual(r["decision"], "accept")

    def test_a_chair_amended_record_requires_the_marker_like_any_choice(self):
        st = self.study_with(CLEAN, mode="chair-amended")
        r = orchestrate.entry_round(st, "widget", "")
        self.assertEqual(r["failed"], ["disclosure-gate"])


class TestTheAliasCase(Round):
    """An alias settles its term by amending the TARGET, so the target is the
    entry that has to carry the disclosure."""

    FOUNDATION = ("### projection fabric\nKind: base\n"
                  "Statement: The fabric is rebuilt as entries land.\n"
                  "Because: the document treats rebuilding as primitive.\n")

    class Scripted(Round.Scripted):
        def complete(self, system, user, resume=None):
            if self.role_name == "proposer":
                out = {"move": "alias", "target": "projection fabric",
                       "note": self.payload, "reasoning": "the document's other name"}
                return json.dumps(out), {"cost_usd": 0.0}
            return super().complete(system, user, resume)

    def setUp(self):
        super().setUp()
        with open(os.path.join(self.study, "foundation.md"), "w") as f:
            f.write(self.FOUNDATION)

    def study_with(self, note, mode="machine-selected", term="NeverStale", chair=None):
        st = orchestrate.Study(self.study)
        st.state["machine_choices"] = [
            {"term": term, "mode": mode, "chosen": "a reading", "why": "kept going"}]
        st.provider = lambda role: self.Scripted(role, note, chair)
        return st

    def test_an_alias_without_disclosure_on_the_target_is_refused(self):
        r = orchestrate.entry_round(
            self.study_with("The document also calls this NeverStale."), "NeverStale", "")
        self.assertEqual(r["failed"], ["disclosure-gate"])
        self.assertIn("projection fabric", r["verdicts"]["disclosure-gate"]["objections"][0])


class TestTheReportNamesUndisclosedTerms(unittest.TestCase):
    """Visibility for studies that already exist. Reported, never healed."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.study = os.path.join(self.dir, "study")
        os.makedirs(os.path.join(self.study, "log"))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def data(self, foundation, choices):
        with open(os.path.join(self.study, "foundation.md"), "w") as f:
            f.write(foundation)
        return {"study": self.study, "machine_choices": choices}

    CHOICE = [{"term": "widget", "mode": "machine-selected", "chosen": "x"}]

    def test_an_undisclosed_term_is_named(self):
        self.assertEqual(report.undisclosed(self.data(CLEAN, self.CHOICE)), ["widget"])

    def test_a_disclosed_term_is_silent(self):
        self.assertEqual(report.undisclosed(self.data(DISCLOSED, self.CHOICE)), [])

    def test_an_adjudicated_term_is_never_named(self):
        self.assertEqual(report.undisclosed(self.data(
            CLEAN, [{"term": "widget", "mode": "adjudicated", "chosen": "x"}])), [])

    def test_a_study_written_before_the_marker_is_read_fairly(self):
        """Runs that predate the canonical marker disclosed in prose. Reading
        only for the exact string would report them as concealing a choice
        they in fact declared — a compliance failure invented by the
        instrument rather than found in the study."""
        legacy = ("### widget\nKind: base\nStatement: A widget turns.\n"
                  "Because: primitive.\n"
                  "Open: this reading was selected by the run without owner "
                  "confirmation and awaits sign-off.\n")
        self.assertEqual(report.undisclosed(self.data(legacy, self.CHOICE)), [])

    def test_a_note_only_disclosure_is_still_undisclosed(self):
        self.assertEqual(report.undisclosed(self.data(IN_NOTE, self.CHOICE)), ["widget"])

    def test_an_unbacked_claim_is_named(self):
        self.assertEqual(report.unbacked(self.data(DISCLOSED, [])), ["widget"])

    def test_a_backed_claim_is_silent(self):
        self.assertEqual(report.unbacked(self.data(DISCLOSED, self.CHOICE)), [])

    def test_a_chair_amended_record_backs_a_claim(self):
        self.assertEqual(report.unbacked(self.data(
            DISCLOSED, [{"term": "widget", "mode": "chair-amended", "chosen": "x"}])), [])

    def test_a_legacy_prose_claim_counts_as_a_claim(self):
        """Old runs claimed in prose, so the unbacked reading has to see prose
        too — otherwise the direction that actually occurred is invisible in
        every study that predates the marker."""
        legacy = ("### widget\nKind: base\nStatement: A widget turns.\n"
                  "Because: primitive.\n"
                  "Open: this reading was selected by the run without owner "
                  "confirmation and awaits sign-off.\n")
        self.assertEqual(report.unbacked(self.data(legacy, [])), ["widget"])

    def test_an_entry_claiming_nothing_is_never_named(self):
        self.assertEqual(report.unbacked(self.data(CLEAN, [])), [])


if __name__ == "__main__":
    unittest.main()
