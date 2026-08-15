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

import difflib
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
# Asked what a list misses, a worker answers — whether or not anything is
# missing. Measured: batches conditioned on a longer list returned MORE terms,
# not fewer, until they were naming every noun in the document. So the ask must
# make an empty answer expected, and make each addition carry its grounds.
CONDITIONED_BATCH = (
    "Name only what this list MISSES: terms the document loads that no recorded term "
    "covers. An empty list is the expected answer when the list is already complete — "
    "returning nothing is a legitimate result, and a better answer than padding it with "
    "words the document merely contains. For each term you do add, the work line must "
    "name what the document does with it: the claim, count, or mechanism that turns on "
    "the term. If the recorded granularity looks wrong — a term that should be split, or "
    "decomposed differently — propose the finer terms and say what the split buys.")
# A verdict that binds an actor must travel with grounds enough to act on, or
# it must not bind. What a decision settles is a proposition; the words it
# arrived in are not part of it, and a proposer told otherwise transcribes them
# into a Statement the format then rejects.
DECISION_BINDS_THE_READING = (
    "\n\nThis decision fixes the READING: the proposition above is settled. It "
    "does not fix any wording. Draft the entry as the rulebook requires, "
    "expressing this reading; where the decision mentions record-keeping "
    "(openness, findings), that is your judgment to place, not text to "
    "transcribe.")


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

    def drop_primer(self, sid):
        """Forget a primer session that no longer resumes."""
        sessions = self.state.get("primer_sessions") or {}
        stale = [k for k, v in sessions.items() if v == sid]
        for k in stale:
            del sessions[k]
        if stale:
            save(self.state_p, self.state)
        return bool(stale)

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
            if resume:
                # A stored session that no longer resumes would fail every
                # call that forks it, stalling the run for good. Drop it: the
                # next attempt primes a fresh one and keeps the packaging the
                # run was configured with, rather than silently going inline.
                self.drop_primer(resume)
            rec = {"role": role, "spec": p.spec(), "at": t0,
                   "seconds": round(time.time() - t0, 1), "error": str(e)[:500]}
            with _loglock:
                d = load(nowp, {}); d.pop(role, None); save(nowp, d)
                with open(os.path.join(self.out, "log", "rounds.jsonl"), "a") as f:
                    f.write(json.dumps(rec) + "\n")
            return {"verdict": "no", "objections": [f"WORKER ERROR: {str(e)[:200]}"],
                    "worker_error": True}
        rec = {"role": role, "spec": p.spec(), "at": t0,
               "seconds": round(time.time() - t0, 1),
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

    def milestone_gate(self, name, detail: str = ""):
        """Stop until the owner has approved this milestone."""
        approved = self.state.get("approved", [])
        if name in approved:
            return
        self.state["pending_milestone"] = name
        save(self.state_p, self.state)
        req = os.path.join(self.out, "APPROVAL-REQUIRED.md")
        with open(req, "w") as f:
            f.write(f"# Approval required: {name}\n\n"
                    + (detail + "\n\n" if detail else "")
                    + "Review the artifacts in this directory, then run:\n\n"
                    + f"    hypelysis {self.out} approve\n")
        print(f"\nSTOP — milestone '{name}' awaits owner approval ({req})")
        sys.exit(0)


# ------------------------------------------------------------------ phases
def phase_extract(st: Study) -> str:
    """Find the terms a foundation must settle, one batch of draws at a time.

    Independent draws mostly re-find each other's terms: measured on this
    method, four candidates in five that a fresh draw reports are already
    recorded, and the union of such draws stops growing long before the
    document is exhausted — that ceiling measures the draws' shared attention,
    not the document. So only the first batch draws blind. Every later batch is
    shown what is already recorded and asked for what the list misses, free to
    re-decompose a recorded term where the granularity looks wrong. Batches
    stop when one adds almost nothing.

    Draws inside a batch run together and never see each other; only completed
    batches are carried forward. Each draw gets its own draw index, or they
    would share a cache key and return one another's answers.
    """
    doc = open(os.path.join(st.sandbox, "document.md")).read()
    rb = open(os.path.join(st.sandbox, "rulebook.md")).read()
    n = st.cfg.get("extractors", 3)
    # Two batches by default — one blind, one hunting what it missed. Of ten
    # terms known to be real and known to be missed by blind draws, twenty-seven
    # of thirty instances were recovered by the second batch; later batches keep
    # finding real terms, but diluted, and every candidate is queue length a run
    # pays for.
    max_batches = st.cfg.get("extraction_batches", 2)
    stop_at = st.cfg.get("extraction_stop", 1)
    base = f"RULEBOOK:\n{rb}\n\nDOCUMENT:\n{doc}"
    merged, seen, batches, draw = [], set(), [], 0
    for b in range(max(max_batches, 1)):
        if b == 0:
            prompt = base
        else:
            prompt = (base + "\n\nCANDIDATES ALREADY RECORDED by earlier draws "
                      "(pre-set; do not re-list them):\n"
                      + "\n".join(f"- {t['term']}" for t in merged)
                      + "\n\n" + CONDITIONED_BATCH)
        with ThreadPoolExecutor(n) as ex:
            outs = list(ex.map(
                lambda i: st.call("extractor", st.role("extractor"), prompt, draw=i),
                range(draw, draw + n)))
        draw += n
        added = 0
        for out in outs:
            for t in (out.get("terms") or []):
                key = str(t.get("term", "")).strip().lower()
                if key and key not in seen:
                    seen.add(key)
                    merged.append(t)
                    added += 1
        batches.append({"batch": b + 1, "conditioned": b > 0,
                        "draws": n, "new_terms": added, "total": len(merged)})
        print(f"extraction batch {b + 1}"
              f"{' (conditioned)' if b else ' (independent)'}: "
              f"+{added} new, {len(merged)} candidates so far")
        if b > 0 and added <= stop_at:
            break
    save(os.path.join(st.out, "candidates-raw.json"), merged)
    st.state["extraction_batches"] = batches
    save(st.state_p, st.state)
    detail = merge_queue(st, merged)
    print(f"extraction: {len(merged)} raw candidates in {len(batches)} batch(es)")
    lines = ["## How the candidates were found", ""]
    for x in batches:
        lines.append(f"- batch {x['batch']} "
                     f"({'conditioned on what was already found' if x['conditioned'] else 'independent'}, "
                     f"{x['draws']} draws): +{x['new_terms']} new, {x['total']} total")
    if batches and batches[-1]["new_terms"] > stop_at:
        lines += ["", f"The last batch was still finding {batches[-1]['new_terms']} new "
                  "terms when the batch limit was reached: raise extraction_batches if "
                  "the set looks short."]
    return "\n".join(lines) + "\n\n" + detail


def first_mention(term: str, doc: str) -> int:
    """Where the document first speaks of a term. The document is what both a
    study and its reader already share, so it orders terms without any study
    needing to know what another study did."""
    t = " ".join(str(term).strip().lower().split())
    i = doc.find(t)
    if i >= 0:
        return i
    seen = [doc.find(w) for w in re.findall(r"[a-z][a-z-]{3,}", t)]
    seen = [x for x in seen if x >= 0]
    return min(seen) if seen else len(doc)


def canonical_order(queue: list, doc: str):
    """Put the queue in the one order the method actually implies.

    The rulebook fixes order only up to topology — an entry may use only
    earlier entries — and every linearisation of that order is legal. The
    merger was choosing among them by whim, and two studies of one document
    diverged there rather than in what they had found. Sorting the same
    topology deterministically, with ties broken by the document's own order of
    mention, removes the whim and keeps every judgement.

    Lane 2 follows lane 1 entire (rule 6). Returns the ordered queue and the
    cycles that had to be broken, which are the presupposition hints
    contradicting each other and are worth an owner's eye.
    """
    doc = doc.lower()
    ordered, cycles = [], []
    for people in (False, True):
        block = [t for t in queue if (t.get("lane") == "people") == people]
        names = {str(t.get("term", "")).strip().lower() for t in block}
        by_name = {str(t.get("term", "")).strip().lower(): t for t in block}
        deps = {n: {str(p).strip().lower() for p in (by_name[n].get("presupposes") or [])
                    if str(p).strip().lower() in names
                    and str(p).strip().lower() != n}
                for n in names}
        placed, mention = set(), {n: first_mention(n, doc) for n in names}
        while len(placed) < len(names):
            ready = sorted((n for n in names if n not in placed and deps[n] <= placed),
                           key=lambda n: (mention[n], n))
            if not ready:
                stuck = sorted((n for n in names if n not in placed),
                               key=lambda n: (mention[n], n))
                ready = [stuck[0]]
                cycles.append({"term": by_name[ready[0]]["term"],
                               "waiting_on": sorted(deps[ready[0]] - placed)})
            ordered.append(by_name[ready[0]])
            placed.add(ready[0])
    return ordered, cycles


def merge_queue(st: Study, merged) -> str:
    """Turn the raw candidates into the working queue.

    Merging is not only tidying: a term the merger leaves out is out of the
    study, which is a decision about scope. Every drop is named with its reason
    and shown at the gate, and a term that is neither queued nor accounted for
    is reported as unaccounted — a silent cut is exactly what the owner's
    approval is supposed to cover.
    """
    rb = open(os.path.join(st.sandbox, "rulebook.md")).read()
    out = st.call("merger", st.role("merger"),
                  f"RULEBOOK:\n{rb}\n\nRAW CANDIDATES:\n{json.dumps(merged, indent=1)}")
    if out.get("worker_error"):
        save(st.state_p, st.state)
        raise SystemExit(
            "STOP - the merger call failed (" + str((out.get("objections") or [""])[0])[:200]
            + "); the draws are saved and cached, so re-running costs only the merge")
    if "queue" not in out:
        raise SystemExit("STOP - the merger answered without a queue: "
                         + json.dumps(out)[:500])
    queue = out["queue"]
    dropped = [d for d in (out.get("dropped") or []) if isinstance(d, dict)]
    accounted = {str(t.get("term", "")).strip().lower() for t in queue}
    for d in dropped:
        accounted.add(str(d.get("term", "")).strip().lower())
        for v in (d.get("merged_into") or []) if isinstance(d.get("merged_into"), list) else []:
            accounted.add(str(v).strip().lower())
    for t in queue:
        for v in (t.get("merged_from") or []):
            accounted.add(str(v).strip().lower())
    unaccounted = [t.get("term") for t in merged
                   if str(t.get("term", "")).strip().lower() not in accounted]
    # A candidate written as a split proposal — "grant minting vs. grant
    # exercise" — says a reader thought one recorded term is doing two jobs.
    # Flattening it back into one term decides the document's granularity, so
    # it is found here rather than trusted to the merger's own account.
    declined = [d for d in (out.get("splits_declined") or []) if isinstance(d, dict)]
    told = {str(d.get("proposed", "")).strip().lower() for d in declined}
    queued = {str(t.get("term", "")).strip().lower() for t in queue}
    silent_splits = []
    for t in merged:
        name = str(t.get("term", "")).strip()
        parts = re.split(r"\s+vs\.?\s+|\s+/\s+", name)
        if len(parts) < 2 or name.strip().lower() in told:
            continue
        survived = [p for p in parts if p.strip().lower() in queued]
        if len(survived) < len(parts):
            silent_splits.append({"proposed": name,
                                  "kept": survived[0] if survived else None})
    doc = open(os.path.join(st.sandbox, "document.md")).read()
    queue, cycles = canonical_order(queue, doc)
    save(os.path.join(st.out, "candidates.json"), queue)
    save(os.path.join(st.out, "candidates-dropped.json"),
         {"dropped": dropped, "unaccounted": unaccounted,
          "splits_declined": declined, "splits_flattened_silently": silent_splits})
    st.state["phase"] = "foundation-lane1"
    st.state["queue_lane1"] = [t["term"] for t in queue if t.get("lane") != "people"]
    st.state["queue_lane2"] = [t["term"] for t in queue if t.get("lane") == "people"]
    save(st.state_p, st.state)
    print(f"queue: {len(st.state['queue_lane1'])} mechanism + "
          f"{len(st.state['queue_lane2'])} people"
          + (f"; {len(dropped)} dropped" if dropped else "")
          + (f"; {len(unaccounted)} unaccounted" if unaccounted else ""))
    lines = [f"## The queue: {len(queue)} terms from {len(merged)} candidates", "",
             "Ordered by what each term presupposes, ties broken by where the document "
             "first speaks of it — the same queue whoever merges it.", ""]
    if cycles:
        lines += ["**These presupposition hints contradict each other**; the cycle was "
                  "broken at the term the document mentions first:", ""]
        lines += [f"- **{c['term']}** placed before {', '.join(c['waiting_on'])}"
                  for c in cycles]
        lines.append("")
    if dropped:
        lines += ["Dropped, with the merger's reason — a term left out is out of the "
                  "study:", ""]
        lines += [f"- **{d.get('term')}** — {d.get('why') or '(no reason given)'}"
                  for d in dropped]
        lines.append("")
    if unaccounted:
        lines += ["**Neither queued nor accounted for** (the merger cut these without "
                  "saying so):", ""]
        lines += [f"- {t}" for t in unaccounted]
        lines.append("")
    if declined or silent_splits:
        lines += ["A draw proposed splitting a term in two and the merger kept one — "
                  "granularity is the owner's to review:", ""]
        lines += [f"- **{d.get('proposed')}** kept as *{d.get('kept')}* — "
                  f"{d.get('why') or '(no reason given)'}" for d in declined]
        lines += [f"- **{d['proposed']}** flattened to *{d['kept'] or 'nothing'}*, "
                  "without the merger saying so" for d in silent_splits]
        lines.append("")
    return "\n".join(lines)


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
    history = attempt_history(st, term)
    # A mechanical failure is cheap to re-draft, so it short-circuits the round
    # — but the same mechanical objection twice running means the proposer
    # cannot see something, and that is a judgement, not a retry. The second
    # one promotes the round: the checks run and the chair, seeing what has
    # already been tried, owns the loop.
    promoted = bool(
        verdicts["rules"]["verdict"] != "ok" and history
        and history[-1].get("failed") == ["rules"]
        and ((history[-1].get("verdicts") or {}).get("rules") or {}).get("objections")
        == verdicts["rules"]["objections"])
    if verdicts["rules"]["verdict"] != "ok" and not promoted:
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
    if "rules" in bad and not promoted:   # mechanical: no chair can overrule it
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
                  + render_trajectory(history)
                  + (("THIS ATTEMPT REPEATS A MECHANICAL FAILURE the proposer could not "
                      "clear on its own; say what to do differently, or escalate.\n\n")
                     if promoted else "")
                  + f"REVIEWER VERDICTS:\n{render_verdicts(verdicts)}")
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
        prop, reviewed = chair_amendment(prop, chair)
        for t in (chair.get("revision_triggers") or []):
            with open(os.path.join(st.out, "revision-backlog.md"), "a") as f:
                f.write(f"- **{term}** — {str(t)[:400]}\n")
        return {"decision": "accept", "failed": bad, "proposal": prop,
                "verdicts": verdicts, "chair": chair,
                **({"reviewed_payload": reviewed} if reviewed else {})}
    if chair["decision"] == "escalate":
        return {"decision": "escalate", "failed": bad, "proposal": prop,
                "verdicts": verdicts, "chair": chair}
    return {"decision": "retry", "failed": bad, "proposal": prop,
            "verdicts": verdicts, "chair": chair}


