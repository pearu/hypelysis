#!/usr/bin/env python3
"""The engine of a study: a checked run over foundation entries.

One candidate term per round: the proposer drafts a move; the checks return
verdicts; the gate accepts, retries with feedback, defers, or refuses. Every
round is logged. At each milestone the run STOPS and writes an approval
request — the owner's approval is an input the machinery waits for, not a step
it performs.

Driven through the command line (see hypelysis.cli): `hypelysis <study> init
<document>...` then `hypelysis <study> run`. State lives in <study>/state.json;
the run is resumable and every worker call is recorded in
<study>/log/rounds.jsonl.
"""
import json
import re
import os
import sys
import time

import hashlib
from . import providers
from . import resources
from .check import check_text
from concurrent.futures import ThreadPoolExecutor
import threading
_loglock = threading.Lock()
CHECKS = ["groundedness", "skeptic", "minimality"]   # AI checks; rules_check is a script
GENERIC_SYSTEM = ("You are one worker in a checked run that studies a document. "
                  "The message you receive holds shared materials, then YOUR ROLE "
                  "INSTRUCTIONS, then your input. Follow the role instructions "
                  "exactly; they are your only task.")
READER_PROFILES = ["a careful reader whose first language is not English",
                   "a software engineer who will implement what the text describes",
                   "a mathematician who expects statements to be precise"]
MILESTONES = ["extraction", "foundation-lane1", "foundation-lane2", "report"]


# ------------------------------------------------------------------ plumbing
def load(path, default):
    return json.load(open(path)) if os.path.exists(path) else default


def save(path, obj):
    json.dump(obj, open(path, "w"), indent=1)


def deep_update(dst: dict, src: dict) -> dict:
    """Merge src into dst, nested dicts included — a config override that
    names one role's model must not drop that role's other settings."""
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            deep_update(dst[k], v)
        else:
            dst[k] = v
    return dst


