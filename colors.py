"""
colors.py — MyShell ANSI Color Palette and Formatting
======================================================

Provides ANSI escape sequences and helpers for colored terminal output.

OS Concepts Demonstrated:
    - Terminal escape sequences (ANSI X3.64 / ECMA-48)
    - Terminal control and cursor measurement protocol
    - TTY detection and non-printing character delimiters (\001, \002 for readline)
"""

import os
import sys


class Colors:
    """Standard ANSI color and text attribute codes."""
    RESET      = "\033[0m"
    BOLD       = "\033[1m"
    DIM        = "\033[2m"
    ITALIC     = "\033[3m"
    UNDERLINE  = "\033[4m"

    # Foreground Colors
    BLACK      = "\033[30m"
    RED        = "\033[91m"
    GREEN      = "\033[92m"
    YELLOW     = "\033[93m"
    BLUE       = "\033[94m"
    MAGENTA    = "\033[95m"
    CYAN       = "\033[96m"
    WHITE      = "\033[97m"

    # Readline-safe codes for prompts (enclosed in \001 and \002)
    RL_RESET   = "\001\033[0m\002"
    RL_BOLD    = "\001\033[1m\002"
    RL_GREEN   = "\001\033[1;92m\002"
    RL_CYAN    = "\033[1;96m"
    RL_BLUE    = "\001\033[1;94m\002"
    RL_YELLOW  = "\001\033[1;93m\002"
    RL_RED     = "\001\033[1;91m\002"


def is_color_enabled():
    """Check if color output should be enabled."""
    if "NO_COLOR" in os.environ:
        return False
    return True


def colorize(text, color_code):
    """Wrap text in an ANSI color code if coloring is supported."""
    if not is_color_enabled():
        return text
    return f"{color_code}{text}{Colors.RESET}"


def red(text):
    return colorize(text, Colors.RED)


def green(text):
    return colorize(text, Colors.GREEN)


def yellow(text):
    return colorize(text, Colors.YELLOW)


def blue(text):
    return colorize(text, Colors.BLUE)


def cyan(text):
    return colorize(text, Colors.CYAN)


def bold(text):
    return colorize(text, Colors.BOLD)


def format_prompt():
    """
    Construct a colorized shell prompt.
    Format: username@myshell:dirname$ 
    Uses readline non-printing delimiters (\001, \002) to prevent cursor distortion.
    """
    user = os.environ.get("USER") or os.environ.get("LOGNAME") or "user"
    home = os.path.expanduser("~")
    try:
        cwd = os.getcwd()
        if cwd == home:
            display_dir = "~"
        elif cwd.startswith(home + "/"):
            display_dir = "~/" + os.path.relpath(cwd, home)
        else:
            display_dir = os.path.basename(cwd) or cwd
    except OSError:
        display_dir = "?"

    if not is_color_enabled():
        return f"{user}@myshell:{display_dir}$ "

    return (
        f"\001{Colors.BOLD}{Colors.GREEN}\002{user}"
        f"\001{Colors.RESET}\002@"
        f"\001{Colors.BOLD}{Colors.CYAN}\002myshell"
        f"\001{Colors.RESET}\002:"
        f"\001{Colors.BOLD}{Colors.BLUE}\002{display_dir}"
        f"\001{Colors.RESET}\002$ "
    )
