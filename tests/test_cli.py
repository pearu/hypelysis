"""Offline tests for the packaged CLI: everything that does not call a worker.

    python -m unittest discover -s tests

Worker calls are not exercised here — those cost money and need a provider;
the acceptance test for the live path is a real study run.
"""
import json
import os
import shutil
import tempfile
import unittest

from hypelysis import cli, orchestrate, report, resources
from hypelysis.check import check_text

DOC = "# Widget Paper\n\nA widget is priced per gadget. Gadgets are counted daily.\n"


class TempStudy(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.study = os.path.join(self.dir, "study")
        self.doc = os.path.join(self.dir, "paper.md")
        with open(self.doc, "w") as f:
            f.write(DOC)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class TestResources(unittest.TestCase):
    def test_rulebook_and_roles_ship_with_the_package(self):
        self.assertIn("### <term>", resources.rulebook())
        for role in ("proposer", "skeptic", "reader", "groundedness",
                     "minimality", "chair", "extractor"):
            self.assertTrue(resources.role(role).strip(), f"empty role: {role}")

    def test_replication_shares_its_base_role_prompt(self):
        self.assertEqual(resources.role("skeptic:rep"), resources.role("skeptic"))

    def test_default_config_is_loadable(self):
        cfg = resources.default_config()
        self.assertIn("default", cfg)
        self.assertIn("model", cfg["default"])


class TestInit(TempStudy):
    def test_init_builds_sandbox_with_document_and_rulebook_only(self):
        self.assertEqual(cli.main([self.study, "init", self.doc]), 0)
        sandbox = os.path.join(self.study, "sandbox")
        self.assertEqual(sorted(os.listdir(sandbox)), ["document.md", "rulebook.md"])
        self.assertIn("widget", open(os.path.join(sandbox, "document.md")).read())
        self.assertEqual(open(os.path.join(sandbox, "rulebook.md")).read(),
                         resources.rulebook())
        state = json.load(open(os.path.join(self.study, "state.json")))
        self.assertEqual(state["phase"], "extraction")

    def test_init_concatenates_several_documents(self):
        second = os.path.join(self.dir, "second.md")
        with open(second, "w") as f:
            f.write("# Second\n\nA sprocket turns.\n")
        cli.main([self.study, "init", self.doc, second])
        text = open(os.path.join(self.study, "sandbox", "document.md")).read()
        self.assertIn("widget", text)
        self.assertIn("sprocket", text)

    def test_init_flags_persist_into_the_study_config(self):
        cli.main([self.study, "init", self.doc, "--view", "lean",
                  "--model", "claude-sonnet-5", "--set", "retry_budget=5"])
        cfg = json.load(open(os.path.join(self.study, "config.json")))
        self.assertEqual(cfg["foundation_view"], "lean")
        self.assertEqual(cfg["default"]["model"], "claude-sonnet-5")
        self.assertEqual(cfg["retry_budget"], 5)


class TestConfigPrecedence(TempStudy):
    def setUp(self):
        super().setUp()
        cli.main([self.study, "init", self.doc])

    def test_run_config_overrides_the_packaged_default(self):
        orchestrate.save(os.path.join(self.study, "config.json"),
                         {"retry_budget": 9})
        self.assertEqual(orchestrate.Study(self.study).cfg["retry_budget"], 9)

    def test_cli_override_wins_over_the_run_config(self):
        orchestrate.save(os.path.join(self.study, "config.json"),
                         {"foundation_view": "full"})
        st = orchestrate.Study(self.study, overrides={"foundation_view": "lean"})
        self.assertEqual(st.cfg["foundation_view"], "lean")

    def test_overriding_one_role_setting_keeps_the_others(self):
        packaged = resources.default_config()["roles"]["skeptic"]
        st = orchestrate.Study(self.study, overrides={
            "roles": {"skeptic": {"effort": "max"}}})
        self.assertEqual(st.cfg["roles"]["skeptic"]["effort"], "max")
        self.assertEqual(st.cfg["roles"]["skeptic"]["model"], packaged["model"])

    def test_provider_flags_land_on_the_default_role(self):
        args = cli.build_parser().parse_args(
            [self.study, "run", "--provider", "openai-http",
             "--base-url", "http://localhost:11434", "--model", "llama3"])
        over = cli.overrides_from(args)
        self.assertEqual(over["default"]["provider"], "openai-http")
        self.assertEqual(over["default"]["base_url"], "http://localhost:11434")
        st = orchestrate.Study(self.study, overrides=over)
        self.assertEqual(st.provider("proposer").spec()["provider"], "openai-http")

    def test_api_key_is_read_from_a_file_never_the_command_line(self):
        keyfile = os.path.join(self.dir, "key")
        with open(keyfile, "w") as f:
            f.write("sk-secret-value\n")
        args = cli.build_parser().parse_args(
            [self.study, "run", "--api-key-file", keyfile])
        self.assertEqual(cli.overrides_from(args)["default"]["api_key"],
                         "sk-secret-value")
        parser_text = cli.build_parser().format_help()
        self.assertNotIn("--api-key ", parser_text)

    def test_set_coerces_json_values_and_nests_on_dots(self):
        args = cli.build_parser().parse_args(
            [self.study, "run", "--set", "note_cap=4",
             "--set", "roles.chair.model=claude-opus-5"])
        over = cli.overrides_from(args)
        self.assertEqual(over["note_cap"], 4)
        self.assertEqual(over["roles"]["chair"]["model"], "claude-opus-5")

    def test_set_without_equals_is_refused(self):
        args = cli.build_parser().parse_args([self.study, "run", "--set", "note_cap"])
        with self.assertRaises(SystemExit):
            cli.overrides_from(args)


class TestGates(TempStudy):
    def setUp(self):
        super().setUp()
        cli.main([self.study, "init", self.doc])

    def test_approve_records_the_pending_milestone_and_clears_the_request(self):
        st = orchestrate.Study(self.study)
        st.state["pending_milestone"] = "extraction"
        orchestrate.save(st.state_p, st.state)
        req = os.path.join(self.study, "APPROVAL-REQUIRED.md")
        with open(req, "w") as f:
            f.write("# Approval required: extraction\n")
        self.assertEqual(cli.main([self.study, "approve"]), 0)
        state = json.load(open(os.path.join(self.study, "state.json")))
        self.assertIn("extraction", state["approved"])
        self.assertIsNone(state["pending_milestone"])
        self.assertFalse(os.path.exists(req))

    def test_the_gate_writes_an_approval_request_naming_the_cli(self):
        st = orchestrate.Study(self.study)
        with self.assertRaises(SystemExit):
            st.milestone_gate("extraction")
        text = open(os.path.join(self.study, "APPROVAL-REQUIRED.md")).read()
        self.assertIn(f"hypelysis {self.study} approve", text)

    def test_resolve_records_the_decision_and_requeues_the_term(self):
        st = orchestrate.Study(self.study)
        st.state["queue_lane1"] = ["gadget"]
        orchestrate.save(st.state_p, st.state)
        self.assertEqual(cli.main([self.study, "resolve", "widget",
                                   "adopt", "the", "attribute", "reading"]), 0)
        state = json.load(open(os.path.join(self.study, "state.json")))
        self.assertEqual(state["resolutions"]["widget"],
                         "adopt the attribute reading")
        self.assertEqual(state["queue_lane1"][0], "widget")

    def test_commands_refuse_a_directory_that_holds_no_study(self):
        with self.assertRaises(SystemExit):
            cli.main([os.path.join(self.dir, "nowhere"), "status"])


class TestStatusAndReport(TempStudy):
    def test_status_reports_phase_and_what_it_waits_on(self):
        cli.main([self.study, "init", self.doc])
        st = orchestrate.Study(self.study)
        st.state.update({"pending_milestone": "extraction", "call_count": 4,
                         "queue_lane1": ["a", "b"], "queue_lane2": ["c"],
                         "outcomes": {"a": "accept", "b": "escalate"}})
        orchestrate.save(st.state_p, st.state)
        self.assertEqual(cli.main([self.study, "status"]), 0)

    def test_report_writes_a_run_report_from_the_logs(self):
        cli.main([self.study, "init", self.doc])
        logdir = os.path.join(self.study, "log")
        with open(os.path.join(logdir, "rounds.jsonl"), "w") as f:
            f.write(json.dumps({"role": "proposer", "seconds": 12.5,
                                "meta": {"cost_usd": 0.25, "output_tokens": 400,
                                         "cache_write_tokens": 20, "cache_read_tokens": 30}}) + "\n")
        with open(os.path.join(logdir, "decisions.jsonl"), "w") as f:
            f.write(json.dumps({"term": "widget", "attempt": 0,
                                "decision": "accept"}) + "\n")
        self.assertEqual(cli.main([self.study, "report"]), 0)
        text = open(os.path.join(self.study, "RUN-REPORT.md")).read()
        self.assertIn("proposer", text)
        self.assertIn("widget", text)
        self.assertIn("$0.25", text)


class TestChecks(unittest.TestCase):
    ENTRY = ("### widget\nKind: base\nStatement: A widget is a thing.\n"
             "Because: Everyday reading suffices.\n")

    def test_a_clean_entry_passes(self):
        self.assertEqual(check_text(self.ENTRY), [])

    def test_declaration_fields_are_accepted_in_the_rulebook_order(self):
        entry = self.ENTRY + ("Defers: gadget — entry owed on first count\n"
                              "Open: whether widgets nest\n"
                              "Finding: the paper counts widgets twice\n"
                              "Note: residual commentary.\n")
        self.assertEqual(check_text(entry), [])

    def test_field_order_violation_names_the_required_order(self):
        entry = self.ENTRY + "Note: commentary.\nOpen: whether widgets nest\n"
        problems = check_text(entry)
        self.assertEqual(len(problems), 1)
        self.assertIn("required order", problems[0])
        self.assertIn("Defers", problems[0])

    def test_note_cap_flags_only_when_asked(self):
        entry = self.ENTRY + "Note: One. Two. Three. Four. Five.\n"
        self.assertEqual(check_text(entry), [])
        self.assertIn("Note exceeds 4 sentences", check_text(entry, note_cap=4)[0])

    def test_a_defined_entry_may_not_use_a_later_term(self):
        entry = ("### beta\nKind: defined\nStatement: Beta wraps alpha.\n"
                 "Uses: alpha\n\n### alpha\nKind: base\n"
                 "Statement: Alpha is a thing.\nBecause: Everyday.\n")
        self.assertIn("not an earlier entry", check_text(entry)[0])


class TestViews(unittest.TestCase):
    FND = ("### alpha\nKind: base\nStatement: Alpha is a thing.\n"
           "Because: Everyday.\nDefers: gamma — entry owed on first count\n"
           "Open: whether alpha nests\nFinding: the paper counts alphas twice\n"
           "Note: residual commentary.\nWorked example: alpha one\n")

    def test_the_full_view_is_the_whole_record(self):
        self.assertEqual(orchestrate.view_foundation(self.FND, None), self.FND)

    def test_the_lean_view_drops_author_facing_fields(self):
        view = orchestrate.view_foundation(self.FND, "lean")
        self.assertNotIn("Finding:", view)
        self.assertNotIn("residual commentary", view)
        self.assertNotIn("Worked example", view)

    def test_the_lean_view_never_drops_a_declaration(self):
        view = orchestrate.view_foundation(self.FND, "lean")
        self.assertIn("Defers: gamma — entry owed on first count", view)
        self.assertIn("Open: whether alpha nests", view)
        self.assertIn("Statement: Alpha is a thing.", view)


if __name__ == "__main__":
    unittest.main()


class TestReportRendering(unittest.TestCase):
    """The file keeps exact numbers; the terminal gets columns and human units."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.study = os.path.join(self.dir, "study")
        cli.main([self.study, "init", os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "fixtures", "sprocket.md")])
        with open(os.path.join(self.study, "log", "rounds.jsonl"), "w") as f:
            for role, secs, out_tok, cost in (("proposer", 4500.0, 2_500_000, 12.5),
                                              ("skeptic", 42.0, 1500, 0.25)):
                f.write(json.dumps({"role": role, "seconds": secs,
                                    "meta": {"cost_usd": cost, "output_tokens": out_tok,
                                             "cache_write_tokens": 0,
                                             "cache_read_tokens": 0}}) + "\n")
        with open(os.path.join(self.study, "log", "decisions.jsonl"), "w") as f:
            f.write(json.dumps({"term": "widget", "attempt": 1,
                                "decision": "accept"}) + "\n")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_the_terminal_rendering_uses_human_units(self):
        shown = report.build(self.study)
        self.assertIn("1.2h", shown)      # 4500 seconds
        self.assertIn("2.50M", shown)     # 2,500,000 output tokens
        self.assertIn("$12.75", shown)    # both calls' cost

    def test_the_terminal_columns_line_up(self):
        shown = report.build(self.study)
        body = [l for l in shown.splitlines() if l.startswith("  ") and "s" in l]
        widths = {len(l.rstrip()) for l in body if not l.strip().startswith("-")}
        self.assertTrue(all(l == l.rstrip() for l in shown.splitlines()),
                        "no line may carry trailing padding")
        self.assertGreater(len(body), 2)
        self.assertLessEqual(max(widths) - min(widths), 60)

    def test_the_file_keeps_the_exact_numbers(self):
        report.build(self.study)
        filed = open(os.path.join(self.study, "RUN-REPORT.md")).read()
        self.assertIn("| proposer | 1 | 4500 |", filed)
        self.assertIn("2500000", filed)


class TestTermCounts(unittest.TestCase):
    """The report says how many terms the study found and how far it has got."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.study = os.path.join(self.dir, "study")
        cli.main([self.study, "init", os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "fixtures", "sprocket.md")])
        json.dump([{"term": "a"}, {"term": "b"}, {"term": "c", "lane": "people"}],
                  open(os.path.join(self.study, "candidates.json"), "w"))
        json.dump([{"term": x} for x in "abcde"],
                  open(os.path.join(self.study, "candidates-raw.json"), "w"))
        st = orchestrate.Study(self.study)
        st.state["queue_lane1"] = ["b"]
        orchestrate.save(st.state_p, st.state)
        with open(os.path.join(self.study, "log", "decisions.jsonl"), "w") as f:
            for term, attempt, decision in (("a", 0, "retry"), ("a", 1, "accept"),
                                            ("c", 0, "escalate"), ("b", 0, "retry")):
                f.write(json.dumps({"term": term, "attempt": attempt,
                                    "decision": decision}) + "\n")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_candidates_are_counted_by_lane_and_against_the_raw_draw(self):
        line = report._terms(report.gather(self.study))
        self.assertIn("3 candidates (2 mechanism, 1 people)", line)
        self.assertIn("merged from 5 raw", line)

    def test_a_term_still_being_retried_is_not_counted_as_settled(self):
        line = report._terms(report.gather(self.study))
        self.assertIn("2 settled (1 accept, 1 escalate)", line)
        self.assertIn("1 in progress", line)
        self.assertIn("1 still queued", line)

    def test_both_renderings_carry_the_counts(self):
        shown = report.build(self.study)
        self.assertIn("terms     3 candidates", shown)
        self.assertIn("Terms: 3 candidates",
                      open(os.path.join(self.study, "RUN-REPORT.md")).read())


