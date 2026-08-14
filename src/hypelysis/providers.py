#!/usr/bin/env python3
"""Provider abstraction: prompt in, text out, no local-configuration bleed.

Adapters:
  replay        a fake worker that replays a recorded run — no network, no
                cost, no AI required, so the run path is testable in CI
  claude-cli    spawns `claude -p` with full isolation flags: the role prompt
                REPLACES the system prompt, no settings sources are loaded, no
                MCP configs, model pinned explicitly, cwd in the sandbox.
  openai-http   POST {base_url}/v1/chat/completions — the de-facto common
                interface, covering OpenAI-compatible local runtimes (ollama,
                llama.cpp server, vLLM) and hosted providers alike.

Every call is logged with the exact invocation, so a run records what produced
each text — which provider, which model, which flags.

Known residual leak of the claude-cli adapter, found by probe.py and not
removable by any flag combination as of CLI verification: the logged-in
account's email address and the current date reach every worker via a
CLI-injected context block. Harmless for neutral subjects; a declared bias
vector when the subject document is affiliated with the account's domain —
route such runs through openai-http, or declare the vector in the run record.
"""
import hashlib
import json
import os
import subprocess
import threading
import urllib.request


def flatten_user(user):
    """Workers may receive the user content as structured blocks
    [{"text": ..., "cache": bool}, ...]; adapters without block support
    join them into one string."""
    if isinstance(user, list):
        return "\n\n".join(b["text"] for b in user)
    return user


class Provider:
    def complete(self, system: str, user: str, resume: str = None):
        """Returns (text, meta) — meta holds cost/duration/token accounting.
        resume: provider session id to continue (claude-cli only)."""
        raise NotImplementedError

    def spec(self) -> dict:
        raise NotImplementedError


class ClaudeCLI(Provider):
    def __init__(self, model: str, cwd: str, timeout: int = 600, effort: str = None):
        self.model, self.cwd, self.timeout = model, cwd, timeout
        self.effort = effort

    def argv(self, system: str, resume: str = None) -> list:
        return ["claude", "-p",
                "--system-prompt", system,
                "--setting-sources", "",
                "--strict-mcp-config",
                "--output-format", "json",
                "--model", self.model] + (
                ["--effort", self.effort] if self.effort else []) + (
                ["--resume", resume] if resume else [])

    def complete(self, system, user, resume=None):
        r = subprocess.run(self.argv(system, resume), input=flatten_user(user),
                           text=True,
                           capture_output=True, cwd=self.cwd, timeout=self.timeout)
        if r.returncode != 0:
            raise RuntimeError(f"claude-cli failed ({r.returncode}): "
                               f"stderr={r.stderr[:300]!r} stdout={r.stdout[:300]!r}")
        d = json.loads(r.stdout)
        usage = d.get("usage", {})
        meta = {"session_id": d.get("session_id"),
                "cost_usd": d.get("total_cost_usd"),
                "duration_ms": d.get("duration_ms"),
                "duration_api_ms": d.get("duration_api_ms"),
                "ttft_ms": d.get("ttft_ms"),
                "ttft_stream_ms": d.get("ttft_stream_ms"),
                "time_to_request_ms": d.get("time_to_request_ms"),
                "num_turns": d.get("num_turns"),
                "input_tokens": usage.get("input_tokens"),
                "cache_read_tokens": usage.get("cache_read_input_tokens"),
                "cache_write_tokens": usage.get("cache_creation_input_tokens"),
                "output_tokens": usage.get("output_tokens")}
        return d.get("result", ""), meta

    def spec(self):
        return {"provider": "claude-cli", "model": self.model,
                "effort": self.effort, "argv": self.argv("<system>")}