def phase_foundation(st: Study, lane: str):
    budget = st.cfg.get("retry_budget", 3)
    # `--until N` bounds one invocation to N terms: a bench that wants five
    # terms of evidence should not have to run a whole lane, and hand-editing
    # the queue to get there loses the run's own account of what it did.
    until = st.cfg.get("until")
    started = len(st.state.get("outcomes", {}))
    qkey = "queue_lane1" if lane == "lane1" else "queue_lane2"
    queue = st.state.get(qkey, [])
    resolutions = st.state.get("resolutions", {})
    while queue:
        done = st.state.get("outcomes", {})
        if until is not None and len(done) - started >= until:
            save(st.state_p, st.state)
            print(f"\nSTOP — {len(done) - started} term(s) settled this run, as asked "
                  f"(--until {until}); {len(queue)} still queued. Run again to continue.")
            sys.exit(0)
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
        attempt, spent, faults, adjudicated = 0, 0, 0, False
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
            detail = (("CHAIR: " + ch.get("feedback", "")) if ch
                      else json.dumps({k: r["verdicts"][k] for k in r["failed"]}, indent=1))
            feedback = rejected_draft(st, r) + detail
            if r["decision"] == "escalate":
                # Some escalations are not the owner's to make: test the
                # options first, once per term, and continue if one stands.
                if not adjudicated:
                    adjudicated = True
                    settled = adjudicate(st, term, r)
                    if settled:
                        feedback = "DECISION (binding):\n" + settled
                        spent = 0
                        continue
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


