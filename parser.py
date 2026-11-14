"""
parser.py — MyShell Input Parser
==================================

Responsible for converting raw user input strings into structured,
tokenized data that the shell can act upon.

Uses `shlex.split()` instead of `str.split()` because shlex correctly
handles:
    - Quoted strings:     echo "hello world"  → ['echo', 'hello world']
    - Escape characters:  echo hello\\ world  → ['echo', 'hello world']
    - Nested quotes:      echo "it's here"    → ['echo', "it's here"]

The parser detects special operators:
    - `&`       (background execution)
    - `|`       (pipe / command chaining)
    - `&&`, `||` (logical conditional execution)
    - `>`, `>>`, `<` (I/O redirection handled downstream)

OS Concepts Demonstrated:
    - Shell input parsing and tokenization
    - Lexical analysis of shell grammar and operator precedence
    - Process conditional execution flow
"""

import sys
import shlex


def parse_input(raw_input):
    """
    Parse a raw input string into a structured command representation.

    Args:
        raw_input (str): The raw string from the user's input.

    Returns:
        dict or None: Returns None if input is empty/whitespace or syntax error.
            Otherwise returns a dict with:
            {
                "is_background": bool,
                "chain": list[dict],      # List of conditional command segments
                "tokens": list[str],      # First segment tokens (backwards compat)
                "is_pipe": bool,          # First segment pipe status
                "pipe_commands": list     # First segment sub-commands
            }
    """
    # ── Guard: Empty Input ─────────────────────────────────────────────
    if not raw_input or not raw_input.strip():
        return None

    # ── Tokenize ───────────────────────────────────────────────────────
    try:
        tokens = shlex.split(raw_input)
    except ValueError as e:
        print(f"myshell: syntax error: {e}", file=sys.stderr)
        return None

    if not tokens:
        return None

    # ── Detect Background Operator '&' ─────────────────────────────────
    is_background = False
    if tokens[-1] == "&":
        is_background = True
        tokens = tokens[:-1]
        if not tokens:
            print("myshell: syntax error: expected command before '&'", file=sys.stderr)
            return None

    # ── Split at Logical Operators ('&&' and '||') ────────────────────
    chain = _split_at_conditionals(tokens)
    if chain is None or not chain:
        return None

    # For each segment in the chain, check for pipe operators ('|')
    for segment in chain:
        seg_tokens = segment["tokens"]
        is_pipe = "|" in seg_tokens
        pipe_commands = []
        if is_pipe:
            pipe_commands = _split_at_pipes(seg_tokens)
            if pipe_commands is None:
                return None
        segment["is_pipe"] = is_pipe
        segment["pipe_commands"] = pipe_commands

    return {
        "is_background": is_background,
        "chain":         chain,
        "tokens":        chain[0]["tokens"],
        "is_pipe":       chain[0]["is_pipe"],
        "pipe_commands": chain[0]["pipe_commands"],
    }


def _split_at_conditionals(tokens):
    """
    Split token list at '&&' and '||' boundaries.

    Returns:
        list[dict] or None: List of dicts with {'op': None|'&&'|'||', 'tokens': list[str]}
                            or None if a syntax error occurred.
    """
    chain = []
    current_tokens = []
    current_op = None

    for token in tokens:
        if token in ("&&", "||"):
            if not current_tokens:
                print(f"myshell: syntax error near unexpected token '{token}'", file=sys.stderr)
                return None
            chain.append({"op": current_op, "tokens": current_tokens})
            current_op = token
            current_tokens = []
        else:
            current_tokens.append(token)

    if not current_tokens:
        if current_op:
            print(f"myshell: syntax error near unexpected token '{current_op}'", file=sys.stderr)
            return None
        return []

    chain.append({"op": current_op, "tokens": current_tokens})
    return chain


def _split_at_pipes(tokens):
    """
    Split a token list at each '|' delimiter.

    Args:
        tokens (list[str]): The full token list containing '|' separators.

    Returns:
        list[list[str]] or None: List of command token lists, or None on error.
    """
    commands = []
    current_command = []

    for token in tokens:
        if token == "|":
            if not current_command:
                print("myshell: syntax error: expected command before '|'", file=sys.stderr)
                return None
            commands.append(current_command)
            current_command = []
        else:
            current_command.append(token)

    if not current_command:
        print("myshell: syntax error: expected command after '|'", file=sys.stderr)
        return None

    commands.append(current_command)
    return commands
