"""Command construction + auth detection for the two agents.

Each agent is driven in its non-interactive ("headless") mode so the API can
spawn it as a subprocess, capture stdout/stderr and return the result.
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field


CLAUDE_CONFIG_DIR = os.environ.get("CLAUDE_CONFIG_DIR", "/data/claude")
CODEX_HOME = os.environ.get("CODEX_HOME", "/data/codex")


@dataclass
class AgentSpec:
    name: str
    binary: str
    # Default model; None lets the CLI pick its account default.
    default_model: str | None = None
    env: dict[str, str] = field(default_factory=dict)


AGENTS: dict[str, AgentSpec] = {
    "claude": AgentSpec(name="claude", binary="claude"),
    "codex": AgentSpec(name="codex", binary="codex"),
}


def is_logged_in(agent: str) -> bool:
    """Best-effort check that a subscription/OAuth session exists."""
    if agent == "claude":
        if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
            return True
        return os.path.isfile(os.path.join(CLAUDE_CONFIG_DIR, ".credentials.json"))
    if agent == "codex":
        return os.path.isfile(os.path.join(CODEX_HOME, "auth.json"))
    return False


def binary_available(agent: str) -> bool:
    spec = AGENTS.get(agent)
    return bool(spec and shutil.which(spec.binary))


def build_command(
    agent: str,
    prompt: str,
    *,
    model: str | None = None,
    full_auto: bool = True,
) -> list[str]:
    """Return argv for a single headless run of `agent` on `prompt`.

    `full_auto` lets the agent edit files / run commands without prompting,
    which is required for unattended API-driven execution. The container is
    the isolation boundary, so we intentionally bypass the per-action prompts.
    """
    if agent not in AGENTS:
        raise ValueError(f"unknown agent: {agent}")
    spec = AGENTS[agent]
    chosen_model = model or spec.default_model

    if agent == "claude":
        # `-p` = print mode (non-interactive); JSON gives us a parseable result.
        cmd = [spec.binary, "-p", prompt, "--output-format", "json"]
        if chosen_model:
            cmd += ["--model", chosen_model]
        if full_auto:
            cmd += ["--dangerously-skip-permissions"]
        return cmd

    if agent == "codex":
        # `exec` = non-interactive run. Skip the git check so it works on any dir.
        cmd = [spec.binary, "exec", "--skip-git-repo-check"]
        if chosen_model:
            cmd += ["-m", chosen_model]
        if full_auto:
            # Run + edit without approval prompts (container is the sandbox).
            cmd += ["--dangerously-bypass-approvals-and-sandbox"]
        cmd += [prompt]
        return cmd

    raise ValueError(f"unhandled agent: {agent}")  # pragma: no cover


def build_env(agent: str) -> dict[str, str]:
    """Environment for the subprocess (inherits parent + agent-specific dirs)."""
    env = dict(os.environ)
    if agent == "claude":
        env["CLAUDE_CONFIG_DIR"] = CLAUDE_CONFIG_DIR
    elif agent == "codex":
        env["CODEX_HOME"] = CODEX_HOME
    return env
