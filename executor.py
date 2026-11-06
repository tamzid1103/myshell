"""
executor.py — MyShell Command Executor
========================================

Handles the execution of single (non-piped) external commands by
interfacing directly with the Linux kernel through system calls.

Execution Flow:
    1. os.fork()   → Creates a child process (duplicate of the shell)
    2. os.execvp() → Replaces the child's memory with the target program
    3. os.waitpid() → Parent waits for child to finish (foreground only)

OS Concepts Demonstrated:
    - Process creation via fork()
        The fork() system call creates a new process by duplicating the
        calling process. The child gets a copy of the parent's address
        space. fork() returns 0 in the child and the child's PID in
        the parent.

    - Program execution via execvp()
        The exec family of system calls replaces the current process
        image with a new program. execvp() searches PATH for the
        binary and passes the argument vector. After exec, the child's
        original Python code is gone — it's now running the new program.

    - Process synchronization via waitpid()
        The parent process suspends execution until the specified child
        terminates. This prevents the shell prompt from reappearing
        before the command finishes (foreground behavior).

    - Background execution
        When '&' is used, the parent simply does NOT call waitpid().
        The child runs concurrently, and the parent immediately returns
        to the prompt. Zombie prevention is handled by SIGCHLD in shell.py.
"""

import os
import sys
import shutil
from redirects import parse_redirections, apply_redirections
from colors import yellow, red

# SEC-10: Set MYSHELL_DEBUG=1 to see full error details from child processes.
DEBUG = os.environ.get("MYSHELL_DEBUG", "0") == "1"


def execute_command(tokens, background=False):
    """
    Execute a single external command using fork + execvp (with I/O redirection).

    Args:
        tokens (list[str]): The tokenized command.
                            tokens[0] is the program name.
                            tokens[1:] are the arguments (may include >, >>, <).
        background (bool):  If True, the parent will not wait for the child.
                            The child runs asynchronously.

    Returns:
        int: Process exit code (0 for success, >0 on error).
    """
    clean_tokens, redirs, err = parse_redirections(tokens)
    if err:
        print(f"myshell: {err}", file=sys.stderr)
        return 2

    # If there are no command tokens left (e.g., user entered `> file.txt`)
    if not clean_tokens:
        if redirs.get("stdout_file"):
            flags = os.O_WRONLY | os.O_CREAT | (os.O_APPEND if redirs.get("append") else os.O_TRUNC)
            try:
                fd = os.open(redirs["stdout_file"], flags, 0o644)
                os.close(fd)
                return 0
            except OSError as e:
                print(f"myshell: {redirs['stdout_file']}: {e}", file=sys.stderr)
                return 1
        return 0

    pid = os.fork()

    if pid == 0:
        # ── CHILD PROCESS ──────────────────────────────────────────────
        # Apply file descriptor redirections (<, >, >>) before exec
        apply_redirections(redirs)

        # SEC-01: Resolve binary via shutil.which() before exec to prevent PATH injection
        resolved = shutil.which(clean_tokens[0])
        if resolved is None:
            print(f"myshell: command not found: {clean_tokens[0]}", file=sys.stderr)
            sys.exit(127)  # 127 = command not found
        try:
            os.execv(resolved, clean_tokens)
        except PermissionError:
            print(f"myshell: permission denied: {clean_tokens[0]}", file=sys.stderr)
            sys.exit(126)  # 126 = permission denied
        except Exception as e:
            if DEBUG:
                print(f"myshell: error executing {clean_tokens[0]}: {e}", file=sys.stderr)
            else:
                print(f"myshell: error executing {clean_tokens[0]}", file=sys.stderr)
            sys.exit(1)

    elif pid > 0:
        # ── PARENT PROCESS ─────────────────────────────────────────────
        if background:
            print(yellow(f"[bg] started process {pid}"))
            return 0
        else:
            try:
                _, status = os.waitpid(pid, 0)
                if os.WIFEXITED(status):
                    exit_code = os.WEXITSTATUS(status)
                    if DEBUG and exit_code != 0:
                        print(f"myshell: [debug] process {pid} exited with code {exit_code}")
                    return exit_code
                elif os.WIFSIGNALED(status):
                    return 128 + os.WTERMSIG(status)
                return 0
            except (ChildProcessError, OSError):
                return 0

    else:
        print("myshell: error: failed to create child process (fork failed)", file=sys.stderr)
        return 1
