"""
pipes.py — MyShell Pipeline Executor
======================================

Handles command chaining using Unix pipes. When the user types:
    ls -l | grep ".py" | wc -l

This module creates pipes between each pair of consecutive commands,
forks a child for each command, and routes file descriptors so that
each command's stdout feeds into the next command's stdin.

Pipe Mechanics (OS Concept: Inter-Process Communication):
    os.pipe() creates a unidirectional data channel:
        read_fd, write_fd = os.pipe()

    Data written to write_fd can be read from read_fd.

    os.dup2(old_fd, new_fd) duplicates a file descriptor:
        os.dup2(write_fd, 1)  → stdout now goes into the pipe
        os.dup2(read_fd, 0)   → stdin now reads from the pipe

File Descriptor Diagram for `cmd_A | cmd_B`:
    ┌──────────┐    write_fd ──────── read_fd    ┌──────────┐
    │  cmd_A   │ ──→  PIPE (kernel buffer)  ──→  │  cmd_B   │
    │ stdout→1 │    (os.pipe creates this)       │ stdin←0  │
    └──────────┘                                  └──────────┘

CRITICAL: The parent MUST close both ends of every pipe after forking.
If the parent keeps write_fd open, cmd_B will never see EOF on its
stdin and will hang forever waiting for more input.

OS Concepts Demonstrated:
    - Inter-process communication (IPC) via pipes
    - File descriptor manipulation via dup2()
    - Multiple process coordination
"""

import os
import sys
import shutil
from redirects import parse_redirections, apply_redirections
from colors import yellow

# SEC-08: Maximum number of commands allowed in a single pipeline.
# Prevents fork-bomb style DoS via `yes | yes | yes | ... (1000 times)`.
MAX_PIPELINE_DEPTH = 32

# SEC-10: Set MYSHELL_DEBUG=1 to see full error details from child processes.
DEBUG = os.environ.get("MYSHELL_DEBUG", "0") == "1"