class TestTermTiming(unittest.TestCase):
    """How long each term took, recovered from the call log."""

    def calls(self, *specs):
        return [dict(role=r, at=at, seconds=s) for r, at, s in specs]

    def test_attempts_line_up_with_decisions_at_proposer_boundaries(self):
        calls = self.calls(("extractor", 100.0, 5.0),          # before any term
                           ("proposer", 200.0, 10.0),          # widget, attempt 0
                           ("skeptic", 210.0, 20.0),
                           ("proposer", 300.0, 10.0),          # widget, attempt 1
                           ("chair", 310.0, 5.0),
                           ("proposer", 400.0, 10.0),          # gadget
                           ("chair", 410.0, 30.0))
        decisions = [{"term": "widget", "decision": "retry"},
                     {"term": "widget", "decision": "accept"},
                     {"term": "gadget", "decision": "accept"}]
        t = report.term_times(calls, decisions)
        self.assertEqual(t["widget"]["wall"], 30.0 + 15.0)   # both attempts
        self.assertEqual(t["gadget"]["wall"], 40.0)
        self.assertTrue(t["widget"]["exact"])

    def test_wall_time_counts_parallel_workers_once(self):
        calls = self.calls(("proposer", 0.0, 10.0), ("skeptic", 10.0, 30.0),
                           ("reader", 10.0, 30.0), ("chair", 40.0, 5.0))
        t = report.term_times(calls, [{"term": "widget", "decision": "accept"}])
        self.assertEqual(t["widget"]["wall"], 45.0)          # not the 75s of worker time
        self.assertEqual(t["widget"]["worker"], 75.0)

    def test_a_log_without_timestamps_reports_worker_time_and_says_so(self):
        calls = [{"role": "proposer", "seconds": 10.0}, {"role": "chair", "seconds": 5.0}]
        t = report.term_times(calls, [{"term": "widget", "decision": "accept"}])
        self.assertFalse(t["widget"]["exact"])
        self.assertEqual(t["widget"]["worker"], 15.0)

    def test_cached_calls_cost_no_time(self):
        calls = [{"role": "proposer", "at": 0.0, "seconds": 10.0},
                 {"role": "skeptic", "cache_hit": True, "seconds": 0.0},
                 {"role": "chair", "at": 10.0, "seconds": 5.0}]
        t = report.term_times(calls, [{"term": "widget", "decision": "accept"}])
        self.assertEqual(t["widget"]["wall"], 15.0)
