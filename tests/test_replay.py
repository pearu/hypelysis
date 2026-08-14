"""The run path, tested without an AI.

A real study's calls are recorded once (tests/fixtures/*.jsonl, built from a
live run with providers.fixture_from_log) and replayed here by the `replay`
provider, which reaches hypelysis through the same interface every real
provider uses. So everything between the CLI and the provider boundary — the
phases, the queue, the logs, the gates, the cost accounting — is exercised
where no provider is reachable and nothing is spent.

    python -m unittest discover -s tests
"""
import json
import os
import shutil
import tempfile
import unittest

from hypelysis import cli, orchestrate, providers
from hypelysis.providers import Replay

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")
DOC = os.path.join(FIXTURES, "sprocket.md")
EXTRACTION = os.path.join(FIXTURES, "sprocket-extraction.jsonl")

# What the recorded run settled on; the replay must reproduce it exactly.
RECORDED_TERMS = 14
RECORDED_MECHANISM = 9
RECORDED_PEOPLE = 5
RECORDED_CALLS = 4


class ReplayStudy(unittest.TestCase):
    def setUp(self):
        Replay.reset()
        self.dir = tempfile.mkdtemp()
        self.study = os.path.join(self.dir, "study")
        cli.main([self.study, "init", DOC,
                  "--set", "default.provider=replay",
                  "--set", f"default.fixture={EXTRACTION}"])

    def tearDown(self):
        Replay.reset()
        shutil.rmtree(self.dir, ignore_errors=True)

    def run_to_gate(self):
        """`run` ends by exiting at the owner gate; that exit is the success."""
        with self.assertRaises(SystemExit) as caught:
            cli.main([self.study, "run"])
        self.assertEqual(caught.exception.code, 0)

    def state(self):
        return json.load(open(os.path.join(self.study, "state.json")))

    def log(self, name):
        p = os.path.join(self.study, "log", name)
        return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []


class TestReplayedExtraction(ReplayStudy):
    def test_extraction_reproduces_the_recorded_queue(self):
        self.run_to_gate()
        queue = json.load(open(os.path.join(self.study, "candidates.json")))
        self.assertEqual(len(queue), RECORDED_TERMS)
        state = self.state()
        self.assertEqual(len(state["queue_lane1"]), RECORDED_MECHANISM)
        self.assertEqual(len(state["queue_lane2"]), RECORDED_PEOPLE)
        self.assertIn("torque budget", state["queue_lane1"])

    def test_the_run_stops_at_the_extraction_gate(self):
        self.run_to_gate()
        state = self.state()
        self.assertEqual(state["phase"], "foundation-lane1")
        self.assertEqual(state["pending_milestone"], "extraction")
        self.assertTrue(os.path.exists(os.path.join(self.study, "APPROVAL-REQUIRED.md")))

    def test_every_recorded_call_is_replayed_and_logged(self):
        self.run_to_gate()
        rounds = self.log("rounds.jsonl")
        self.assertEqual(len(rounds), RECORDED_CALLS)
        self.assertEqual(self.state()["call_count"], RECORDED_CALLS)
        self.assertEqual([r["role"] for r in rounds].count("extractor"), 3)
        self.assertEqual([r["role"] for r in rounds].count("merger"), 1)
        for r in rounds:
            self.assertTrue(r["meta"]["replayed"])
            self.assertEqual(r["spec"]["provider"], "replay")

    def test_a_replayed_run_costs_nothing(self):
        self.run_to_gate()
        self.assertEqual(sum(r["meta"]["cost_usd"] for r in self.log("rounds.jsonl")), 0.0)
        self.assertIn("$0.00", cli.report_mod.build(self.study))

    def test_the_recorded_draws_stay_distinct(self):
        """Three extractors draw independently on one identical prompt. Each
        must be a real call with its own answer: served from the call cache
        instead, the three would collapse to one draw and the merge would see a
        third of the candidates. A fast provider makes that collapse likely —
        the first call returns before its siblings start — so this is where it
        gets caught."""
        self.run_to_gate()
        rounds = self.log("rounds.jsonl")
        self.assertEqual([r.get("cache_hit") for r in rounds].count(True), 0,
                         "an extractor draw was served from the call cache")
        outputs = [r["output"] for r in rounds if r["role"] == "extractor"]
        self.assertEqual(len(set(outputs)), 3)


