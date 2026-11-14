"""
globbing.py — MyShell Wildcard / Pathname Expansion
====================================================

Implements pathname expansion (globbing) for '*' and '?' wildcard characters.

OS Concepts Demonstrated:
    - Shell-side wildcard expansion: in POSIX systems, the shell expands globs
      before invoking the executable, passing the expanded list of filenames
      via the argument vector (argv).
"""

import glob


def expand_globs(tokens):
    """
    Expand wildcard patterns in a token list.

    For each token containing '*' or '?', expands matches from the filesystem.
    If no matches are found, the pattern is preserved as-is (standard POSIX shell behavior).

    Args:
        tokens (list[str]): Command tokens.

    Returns:
        list[str]: Expanded tokens list.
    """
    expanded = []
    for token in tokens:
        if "*" in token or "?" in token:
            matches = glob.glob(token)
            if matches:
                expanded.extend(sorted(matches))
            else:
                expanded.append(token)
        else:
            expanded.append(token)
    return expanded
