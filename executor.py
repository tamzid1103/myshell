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
import jobs as _jobs_registry

# SEC-10: Set MYSHELL_DEBUG=1 to see full error details from child processes.
DEBUG = os.environ.get("MYSHELL_DEBUG", "0") == "1"

# Critical system directories and files protected against destructive removal commands
PROTECTED_SYSTEM_PATHS = {
    "/", "/bin", "/sbin", "/usr", "/usr/bin", "/usr/sbin",
    "/etc", "/boot", "/dev", "/sys", "/proc", "/root",
    "/etc/passwd", "/etc/shadow", "/etc/sudoers"
}


def check_destructive_command(clean_tokens):
    """
    Prevent accidental catastrophic deletion of root and critical system directories.
    Blocks removal commands targeting protected paths (e.g., `rm -rf /` or expanded `/*`).
    """
    if not clean_tokens:
        return None
    cmd = os.path.basename(clean_tokens[0])
    if cmd in ("rm", "rmdir", "unlink"):
        for arg in clean_tokens[1:]:
            if arg.startswith("-"):
                continue  # skip flags like -r, -f
            norm = os.path.normpath(os.path.expanduser(arg))
            if norm in PROTECTED_SYSTEM_PATHS:
                return f"myshell: security warning: removal of protected system path '{arg}' is blocked"
    return None


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

    # Security check: prevent catastrophic file/directory removal
    sec_err = check_destructive_command(clean_tokens)
    if sec_err:
        print(sec_err, file=sys.stderr)
        return 1

    pid = os.fork()

    if pid == 0:
        # ── CHILD PROCESS ──────────────────────────────────────────────
        # Apply any explicit file redirections for this command
        apply_redirections(redirs)

        # Resolve command path and verify file permissions
        prog = clean_tokens[0]
        resolved = None

        if "/" in prog or os.path.exists(prog):
            if os.path.isdir(prog):
                print(f"myshell: {prog}: Is a directory", file=sys.stderr)
                sys.exit(126)
            if not os.path.exists(prog):
                print(f"myshell: {prog}: No such file or directory", file=sys.stderr)
                sys.exit(127)
            if not os.access(prog, os.X_OK):
                print(f"myshell: permission denied: {prog}", file=sys.stderr)
                sys.exit(126)
            resolved = os.path.abspath(prog)
        else:
            # SEC-01: Search PATH safely using shutil.which() with fallback to os.defpath
            search_path = os.environ.get("PATH") or os.defpath
            resolved = shutil.which(prog, path=search_path)

        if resolved is None:
            print(f"myshell: command not found: {prog}", file=sys.stderr)
            sys.exit(127)  # 127 = command not found (standard convention)

        try:
            # os.execv takes an absolute path — no PATH lookup performed.
            os.execv(resolved, clean_tokens)
        except PermissionError:
            print(f"myshell: permission denied: {prog}", file=sys.stderr)
            sys.exit(126)  # 126 = permission denied (standard convention)
        except Exception as e:
            # SEC-10: Only expose internal error details in debug mode.
            if DEBUG:
                print(f"myshell: error executing {prog}: {e}", file=sys.stderr)
            else:
                print(f"myshell: error executing {prog}", file=sys.stderr)
            sys.exit(1)

    elif pid > 0:
        # ── PARENT PROCESS ─────────────────────────────────────────────
        if background:
            # Register in job table so `jobs` builtin can list it
            jid = _jobs_registry.register(pid, clean_tokens)
            print(yellow(f"[{jid}] {pid}  {' '.join(clean_tokens)}"))
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
        # fork() returned a negative value — fork failed
        print("myshell: error: failed to create child process (fork failed)", file=sys.stderr)
        return 1