class TestReplayFidelity(ReplayStudy):
    def test_running_out_of_recorded_replies_fails_loudly(self):
        self.run_to_gate()                      # consumes the whole fixture
        st = orchestrate.Study(self.study)
        with self.assertRaises(RuntimeError) as caught:
            st.provider("merger").complete("system", "one call too many")
        self.assertIn("re-record the fixture", str(caught.exception))

    def test_a_missing_fixture_is_refused_at_once(self):
        with self.assertRaises(RuntimeError):
            providers.make({"provider": "replay",
                            "fixture": os.path.join(self.dir, "nope.jsonl")}, self.dir)

    def test_a_replayed_run_is_itself_recordable(self):
        """Every call logs a digest of its exact prompt, so any finished run —
        replayed ones included — can become the next fixture."""
        self.run_to_gate()
        dest = os.path.join(self.dir, "again.jsonl")
        n = providers.fixture_from_log(self.study, dest)
        self.assertEqual(n, RECORDED_CALLS)
        records = [json.loads(l) for l in open(dest)]
        self.assertTrue(all(r["prompt_sha"] for r in records))
        self.assertEqual(len(set(r["prompt_sha"] for r in records
                                 if r["role"] == "extractor")), 1,
                         "the three extractor draws share one prompt")

    def test_a_stale_prompt_is_reported_and_refused_under_strict(self):
        stale = os.path.join(self.dir, "stale.jsonl")
        with open(stale, "w") as f:
            f.write(json.dumps({"role": "extractor", "prompt_sha": "0" * 64,
                                "output": '{"terms": []}'}) + "\n")
        lenient = providers.make({"provider": "replay", "fixture": stale},
                                 self.dir, role="extractor")
        lenient.complete("system", "a prompt that is not the recorded one")
        self.assertEqual(len(lenient.mismatches), 1)
        self.assertEqual(lenient.mismatches[0]["role"], "extractor")

        Replay.reset(stale)
        strict = providers.make({"provider": "replay", "fixture": stale,
                                 "strict": True}, self.dir, role="extractor")
        with self.assertRaises(RuntimeError) as caught:
            strict.complete("system", "a prompt that is not the recorded one")
        self.assertIn("fixture is stale", str(caught.exception))

    def test_the_matching_prompt_raises_no_mismatch(self):
        fresh = os.path.join(self.dir, "fresh.jsonl")
        system, user = "the system prompt", "the user prompt"
        with open(fresh, "w") as f:
            f.write(json.dumps({"role": "extractor",
                                "prompt_sha": providers.prompt_sha(system, user),
                                "output": '{"terms": []}'}) + "\n")
        p = providers.make({"provider": "replay", "fixture": fresh, "strict": True},
                           self.dir, role="extractor")
        text, meta = p.complete(system, user)
        self.assertEqual(text, '{"terms": []}')
        self.assertEqual(p.mismatches, [])

    def test_replication_replays_from_its_base_role(self):
        """A ':rep' worker is the same instrument at another draw, so it draws
        from the same recorded role."""
        p = providers.make({"provider": "replay", "fixture": EXTRACTION},
                           self.dir, role="extractor:rep")
        self.assertEqual(p.spec()["role"], "extractor")
        self.assertTrue(p.complete("s", "u")[0])


class TestGateCycleUnderReplay(ReplayStudy):
    def test_approving_the_gate_lets_the_next_phase_begin(self):
        self.run_to_gate()
        cli.main([self.study, "approve"])
        state = self.state()
        self.assertIn("extraction", state["approved"])
        self.assertIsNone(state["pending_milestone"])
    def test_a_run_past_the_end_of_the_fixture_stops_and_says_why(self):
        """Lane 1 would start here, but the fixture records no further calls.
        A provider error is a worker fault to the run, so it stops after three
        of them rather than inventing answers — and the reason it could not
        answer is in the log."""
        self.run_to_gate()
        cli.main([self.study, "approve"])
        with self.assertRaises(SystemExit) as caught:
            cli.main([self.study, "run"])
        self.assertIn("worker faults", str(caught.exception.code))
        errors = [r["error"] for r in self.log("rounds.jsonl") if r.get("error")]
        self.assertTrue(errors)
        self.assertIn("re-record the fixture", errors[-1])

    def test_status_after_a_replayed_run(self):
        self.run_to_gate()
        self.assertEqual(cli.main([self.study, "status"]), 0)


if __name__ == "__main__":
    unittest.main()