class OpenAIHTTP(Provider):
    def __init__(self, base_url: str, model: str, api_key: str = "",
                 temperature: float = 1.0, timeout: int = 600):
        self.base_url = base_url.rstrip("/")
        self.model, self.api_key = model, api_key
        self.temperature, self.timeout = temperature, timeout

    def complete(self, system, user, resume=None):
        if resume:
            raise RuntimeError("openai-http adapter does not support session resume")
        body = json.dumps({"model": self.model, "temperature": self.temperature,
                           "messages": [{"role": "system", "content": system},
                                        {"role": "user",
                                         "content": flatten_user(user)}]}).encode()
        req = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions", data=body,
            headers={"Content-Type": "application/json",
                     **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {})})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            out = json.load(resp)
        usage = out.get("usage", {})
        meta = {"cost_usd": None,
                "input_tokens": usage.get("prompt_tokens"),
                "output_tokens": usage.get("completion_tokens")}
        return out["choices"][0]["message"]["content"], meta

    def spec(self):
        return {"provider": "openai-http", "base_url": self.base_url,
                "model": self.model, "temperature": self.temperature}


class AnthropicHTTP(Provider):
    """Direct Messages API: no CLI agent preamble (the ~21.6k-token tool
    scaffolding claude -p prepends), no account email/date injection (the
    documented residual leak of the claude-cli adapter), and explicit
    cache_control so a shared block is written once and read by every role
    that presents the same prefix."""

    API = "https://api.anthropic.com/v1/messages"

    def __init__(self, model: str, api_key: str = "", max_tokens: int = 8000,
                 temperature: float = 1.0, timeout: int = 600):
        self.model, self.max_tokens = model, max_tokens
        self.temperature, self.timeout = temperature, timeout
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    def complete(self, system, user, resume=None):
        if resume:
            raise RuntimeError("anthropic-http adapter does not support session resume")
        if not self.api_key:
            raise RuntimeError("no API key: set ANTHROPIC_API_KEY or config api_key")
        if isinstance(user, list):
            content = [dict({"type": "text", "text": b["text"]},
                            **({"cache_control": {"type": "ephemeral"}}
                               if b.get("cache") else {})) for b in user]
        else:
            content = [{"type": "text", "text": user}]
        body = json.dumps({
            "model": self.model, "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "system": [{"type": "text", "text": system,
                        "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": content}]}).encode()
        req = urllib.request.Request(
            self.API, data=body,
            headers={"Content-Type": "application/json",
                     "x-api-key": self.api_key,
                     "anthropic-version": "2023-06-01"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                out = json.load(resp)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"anthropic-http {e.code}: {e.read()[:300]!r}")
        usage = out.get("usage", {})
        meta = {"input_tokens": usage.get("input_tokens"),
                "cache_read_tokens": usage.get("cache_read_input_tokens"),
                "cache_write_tokens": usage.get("cache_creation_input_tokens"),
                "output_tokens": usage.get("output_tokens")}
        text = "".join(b.get("text", "") for b in out.get("content", [])
                       if b.get("type") == "text")
        return text, meta

    def spec(self):
        return {"provider": "anthropic-http", "model": self.model,
                "max_tokens": self.max_tokens, "temperature": self.temperature}


class Replay(Provider):
    """A fake worker that replays a finished run: no network, no cost, no AI
    needed — so the run path is testable where no provider is reachable.

    The fixture is a JSONL transcript in call order, one record per call:
    {"role": ..., "output": ..., "prompt_sha": ..., "meta": {...}}. Build one
    from any completed study with fixture_from_log().

    Replies are handed out per role in recorded order, not matched on prompt
    text: a run makes several identical calls on purpose (three extractors
    drawing independently), and matching on text alone could not tell those
    draws apart. Prompts are still verified — when a record carries a
    prompt_sha that does not match the prompt actually sent, the mismatch is
    recorded in `mismatches`, and refused outright under strict. Running out of
    recorded replies is an error, never a silent empty answer."""

    _state = {}
    _lock = threading.Lock()

    def __init__(self, fixture: str, role: str = None, strict: bool = False):
        self.fixture = os.path.abspath(fixture)
        self.role = (role or "").split(":")[0]
        self.strict = strict
        with Replay._lock:
            if self.fixture not in Replay._state:
                Replay._state[self.fixture] = self._load()

    def _load(self) -> dict:
        if not os.path.exists(self.fixture):
            raise RuntimeError(f"replay fixture not found: {self.fixture}")
        byrole, order = {}, []
        with open(self.fixture) as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                byrole.setdefault((r.get("role") or "").split(":")[0], []).append(r)
                order.append(r)
        return {"byrole": byrole, "used": {}, "mismatches": [], "calls": 0,
                "total": len(order)}

    @property
    def mismatches(self) -> list:
        return Replay._state[self.fixture]["mismatches"]

    @classmethod
    def reset(cls, fixture: str = None):
        """Forget how far a fixture has been consumed. Consumption state is
        shared across provider instances — a study builds a fresh one per
        call — so a second replay of the same fixture must reset first."""
        with cls._lock:
            if fixture is None:
                cls._state.clear()
            else:
                cls._state.pop(os.path.abspath(fixture), None)

    def complete(self, system, user, resume=None):
        st = Replay._state[self.fixture]
        with Replay._lock:
            queue = st["byrole"].get(self.role, [])
            i = st["used"].get(self.role, 0)
            if i >= len(queue):
                raise RuntimeError(
                    f"replay: the fixture holds {len(queue)} reply(ies) for role "
                    f"{self.role!r} and this is call {i + 1}; re-record the "
                    f"fixture from a run that goes this far ({self.fixture})")
            st["used"][self.role] = i + 1
            st["calls"] += 1
            rec = queue[i]
            want = rec.get("prompt_sha")
            got = prompt_sha(system, user)
            if want and want != got:
                st["mismatches"].append(
                    {"role": self.role, "call": i + 1, "recorded": want, "sent": got})
                if self.strict:
                    raise RuntimeError(
                        f"replay: prompt for {self.role!r} call {i + 1} differs from "
                        "the recorded one — the fixture is stale for these prompts")
        meta = dict(rec.get("meta") or {})
        meta.update({"cost_usd": 0.0, "replayed": True})
        return rec.get("output", ""), meta

    def spec(self):
        return {"provider": "replay", "model": "replay",
                "fixture": os.path.basename(self.fixture), "role": self.role}


def prompt_sha(system, user) -> str:
    """A stable digest of one exact prompt: what a replay fixture verifies
    against, without keeping the prompt itself."""
    return hashlib.sha256(("\x00".join([system or "", flatten_user(user) or ""]))
                          .encode("utf-8")).hexdigest()


def fixture_from_log(study: str, dest: str) -> int:
    """Turn a completed study's call log into a replay fixture; returns how
    many calls it holds. Cache hits carry no output and are skipped — replay
    reproduces the calls, and the study's own cache handles the rest."""
    src = os.path.join(study, "log", "rounds.jsonl")
    n = 0
    with open(src) as f, open(dest, "w") as out:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("output") is None:
                continue
            out.write(json.dumps({"role": r.get("role"),
                                  "prompt_sha": r.get("prompt_sha"),
                                  "output": r["output"],
                                  "meta": {k: v for k, v in (r.get("meta") or {}).items()
                                           if k in ("output_tokens", "input_tokens")}}) + "\n")
            n += 1
    return n


def make(cfg: dict, sandbox: str, role: str = None) -> Provider:
    kind = cfg.get("provider", "claude-cli")
    if kind == "replay":
        return Replay(cfg["fixture"], role=role, strict=cfg.get("strict", False))
    if kind == "claude-cli":
        return ClaudeCLI(cfg["model"], cwd=sandbox, timeout=cfg.get("timeout", 600),
                         effort=cfg.get("effort"))
    if kind == "anthropic-http":
        return AnthropicHTTP(cfg["model"], cfg.get("api_key", ""),
                             cfg.get("max_tokens", 8000),
                             cfg.get("temperature", 1.0), cfg.get("timeout", 600))
    if kind == "openai-http":
        return OpenAIHTTP(cfg["base_url"], cfg["model"], cfg.get("api_key", ""),
                          cfg.get("temperature", 1.0), cfg.get("timeout", 600))
    raise ValueError(f"unknown provider kind: {kind}")


def json_out(text: str) -> dict:
    """Extract the last JSON object from a worker's output; workers are told
    to output JSON only, but fences and prefaces happen."""
    depth, start, best = 0, None, None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                best = text[start:i + 1]
    if best is None:
        raise ValueError(f"no JSON object in worker output: {text[:200]!r}")
    return json.loads(best)
