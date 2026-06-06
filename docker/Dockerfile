# GPU-enabled image that bundles Claude Code + OpenAI Codex CLIs,
# a FastAPI HTTP control plane, Ollama (local models) and supervisord.
#
# Base provides CUDA runtime so local GPU models (Ollama / vLLM) work,
# while the cloud agents (Claude Code / Codex) only need the network.
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    NODE_MAJOR=22 \
    LANG=C.UTF-8 \
    # Credentials live under these dirs; we mount them as volumes so a
    # one-time interactive OAuth login survives container restarts.
    CLAUDE_CONFIG_DIR=/data/claude \
    CODEX_HOME=/data/codex \
    OLLAMA_MODELS=/data/ollama \
    PYTHONUNBUFFERED=1

# --- System deps -----------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl git gnupg ripgrep tini python3 python3-pip python3-venv \
        sudo procps less openssh-client \
    && rm -rf /var/lib/apt/lists/*

# --- Node.js (for Claude Code + Codex) -------------------------------------
RUN mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
        | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_${NODE_MAJOR}.x nodistro main" \
        > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# --- Agent CLIs ------------------------------------------------------------
# Claude Code (Anthropic) + Codex (OpenAI), both as headless-capable CLIs.
RUN npm install -g @anthropic-ai/claude-code @openai/codex \
    && npm cache clean --force

# --- Ollama (local GPU models) ---------------------------------------------
RUN curl -fsSL https://ollama.com/install.sh | sh

# --- Supervisor + API deps -------------------------------------------------
COPY api/requirements.txt /opt/api/requirements.txt
RUN pip3 install --no-cache-dir supervisor -r /opt/api/requirements.txt

# --- App -------------------------------------------------------------------
COPY api/ /opt/api/
COPY docker/supervisord.conf /etc/supervisor/supervisord.conf
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY scripts/login.sh /usr/local/bin/agent-login
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/agent-login

# Workspace the agents operate in (repos are checked out / mounted here).
RUN mkdir -p /data/claude /data/codex /data/ollama /workspace

WORKDIR /workspace
EXPOSE 8080 11434

# tini reaps zombies from the agent subprocesses spawned by the API.
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint.sh"]
CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