class Study:
    def __init__(self, out, overrides: dict = None):
        self.out = out
        self.sandbox = os.path.join(out, "sandbox")
        self.state_p = os.path.join(out, "state.json")
        self.state = load(self.state_p, {})
        self.cfg = resources.default_config()
        deep_update(self.cfg, load(os.path.join(out, "config.json"), {}))  # run-local
        deep_update(self.cfg, overrides or {})                             # CLI flags win
        self.last_meta = None
        self.cache = {}
        cp = os.path.join(out, "log", "callcache.jsonl")
        if os.path.exists(cp):
            for line in open(cp):
                r = json.loads(line)
                self.cache[r["key"]] = r["output"]

    def role(self, name, **fmt):
        prompt = resources.role(name)
        for k, v in fmt.items():
            prompt = prompt.replace("{" + k + "}", v)
        return prompt

    def provider(self, role):
        roles = self.cfg.get("roles", {})
        # ':rep' replications inherit the base role's provider: a replication
        # is the same instrument at a different draw, so the model is pinned
        cfg = roles.get(role) or roles.get(role.split(":")[0]) \
            or self.cfg["default"]
        return providers.make(cfg, self.sandbox, role=role)

    def packaged(self, role_prompt, shared, tail):
        """Default packaging: the role prompt is the system prompt, so each
        role presents a different byte-0 prefix to the provider's prompt
        cache. shared-prefix packaging: one generic system prompt for every
        role and the role instructions placed AFTER the shared block, so all
        roles present the same prefix (system + document + rulebook +
        foundation) and the cache is written once, read six times."""
        mode = self.cfg.get("prompt_packaging")
        if mode == "shared-prefix":
            return (GENERIC_SYSTEM,
                    f"{shared}YOUR ROLE INSTRUCTIONS:\n{role_prompt}\n\n{tail}")
        if mode == "shared-prefix-blocks":
            # structured for adapters with explicit cache_control: the shared
            # block is marked cacheable; the role-specific part follows it
            return (GENERIC_SYSTEM,
                    [{"text": shared, "cache": True},
                     {"text": f"YOUR ROLE INSTRUCTIONS:\n{role_prompt}\n\n{tail}"}])
        return (role_prompt, shared + tail)

    def primer(self, shared, like="primer"):
        """session-primer packaging: deliver the shared block to one throwaway
        session; every role call then forks it via --resume, so the request
        prefix (system + shared turn + stored reply) is byte-identical across
        roles — a message-boundary-aligned cache prefix the CLI can share.
        Byte-identity is guaranteed by replay, not generation: forks re-send
        the stored turn verbatim. One primer call per shared-block state."""
        spec = self.provider(like).spec()
        key = (f"{spec.get('provider')}:{spec.get('model')}:"
               + hashlib.sha256(shared.encode()).hexdigest())
        sid = self.state.setdefault("primer_sessions", {}).get(key)
        if sid:
            return sid
        reply = self.call(f"primer[{spec.get('model')}]", GENERIC_SYSTEM,
                          shared + '\nThe material above is shared context for '
                          'instructions that follow later. Acknowledge by '
                          'replying with exactly this JSON and nothing else: '
                          '{"ok": true}', provider_as=like)
        sid = (self.last_meta or {}).get("session_id")
        if isinstance(reply, dict) and reply.get("ok") is True and sid:
            self.state["primer_sessions"][key] = sid
            save(self.state_p, self.state)
            return sid
        return None   # primer failed; caller falls back to inline packaging

    def call(self, role, system, user, draw=0, resume=None, provider_as=None):
        self.last_meta = None
        n = self.state.get("call_count", 0) + 1
        self.state["call_count"] = n
        ceiling = self.cfg.get("max_calls_per_run", 600)
        if n > ceiling:
            raise SystemExit(f"CALL CEILING ({ceiling}) reached — stopping; "
                             "raise max_calls_per_run in config.json to continue")
        p = self.provider(provider_as or role)
        spec = p.spec()
        key = hashlib.sha256(json.dumps(
            [spec.get("provider"), spec.get("model"), spec.get("effort"),
             system, user, draw, resume]).encode()).hexdigest()
        if key in self.cache:
            with _loglock:
                with open(os.path.join(self.out, "log", "rounds.jsonl"), "a") as f:
                    f.write(json.dumps({"role": role, "cache_hit": True,
                                        "seconds": 0.0, "key": key}) + "\n")
            return providers.json_out(self.cache[key])
        t0 = time.time()
        nowp = os.path.join(self.out, "log", "now.json")
        with _loglock:
            d = load(nowp, {})
            d[role] = {"term": self.state.get("now_term", "?"), "t0": t0}
            save(nowp, d)
        try:
            text, meta = p.complete(system, user, resume=resume)
        except Exception as e:
            rec = {"role": role, "spec": p.spec(),
                   "seconds": round(time.time() - t0, 1), "error": str(e)[:500]}
            with _loglock:
                d = load(nowp, {}); d.pop(role, None); save(nowp, d)
                with open(os.path.join(self.out, "log", "rounds.jsonl"), "a") as f:
                    f.write(json.dumps(rec) + "\n")
            return {"verdict": "no", "objections": [f"WORKER ERROR: {str(e)[:200]}"],
                    "worker_error": True}
        rec = {"role": role, "spec": p.spec(), "seconds": round(time.time() - t0, 1),
               "resumed": bool(resume), "meta": meta,
               "system_sha": hash(system) & 0xffffffff,
               # a stable digest of the exact prompt, so a finished run can be
               # replayed by the fake provider without storing the prompts
               "prompt_sha": providers.prompt_sha(system, user), "output": text}
        with _loglock:
            d = load(nowp, {}); d.pop(role, None); save(nowp, d)
            with open(os.path.join(self.out, "log", "rounds.jsonl"), "a") as f:
                f.write(json.dumps(rec) + "\n")
            with open(os.path.join(self.out, "log", "callcache.jsonl"), "a") as f:
                f.write(json.dumps({"key": key, "output": text}) + "\n")
            self.cache[key] = text
            self.last_meta = meta
        try:
            return providers.json_out(text)
        except Exception as e:
            return {"verdict": "no", "objections": [f"UNPARSEABLE OUTPUT: {str(e)[:200]}"],
                    "worker_error": True}

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
                    f"directory, then run:\n\n    hypelysis {self.out} approve\n")
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


FIELD_START = re.compile(r"^(Kind|Given|Statement|Because|Uses|Notation|Defers|Open"
                         r"|Finding|Note|Worked example):")
