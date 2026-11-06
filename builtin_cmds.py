"""
builtin_cmds.py — MyShell Built-in Commands
========================================

Built-in commands are executed directly in the parent (shell) process,
NOT in a forked child. This is a critical OS concept:

    - `cd` MUST run in the parent because a child process gets its own
      copy of the address space (including the current working directory).
      If `cd` ran in a child, only the child's directory would change,
      and it would be discarded when the child exits.

    - `exit` must terminate the parent shell process itself.

OS Concepts Demonstrated:
    - Process address space isolation (why cd must be a builtin)
    - Environment variable access (HOME directory)
"""

import os
import sys


def builtin_cd(args):
    """
    Change the shell's current working directory.

    OS Concept: os.chdir() modifies the calling process's working directory.
    Since builtins run in the parent, this correctly changes the shell's cwd.

    Args:
        args (list): List of arguments. args[0] is the target directory.
                     If empty, navigates to $HOME.
    """
    if len(args) == 0:
        # No argument provided — navigate to user's home directory
        target = os.environ.get("HOME", "/")
    else:
        target = args[0]

    # Expand ~ and ~user to the full home directory path
    # (Python's os.chdir does NOT auto-expand tilde like bash)
    target = os.path.expanduser(target)

    try:
        os.chdir(target)
        return 0
    except FileNotFoundError:
        print(f"myshell: cd: {target}: No such file or directory", file=sys.stderr)
        return 1
    except PermissionError:
        print(f"myshell: cd: {target}: Permission denied", file=sys.stderr)
        return 1
    except NotADirectoryError:
        print(f"myshell: cd: {target}: Not a directory", file=sys.stderr)
        return 1


def builtin_exit(args):
    """
    Exit the shell cleanly.

    OS Concept: sys.exit() raises SystemExit, which terminates the process.
    The exit code is passed to the parent process (the terminal emulator).

    Args:
        args (list): Optional exit code. Defaults to 0 (success).
    """
    exit_code = 0
    if len(args) > 0:
        try:
            exit_code = int(args[0])
            # SEC-12: Unix exit codes are a single byte (0–255).
            # Clamp the value to prevent undefined OS behavior from
            # arbitrarily large integers (e.g., `exit 9999999999`).
            exit_code = exit_code % 256
        except ValueError:
            print(f"myshell: exit: {args[0]}: numeric argument required")
            exit_code = 1

    print("Exiting MyShell. Goodbye!")
    sys.exit(exit_code)


def builtin_export(args):
    """
    Set environment variables.

    Usage:
        export VAR=value
        export VAR="value with spaces"
        export (lists all exported variables)
    """
    if not args:
        for k, v in sorted(os.environ.items()):
            print(f"declare -x {k}=\"{v}\"")
        return 0

    exit_code = 0
    for arg in args:
        if "=" in arg:
            key, val = arg.split("=", 1)
        else:
            key, val = arg, ""

        # Strip surrounding quotes if present
        if len(val) >= 2 and ((val[0] == '"' and val[-1] == '"') or (val[0] == "'" and val[-1] == "'")):
            val = val[1:-1]

        # Identifier check
        if not key or not (key[0].isalpha() or key[0] == '_') or not all(c.isalnum() or c == '_' for c in key):
            print(f"myshell: export: '{arg}': not a valid identifier", file=sys.stderr)
            exit_code = 1
            continue

        os.environ[key] = val
    return exit_code


def builtin_unset(args):
    """
    Remove environment variables from the shell environment.

    Usage:
        unset VAR ...
    """
    if not args:
        return 0

    exit_code = 0
    for var in args:
        if not var or not (var[0].isalpha() or var[0] == '_') or not all(c.isalnum() or c == '_' for c in var):
            print(f"myshell: unset: '{var}': not a valid identifier", file=sys.stderr)
            exit_code = 1
            continue
        os.environ.pop(var, None)
    return exit_code


def builtin_env(args):
    """
    Print all environment variables.

    Usage:
        env
    """
    for k, v in sorted(os.environ.items()):
        print(f"{k}={v}")
    return 0


try:
    import readline
except ImportError:
    readline = None

HISTORY_FILE = os.path.expanduser("~/.myshell_history")


def setup_history():
    """Load persistent command history from disk."""
    if readline is None:
        return
    try:
        readline.read_history_file(HISTORY_FILE)
    except (FileNotFoundError, OSError):
        pass

    import atexit
    def _save():
        try:
            readline.write_history_file(HISTORY_FILE)
        except (PermissionError, OSError):
            pass
    atexit.register(_save)


def builtin_history(args):
    """
    Print command history or clear it.

    Usage:
        history
        history -c (clear history)
    """
    if readline is None:
        print("myshell: history: readline not available", file=sys.stderr)
        return 1

    if args and args[0] == "-c":
        readline.clear_history()
        return 0

    length = readline.get_current_history_length()
    for i in range(1, length + 1):
        item = readline.get_history_item(i)
        print(f"  {i:4d}  {item}")
    return 0


def builtin_help(args):
    """
    Display help information about MyShell and its built-in commands.

    Also explains the OS concepts demonstrated by this shell, which is
    useful for lab viva/report discussions.

    Args:
        args (list): Unused, included for consistent function signature.
    """
    help_text = """
╔══════════════════════════════════════════════════════════════╗
║                     MyShell — Help                         ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Built-in Commands:                                          ║
║    cd [dir]       Change directory (default: $HOME)          ║
║    exit [code]    Exit the shell (default code: 0)           ║
║    help           Display this help message                  ║
║                                                              ║
║  Features:                                                   ║
║    command        Execute any system command (ls, pwd, etc.) ║
║    cmd1 | cmd2    Pipe: route cmd1's output into cmd2        ║
║    command &      Run command in the background              ║
║                                                              ║
║  Shortcuts:                                                  ║
║    Ctrl+C         Cancel current input (won't kill shell)    ║
║    Ctrl+D         Exit the shell                             ║
║                                                              ║
║  OS Concepts Demonstrated:                                   ║
║    • Process creation        — os.fork()                     ║
║    • Program execution       — os.execvp()                   ║
║    • Process synchronization — os.waitpid()                  ║
║    • Inter-process comm.     — os.pipe() + os.dup2()         ║
║    • Signal handling         — signal.SIGCHLD                ║
║    • Address space isolation — why cd is a builtin           ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(help_text)


# ─── Builtin Dispatch Table ───────────────────────────────────────────
# Maps command name (string) → handler function.
# To add a new builtin, simply add an entry here.
BUILTINS = {
    "cd":      builtin_cd,
    "exit":    builtin_exit,
    "help":    builtin_help,
    "export":  builtin_export,
    "unset":   builtin_unset,
    "env":     builtin_env,
    "history": builtin_history,
}


def is_builtin(command_name):
    """
    Check if a command name is a built-in command.

    Args:
        command_name (str): The command to check.

    Returns:
        bool: True if the command is a builtin.
    """
    return command_name in BUILTINS


def run_builtin(command_name, args):
    """
    Execute a built-in command.

    Args:
        command_name (str): The builtin command name.
        args (list): Arguments to pass to the builtin function.

    Returns:
        int: Exit status code (0 for success, non-zero for failure).
    """
    handler = BUILTINS.get(command_name)
    if handler:
        res = handler(args)
        return 0 if res is None else res
    return 1
