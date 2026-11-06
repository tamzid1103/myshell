"""
variables.py — MyShell Environment Variable Expansion
======================================================

Handles expansion of environment variables ($VAR, ${VAR}, $?, $$) in command
tokens before execution.

OS Concepts Demonstrated:
    - Process environment block (os.environ)
    - Shell-side parameter expansion
    - Process state inspection ($? exit status, $$ process ID)
"""

import os
import re

# Matches $VAR, ${VAR}, $?, and $$
VAR_REGEX = re.compile(r'\$(\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*)|\?|\$)')


def expand_variables(tokens, last_exit_code=0):
    """
    Scan tokens for environment variable references and replace them with values.

    Args:
        tokens (list[str]): Tokenized command input.
        last_exit_code (int): The exit code of the last executed command ($?).

    Returns:
        list[str]: Tokens with variables expanded.
    """
    def _replace(match):
        full = match.group(0)
        if full == "$?":
            return str(last_exit_code)
        if full == "$$":
            return str(os.getpid())
        var_name = match.group(2) or match.group(3)
        return os.environ.get(var_name, "")

    expanded = []
    for token in tokens:
        new_token = VAR_REGEX.sub(_replace, token)
        expanded.append(new_token)

    return expanded