# Author-facing fields, dropped from every prior entry in a lean worker view.
VIEW_DROP = {"Finding", "Note", "Worked example"}
# Never stripped at any level: the lane-2 A/B showed checks re-derive
# stripped declarations as objections, at a retry round apiece.
DECLARATIONS = {"Defers", "Open"}
# Aggressive mode reduces out-of-neighborhood entries to these.
VIEW_MINIMAL = {"Given", "Statement"} | DECLARATIONS


def view_foundation(fnd: str, mode: str, term: str = None, st=None) -> str:
    """Worker view of the foundation; the on-disk file remains the full
    record, only prompts shrink. 'lean' drops the author-facing fields
    (Finding, Note, worked examples) from every entry. 'lean-aggressive'
    additionally reduces entries outside the candidate term's dependency
    neighborhood (its presupposed terms, closed over Uses lines) to
    Given/Statement plus declarations."""
    if mode not in ("lean", "lean-aggressive"):
        return fnd
    blocks = re.split(r"(?=^### )", fnd, flags=re.M)
    uses = {}
    for b in blocks:
        m = re.match(r"^### (.+)", b)
        u = re.search(r"^Uses: ?(.*)", b, re.M)
        if m and u and u.group(1).strip().lower() != "everyday language only":
            uses[m.group(1).strip().lower()] = [x.strip().lower()
                                               for x in u.group(1).split(",") if x.strip()]
    neighborhood = None
    if mode == "lean-aggressive" and term and st:
        seed = [p.strip().lower() for c in load(os.path.join(st.out, "candidates.json"), [])
                if c["term"].strip().lower() == term.strip().lower()
                for p in (c.get("presupposes") or [])]
        neighborhood = set(seed)
        frontier = list(seed)
        while frontier:
            for n in uses.get(frontier.pop(), []):
                if n not in neighborhood:
                    neighborhood.add(n)
                    frontier.append(n)
    out = []
    for b in blocks:
        m = re.match(r"^### (.+)", b)
        if not m:
            out.append(b)
            continue
        keep = None
        if neighborhood is not None and m.group(1).strip().lower() not in neighborhood:
            keep = VIEW_MINIMAL
        lines, field = [m.group(0)], None
        for line in b.splitlines()[1:]:
            fs = FIELD_START.match(line)
            if fs:
                field = fs.group(1)
            if field in VIEW_DROP:
                continue
            if keep is not None and field is not None and field not in keep:
                continue
            lines.append(line)
        out.append("\n".join(lines).rstrip() + "\n\n")
    return "".join(out)


def rules_check(st: Study, foundation: str) -> dict:
    problems = check_text(foundation, st.cfg.get("note_cap"))
    return {"verdict": "no" if problems else "ok", "objections": problems}


def presupposed_by(st: Study, term: str) -> list:
    cands = load(os.path.join(st.out, "candidates.json"), [])
    t = term.strip().lower()
    return [c["term"] for c in cands
            if t in [p.strip().lower() for p in (c.get("presupposes") or [])]]


