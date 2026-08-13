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
"""
import json
import subprocess
import urllib.request


class Provider:
    def complete(self, system: str, user: str) -> str:
        raise NotImplementedError

    def spec(self) -> dict:
        raise NotImplementedError


class ClaudeCLI(Provider):
    def __init__(self, model: str, cwd: str, timeout: int = 600):
        self.model, self.cwd, self.timeout = model, cwd, timeout

    def argv(self, system: str) -> list:
        return ["claude", "-p",
                "--system-prompt", system,
                "--setting-sources", "",
                "--strict-mcp-config",
                "--model", self.model]

    def complete(self, system, user):
        r = subprocess.run(self.argv(system), input=user, text=True,
                           capture_output=True, cwd=self.cwd, timeout=self.timeout)
        if r.returncode != 0:
            raise RuntimeError(f"claude-cli failed ({r.returncode}): {r.stderr[:500]}")
        return r.stdout

    def spec(self):
        return {"provider": "claude-cli", "model": self.model,
                "argv": self.argv("<system>")}


class OpenAIHTTP(Provider):
    def __init__(self, base_url: str, model: str, api_key: str = "",
                 temperature: float = 1.0, timeout: int = 600):
        self.base_url = base_url.rstrip("/")
        self.model, self.api_key = model, api_key
        self.temperature, self.timeout = temperature, timeout

    def complete(self, system, user):
        body = json.dumps({"model": self.model, "temperature": self.temperature,
                           "messages": [{"role": "system", "content": system},
                                        {"role": "user", "content": user}]}).encode()
        req = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions", data=body,
            headers={"Content-Type": "application/json",
                     **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {})})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            out = json.load(resp)
        return out["choices"][0]["message"]["content"]

    def spec(self):
        return {"provider": "openai-http", "base_url": self.base_url,
                "model": self.model, "temperature": self.temperature}


def make(cfg: dict, sandbox: str) -> Provider:
    kind = cfg.get("provider", "claude-cli")
    if kind == "claude-cli":
        return ClaudeCLI(cfg["model"], cwd=sandbox, timeout=cfg.get("timeout", 600))
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
