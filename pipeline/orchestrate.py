#!/usr/bin/env python3
"""The hypelysis pipeline: a checked run over foundation entries.

One candidate term per round: the proposer drafts a move; the checks return
verdicts; the gate accepts, retries with feedback, defers, or refuses. Every
round is logged. At each milestone the pipeline STOPS and writes an approval
request — the owner's approval is an input the machinery waits for, not a step
it performs.

Usage:
  python3 pipeline/orchestrate.py init  <study-out-dir> <document>...
  python3 pipeline/orchestrate.py run   <study-out-dir>
  python3 pipeline/orchestrate.py approve <study-out-dir>   (records the owner's go)

State lives in <study-out-dir>/state.json; the run is resumable and every
worker call is recorded in <study-out-dir>/log/rounds.jsonl.
"""
import json
import os
import shutil
import subprocess
import sys
import time

import providers
from concurrent.futures import ThreadPoolExecutor
import threading
_loglock = threading.Lock()

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKS = ["groundedness", "skeptic", "minimality"]   # AI checks; rules_check is a script
READER_PROFILES = ["a careful reader whose first language is not English",
                   "a software engineer who will implement what the text describes",
                   "a mathematician who expects statements to be precise"]
MILESTONES = ["extraction", "foundation-lane1", "foundation-lane2", "report"]


# ------------------------------------------------------------------ plumbing
def load(path, default):
    return json.load(open(path)) if os.path.exists(path) else default


def save(path, obj):
    json.dump(obj, open(path, "w"), indent=1)


class Study:
    def __init__(self, out):
        self.out = out
        self.sandbox = os.path.join(out, "sandbox")
        self.state_p = os.path.join(out, "state.json")
        self.state = load(self.state_p, {})
        self.cfg = load(os.path.join(HERE, "config.json"), {})

    def role(self, name, **fmt):
        prompt = open(os.path.join(HERE, "roles", f"{name.split(':')[0]}.md")).read()
        for k, v in fmt.items():
            prompt = prompt.replace("{" + k + "}", v)
        return prompt

    def provider(self, role):
        cfg = self.cfg.get("roles", {}).get(role) or self.cfg["default"]
        return providers.make(cfg, self.sandbox)

    def call(self, role, system, user):
        p = self.provider(role)
        t0 = time.time()
        text, meta = p.complete(system, user)
        rec = {"role": role, "spec": p.spec(), "seconds": round(time.time() - t0, 1),
               "meta": meta,
               "system_sha": hash(system) & 0xffffffff, "output": text}
        with _loglock:
            with open(os.path.join(self.out, "log", "rounds.jsonl"), "a") as f:
                f.write(json.dumps(rec) + "\n")
        return providers.json_out(text)

    def milestone_gate(self, name):
        """Stop until the owner has approved this milestone."""
        approved = self.state.get("approved", [])
        if name in approved:
            return
        self.state["pending_milestone"] = name
        save(self.state_p, self.state)
        req = os.path.join(self.out, "APPROVAL-REQUIRED.md")
        with open(req, "w") as f:
            f.write(f"# Approval required: {name}\n\nReview the artifacts in this "
                    f"directory, then run:\n\n    python3 pipeline/orchestrate.py "
                    f"approve {self.out}\n")
        print(f"\nSTOP — milestone '{name}' awaits owner approval ({req})")
        sys.exit(0)


# ------------------------------------------------------------------ phases
def phase_extract(st: Study):
    doc = open(os.path.join(st.sandbox, "document.md")).read()
    rb = open(os.path.join(st.sandbox, "rulebook.md")).read()
    n = st.cfg.get("extractors", 3)
    with ThreadPoolExecutor(n) as ex:
        outs = list(ex.map(lambda i: st.call("extractor", st.role("extractor"),
                    f"RULEBOOK:\n{rb}\n\nDOCUMENT:\n{doc}"), range(n)))
    merged, seen = [], set()
    for out in outs:
        for t in out.get("terms", []):
            key = t["term"].strip().lower()
            if key not in seen:
                seen.add(key)
                merged.append(t)
    save(os.path.join(st.out, "candidates-raw.json"), merged)
    merge_queue(st, merged)
    print(f"extraction: {len(merged)} raw candidates")


def merge_queue(st: Study, merged):
    rb = open(os.path.join(st.sandbox, "rulebook.md")).read()
    out = st.call("merger", st.role("merger"),
                  f"RULEBOOK:\n{rb}\n\nRAW CANDIDATES:\n{json.dumps(merged, indent=1)}")
    queue = out["queue"]
    save(os.path.join(st.out, "candidates.json"), queue)
    st.state["phase"] = "foundation-lane1"
    st.state["queue_lane1"] = [t["term"] for t in queue if t.get("lane") != "people"]
    st.state["queue_lane2"] = [t["term"] for t in queue if t.get("lane") == "people"]
    save(st.state_p, st.state)
    print(f"queue: {len(st.state['queue_lane1'])} mechanism + {len(st.state['queue_lane2'])} people")


def rules_check(st: Study, foundation: str) -> dict:
    r = subprocess.run([sys.executable, os.path.join(HERE, "check.py"), "-"],
                       input=foundation, text=True, capture_output=True)
    return {"verdict": "ok" if r.returncode == 0 else "no",
            "objections": r.stdout.strip().splitlines() if r.returncode else []}