def execute_pipeline(commands, background=False):
    """
    Execute a pipeline of commands connected by pipes.

    Supports N-stage pipelines: cmd1 | cmd2 | cmd3 | ... | cmdN

    Args:
        commands (list[list[str]]): List of tokenized commands.
            Example: [['ls', '-l'], ['grep', '.py'], ['wc', '-l']]

    OS Flow for 3-command pipeline (cmd1 | cmd2 | cmd3):

        cmd1 ──[pipe1]──→ cmd2 ──[pipe2]──→ cmd3
         │                  │                  │
         stdout → pipe1    stdin ← pipe1      stdin ← pipe2
                           stdout → pipe2      stdout → terminal
    """
    if len(commands) < 2:
        # Should not happen (parser ensures at least 2 commands for a pipe)
        print("myshell: pipe error: need at least two commands")
        return

    # SEC-08: Enforce pipeline depth limit to prevent fork-bomb DoS.
    if len(commands) > MAX_PIPELINE_DEPTH:
        print(f"myshell: pipe error: pipeline too long (max {MAX_PIPELINE_DEPTH} commands)")
        return

    # ── Create all pipes ───────────────────────────────────────────────
    # For N commands, we need N-1 pipes.
    # Each pipe is a (read_fd, write_fd) tuple.
    num_pipes = len(commands) - 1
    pipe_fds = []
    for _ in range(num_pipes):
        # SEC-02: Use O_CLOEXEC so these fds are automatically closed
        # across exec() — prevents fd leakage into child programs.
        # os.pipe2 is Linux-specific; fall back to os.pipe on other systems.
        try:
            read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
        except AttributeError:
            read_fd, write_fd = os.pipe()  # macOS / non-Linux fallback
        pipe_fds.append((read_fd, write_fd))

    # ── Fork children for each command ─────────────────────────────────
    child_pids = []

    for i, cmd in enumerate(commands):
        pid = os.fork()

        if pid == 0:
            # ── CHILD PROCESS ──────────────────────────────────────────
            # Parse any command-specific I/O redirections (e.g. `cat < file` or `grep > out`)
            clean_cmd, redirs, err = parse_redirections(cmd)
            if err:
                print(f"myshell: {err}", file=sys.stderr)
                sys.exit(2)

            if not clean_cmd:
                sys.exit(0)

            # Set up this child's stdin/stdout based on its position
            # in the pipeline.

            # If NOT the first command → read from previous pipe
            if i > 0:
                # Redirect stdin to read from the previous pipe
                os.dup2(pipe_fds[i - 1][0], sys.stdin.fileno())

            # If NOT the last command → write to next pipe
            if i < num_pipes:
                # Redirect stdout to write into the current pipe
                os.dup2(pipe_fds[i][1], sys.stdout.fileno())

            # Close ALL pipe fds in this child
            # (the child only needs the dup2'd copies, not the originals)
            # SEC-05: Wrap each close in try/except — if dup2() already
            # closed a fd whose number matched stdin/stdout, a bare
            # os.close() would raise OSError: Bad file descriptor.
            for read_fd, write_fd in pipe_fds:
                try:
                    os.close(read_fd)
                except OSError:
                    pass
                try:
                    os.close(write_fd)
                except OSError:
                    pass

            # Apply any explicit file redirections for this command
            apply_redirections(redirs)

            # SEC-01: Resolve binary to absolute path via shutil.which()
            # before exec, preventing PATH injection attacks.
            resolved = shutil.which(clean_cmd[0])
            if resolved is None:
                print(f"myshell: command not found: {clean_cmd[0]}", file=sys.stderr)
                sys.exit(127)
            try:
                # os.execv uses the exact resolved path — no PATH lookup.
                os.execv(resolved, clean_cmd)
            except PermissionError:
                print(f"myshell: permission denied: {clean_cmd[0]}", file=sys.stderr)
                sys.exit(126)
            except Exception as e:
                # SEC-10: Only expose internal details in debug mode.
                if DEBUG:
                    print(f"myshell: error executing {clean_cmd[0]}: {e}", file=sys.stderr)
                else:
                    print(f"myshell: error executing {clean_cmd[0]}", file=sys.stderr)
                sys.exit(1)

        elif pid > 0:
            # ── PARENT PROCESS ─────────────────────────────────────────
            child_pids.append(pid)

        else:
            # fork() failed — clean up before returning
            print("myshell: error: fork failed during pipeline setup")
            # Close all pipe file descriptors to prevent leaks
            for read_fd, write_fd in pipe_fds:
                try:
                    os.close(read_fd)
                    os.close(write_fd)
                except OSError:
                    pass
            # Wait for any children already forked to prevent orphans
            for orphan_pid in child_pids:
                try:
                    os.waitpid(orphan_pid, 0)
                except (ChildProcessError, OSError):
                    pass
            return

    # ── Parent: Close ALL pipe file descriptors ────────────────────────
    # CRITICAL: If the parent doesn't close the write-end of each pipe,
    # the reading child will never receive EOF and will hang forever.
    for read_fd, write_fd in pipe_fds:
        os.close(read_fd)
        os.close(write_fd)

    # ── Parent: Wait for ALL children to finish ────────────────────────
    pipeline_exit_code = 0
    if background:
        # Background pipeline: don't wait, print info and return
        print(yellow(f"[bg] started pipeline with {len(child_pids)} processes"))
        return 0
    else:
        for idx, pid in enumerate(child_pids):
            try:
                # SEC-07/11: Capture each child's exit status.
                _, status = os.waitpid(pid, 0)
                if os.WIFEXITED(status):
                    code = os.WEXITSTATUS(status)
                    if DEBUG and code != 0:
                        print(f"myshell: [debug] pipeline process {pid} exited with code {code}")
                    # By Unix convention, pipeline exit code is the exit code of the last process
                    if idx == len(child_pids) - 1:
                        pipeline_exit_code = code
                elif os.WIFSIGNALED(status):
                    if idx == len(child_pids) - 1:
                        pipeline_exit_code = 128 + os.WTERMSIG(status)
            except (ChildProcessError, OSError):
                # Child was already reaped (e.g., by SIGCHLD handler)
                pass
        return pipeline_exit_code
