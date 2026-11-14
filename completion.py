"""
completion.py — MyShell Tab Completion
========================================

Implements intelligent tab completion using Python's standard `readline` module
and terminal I/O control (termios under the hood).

Features:
    - Command completion: builtins + system executables in PATH (when completing first word)
    - File and path completion: local files, directories (with trailing '/'), tilde expansion
    - Non-intrusive: falls back gracefully if readline is unavailable
"""

import os
import glob
try:
    import readline
except ImportError:
    readline = None


def get_command_candidates(prefix):
    """Return builtin commands and PATH executables matching prefix."""
    matches = set()

    # 1. Built-in commands
    try:
        from builtin_cmds import BUILTINS
        for cmd in BUILTINS:
            if cmd.startswith(prefix):
                matches.add(cmd)
    except ImportError:
        pass

    # 2. Executables from PATH
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    for p_dir in path_dirs:
        if not p_dir or not os.path.isdir(p_dir):
            continue
        try:
            for entry in os.listdir(p_dir):
                if entry.startswith(prefix):
                    full_p = os.path.join(p_dir, entry)
                    if os.access(full_p, os.X_OK):
                        matches.add(entry)
        except (PermissionError, OSError):
            continue

    return sorted(matches)


def get_path_candidates(prefix):
    """Return matching file and directory paths for prefix."""
    # Expand tilde for lookup
    expanded_prefix = os.path.expanduser(prefix)
    is_tilde = prefix.startswith("~")

    # Use glob to find matches
    search_pattern = expanded_prefix + "*"
    raw_matches = glob.glob(search_pattern)

    formatted_matches = []
    for match in raw_matches:
        display_match = match
        if is_tilde:
            # Revert expanded home dir back to ~
            home = os.path.expanduser("~")
            if match.startswith(home):
                display_match = "~" + match[len(home):]

        if os.path.isdir(match):
            display_match += "/"

        formatted_matches.append(display_match)

    return sorted(formatted_matches)


def completer(text, state):
    """
    Completion callback invoked by readline.

    Args:
        text (str): The current word prefix being completed.
        state (int): Iteration counter (0, 1, 2, ...) until None is returned.

    Returns:
        str or None: The completion candidate, or None when exhausted.
    """
    if readline is None:
        return None

    try:
        line_buffer = readline.get_line_buffer()
        begidx = readline.get_begidx()
    except Exception:
        line_buffer = ""
        begidx = 0

    # Determine if we're completing the command (first token) or an argument
    prefix_line = line_buffer[:begidx].strip()
    is_command_position = (prefix_line == "")

    if is_command_position and not text.startswith((".", "/", "~")):
        options = get_command_candidates(text)
    else:
        options = get_path_candidates(text)

    if state < len(options):
        return options[state]
    return None


def setup_completion():
    """Configure readline to enable tab completion."""
    if readline is None:
        return

    readline.set_completer(completer)
    # Configure word delimiters so path characters like '/' and '~' remain part of the word
    readline.set_completer_delims(" \t\n;|&><")

    # Enable tab completion binding
    if "libedit" in readline.__doc__:
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")
