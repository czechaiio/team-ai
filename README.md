# team-ai — GPU server agent control plane

Runs **Claude Code** (Anthropic) and **OpenAI Codex** CLIs inside a single
GPU-enabled Docker container, supervised by **supervisord**, and driven through
an **HTTP REST API**. Both agents use your **subscription / OAuth login**
(Claude.ai Pro/Max + ChatGPT Plus/Pro), and the container also runs **Ollama**
so local GPU models are available alongside the cloud agents.

```
            ┌────────────────────────── container ──────────────────────────┐
  HTTP  ──▶ │  FastAPI (:8080)  ──spawns──▶  claude -p … / codex exec …      │
            │        │                                                       │
            │   supervisord ──┬── api (uvicorn)                              │
            │                 └── ollama serve (:11434, GPU, local models)   │
            │                                                                │
            │   /data volume:  claude creds · codex creds · ollama models    │
            │   /workspace volume:  repos the agents operate on              │
            └────────────────────────────────────────────────────────────────┘
```

## Prerequisites (GPU host)

- Docker + Docker Compose
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
  (`nvidia-smi` works inside containers)
- A Claude.ai Pro/Max account and a ChatGPT Plus/Pro account

## Quick start

```bash
cp .env.example .env
# edit .env: set API_AUTH_TOKEN=$(openssl rand -hex 32)

docker compose build
docker compose up -d
```

### One-time login (subscription / OAuth)

Credentials are stored in the `agent-creds` volume and survive restarts.

```bash
# Claude Code: prints a URL, open it in your browser, paste the code back.
docker compose exec agents agent-login claude

# Codex: opens a local OAuth callback on port 1455.
# From your laptop first: ssh -L 1455:localhost:1455 <user>@<gpu-server>
docker compose exec -it agents agent-login codex

# check both
docker compose exec agents agent-login status
```

## Using the API

All `/v1/*` calls need `Authorization: Bearer $API_AUTH_TOKEN`.

```bash
TOKEN=...   # value of API_AUTH_TOKEN
BASE=http://<gpu-server>:8080

# health (no auth)
curl $BASE/health

# which agents are installed + logged in
curl -H "Authorization: Bearer $TOKEN" $BASE/v1/agents

# submit a job (returns immediately with a job id)
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"agent":"claude","prompt":"List the files and summarise the repo","workspace":"myrepo"}' \
  $BASE/v1/jobs

# poll for the result
curl -H "Authorization: Bearer $TOKEN" $BASE/v1/jobs/<job_id>

# run Codex instead
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"agent":"codex","prompt":"Fix the failing test in app/","workspace":"myrepo"}' \
  $BASE/v1/jobs
```

### Endpoints

| Method | Path             | Description                                  |
|--------|------------------|----------------------------------------------|
| GET    | `/health`        | Liveness (no auth)                           |
| GET    | `/v1/agents`     | Installed / logged-in status per agent       |
| POST   | `/v1/jobs`       | Start a headless run → `{id, state, …}`      |
| GET    | `/v1/jobs`       | List jobs                                    |
| GET    | `/v1/jobs/{id}`  | Job status + `stdout`/`stderr`               |
| DELETE | `/v1/jobs/{id}`  | Cancel a running job                         |

**Job request body**

```jsonc
{
  "agent": "claude" | "codex",  // required
  "prompt": "…",                 // required
  "workspace": "subdir",         // optional, under /workspace
  "model": "…",                  // optional, overrides account default
  "full_auto": true              // optional, run/edit without approval prompts
}
```

> Jobs run with approvals bypassed (`--dangerously-skip-permissions` /
> `--dangerously-bypass-approvals-and-sandbox`) because the **container is the
> isolation boundary**. Keep `API_AUTH_TOKEN` secret and don't expose port 8080
> publicly — a caller can run arbitrary code in the workspace.

## Local GPU models (Ollama)

Ollama runs in the same container and is reachable at `:11434`.

```bash
docker compose exec agents ollama pull llama3.1
curl http://<gpu-server>:11434/api/generate -d '{"model":"llama3.1","prompt":"hi"}'
```

Set `ENABLE_OLLAMA=false` in `.env` to disable it.

## Operations

```bash
docker compose logs -f agents                       # all logs
docker compose exec agents supervisorctl status     # process states
docker compose exec agents supervisorctl restart api
```

## Layout

```
docker/
  Dockerfile         CUDA base + Node (Claude Code/Codex) + Python + Ollama
  supervisord.conf   supervises: api, ollama
  entrypoint.sh      prepares dirs, warns if not logged in
api/
  server.py          FastAPI control plane + job registry
  runners.py         headless command construction + auth detection
  requirements.txt
scripts/
  login.sh           one-time OAuth login helper (`agent-login`)
docker-compose.yml   GPU reservation, volumes, ports
.env.example         configuration template
```