def entry_round(st: Study, term: str, feedback: str) -> dict:
    rb = open(os.path.join(st.sandbox, "rulebook.md")).read()
    doc = open(os.path.join(st.sandbox, "document.md")).read()
    fnd = open(os.path.join(st.out, "foundation.md")).read() \
        if os.path.exists(os.path.join(st.out, "foundation.md")) else "(empty)"
    fnd = view_foundation(fnd, st.cfg.get("foundation_view"), term, st)
    shared = (f"DOCUMENT UNDER STUDY:\n{doc}\n\nRULEBOOK:\n{rb}\n\n"
              f"FOUNDATION:\n{fnd}\n\n")
    conv = st.cfg.get("proposer_mode") == "conversational"
    sid = (st.state.get("proposer_sessions") or {}).get(term) if conv else None
    if sid:
        # live session: the proposer already holds document, rulebook and its
        # own drafts; a retry sends only the fresh verdicts as a short turn
        prop = st.call("proposer", st.role("proposer"),
                       f"REVIEWER FEEDBACK on your previous proposal:\n"
                       f"{feedback or '(none)'}\n\n"
                       "Revise accordingly and output the complete JSON move "
                       "again, per your role instructions.", resume=sid)
    else:
        ptail = (f"CANDIDATE: {term}\n"
                 f"\nREVIEWER FEEDBACK:\n{feedback or '(none)'}")
        prime_sid = st.primer(shared, "proposer") \
            if st.cfg.get("prompt_packaging") == "session-primer" else None
        if prime_sid:
            prop = st.call("proposer", GENERIC_SYSTEM,
                           f"YOUR ROLE INSTRUCTIONS:\n{st.role('proposer')}"
                           f"\n\n{ptail}", resume=prime_sid)
        else:
            psys, puser = st.packaged(st.role("proposer"), shared, ptail)
            prop = st.call("proposer", psys, puser)
    if conv and (st.last_meta or {}).get("session_id"):
        st.state.setdefault("proposer_sessions", {})[term] = \
            st.last_meta["session_id"]
        save(st.state_p, st.state)
    if prop.get("move") not in ("entry", "revision", "reorder", "defer", "prerequisites"):
        return {"decision": "retry", "failed": ["proposer"], "proposal": prop,
                "verdicts": {"proposer": {"verdict": "no", "objections": [
                    "proposer reply unusable (worker error or off-schema); try again"]}}}
    if prop["move"] == "prerequisites":
        return {"decision": "prerequisites", "proposal": prop, "verdicts": {}}

    if prop["move"] in ("defer",):
        needed_by = presupposed_by(st, term)
        if needed_by:
            return {"decision": "retry", "failed": ["defer-gate"], "proposal": prop,
                    "verdicts": {"defer-gate": {"verdict": "no", "objections": [
                        f"deferral rejected mechanically: {term} is presupposed by "
                        f"{', '.join(needed_by[:5])} — propose an entry"]}}}
        sk = st.call("skeptic", st.role("skeptic"),
                     f"DOCUMENT UNDER STUDY:\n{doc}\n\nRULEBOOK:\n{rb}\n\n"
                     f"FOUNDATION:\n{fnd}\n\nPROPOSAL (a deferral "
                     f"— judge whether its reasoning holds):\n{json.dumps(prop, indent=1)}")
        if sk.get("verdict") != "ok":
            return {"decision": "retry", "failed": ["skeptic"], "proposal": prop,
                    "verdicts": {"skeptic": sk}}
        return {"decision": "defer", "proposal": prop, "verdicts": {"skeptic": sk}}

    verdicts = {}
    payload = prop["payload"]
    if not isinstance(payload, str):
        payload = json.dumps(payload, indent=1)
    verdicts["rules"] = rules_check(
        st, fnd + "\n\n" + payload if prop["move"] == "entry" else payload)
    if verdicts["rules"]["verdict"] != "ok":
        return {"decision": "retry", "failed": ["rules"], "proposal": prop,
                "verdicts": verdicts}
    tail = (f"PROPOSAL:\n{payload}\n\n"
            f"PROPOSER'S REASONING:\n{prop.get('reasoning', '')}\n\n"
            f"PRIOR OBJECTIONS AND REBUTTALS:\n{feedback or '(none — first attempt)'}")
    priming = st.cfg.get("prompt_packaging") == "session-primer"
    jobs = {}
    for c in CHECKS:
        sid_c = st.primer(shared, c) if priming else None
        if sid_c:
            jobs[c] = {"role": c, "system": GENERIC_SYSTEM, "resume": sid_c,
                       "user": f"YOUR ROLE INSTRUCTIONS:\n{st.role(c)}\n\n{tail}"}
        else:
            sys_c, user_c = st.packaged(st.role(c), shared, tail)
            jobs[c] = {"role": c, "system": sys_c, "user": user_c}
    for i, profile in enumerate(READER_PROFILES):
        jobs[f"reader:{i}"] = {"role": f"reader:{i}",
                               "system": st.role("reader", profile=profile),
                               "user": f"ENTRY:\n{payload}"}

    def runjob(j, draw=0, rep=False):
        return st.call(j["role"] + (":rep" if rep else ""), j["system"],
                       j["user"], draw=draw, resume=j.get("resume"))
    if st.cfg.get("verdict_strategy") == "staged":
        cheap = {k: v for k, v in jobs.items() if k != "skeptic"}
        with ThreadPoolExecutor(len(cheap)) as ex:
            results = dict(zip(cheap, ex.map(runjob, cheap.values())))
        cheap_fail = any(results[c].get("verdict") != "ok" for c in CHECKS if c in results) \
            or sum(1 for i in range(len(READER_PROFILES))
                   if results[f"reader:{i}"].get("ambiguous")) >= 2
        if cheap_fail:
            results["skeptic"] = {"verdict": "no", "objections": [
                "skipped under staged strategy: cheaper checks already failed"],
                "skipped": True}
        else:
            results["skeptic"] = runjob(jobs["skeptic"])
    else:
        with ThreadPoolExecutor(len(jobs)) as ex:
            results = dict(zip(jobs, ex.map(runjob, jobs.values())))
    for c in CHECKS:
        verdicts[c] = results[c]
    restatements = [results[f"reader:{i}"] for i in range(len(READER_PROFILES))]
    # readers agree iff no reader reports ambiguity; divergence checking of the
    # restatements themselves is the skeptic's job in the next round's feedback
    n_flagged = sum(1 for r in restatements if r.get("ambiguous"))
    verdicts["readers"] = {"verdict": "no" if n_flagged >= 2 else "ok",
                           "flagged": n_flagged, "restatements": restatements}

    bad = [k for k, v in verdicts.items() if v.get("verdict") != "ok"]
    if not bad:
        return {"decision": "accept", "failed": [], "proposal": prop, "verdicts": verdicts}
    if "rules" in bad:   # the mechanical check is absolute; no chair can overrule it
        return {"decision": "retry", "failed": bad, "proposal": prop, "verdicts": verdicts}
    # replicate failed AI checks once, blind: an objection that recurs across
    # independent draws is signal; one that does not is possibly draw noise
    to_rep = [c for c in bad if c in CHECKS
              and not (verdicts[c].get("skipped") or verdicts[c].get("worker_error"))]
    if to_rep:
        with ThreadPoolExecutor(len(to_rep)) as ex:
            reps = dict(zip(to_rep, ex.map(
                lambda c: runjob(jobs[c], draw=1, rep=True), to_rep)))
        for c, rep in reps.items():
            verdicts[c] = {"sample_1": verdicts[c], "sample_2_blind": rep,
                           "verdict": verdicts[c]["verdict"]}
    chair_tail = (f"PROPOSAL:\n{payload}\n\n"
                  f"REVIEWER VERDICTS:\n{json.dumps(verdicts, indent=1)[:12000]}")
    chair_sid = st.primer(shared, "chair") \
        if st.cfg.get("prompt_packaging") == "session-primer" else None
    if chair_sid:
        chair = st.call("chair", GENERIC_SYSTEM,
                        f"YOUR ROLE INSTRUCTIONS:\n{st.role('chair')}\n\n"
                        f"{chair_tail}", resume=chair_sid)
    else:
        chair = st.call("chair", st.role("chair"),
                        f"DOCUMENT UNDER STUDY:\n{doc}\n\nRULEBOOK:\n{rb}\n\n"
                        f"FOUNDATION:\n{fnd}\n\n{chair_tail}")
    if chair.get("decision") not in ("accept", "revise", "escalate"):
        # chair failed or replied off-schema: fall back to a plain retry with
        # the raw verdicts as feedback; never let the arbiter crash the round
        return {"decision": "retry", "failed": bad, "proposal": prop,
                "verdicts": verdicts, "chair": {"decision": "retry",
                "feedback": "chair unavailable; address the reviewer verdicts directly",
                "error": str(chair)[:300]}}
    if chair["decision"] == "accept":
        if chair.get("payload"):
            prop = dict(prop, payload=chair["payload"])
        for t in (chair.get("revision_triggers") or []):
            with open(os.path.join(st.out, "revision-backlog.md"), "a") as f:
                f.write(f"- **{term}** — {str(t)[:400]}\n")
        return {"decision": "accept", "failed": bad, "proposal": prop,
                "verdicts": verdicts, "chair": chair}
    if chair["decision"] == "escalate":
        return {"decision": "escalate", "failed": bad, "proposal": prop,
                "verdicts": verdicts, "chair": chair}
    return {"decision": "retry", "failed": bad, "proposal": prop,
            "verdicts": verdicts, "chair": chair}


