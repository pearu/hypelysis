#!/usr/bin/env python3
"""Provider abstraction: prompt in, text out, no local-configuration bleed.

Two adapters:
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
import json
import os
import subprocess
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


def make(cfg: dict, sandbox: str) -> Provider:
    kind = cfg.get("provider", "claude-cli")
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
