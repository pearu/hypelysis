"""Extraction in batches: draw blind once, then hunt what is missing.

Independent draws mostly re-find each other's terms, so their union stops
growing long before the document is exhausted. Later batches are told what is
already recorded and asked for the rest.
"""
import json
import os
import shutil
import tempfile
import unittest

from hypelysis import cli, orchestrate, resources


class Extraction(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.study = os.path.join(self.dir, "study")
        cli.main([self.study, "init", os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "fixtures", "sprocket.md")])
        self.st = orchestrate.Study(self.study)
        self.prompts, self.draws = [], []

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def extractors(self, *batches, merger=None):
        """A stand-in worker: each batch of draws returns the terms it is given."""
        state = {"batch": -1, "in_batch": 0}
        per_batch = self.st.cfg.get("extractors", 3)

        def call(role, system, user, draw=0, resume=None, provider_as=None):
            if role == "merger":
                return merger or {"queue": [{"term": t, "lane": "mechanism"}
                                            for t in sorted(self.seen)]}
            self.prompts.append(user)
            self.draws.append(draw)
            if state["in_batch"] % per_batch == 0:
                state["batch"] += 1
            state["in_batch"] += 1
            terms = batches[min(state["batch"], len(batches) - 1)]
            self.seen.update(terms)
            return {"terms": [{"term": t, "work": "…", "presupposes": []} for t in terms]}
        self.seen = set()
        self.st.call = call

    def raw(self):
        return [t["term"] for t in
                json.load(open(os.path.join(self.study, "candidates-raw.json")))]


class TestBatches(Extraction):
    def test_the_first_batch_draws_blind(self):
        self.extractors(["a", "b"], [])
        orchestrate.phase_extract(self.st)
        self.assertNotIn("ALREADY RECORDED", self.prompts[0])

    def test_later_batches_are_told_what_is_already_found(self):
        self.extractors(["a", "b"], ["c"], [])
        orchestrate.phase_extract(self.st)
        second = self.prompts[3]
        self.assertIn("ALREADY RECORDED", second)
        self.assertIn("- a", second)
        self.assertIn("do not re-list", second)

    def test_later_batches_may_re_decompose_what_was_recorded(self):
        """The licence is the point: without it a conditioned draw cannot
        disagree with the granularity it is handed."""
        self.extractors(["a"], ["b"], [])
        orchestrate.phase_extract(self.st)
        self.assertIn("granularity looks wrong", self.prompts[3])
        self.assertIn("propose the finer terms", self.prompts[3])

    def test_batches_stop_when_one_adds_almost_nothing(self):
        """The default stop is 'at most one new term', so the batch that finds
        a single term is the last one."""
        self.extractors(["a", "b"], ["c"], ["d"])
        orchestrate.phase_extract(self.st)
        self.assertEqual(sorted(self.raw()), ["a", "b", "c"])
        batches = json.load(open(self.st.state_p))["extraction_batches"]
        self.assertEqual([b["new_terms"] for b in batches], [2, 1])
        self.assertEqual([b["conditioned"] for b in batches], [False, True])

    def test_a_stricter_stop_keeps_drawing_while_anything_is_new(self):
        self.st.cfg["extraction_stop"] = 0
        self.extractors(["a", "b"], ["c"], [], ["d"])
        orchestrate.phase_extract(self.st)
        batches = json.load(open(self.st.state_p))["extraction_batches"]
        self.assertEqual([b["new_terms"] for b in batches], [2, 1, 0])

    def test_the_batch_limit_is_honoured(self):
        self.st.cfg["extraction_batches"] = 2
        self.extractors(["a"], ["b"], ["c"], ["d"])
        orchestrate.phase_extract(self.st)
        self.assertEqual(sorted(self.raw()), ["a", "b"])

    def test_a_batch_still_finding_terms_at_the_limit_says_so(self):
        self.st.cfg["extraction_batches"] = 2
        self.extractors(["a"], ["b", "c"])
        detail = orchestrate.phase_extract(self.st)
        self.assertIn("still finding", detail)
        self.assertIn("raise extraction_batches", detail)

    def test_every_draw_has_its_own_index(self):
        """Identical prompts within a batch would otherwise share a cache key
        and hand every draw the first one's answer."""
        self.extractors(["a"], ["b"], [])
        orchestrate.phase_extract(self.st)
        self.assertEqual(len(self.draws), len(set(self.draws)))

    def test_a_single_batch_run_is_still_possible(self):
        self.st.cfg["extraction_batches"] = 1
        self.extractors(["a", "b"])
        orchestrate.phase_extract(self.st)
        self.assertEqual(sorted(self.raw()), ["a", "b"])
        self.assertEqual(len(self.draws), 3)