def attempt_history(st: Study, term: str, keep: int = 5) -> list:
    """What has already been tried on this term, from the decision log."""
    p = os.path.join(st.out, "log", "decisions.jsonl")
    if not os.path.exists(p):
        return []
    out = []
    for line in open(p):
        if not line.strip():
            continue
        d = json.loads(line)
        if d.get("term") == term:
            out.append(d)
    return out[-keep:]


def one_line(o, width: int = 160) -> str:
    """An objection as one line: what it says, not how it is wrapped."""
    if isinstance(o, dict):
        text = o.get("defect") or o.get("failing_case") or o.get("why") or json.dumps(o)
        if o.get("failing_case") and o.get("defect"):
            text += f" — failing case: {o['failing_case']}"
        if o.get("severity"):
            text += f" [{o['severity']}]"
    else:
        text = str(o)
    text = " ".join(str(text).split())
    return text if len(text) <= width else text[:width - 1] + "…"


def render_trajectory(history: list) -> str:
    """The term's earlier attempts, so a chair can see a loop rather than
    judging each attempt as if it were the first."""
    if not history:
        return ""
    lines = ["THIS TERM'S EARLIER ATTEMPTS:"]
    for d in history:
        failed = ",".join(d.get("failed") or []) or "nothing"
        lines.append(f"- attempt {d.get('attempt')}: {d.get('decision')} "
                     f"(failed: {failed})")
        for role in (d.get("failed") or []):
            v = (d.get("verdicts") or {}).get(role) or {}
            samples = [v] + [x for k, x in v.items()
                             if k.startswith("sample") and isinstance(x, dict)]
            for sample in samples[:1]:
                for o in (sample.get("objections") or [])[:2]:
                    lines.append(f"    ({role}) {one_line(o, 120)}")
        ch = d.get("chair") or {}
        if ch.get("feedback"):
            lines.append(f"    you told the proposer: {one_line(ch['feedback'], 200)}")
    return "\n".join(lines) + "\n\n"


