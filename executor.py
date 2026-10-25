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


def execute_command(tokens, background=False):
    """
    Execute a single external command using fork + execvp.

    Args:
        tokens (list[str]): The tokenized command.
                            tokens[0] is the program name.
                            tokens[1:] are the arguments.
        background (bool):  If True, the parent will not wait for the child.
                            The child runs asynchronously.

    OS Flow:
        Parent Process (the shell)
            │
            ├── os.fork() ──────────────────────┐
            │                                    │
            │   [Parent: pid > 0]          [Child: pid == 0]
            │       │                            │
            │       │                      os.execvp(cmd)
            │       │                      (child becomes `cmd`)
            │       │                            │
            │   if foreground:                   │
            │       os.waitpid(pid, 0)      child runs and exits
            │       (blocks until done)          │
            │   else:                            │
            │       print PID, continue          │
            │                                    │
            └── prompt returns ──────────────────┘
    """
    pid = os.fork()

    if pid == 0:
        # ── CHILD PROCESS ──────────────────────────────────────────────
        # This is the child. Replace this process with the target program.
        # After execvp(), none of the Python code below will execute
        # because the process image is entirely replaced.
        try:
            os.execvp(tokens[0], tokens)
        except FileNotFoundError:
            # The binary was not found in PATH
            print(f"myshell: command not found: {tokens[0]}")
            sys.exit(127)  # 127 = command not found (standard convention)
        except PermissionError:
            # The binary exists but is not executable
            print(f"myshell: permission denied: {tokens[0]}")
            sys.exit(126)  # 126 = permission denied (standard convention)
        except Exception as e:
            # Catch any other unexpected error in the child
            print(f"myshell: error executing {tokens[0]}: {e}")
            sys.exit(1)

    elif pid > 0:
        # ── PARENT PROCESS ─────────────────────────────────────────────
        # The parent either waits for the child (foreground) or
        # continues immediately (background).
        if background:
            # Background: print the child's PID and return to prompt
            print(f"[bg] started process {pid}")
            # Note: We do NOT call os.waitpid() here.
            # Zombie cleanup is handled by signal.SIGCHLD → SIG_IGN in shell.py
        else:
            # Foreground: block until the child process terminates
            try:
                os.waitpid(pid, 0)
            except (ChildProcessError, OSError):
                # Child was already reaped (e.g., by SIGCHLD handler)
                # Some Linux kernels raise OSError (ECHILD) instead of
                # ChildProcessError when SIGCHLD is set to SIG_IGN
                pass

    else:
        # fork() returned a negative value — fork failed
        print("myshell: error: failed to create child process (fork failed)")
