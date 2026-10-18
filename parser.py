"""
parser.py — MyShell Input Parser
==================================

Responsible for converting raw user input strings into structured,
tokenized data that the shell can act upon.

Uses `shlex.split()` instead of `str.split()` because shlex correctly
handles:
    - Quoted strings:  echo "hello world"  → ['echo', 'hello world']
    - Escape characters:  echo hello\\ world  → ['echo', 'hello world']
    - Nested quotes:  echo "it's here"  → ['echo', "it's here"]

The parser also detects special operators:
    - `&` (background execution)
    - `|` (pipe / command chaining)

OS Concepts Demonstrated:
    - Shell input parsing and tokenization
    - Operator detection for IPC (pipes) and async execution (background)
"""

import shlex


def parse_input(raw_input):
    """
    Parse a raw input string into a structured command representation.

    Args:
        raw_input (str): The raw string from the user's input.

    Returns:
        dict or None: Returns None if input is empty/whitespace.
            Otherwise returns a dict with:
            {
                "tokens":        list[str],       # Tokenized command
                "is_background": bool,            # True if '&' was found
                "is_pipe":       bool,            # True if '|' was found
                "pipe_commands": list[list[str]]  # Sub-commands split at '|'
            }
    """
    # ── Guard: Empty Input ─────────────────────────────────────────────
    # Prevents IndexError when user just presses Enter
    if not raw_input or not raw_input.strip():
        return None

    # ── Tokenize ───────────────────────────────────────────────────────
    try:
        tokens = shlex.split(raw_input)
    except ValueError as e:
        # Catches unmatched quotes, e.g.: echo "hello
        print(f"myshell: syntax error: {e}")
        return None

    # Empty after tokenization (shouldn't happen, but guard anyway)
    if not tokens:
        return None

    # ── Detect Background Operator '&' ─────────────────────────────────
    # If the last token is '&', the command should run in the background.
    # Remove '&' from the token list so it's not passed to execvp.
    is_background = False
    if tokens[-1] == "&":
        is_background = True
        tokens = tokens[:-1]
        if not tokens:
            print("myshell: syntax error: expected command before '&'")
            return None

    # ── Detect Pipe Operator '|' ───────────────────────────────────────
    # Split the token list at each '|' to get individual commands.
    # Example: ['ls', '-l', '|', 'grep', 'txt']
    #        → [['ls', '-l'], ['grep', 'txt']]
    is_pipe = "|" in tokens
    pipe_commands = []

    if is_pipe:
        pipe_commands = _split_at_pipes(tokens)
        if pipe_commands is None:
            return None  # Syntax error was already printed

    return {
        "tokens":        tokens,
        "is_background": is_background,
        "is_pipe":       is_pipe,
        "pipe_commands": pipe_commands,
    }


def _split_at_pipes(tokens):
    """
    Split a token list at each '|' delimiter.

    Args:
        tokens (list[str]): The full token list containing '|' separators.

    Returns:
        list[list[str]] or None: List of command token lists, or None on error.

    Example:
        ['ls', '-l', '|', 'grep', 'py', '|', 'wc', '-l']
        → [['ls', '-l'], ['grep', 'py'], ['wc', '-l']]
    """
    commands = []
    current_command = []

    for token in tokens:
        if token == "|":
            if not current_command:
                print("myshell: syntax error: expected command before '|'")
                return None
            commands.append(current_command)
            current_command = []
        else:
            current_command.append(token)

    # Don't forget the last command (after the final '|')
    if not current_command:
        print("myshell: syntax error: expected command after '|'")
        return None

    commands.append(current_command)
    return commands
