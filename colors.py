"""
colors.py — MyShell ANSI Color Palette and Formatting
======================================================

Provides ANSI escape sequences and helpers for colored terminal output,
dynamic text color customization, and readline-compatible prompt styling.

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
    RL_CYAN    = "\001\033[1;96m\002"
    RL_BLUE    = "\001\033[1;94m\002"
    RL_YELLOW  = "\001\033[1;93m\002"
    RL_RED     = "\001\033[1;91m\002"


COLOR_MAP = {
    "red":     Colors.RED,
    "green":   Colors.GREEN,
    "yellow":  Colors.YELLOW,
    "blue":    Colors.BLUE,
    "magenta": Colors.MAGENTA,
    "purple":  Colors.MAGENTA,
    "cyan":    Colors.CYAN,
    "white":   Colors.WHITE,
    "black":   Colors.BLACK,
}

# Dynamic shell color state
_active_text_color = None
_active_prompt_color = None


def is_color_enabled():
    """Check if color output should be enabled."""
    if "NO_COLOR" in os.environ:
        return False
    return True


def colorize(text, color_code):
    """Wrap text in an ANSI color code if coloring is supported."""
    if not is_color_enabled() or not color_code:
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


def get_available_colors():
    """Return a list of supported color names."""
    return [c for c in COLOR_MAP.keys() if c != "purple"]


def set_text_color(color_name):
    """
    Set active terminal text color.
    Returns (success: bool, message: str).
    """
    global _active_text_color
    if not color_name:
        return False, "Usage: color <name> (e.g. green, cyan, blue, red, reset)"

    normalized = color_name.strip().lower()
    if normalized in ("reset", "default", "none"):
        _active_text_color = None
        restore_terminal()
        return True, "Shell text color reset to default."

    if normalized in COLOR_MAP:
        _active_text_color = normalized
        apply_text_color()
        sample = colorize(normalized, COLOR_MAP[normalized])
        return True, f"Shell text color set to {sample}."

    available = ", ".join(get_available_colors())
    return False, f"Unknown color '{color_name}'. Available: {available}, reset"


def get_text_color():
    return _active_text_color


def set_prompt_color(color_name):
    """
    Set active prompt accent color.
    Returns (success: bool, message: str).
    """
    global _active_prompt_color
    normalized = color_name.strip().lower() if color_name else ""
    if normalized in ("reset", "default", "none", ""):
        _active_prompt_color = None
        return True, "Shell prompt color reset to default."

    if normalized in COLOR_MAP:
        _active_prompt_color = normalized
        sample = colorize(normalized, COLOR_MAP[normalized])
        return True, f"Shell prompt color set to {sample}."

    available = ", ".join(get_available_colors())
    return False, f"Unknown color '{color_name}'. Available: {available}, reset"


def get_prompt_color():
    return _active_prompt_color


def reset_all_colors():
    global _active_text_color, _active_prompt_color
    _active_text_color = None
    _active_prompt_color = None
    restore_terminal()


def apply_text_color():
    """Emit the active text color code to the terminal."""
    if _active_text_color and _active_text_color in COLOR_MAP:
        sys.stdout.write(COLOR_MAP[_active_text_color])
        sys.stdout.flush()


def restore_terminal():
    """Reset terminal text styling."""
    sys.stdout.write(Colors.RESET)
    sys.stdout.flush()


def format_palette():
    """Return formatted palette of all available colors with visual samples."""
    lines = [
        cyan("╔══════════════════════════════════════════════════════════════╗"),
        cyan("║                 MyShell Color Palette                        ║"),
        cyan("╠══════════════════════════════════════════════════════════════╣"),
        "║  Available Colors:                                           ║",
    ]
    for name in get_available_colors():
        sample = colorize(f"■ {name:<10}", COLOR_MAP[name])
        active_mark = " (active)" if name == _active_text_color else ""
        lines.append(f"║    {sample}{active_mark:<16}                        ║")
    lines.extend([
        "║                                                              ║",
        "║  Commands:                                                   ║",
        "║    color <name>         Set terminal text color              ║",
        "║    color prompt <name>  Set prompt accent color              ║",
        "║    color reset          Reset terminal colors to default     ║",
        "║    color list           Display this palette                 ║",
        cyan("╚══════════════════════════════════════════════════════════════╝"),
    ])
    return "\n".join(lines)


def build_prompt(dir_name):
    """Build a styled, color-aware prompt string."""
    return format_prompt()


def format_prompt(last_exit_code=0):
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
        badge = f" [\u2717 {last_exit_code}]" if last_exit_code != 0 else ""
        return f"{user}@myshell:{display_dir}{badge}$ "

    user_col = Colors.GREEN
    shell_col = COLOR_MAP.get(_active_prompt_color, Colors.CYAN)
    dir_col = Colors.BLUE

    # Non-zero exit code → red failure badge between path and $
    if last_exit_code != 0:
        exit_badge = (
            f" \001{Colors.BOLD}{Colors.RED}\002"
            f"[\u2717 {last_exit_code}]"
            f"\001{Colors.RESET}\002"
        )
    else:
        exit_badge = ""

    # If active text color is selected, set it at the end of prompt
    text_code = f"\001{COLOR_MAP[_active_text_color]}\002" if _active_text_color in COLOR_MAP else ""

    return (
        f"\001{Colors.BOLD}{user_col}\002{user}"
        f"\001{Colors.RESET}\002@"
        f"\001{Colors.BOLD}{shell_col}\002myshell"
        f"\001{Colors.RESET}\002:"
        f"\001{Colors.BOLD}{dir_col}\002{display_dir}"
        f"\001{Colors.RESET}\002{exit_badge}$ {text_code}"
    )
