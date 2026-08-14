"""Method materials shipped with the package: the rulebook, the role prompts,
and the default config. Installed as package data, so a study can be run from
any directory without a checkout of this repository."""
import json
import os

try:
    from importlib.resources import files as _files          # Python 3.9+

    def _text(*parts) -> str:
        return _files(__package__).joinpath("data", *parts).read_text(encoding="utf-8")
except ImportError:                                          # Python 3.8
    _DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

    def _text(*parts) -> str:
        with open(os.path.join(_DATA, *parts), encoding="utf-8") as f:
            return f.read()


def rulebook() -> str:
    return _text("rulebook.md")


def role(name: str) -> str:
    """The role prompt for a worker. ':rep' replications share the base
    role's prompt — a replication is the same instrument at another draw."""
    return _text("roles", f"{name.split(':')[0]}.md")


def default_config() -> dict:
    return json.loads(_text("config.json"))