def render_verdicts(verdicts: dict, limit: int = 20000) -> str:
    """The reviewers' verdicts as the chair needs them: every objection kept,
    identical objections across blind samples merged and marked as recurring,
    and the JSON scaffolding that was most of the bulk removed.

    The old rendering was a JSON dump cut at a fixed length, so a chair could
    decide having never seen an objection, with nothing saying so. Anything
    dropped here is counted and announced."""
    lines, dropped = [], 0
    for name, v in verdicts.items():
        if not isinstance(v, dict):
            continue
        samples = {k: x for k, x in v.items()
                   if k.startswith("sample") and isinstance(x, dict)}
        lines.append(f"{name}: {v.get('verdict', '?')}"
                     + (f" ({len(samples)} blind samples)" if samples else ""))
        if samples:
            seen = {}
            for label, sample in samples.items():
                for o in (sample.get("objections") or []):
                    seen.setdefault(one_line(o, 400), []).append(label)
            if len(samples) > 1:
                lines.append("  (independent draws: they rarely word the same "
                             "objection alike, so judge recurrence by substance — "
                             "a label marks only where this exact text appeared)")
            for text, labels in seen.items():
                mark = ("[all samples]" if len(labels) == len(samples)
                        else f"[{', '.join(sorted(labels))}]")
                lines.append(f"  {mark} {text}")
            continue
        for o in (v.get("objections") or []):
            lines.append(f"  - {one_line(o, 400)}")
        if v.get("recommendation"):
            lines.append(f"  recommendation: {v['recommendation']}")
        if v.get("evidence"):
            lines.append(f"  evidence: {one_line(v['evidence'], 400)}")
        for r in (v.get("restatements") or []):
            if r.get("restatement"):
                lines.append(f"  - read as: {one_line(r['restatement'], 300)}")
            for a in (r.get("ambiguous") or []):
                lines.append(f"      ambiguous: {one_line(a, 300)}")
    out = "\n".join(lines)
    if len(out) > limit:
        kept = []
        for line in lines:
            if len("\n".join(kept + [line])) > limit:
                dropped += 1
                continue
            kept.append(line)
        out = "\n".join(kept) + (
            f"\n[{dropped} further objection line(s) omitted for length — "
            "ask for a revision rather than deciding without them]")
    return out