def phase_foundation(st: Study, lane: str):
    budget = st.cfg.get("retry_budget", 3)
    qkey = "queue_lane1" if lane == "lane1" else "queue_lane2"
    queue = st.state.get(qkey, [])
    resolutions = st.state.get("resolutions", {})
    while queue:
        done = st.state.get("outcomes", {})
        if len(done) >= 6:
            landed = sum(1 for v in done.values() if v == "accept")
            if landed == 0 or landed / len(done) < 0.2:
                with open(os.path.join(st.out, "VERDICT.md"), "w") as f:
                    f.write("# Saturation stop\n\nOf the first "
                            f"{len(done)} terms, {landed} could be founded. The document "
                            "does not support a foundation; see escalations.md and the "
                            "decision log for why, term by term.\n")
                st.state["phase"] = "report"
                save(st.state_p, st.state)
                print("\nSATURATION STOP — the document does not support a foundation.")
                sys.exit(0)
        term = queue[0]
        st.state["now_term"] = term
        feedback = ""
        if term in resolutions:
            feedback = "OWNER DECISION (binding):\n" + resolutions.pop(term)
        attempt, spent, faults = 0, 0, 0
        while spent < budget:
            r = entry_round(st, term, feedback)
            worker_fault = any((r["verdicts"].get(k) or {}).get("worker_error")
                               for k in (r.get("failed") or [])) or \
                r.get("failed") == ["proposer"]
            faults = faults + 1 if worker_fault else 0
            if faults >= 3:
                raise SystemExit(
                    f"STOP - 3 consecutive worker faults on '{term}' (provider "
                    "refusing, likely a rate/usage limit); state is saved - "
                    "rerun when the limit resets")
            spent += 0 if worker_fault else 1
            attempt += 1
            log = {"term": term, "attempt": attempt - 1, **r}
            with open(os.path.join(st.out, "log", "decisions.jsonl"), "a") as f:
                f.write(json.dumps(log) + "\n")
            if r["decision"] == "accept":
                apply_move(st, r["proposal"])
                st.state.setdefault("outcomes", {})[term] = "accept"
                break
            if r["decision"] == "defer":
                record_deferral(st, term, r["proposal"])
                break
            if r["decision"] == "prerequisites":
                fnd_p = os.path.join(st.out, "foundation.md")
                have = set(m.lower() for m in __import__("re").findall(
                    r"^### (.+)$", open(fnd_p).read(), 8)) if os.path.exists(fnd_p) else set()
                named = [t for t in r["proposal"]["payload"]
                         if t.lower() not in have][:4]
                if not named:   # everything already founded: a failed attempt
                    feedback = "prerequisites rejected: all named terms already have entries"
                    continue
                # hoist queued-later terms in front of this one; insert new ones
                hoist = [t for t in named if t.lower() in
                         {x.lower() for x in queue[1:]}]
                fresh = [t for t in named if t not in hoist]
                for t in hoist:
                    queue.remove(next(x for x in queue if x.lower() == t.lower()))
                st.state.setdefault("inserted", []).extend(fresh)
                queue[0:0] = hoist + fresh
                break
            ch = r.get("chair")
            feedback = (("CHAIR: " + ch.get("feedback", "")) if ch
                        else json.dumps({k: r["verdicts"][k] for k in r["failed"]}, indent=1))
            if r["decision"] == "escalate":
                record_escalation(st, term, r)
                queue.pop(0)
                st.state[qkey] = queue
                save(st.state_p, st.state)
                if presupposed_by(st, term):
                    st.state["pending_milestone"] = f"escalation:{term}"
                    save(st.state_p, st.state)
                    print(f"\nSTOP — root term '{term}' escalated; dependents blocked. "
                          f"Resolve it, then approve and rerun.")
                    sys.exit(0)
                break
        else:
            record_escalation(st, term, r)
            st.state.setdefault("outcomes", {})[term] = "escalate"
            if presupposed_by(st, term):
                queue.pop(0)
                st.state[qkey] = queue
                st.state["pending_milestone"] = f"escalation:{term}"
                save(st.state_p, st.state)
                print(f"\nSTOP — root term '{term}' escalated after budget; "
                      f"dependents blocked. Resolve it, then rerun.")
                sys.exit(0)
        if queue and queue[0] == term:
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
    elif prop["move"] in ("revision", "reorder"):
        # the payload is the complete replacement foundation, already validated
        # by rules_check against the whole text
        with open(os.path.join(st.out, "log", "structure-moves.jsonl"), "a") as f:
            f.write(json.dumps(prop) + "\n")
        payload = prop["payload"]
        if isinstance(payload, str) and payload.strip().startswith("###"):
            import re as _re
            new_names = set(_re.findall(r"^### (.+)$", payload, _re.M))
            have = set(_re.findall(r"^### (.+)$", open(p).read(), _re.M)) \
                if os.path.exists(p) else set()
            if have <= new_names:
                open(p, "w").write(payload.strip() + "\n")   # true full replacement
            elif not (new_names & have):
                with open(p, "a") as f:                        # purely new entries
                    f.write("\n" + payload.strip() + "\n")
            else:
                # partial overlap would destroy entries: apply the overlapping
                # blocks in place instead of overwriting the file
                text = open(p).read()
                for name in new_names & have:
                    m = _re.search(rf"### {_re.escape(name)}\n.*?(?=\n### |\Z)",
                                   payload, _re.S)
                    if m:
                        text = _re.sub(rf"### {_re.escape(name)}\n.*?(?=\n### |\Z)",
                                       m.group(0).rstrip() + "\n", text, flags=_re.S)
                for name in new_names - have:
                    m = _re.search(rf"### {_re.escape(name)}\n.*?(?=\n### |\Z)",
                                   payload, _re.S)
                    if m:
                        text = text.rstrip() + "\n\n" + m.group(0).strip() + "\n"
                open(p, "w").write(text)


