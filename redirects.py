"""
redirects.py — MyShell I/O Redirection Handler
================================================

Handles redirection of standard input and standard output to and from files
using Unix system calls:
    - os.open()  — Open or create files with specific flags (O_RDONLY, O_WRONLY, O_CREAT, O_TRUNC, O_APPEND)
    - os.dup2()  — Duplicate file descriptors onto stdin (fd 0) or stdout (fd 1)
    - os.close() — Close redundant file descriptors

Supported Operators:
    - '>'   Redirect stdout (overwrite mode)
    - '>>'  Redirect stdout (append mode)
    - '<'   Redirect stdin (read mode)

OS Concepts Demonstrated:
    - File descriptor table manipulation
    - Redirection mechanics (how shells decouple programs from hardware I/O)
    - POSIX file opening modes and permission masks
"""

import os
import sys


def parse_redirections(tokens):
    """
    Extract redirection operators and target filenames from a token list.

    Args:
        tokens (list[str]): The command tokens (e.g. ['cat', '<', 'in.txt', '>', 'out.txt'])

    Returns:
        tuple: (clean_tokens, redirections, error)
            - clean_tokens (list[str]): Tokens with redirection operators and filenames removed.
            - redirections (dict): {
                "stdin_file": str or None,
                "stdout_file": str or None,
                "append": bool
              }
            - error (str or None): Error message if syntax is invalid, else None.
    """
    clean_tokens = []
    redirections = {
        "stdin_file": None,
        "stdout_file": None,
        "append": False,
    }

    i = 0
    n = len(tokens)

    while i < n:
        token = tokens[i]

        if token == ">":
            if i + 1 >= n or tokens[i + 1] in (">", ">>", "<", "|", "&&", "||"):
                return None, None, "syntax error near unexpected token 'newline'"
            redirections["stdout_file"] = tokens[i + 1]
            redirections["append"] = False
            i += 2
        elif token == ">>":
            if i + 1 >= n or tokens[i + 1] in (">", ">>", "<", "|", "&&", "||"):
                return None, None, "syntax error near unexpected token 'newline'"
            redirections["stdout_file"] = tokens[i + 1]
            redirections["append"] = True
            i += 2
        elif token == "<":
            if i + 1 >= n or tokens[i + 1] in (">", ">>", "<", "|", "&&", "||"):
                return None, None, "syntax error near unexpected token 'newline'"
            redirections["stdin_file"] = tokens[i + 1]
            i += 2
        elif token.startswith(">>") and len(token) > 2:
            redirections["stdout_file"] = token[2:]
            redirections["append"] = True
            i += 1
        elif token.startswith(">") and len(token) > 1:
            redirections["stdout_file"] = token[1:]
            redirections["append"] = False
            i += 1
        elif token.startswith("<") and len(token) > 1:
            redirections["stdin_file"] = token[1:]
            i += 1
        else:
            clean_tokens.append(token)
            i += 1

    return clean_tokens, redirections, None


def apply_redirections(redirections):
    """
    Apply file descriptor redirection in the child process before exec.

    Args:
        redirections (dict): Redirection configuration from parse_redirections.

    Exits the process with code 1 if a file cannot be opened.
    """
    if not redirections:
        return

    # Handle Input Redirection (<)
    stdin_file = redirections.get("stdin_file")
    if stdin_file:
        try:
            fd_in = os.open(stdin_file, os.O_RDONLY)
            os.dup2(fd_in, sys.stdin.fileno())
            os.close(fd_in)
        except FileNotFoundError:
            print(f"myshell: {stdin_file}: No such file or directory", file=sys.stderr)
            sys.exit(1)
        except PermissionError:
            print(f"myshell: {stdin_file}: Permission denied", file=sys.stderr)
            sys.exit(1)
        except OSError as e:
            print(f"myshell: {stdin_file}: {e}", file=sys.stderr)
            sys.exit(1)

    # Handle Output Redirection (> or >>)
    stdout_file = redirections.get("stdout_file")
    if stdout_file:
        flags = os.O_WRONLY | os.O_CREAT
        if redirections.get("append"):
            flags |= os.O_APPEND
        else:
            flags |= os.O_TRUNC

        try:
            fd_out = os.open(stdout_file, flags, 0o644)
            os.dup2(fd_out, sys.stdout.fileno())
            os.close(fd_out)
        except PermissionError:
            print(f"myshell: {stdout_file}: Permission denied", file=sys.stderr)
            sys.exit(1)
        except OSError as e:
            print(f"myshell: {stdout_file}: {e}", file=sys.stderr)
            sys.exit(1)