def chair_amendment(prop: dict, chair: dict):
    """Fold the chair's amendment into the entry, keeping what was reviewed.

    A chair may amend the entry it accepts, and the amended text is what enters
    the foundation. But the reviewers judged the draft as proposed: overwriting
    it left the record unable to say afterwards what the readers actually read,
    which is exactly what a later study of the checks needs. Both are kept —
    the approved entry as the proposal, the reviewed draft beside it."""
    amended = chair.get("payload")
    if not amended or amended == prop.get("payload"):
        return prop, None
    return dict(prop, payload=amended), prop.get("payload")


def rejected_draft(st: Study, r: dict) -> str:
    """The draft a retry is about, quoted back to its author.

    A proposer is drawn fresh for every attempt and never sees what it wrote
    last time. Objections that describe a draft — "Statement exceeds three
    sentences" — are unactionable without it: the next draft is written from
    scratch and can fail the same way forever. Revision and reorder moves carry
    the whole foundation as their payload, which is already in the prompt, so
    only entry moves are quoted."""
    prop = r.get("proposal") or {}
    payload = prop.get("payload")
    if not payload or not isinstance(payload, str):
        return ""
    if prop.get("move") == "entry":
        return f"YOUR PREVIOUS PROPOSAL, WHICH WAS REJECTED:\n{payload}\n\n"
    if prop.get("move") not in ("revision", "reorder"):
        return ""
    fnd_p = os.path.join(st.out, "foundation.md")
    current = open(fnd_p).read() if os.path.exists(fnd_p) else ""
    if prop["move"] == "reorder":
        before = re.findall(r"^### (.+)$", current, re.M)
        after = re.findall(r"^### (.+)$", payload, re.M)
        moves = [f"{t}: position {before.index(t) + 1} -> {after.index(t) + 1}"
                 for t in after if t in before and before.index(t) != after.index(t)]
        return ("YOUR PREVIOUS REORDER, WHICH WAS REJECTED:\n"
                + ("\n".join(moves) or "(no entry changed position)") + "\n\n")
    diff = list(difflib.unified_diff(current.splitlines(), payload.splitlines(),
                                     "foundation as it stands", "your revision",
                                     lineterm="", n=1))
    if len(diff) > 200:
        return ("YOUR PREVIOUS REVISION WAS REJECTED, and it is too large to quote "
                f"back ({len(diff)} changed lines). Rule 5 makes every entry after a "
                "revised one a re-checking obligation, so a revision this wide is "
                "hard to review and hard to trust: propose a smaller one.\n\n")
    return ("YOUR PREVIOUS REVISION, WHICH WAS REJECTED (as a diff against the "
            "foundation you were given):\n" + "\n".join(diff) + "\n\n")


