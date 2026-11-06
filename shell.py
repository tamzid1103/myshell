#!/usr/bin/env python3
"""
shell.py — MyShell Main Entry Point
=====================================

This is the Read-Eval-Print Loop (REPL) — the heart of the shell.
It continuously:
    1. Prints the prompt (myshell> )
    2. Reads user input
    3. Parses the input into tokens
    4. Dispatches to the correct handler:
       - Built-in commands → builtin_cmds.py (runs in parent)
       - Piped commands    → pipes.py (fork + pipe + dup2)
       - Single commands   → executor.py (fork + execvp)
    5. Loops back to step 1

Signal Handling (OS Concept):
    At startup, we set:
        signal.signal(signal.SIGCHLD, signal.SIG_IGN)

    This tells the Linux kernel to automatically clean up (reap) child
    processes when they terminate. Without this, background processes
    ('command &') would become zombies — entries stuck in the process
    table because the parent never called wait() on them.

    A zombie process has finished executing but still occupies a slot in
    the kernel's process table. If too many accumulate, the system can't
    create new processes. SIG_IGN prevents this entirely.

Usage:
    $ python3 shell.py

OS Concepts Demonstrated:
    - REPL (Read-Eval-Print Loop) — how all shells work
    - Signal handling (SIGCHLD for zombie prevention)
    - Process dispatch (builtin vs external)
    - Graceful signal handling (SIGINT / Ctrl+C)
"""

import os
import sys
import signal

# ── MyShell Module Imports ────────────────────────────────────────────
from parser import parse_input
from builtin_cmds import is_builtin, run_builtin, setup_history
from executor import execute_command
from pipes import execute_pipeline


def display_banner():
    """Display the MyShell welcome banner on startup."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║               🐚  Welcome to MyShell  🐚                    ║
║                                                              ║
║        A Custom Unix Shell — OS Lab Project                  ║
║        Type 'help' for available commands                    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def get_prompt():
    """
    Build the shell prompt string.

    Displays the current working directory's basename for context,
    similar to how bash shows the directory in the prompt.

    Returns:
        str: The formatted prompt string.
    """
    try:
        cwd = os.getcwd()
        # Show just the directory name, not the full path
        dir_name = os.path.basename(cwd) or cwd
    except OSError:
        dir_name = "?"

    return f"myshell [{dir_name}]> "


def main():
    """
    The main REPL loop for MyShell.

    This function:
    1. Sets up signal handling to prevent zombie processes
    2. Displays the welcome banner
    3. Enters an infinite loop that reads, parses, and dispatches commands
    4. Handles Ctrl+C (SIGINT) and Ctrl+D (EOF) gracefully
    """

    # ── Signal Setup ───────────────────────────────────────────────────
    # SIGCHLD is sent to the parent when a child process terminates.
    # SIG_IGN tells the kernel: "I don't care, just clean it up."
    # This prevents zombie processes from background commands ('cmd &').
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)

    # ── Command History Setup ──────────────────────────────────────────
    setup_history()

    # ── Welcome Banner ────────────────────────────────────────────────
    display_banner()

    # ── REPL Loop ──────────────────────────────────────────────────────
    while True:
        try:
            # ── READ: Get user input ───────────────────────────────────
            raw_input_str = input(get_prompt())

        except EOFError:
            # User pressed Ctrl+D — end of input stream
            print("\nExiting MyShell. Goodbye!")
            sys.exit(0)

        except KeyboardInterrupt:
            # User pressed Ctrl+C — cancel current input, don't exit
            print()  # Move to a new line
            continue

        except OSError as e:
            # SEC-09: stdin can raise OSError if the terminal is detached
            # (e.g., stdin is a broken pipe or the controlling tty is gone).
            # Exit cleanly rather than crashing with an unhandled exception.
            print(f"\nmyshell: terminal error: {e}")
            sys.exit(1)

        # ── EVAL: Parse the input ──────────────────────────────────────
        parsed = parse_input(raw_input_str)

        if parsed is None:
            # Empty input or syntax error — skip to next iteration
            continue

        # Extract the command name (first token)
        command_name = parsed["tokens"][0]
        command_args = parsed["tokens"][1:]

        # ── DISPATCH: Route to the correct handler ─────────────────────

        # 1. Check for built-in commands (must run in parent process)
        if is_builtin(command_name):
            run_builtin(command_name, command_args)
            continue

        # 2. Check for piped commands (inter-process communication)
        if parsed["is_pipe"]:
            execute_pipeline(parsed["pipe_commands"], background=parsed["is_background"])
            continue

        # 3. Single external command (fork + execvp)
        execute_command(parsed["tokens"], background=parsed["is_background"])


# ── Entry Point ───────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