def record_deferral(st: Study, term, prop):
    with open(os.path.join(st.out, "deferred.md"), "a") as f:
        f.write(f"- **{term}** — {prop.get('reasoning', '')}\n")


def record_escalation(st: Study, term, last):
    """Budget exhausted on a genuine choice: put it to the owner at the gate."""
    with open(os.path.join(st.out, "escalations.md"), "a") as f:
        f.write(f"\n## {term}\n\nLast proposal:\n\n```\n"
                f"{last['proposal'].get('payload', '')[:1200]}\n```\n\n"
                f"What the checks converged on:\n")
        for k in last.get("failed", []):
            v = last["verdicts"].get(k, {})
            for o in (v.get("objections") or [])[:3]:
                f.write(f"- ({k}) {str(o)[:300]}\n")
            for r in (v.get("restatements") or []):
                for a in (r.get("ambiguous") or [])[:1]:
                    f.write(f"- (reader) {str(a)[:300]}\n")
        f.write(f"\nResolve with:\n    hypelysis {st.out} resolve "
                f"\"{term}\" \"<your decision>\"\n")


# ------------------------------------------------------------------ commands
def cmd_init(st: Study, documents: list):
    """Create the study: its sandbox holds the documents under study and the
    rulebook, nothing else — a worker sees the method and the subject."""
    os.makedirs(st.sandbox, exist_ok=True)
    os.makedirs(os.path.join(st.out, "log"), exist_ok=True)
    docs = [open(d).read() for d in documents]
    open(os.path.join(st.sandbox, "document.md"), "w").write("\n\n".join(docs))
    open(os.path.join(st.sandbox, "rulebook.md"), "w").write(resources.rulebook())
    st.state = {"phase": "extraction", "approved": []}
    save(st.state_p, st.state)
    print(f"initialized {st.out} from {len(docs)} document(s); "
          "sandbox holds the document and rulebook only")


def cmd_resolve(st: Study, term: str, decision: str):
    """Record the owner's decision on an escalated term and re-queue it; the
    decision reaches the proposer as binding feedback."""
    st.state.setdefault("resolutions", {})[term] = decision
    for qk in ("queue_lane1", "queue_lane2"):
        q = st.state.get(qk, [])
        if term not in q and qk == "queue_lane1":
            q.insert(0, term)
            st.state[qk] = q
            break
    save(st.state_p, st.state)
    print(f"resolution recorded; '{term}' re-queued with the owner's decision as feedback")


def cmd_approve(st: Study):
    """Record the owner's approval of the milestone the run is waiting on."""
    name = st.state.get("pending_milestone") or st.state.get("phase")
    st.state.setdefault("approved", []).append(name)
    st.state["pending_milestone"] = None
    save(st.state_p, st.state)
    req = os.path.join(st.out, "APPROVAL-REQUIRED.md")
    os.path.exists(req) and os.remove(req)
    print(f"approved: {name}")


def cmd_run(st: Study):
    """Advance the study to its next owner gate."""
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
