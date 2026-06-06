"""HTTP control plane for running Claude Code / Codex on the GPU server.

Submit a prompt -> a headless agent subprocess runs in a workspace -> poll the
job for status and output. Long-running agents are tracked as async jobs so the
REST call returns immediately.

Auth model:
  * The *agents* authenticate via their own subscription/OAuth session
    (persisted under /data). See `agent-login`.
  * The *API itself* is protected by a static bearer token (API_AUTH_TOKEN);
    because a job can run arbitrary code, never expose it unauthenticated.
"""
from __future__ import annotations

import asyncio
import os
import secrets
import time
import uuid
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

import runners

API_AUTH_TOKEN = os.environ.get("API_AUTH_TOKEN", "")
WORKSPACE_ROOT = os.environ.get("WORKSPACE_ROOT", "/workspace")
MAX_OUTPUT_BYTES = int(os.environ.get("MAX_OUTPUT_BYTES", str(2_000_000)))
JOB_TIMEOUT_SECONDS = int(os.environ.get("JOB_TIMEOUT_SECONDS", "1800"))

app = FastAPI(title="team-ai agent control plane", version="1.0.0")
_bearer = HTTPBearer(auto_error=False)


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
def require_token(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> None:
    if not API_AUTH_TOKEN:
        # No token configured -> refuse rather than run wide open.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API_AUTH_TOKEN not configured on the server",
        )
    if creds is None or not secrets.compare_digest(creds.credentials, API_AUTH_TOKEN):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
class JobRequest(BaseModel):
    agent: Literal["claude", "codex"]
    prompt: str = Field(min_length=1)
    # Sub-directory under WORKSPACE_ROOT the agent runs in (created if absent).
    workspace: str | None = None
    model: str | None = None
    full_auto: bool = True


class JobInfo(BaseModel):
    id: str
    agent: str
    state: Literal["running", "succeeded", "failed", "timeout", "cancelled"]
    created_at: float
    finished_at: float | None = None
    exit_code: int | None = None
    workspace: str


class JobResult(JobInfo):
    stdout: str = ""
    stderr: str = ""


# --------------------------------------------------------------------------- #
# Job registry
# --------------------------------------------------------------------------- #
class Job:
    def __init__(self, agent: str, workspace: str):
        self.id = uuid.uuid4().hex
        self.agent = agent
        self.workspace = workspace
        self.state: str = "running"
        self.created_at = time.time()
        self.finished_at: float | None = None
        self.exit_code: int | None = None
        self.stdout = ""
        self.stderr = ""
        self.proc: asyncio.subprocess.Process | None = None

    def info(self) -> JobInfo:
        return JobInfo(
            id=self.id, agent=self.agent, state=self.state,
            created_at=self.created_at, finished_at=self.finished_at,
            exit_code=self.exit_code, workspace=self.workspace,
        )

    def result(self) -> JobResult:
        return JobResult(**self.info().model_dump(), stdout=self.stdout, stderr=self.stderr)


JOBS: dict[str, Job] = {}


def _safe_workspace(sub: str | None) -> str:
    """Resolve a workspace sub-path, refusing to escape WORKSPACE_ROOT."""
    root = os.path.realpath(WORKSPACE_ROOT)
    target = os.path.realpath(os.path.join(root, sub or "."))
    if target != root and not target.startswith(root + os.sep):
        raise HTTPException(status_code=400, detail="workspace escapes WORKSPACE_ROOT")
    os.makedirs(target, exist_ok=True)
    return target


async def _run_job(job: Job, cmd: list[str], env: dict[str, str]) -> None:
    try:
        job.proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=job.workspace, env=env,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            out, err = await asyncio.wait_for(
                job.proc.communicate(), timeout=JOB_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            job.proc.kill()
            await job.proc.wait()
            job.state = "timeout"
            job.finished_at = time.time()
            return

        job.stdout = out.decode("utf-8", "replace")[:MAX_OUTPUT_BYTES]
        job.stderr = err.decode("utf-8", "replace")[:MAX_OUTPUT_BYTES]
        job.exit_code = job.proc.returncode
        if job.state == "cancelled":
            pass
        elif job.proc.returncode == 0:
            job.state = "succeeded"
        else:
            job.state = "failed"
    except Exception as exc:  # noqa: BLE001 - surface any spawn failure to caller
        job.state = "failed"
        job.stderr = f"{job.stderr}\n[control-plane] {exc}".strip()
    finally:
        if job.finished_at is None:
            job.finished_at = time.time()


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/v1/agents", dependencies=[Depends(require_token)])
async def list_agents() -> dict:
    return {
        "agents": [
            {
                "name": name,
                "installed": runners.binary_available(name),
                "logged_in": runners.is_logged_in(name),
            }
            for name in runners.AGENTS
        ]
    }


@app.post("/v1/jobs", dependencies=[Depends(require_token)], response_model=JobInfo)
async def create_job(req: JobRequest) -> JobInfo:
    if not runners.binary_available(req.agent):
        raise HTTPException(status_code=400, detail=f"{req.agent} CLI not installed")
    if not runners.is_logged_in(req.agent):
        raise HTTPException(
            status_code=409,
            detail=f"{req.agent} not logged in; run `agent-login {req.agent}`",
        )

    workspace = _safe_workspace(req.workspace)
    cmd = runners.build_command(
        req.agent, req.prompt, model=req.model, full_auto=req.full_auto
    )
    env = runners.build_env(req.agent)

    job = Job(req.agent, workspace)
    JOBS[job.id] = job
    asyncio.create_task(_run_job(job, cmd, env))
    return job.info()


@app.get("/v1/jobs", dependencies=[Depends(require_token)])
async def list_jobs() -> dict:
    return {"jobs": [j.info().model_dump() for j in JOBS.values()]}


@app.get("/v1/jobs/{job_id}", dependencies=[Depends(require_token)], response_model=JobResult)
async def get_job(job_id: str) -> JobResult:
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job.result()


@app.delete("/v1/jobs/{job_id}", dependencies=[Depends(require_token)], response_model=JobInfo)
async def cancel_job(job_id: str) -> JobInfo:
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.state == "running" and job.proc and job.proc.returncode is None:
        job.state = "cancelled"
        job.proc.kill()
    return job.info()
