"""
jobs.py — MyShell Background Job Registry
==========================================

Maintains a process table of active background jobs so the shell can:
  - Display them with the `jobs` builtin
  - Signal them with the `kill` builtin
  - Reap them asynchronously without blocking the REPL

OS Concepts Demonstrated:
    - Process table management (the kernel keeps one too — this mirrors it)
    - Non-blocking child process reaping via WNOHANG
    - Job control concepts (foreground / background process groups)
"""

import os

# ── Job Registry ─────────────────────────────────────────────────────
# Maps pid (int) → { jid, pid, cmd, status }
_jobs: dict = {}
_next_jid: int = 1


def register(pid: int, cmd_tokens: list) -> int:
    """
    Register a newly spawned background process in the job table.

    Args:
        pid (int): The child process ID returned by os.fork().
        cmd_tokens (list[str]): The command tokens (used for display).

    Returns:
        int: The job ID assigned (1-based, like bash's [1], [2], ...).
    """
    global _next_jid
    jid = _next_jid
    _next_jid += 1
    _jobs[pid] = {
        "jid":    jid,
        "pid":    pid,
        "cmd":    " ".join(cmd_tokens),
        "status": "Running",
    }
    return jid


def remove(pid: int) -> dict | None:
    """Remove a job from the registry. Returns the job info or None."""
    return _jobs.pop(pid, None)


def list_jobs() -> list:
    """Return all active background jobs as a list of dicts, sorted by jid."""
    return sorted(_jobs.values(), key=lambda j: j["jid"])


def reap() -> list:
    """
    Non-blocking reap of all terminated background processes.

    Uses os.waitpid(-1, os.WNOHANG):
        -1        → wait for ANY child process
        WNOHANG   → return immediately if no child has exited (non-blocking)

    This prevents zombie accumulation without ever blocking the REPL.

    Returns:
        list[tuple]: (pid, job_info) for each reaped job.
    """
    reaped = []
    while True:
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)
            if pid <= 0:
                break  # No more children have exited
            job = remove(pid)
            if job:
                reaped.append((pid, job, status))
        except (ChildProcessError, OSError):
            break  # No children at all
    return reaped


def count() -> int:
    """Return the number of currently tracked background jobs."""
    return len(_jobs)