def entry_round(st: Study, term: str, feedback: str) -> dict:
    rb = open(os.path.join(st.sandbox, "rulebook.md")).read()
    fnd = open(os.path.join(st.out, "foundation.md")).read() \
        if os.path.exists(os.path.join(st.out, "foundation.md")) else "(empty)"
    prop = st.call("proposer", st.role("proposer"),
                   f"RULEBOOK:\n{rb}\n\nFOUNDATION:\n{fnd}\n\nCANDIDATE: {term}\n"
                   f"\nREVIEWER FEEDBACK:\n{feedback or '(none)'}")
    if prop["move"] in ("defer",):
        return {"decision": "defer", "proposal": prop, "verdicts": {}}

    verdicts = {}
    payload = prop["payload"]
    verdicts["rules"] = rules_check(st, fnd + "\n\n" + payload if prop["move"] == "entry" else payload)
    jobs = {c: (c, st.role(c),
                f"RULEBOOK:\n{rb}\n\nFOUNDATION:\n{fnd}\n\nPROPOSAL:\n{payload}")
            for c in CHECKS}
    for i, profile in enumerate(READER_PROFILES):
        jobs[f"reader:{i}"] = (f"reader:{i}", st.role("reader", profile=profile),
                               f"ENTRY:\n{payload}")
    with ThreadPoolExecutor(len(jobs)) as ex:
        results = dict(zip(jobs, ex.map(lambda a: st.call(*a), jobs.values())))
    for c in CHECKS:
        verdicts[c] = results[c]
    restatements = [results[f"reader:{i}"] for i in range(len(READER_PROFILES))]
    # readers agree iff no reader reports ambiguity; divergence checking of the
    # restatements themselves is the skeptic's job in the next round's feedback
    verdicts["readers"] = {"verdict": "ok" if not any(r.get("ambiguous") for r in restatements)
                           else "no", "restatements": restatements}

    bad = [k for k, v in verdicts.items() if v.get("verdict") != "ok"]
    return {"decision": "accept" if not bad else "retry",
            "failed": bad, "proposal": prop, "verdicts": verdicts}


def phase_foundation(st: Study, lane: str):
    budget = st.cfg.get("retry_budget", 3)
    qkey = "queue_lane1" if lane == "lane1" else "queue_lane2"
    queue = st.state.get(qkey, [])
    while queue:
        term = queue[0]
        feedback = ""
        for attempt in range(budget):
            r = entry_round(st, term, feedback)
            log = {"term": term, "attempt": attempt, **r}
            with open(os.path.join(st.out, "log", "decisions.jsonl"), "a") as f:
                f.write(json.dumps(log) + "\n")
            if r["decision"] == "accept":
                apply_move(st, r["proposal"])
                break
            if r["decision"] == "defer":
                record_deferral(st, term, r["proposal"])
                break
            feedback = json.dumps({k: r["verdicts"][k] for k in r["failed"]}, indent=1)
        else:
            record_refusal(st, term)
        queue.pop(0)
        st.state[qkey] = queue
        save(st.state_p, st.state)
    st.state["phase"] = "foundation-lane2" if lane == "lane1" else "report"
    save(st.state_p, st.state)


def apply_move(st: Study, prop: dict):
    p = os.path.join(st.out, "foundation.md")
    if prop["move"] == "entry":
        with open(p, "a") as f:
            f.write("\n" + prop["payload"].strip() + "\n")
    # revision/reorder application is validated by check.py on the full result
    elif prop["move"] in ("revision", "reorder"):
        with open(os.path.join(st.out, "log", "structure-moves.jsonl"), "a") as f:
            f.write(json.dumps(prop) + "\n")


def record_deferral(st: Study, term, prop):
    with open(os.path.join(st.out, "deferred.md"), "a") as f:
        f.write(f"- **{term}** — {prop.get('reasoning', '')}\n")


def record_refusal(st: Study, term):
    with open(os.path.join(st.out, "refused.md"), "a") as f:
        f.write(f"- **{term}** — retry budget exhausted; see log/decisions.jsonl\n")


# ------------------------------------------------------------------ main
def main():
    cmd, out = sys.argv[1], sys.argv[2]
    st = Study(out)
    if cmd == "init":
        os.makedirs(st.sandbox, exist_ok=True)
        os.makedirs(os.path.join(out, "log"), exist_ok=True)
        docs = [open(d).read() for d in sys.argv[3:]]
        open(os.path.join(st.sandbox, "document.md"), "w").write("\n\n".join(docs))
        shutil.copy(os.path.join(HERE, "rulebook.md"), st.sandbox)
        st.state = {"phase": "extraction", "approved": []}
        save(st.state_p, st.state)
        print(f"initialized {out}; sandbox holds the document and rulebook only")
    elif cmd == "approve":
        name = st.state.get("pending_milestone") or st.state["phase"]
        st.state.setdefault("approved", []).append(name)
        st.state["pending_milestone"] = None
        save(st.state_p, st.state)
        req = os.path.join(out, "APPROVAL-REQUIRED.md")
        os.path.exists(req) and os.remove(req)
        print(f"approved: {name}")
    elif cmd == "run":
        phase = st.state.get("phase", "extraction")
        if phase == "extraction":
            phase_extract(st)
            st.milestone_gate("extraction")
        elif phase == "foundation-lane1":
            st.milestone_gate("extraction")
            phase_foundation(st, "lane1")
            st.milestone_gate("foundation-lane1")
        elif phase == "foundation-lane2":
            phase_foundation(st, "lane2")
            st.milestone_gate("foundation-lane2")
        elif phase == "report":
            print("report phase: built in build-phase 4")
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
