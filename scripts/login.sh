#!/usr/bin/env bash
# One-time interactive OAuth login for the subscription-based agents.
# Credentials are written into the mounted /data volume so they persist.
#
# Usage (from the host):
#   docker exec -it team-ai-agents agent-login claude
#   docker exec -it team-ai-agents agent-login codex
#   docker exec -it team-ai-agents agent-login status
set -euo pipefail

agent="${1:-status}"

claude_logged_in() {
    [ -f "${CLAUDE_CONFIG_DIR:-/data/claude}/.credentials.json" ] || [ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]
}
codex_logged_in() {
    [ -f "${CODEX_HOME:-/data/codex}/auth.json" ]
}

case "$agent" in
  claude)
    echo ">> Claude Code subscription login (Claude.ai Pro/Max account)."
    echo ">> A URL will be printed — open it in YOUR browser, approve, paste the code back."
    # setup-token performs the OAuth device flow and stores a long-lived token
    # under CLAUDE_CONFIG_DIR; works without a browser on the server itself.
    claude setup-token
    echo ">> Done. Credentials stored in ${CLAUDE_CONFIG_DIR}."
    ;;

  codex)
    echo ">> Codex subscription login (ChatGPT Plus/Pro account)."
    echo ">> Codex starts a local callback server on port 1455."
    echo ">> If you're on a remote server, first open an SSH tunnel from your laptop:"
    echo ">>     ssh -L 1455:localhost:1455 <user>@<gpu-server>"
    echo ">> then open the printed URL in your local browser."
    codex login
    echo ">> Done. Credentials stored in ${CODEX_HOME}."
    ;;

  status)
    if claude_logged_in; then echo "claude: LOGGED IN"; else echo "claude: NOT logged in"; fi
    if codex_logged_in;  then echo "codex:  LOGGED IN"; else echo "codex:  NOT logged in"; fi
    ;;

  *)
    echo "unknown agent '$agent' (expected: claude | codex | status)" >&2
    exit 2
    ;;
esac