class TestDropsTravelWithGrounds(Extraction):
    MERGER = {"queue": [{"term": "alpha", "lane": "mechanism",
                         "merged_from": ["alpha term"]}],
              "dropped": [{"term": "beta", "why": "the document never loads it"}]}

    def test_the_reason_for_each_drop_reaches_the_gate(self):
        self.extractors(["alpha", "alpha term", "beta"], [], merger=self.MERGER)
        detail = orchestrate.phase_extract(self.st)
        self.assertIn("**beta** — the document never loads it", detail)
        self.assertIn("a term left out is out of the study", detail)

    def test_a_term_cut_without_a_reason_is_reported_as_unaccounted(self):
        self.extractors(["alpha", "beta", "gamma"], [], merger=self.MERGER)
        detail = orchestrate.phase_extract(self.st)
        self.assertIn("Neither queued nor accounted for", detail)
        self.assertIn("- gamma", detail)
        saved = json.load(open(os.path.join(self.study, "candidates-dropped.json")))
        self.assertEqual(saved["unaccounted"], ["gamma"])

    def test_a_term_absorbed_by_another_is_accounted_for(self):
        self.extractors(["alpha", "alpha term", "beta"], [], merger=self.MERGER)
        orchestrate.phase_extract(self.st)
        saved = json.load(open(os.path.join(self.study, "candidates-dropped.json")))
        self.assertEqual(saved["unaccounted"], [])

    def test_the_owner_sees_all_of_it_in_the_approval_request(self):
        self.extractors(["alpha", "beta", "gamma"], [], merger=self.MERGER)
        detail = orchestrate.phase_extract(self.st)
        with self.assertRaises(SystemExit):
            self.st.milestone_gate("extraction", detail)
        text = open(os.path.join(self.study, "APPROVAL-REQUIRED.md")).read()
        self.assertIn("How the candidates were found", text)
        self.assertIn("**beta**", text)
        self.assertIn("- gamma", text)
        self.assertIn(f"hypelysis {self.study} approve", text)


class TestRolePrompts(unittest.TestCase):
    def test_the_merger_must_account_for_every_candidate(self):
        role = resources.role("merger")
        self.assertIn("A term you leave out is out of the study", role)
        self.assertIn('"dropped"', role)
        self.assertIn("Do not\ndrop a term merely because it looks minor", role)

    def test_the_binding_text_carries_real_newlines(self):
        self.assertTrue(orchestrate.DECISION_BINDS_THE_READING.startswith("\n\n"))
        self.assertNotIn("\\n", orchestrate.DECISION_BINDS_THE_READING)

    def test_no_role_prompt_ends_in_an_escaped_newline(self):
        for role in ("options", "merger", "extractor", "adjudicator", "arbiter"):
            self.assertNotIn("\\n", resources.role(role), f"{role}.md")


if __name__ == "__main__":
    unittest.main()


class TestUntil(unittest.TestCase):
    """`--until N` bounds an invocation to N terms and leaves it resumable."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.study = os.path.join(self.dir, "study")
        cli.main([self.study, "init", os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "fixtures", "sprocket.md")])

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def prepared(self, until, already=()):
        st = orchestrate.Study(self.study, overrides={"until": until})
        st.state.update({"phase": "foundation-lane1",
                         "approved": ["extraction"],
                         "queue_lane1": ["a", "b", "c"],
                         "outcomes": {t: "accept" for t in already}})
        orchestrate.save(st.state_p, st.state)
        st.call = lambda *a, **k: self.fail("no term should be attempted")
        return st

    def test_zero_terms_stops_before_any_work(self):
        st = self.prepared(0)
        with self.assertRaises(SystemExit) as caught:
            orchestrate.phase_foundation(st, "lane1")
        self.assertEqual(caught.exception.code, 0)
        self.assertEqual(json.load(open(st.state_p))["queue_lane1"], ["a", "b", "c"])

    def test_the_limit_counts_only_this_invocation(self):
        """A study that already settled terms is not finished by a later
        --until 2; it settles two more."""
        st = self.prepared(2, already=("x", "y", "z"))
        st.call = lambda *a, **k: self.fail("stopped too early")
        try:
            orchestrate.phase_foundation(st, "lane1")
        except SystemExit:
            self.fail("--until 2 must not stop before settling anything")
        except AssertionError:
            pass          # reached the first term, which is the point

    def test_the_flag_reaches_the_config(self):
        args = cli.build_parser().parse_args([self.study, "run", "--until", "5"])
        self.assertEqual(cli.overrides_from(args)["until"], 5)
        args = cli.build_parser().parse_args([self.study, "run"])
        self.assertNotIn("until", cli.overrides_from(args))

    def test_zero_is_a_real_limit_not_an_absent_one(self):
        args = cli.build_parser().parse_args([self.study, "run", "--until", "0"])
        self.assertEqual(cli.overrides_from(args)["until"], 0)
