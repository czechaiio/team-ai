#!/usr/bin/env bash
# Container entrypoint: prepare runtime dirs, normalise env defaults, then
# hand off to supervisord (or whatever CMD was passed, e.g. `agent-login`).
set -euo pipefail

# Defaults so supervisord.conf's %(ENV_*)s interpolation never fails.
export ENABLE_OLLAMA="${ENABLE_OLLAMA:-true}"

mkdir -p /var/log/supervisor \
         "${CLAUDE_CONFIG_DIR:-/data/claude}" \
         "${CODEX_HOME:-/data/codex}" \
         "${OLLAMA_MODELS:-/data/ollama}" \
         /workspace

# Warn (don't fail) when no credentials are present yet — the operator is
# expected to run `agent-login` once to perform the OAuth flow.
if [ ! -f "${CLAUDE_CONFIG_DIR}/.credentials.json" ] && [ -z "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]; then
    echo "[entrypoint] Claude Code not logged in yet. Run: docker exec -it <ctr> agent-login claude" >&2
fi
if [ ! -f "${CODEX_HOME}/auth.json" ]; then
    echo "[entrypoint] Codex not logged in yet. Run: docker exec -it <ctr> agent-login codex" >&2
fi

exec "$@"
