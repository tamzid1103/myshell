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
from completion import setup_completion
from colors import format_prompt, cyan, bold, yellow, red
from executor import execute_command
from pipes import execute_pipeline
from variables import expand_variables
from globbing import expand_globs
from redirects import parse_redirections


def display_banner():
    """Display the MyShell welcome banner on startup."""
    banner = f"""
{cyan("╔══════════════════════════════════════════════════════════════╗")}
{cyan("║")}                                                              {cyan("║")}
{cyan("║")}               🐚  {bold("Welcome to MyShell")}  🐚                    {cyan("║")}
{cyan("║")}                                                              {cyan("║")}
{cyan("║")}        A Custom Unix Shell — OS Lab Project                  {cyan("║")}
{cyan("║")}        Type 'help' for available commands                    {cyan("║")}
{cyan("║")}                                                              {cyan("║")}
{cyan("╚══════════════════════════════════════════════════════════════╝")}
"""
    print(banner)


def get_prompt():
    """
    Build the shell prompt string with ANSI colors.
    """
    return format_prompt()


def dispatch_segment(segment, background=False, last_exit_code=0):
    """
    Dispatch a single command segment (single command or pipeline).

    Args:
        segment (dict): Command segment with 'tokens', 'is_pipe', 'pipe_commands'.
        background (bool): Whether to run asynchronously.
        last_exit_code (int): Previous exit code for variable expansion ($?).

    Returns:
        int: Exit status code.
    """
    tokens = segment["tokens"]

    # 1. Expand environment variables ($VAR, $?, $$)
    tokens = expand_variables(tokens, last_exit_code=last_exit_code)

    # 2. Check for piped commands (inter-process communication)
    if segment.get("is_pipe"):
        pipe_commands = []
        for cmd in segment["pipe_commands"]:
            cmd_vars = expand_variables(cmd, last_exit_code=last_exit_code)
            cmd_globs = expand_globs(cmd_vars)
            pipe_commands.append(cmd_globs)
        return execute_pipeline(pipe_commands, background=background)

    # 3. Expand wildcards / globs (*, ?) for non-piped commands
    tokens = expand_globs(tokens)

    # 3. Check for built-in commands (executed in parent process)
    clean_tokens, redirs, err = parse_redirections(tokens)
    if err:
        print(f"myshell: {err}", file=sys.stderr)
        return 2

    if not clean_tokens:
        # Bare redirection without command (e.g. `> file`)
        return execute_command(tokens, background=background)

    cmd_name = clean_tokens[0]
    cmd_args = clean_tokens[1:]

    if is_builtin(cmd_name):
        saved_stdout = None
        saved_stdin = None
        try:
            if redirs.get("stdout_file"):
                flags = os.O_WRONLY | os.O_CREAT | (os.O_APPEND if redirs.get("append") else os.O_TRUNC)
                fd_out = os.open(redirs["stdout_file"], flags, 0o644)
                saved_stdout = os.dup(sys.stdout.fileno())
                os.dup2(fd_out, sys.stdout.fileno())
                os.close(fd_out)
            if redirs.get("stdin_file"):
                fd_in = os.open(redirs["stdin_file"], os.O_RDONLY)
                saved_stdin = os.dup(sys.stdin.fileno())
                os.dup2(fd_in, sys.stdin.fileno())
                os.close(fd_in)
            return run_builtin(cmd_name, cmd_args)
        except OSError as e:
            print(f"myshell: {e}", file=sys.stderr)
            return 1
        finally:
            if saved_stdout is not None:
                os.dup2(saved_stdout, sys.stdout.fileno())
                os.close(saved_stdout)
            if saved_stdin is not None:
                os.dup2(saved_stdin, sys.stdin.fileno())
                os.close(saved_stdin)

    # 4. Single external command (fork + execvp + waitpid)
    return execute_command(tokens, background=background)


def dispatch_line(parsed, last_exit_code=0):
    """
    Execute a parsed command line respecting logical operators (&&, ||).

    Args:
        parsed (dict): The output of parse_input().
        last_exit_code (int): Current exit status before line execution.

    Returns:
        int: Final exit status.
    """
    for segment in parsed["chain"]:
        op = segment["op"]
        if op == "&&" and last_exit_code != 0:
            continue
        if op == "||" and last_exit_code == 0:
            continue

        last_exit_code = dispatch_segment(
            segment,
            background=parsed["is_background"],
            last_exit_code=last_exit_code,
        )

    return last_exit_code


def run_script(filepath, echo=True):
    """
    Execute commands from a script file sequentially (batch processing).

    Args:
        filepath (str): Path to the script file.
        echo (bool): If True, echo commands before executing (myshell> ...).

    Returns:
        int: Exit status of the last executed command.
    """
    try:
        with open(filepath, "r") as f:
            last_code = 0
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if echo:
                    print(f"myshell> {line}")
                parsed = parse_input(line)
                if parsed:
                    last_code = dispatch_line(parsed, last_exit_code=last_code)
            return last_code
    except FileNotFoundError:
        print(f"myshell: script not found: {filepath}", file=sys.stderr)
        return 1
    except PermissionError:
        print(f"myshell: permission denied: {filepath}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"myshell: error reading {filepath}: {e}", file=sys.stderr)
        return 1


def main():
    """
    Main entry point for MyShell. Supports interactive REPL and batch script modes.
    """
    # ── Signal Setup ───────────────────────────────────────────────────
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)

    # ── Script Execution Mode: python3 shell.py <script_file> ──────────
    if len(sys.argv) > 1:
        script_file = sys.argv[1]
        exit_code = run_script(script_file, echo=True)
        sys.exit(exit_code)

    # ── Interactive REPL Mode Setup ────────────────────────────────────
    setup_history()
    setup_completion()
    display_banner()

    # ── REPL Loop ──────────────────────────────────────────────────────
    last_exit_code = 0
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

        # ── DISPATCH: Route commands through conditional execution chain
        last_exit_code = dispatch_line(parsed, last_exit_code=last_exit_code)


# ── Entry Point ───────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
