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


def execute_pipeline(commands):
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

    # ── Create all pipes ───────────────────────────────────────────────
    # For N commands, we need N-1 pipes.
    # Each pipe is a (read_fd, write_fd) tuple.
    num_pipes = len(commands) - 1
    pipe_fds = []
    for _ in range(num_pipes):
        read_fd, write_fd = os.pipe()
        pipe_fds.append((read_fd, write_fd))

    # ── Fork children for each command ─────────────────────────────────
    child_pids = []

    for i, cmd in enumerate(commands):
        pid = os.fork()

        if pid == 0:
            # ── CHILD PROCESS ──────────────────────────────────────────
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
            for read_fd, write_fd in pipe_fds:
                os.close(read_fd)
                os.close(write_fd)

            # Replace this child with the target program
            try:
                os.execvp(cmd[0], cmd)
            except FileNotFoundError:
                print(f"myshell: command not found: {cmd[0]}", file=sys.stderr)
                sys.exit(127)
            except PermissionError:
                print(f"myshell: permission denied: {cmd[0]}", file=sys.stderr)
                sys.exit(126)
            except Exception as e:
                print(f"myshell: error executing {cmd[0]}: {e}", file=sys.stderr)
                sys.exit(1)

        elif pid > 0:
            # ── PARENT PROCESS ─────────────────────────────────────────
            child_pids.append(pid)

        else:
            # fork() failed
            print("myshell: error: fork failed during pipeline setup")
            return

    # ── Parent: Close ALL pipe file descriptors ────────────────────────
    # CRITICAL: If the parent doesn't close the write-end of each pipe,
    # the reading child will never receive EOF and will hang forever.
    for read_fd, write_fd in pipe_fds:
        os.close(read_fd)
        os.close(write_fd)

    # ── Parent: Wait for ALL children to finish ────────────────────────
    for pid in child_pids:
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            # Child was already reaped (e.g., by SIGCHLD handler)
            pass