def adjudicate(st: Study, term: str, r: dict):
    """Test a chair's escalation before handing it to the owner.

    The chair escalates when a choice looks like the owner's. Some of those
    choices are not choices at all: all but one option is refuted by the
    document itself, and the run can settle it with reasons. This stage lists
    the options, tries to refute each one independently, and:

      - one survivor, the rest refuted  -> adjudicated; the run continues
      - several survive (or none)       -> the owner's call, unless keep_going

    keep_going ('best' or 'random') is for unattended benchmarks: it picks
    anyway and marks the study as carrying a choice its owner never made.
    Returns a resolution string to re-queue the term with, or None to escalate.
    """
    chair = r.get("chair") or {}
    if not (chair.get("choice") or "").strip():
        return None
    keep_going = st.cfg.get("keep_going")
    opts = (st.call("options", st.role("options"),
                    f"ESCALATION:\n{chair['choice']}") or {}).get("options") or []
    opts = [o for o in opts if isinstance(o, str) and o.strip()]
    if len(opts) < 2:
        return None

    rb = open(os.path.join(st.sandbox, "rulebook.md")).read()
    doc = open(os.path.join(st.sandbox, "document.md")).read()
    fnd_p = os.path.join(st.out, "foundation.md")
    fnd = open(fnd_p).read() if os.path.exists(fnd_p) else "(empty)"
    fnd = view_foundation(fnd, st.cfg.get("foundation_view"), term, st)
    shared = (f"DOCUMENT UNDER STUDY:\n{doc}\n\nRULEBOOK:\n{rb}\n\n"
              f"FOUNDATION:\n{fnd}\n\nCANDIDATE: {term}\n"
              f"PROPOSED ENTRY:\n{(r.get('proposal') or {}).get('payload', '')}\n\n")
    with ThreadPoolExecutor(len(opts)) as ex:
        verdicts = list(ex.map(
            lambda i: st.call("adjudicator", st.role("adjudicator"),
                              f"{shared}OPTION UNDER TEST:\n{opts[i]}", draw=i),
            range(len(opts))))
    survived = [i for i, v in enumerate(verdicts)
                if (v or {}).get("verdict") == "survives"]
    tested = "\n".join(f"- {o} => {(v or {}).get('verdict', '?')}"
                       f"{': ' + v['failing_case'] if (v or {}).get('failing_case') else ''}"
                       for o, v in zip(opts, verdicts))

    if len(survived) == 1:
        pick, mode, why = survived[0], "adjudicated", "every rival option is refuted"
    elif not keep_going:
        return None
    else:
        pool = survived or list(range(len(opts)))
        if keep_going == "random":
            # arbitrary, but a function of the term and its options, so a
            # replayed run makes the same arbitrary choice
            seed = hashlib.sha256((term + "".join(opts)).encode()).hexdigest()
            pick = pool[int(seed, 16) % len(pool)]
            why = "picked arbitrarily among the readings that survived refutation"
        else:
            a = st.call("arbiter", st.role("arbiter"),
                        f"{shared}OPTIONS AND WHAT THE ADJUDICATORS FOUND:\n{tested}\n\n"
                        f"Choose among indices {pool}.") or {}
            pick = a.get("pick") if a.get("pick") in pool else pool[0]
            why = (a.get("why") or "")[:300]
        mode = "machine-selected"

    st.state.setdefault("machine_choices", []).append(
        {"term": term, "mode": mode, "chosen": opts[pick], "why": why,
         "options": opts, "verdicts": verdicts})
    save(st.state_p, st.state)
    with open(os.path.join(st.out, "adjudications.md"), "a") as f:
        f.write(f"## {term} — {mode}\n\nChosen: {opts[pick]}\n\nWhy: {why}\n\n"
                f"Options tested:\n{tested}\n\n")
    if mode == "adjudicated":
        return (f"ADJUDICATED (the run settled this; every rival reading is refuted by "
                f"the document): {opts[pick]}\n\nOptions tested:\n{tested}")
    return (f"MACHINE-SELECTED WITHOUT OWNER APPROVAL (the run was told to keep going): "
            f"{opts[pick]}\nWhy: {why}\n\nOptions tested:\n{tested}\n\n"
            f"Because no owner chose this, the entry must carry an Open clause saying "
            f"that this reading was selected by the run and awaits the owner's "
            f"confirmation." + DECISION_BINDS_THE_READING)


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
        detail = phase_extract(st)
        st.milestone_gate("extraction", detail)
    elif phase == "foundation-lane1":
        st.milestone_gate("extraction")
        phase_foundation(st, "lane1")
        st.milestone_gate("foundation-lane1")
    elif phase == "foundation-lane2":
        # Re-check the gate behind us, as lane 1 does for extraction: a gate
        # that only stops the run that reached it is no gate at all, since the
        # next invocation would carry straight on into unapproved work.
        st.milestone_gate("foundation-lane1")
        phase_foundation(st, "lane2")
        st.milestone_gate("foundation-lane2")
    elif phase == "report":
        print("report phase: built in build-phase 4")
