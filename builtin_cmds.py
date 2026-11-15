"""
builtin_cmds.py — MyShell Built-in Commands
============================================

Built-in commands are executed directly in the parent (shell) process,
NOT in a forked child. This is a critical OS concept:

    - `cd` MUST run in the parent because a child process gets its own
      copy of the address space (including the current working directory).
      If `cd` ran in a child, only the child's directory would change,
      and it would be discarded when the child exits.

    - `exit` must terminate the parent shell process itself.

    - `export` and `unset` modify the parent process's environment block
      (os.environ), which is inherited by all subsequent child processes.

    - `source` / `.` executes commands directly within the current shell
      process environment without spawning an independent subshell.

OS Concepts Demonstrated:
    - Process address space isolation (why cd must be a builtin)
    - Process environment inheritance (os.environ, export, unset)
    - Command history persistence (GNU Readline integration)
    - In-process batch execution (source / .)
    - Terminal escape sequences (ANSI color management)
"""

import os
import sys
import shutil

# Optional import for colors module
try:
    import colors
except ImportError:
    colors = None

# Optional import for readline (history management)
try:
    import readline
except ImportError:
    readline = None

HISTORY_FILE = os.path.expanduser("~/.myshell_history")


def builtin_cd(args):
    """
    Change the shell's current working directory.

    OS Concept: os.chdir() modifies the calling process's working directory.
    Since builtins run in the parent, this correctly changes the shell's cwd.

    Args:
        args (list): List of arguments. args[0] is the target directory.
                     If empty, navigates to $HOME.

    Returns:
        int: 0 on success, 1 on failure.
    """
    if len(args) > 1:
        print("myshell: cd: too many arguments", file=sys.stderr)
        return 1

    if len(args) == 0:
        # No argument provided — navigate to user's home directory
        target = os.environ.get("HOME", "/")
    else:
        target = args[0]

    # Expand ~ and ~user to the full home directory path
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
    except (OSError, ValueError) as e:
        print(f"myshell: cd: {target}: {e}", file=sys.stderr)
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
    if len(args) > 1:
        print("myshell: exit: too many arguments", file=sys.stderr)
        return 1

    if len(args) == 1:
        try:
            exit_code = int(args[0])
            # SEC-12: Unix exit codes are a single byte (0–255).
            exit_code = exit_code % 256
        except ValueError:
            print(f"myshell: exit: {args[0]}: numeric argument required", file=sys.stderr)
            exit_code = 1

    if colors and hasattr(colors, "restore_terminal"):
        colors.restore_terminal()

    print("Exiting MyShell. Goodbye!")
    sys.exit(exit_code)


def builtin_color(args):
    """
    Change or inspect the color of the shell terminal text and prompt.

    OS Concept: Terminal escape sequences (ANSI codes) allow programs to
    instruct the terminal emulator to alter text rendering colors and styles.

    Usage:
        color                Show current color configuration and quick help
        color list           Display visual palette of all available colors
        color <name>         Set terminal text color (green, cyan, red, blue, etc.)
        color prompt <name>  Set prompt accent color
        color reset          Reset terminal text and prompt to defaults

    Returns:
        int: 0 on success, 1 on failure.
    """
    if colors is None:
        print("myshell: color: colors module not available", file=sys.stderr)
        return 1

    if len(args) == 0:
        curr_text = colors.get_text_color() or "default (terminal standard)"
        curr_prompt = colors.get_prompt_color() or "default"
        print(f"Current text color:   {curr_text}")
        print(f"Current prompt color: {curr_prompt}")
        print("Use 'color list' to preview colors, or 'color <name>' to change.")
        return 0

    subcmd = args[0].lower()

    if subcmd in ("list", "palette", "show"):
        print(colors.format_palette())
        return 0

    if subcmd == "prompt":
        if len(args) < 2:
            print("Usage: color prompt <color_name> (or 'color prompt reset')", file=sys.stderr)
            return 1
        success, msg = colors.set_prompt_color(args[1])
        out_stream = sys.stdout if success else sys.stderr
        print(msg, file=out_stream)
        return 0 if success else 1

    if subcmd == "text":
        if len(args) < 2:
            print("Usage: color text <color_name> (or 'color text reset')", file=sys.stderr)
            return 1
        success, msg = colors.set_text_color(args[1])
        out_stream = sys.stdout if success else sys.stderr
        print(msg, file=out_stream)
        return 0 if success else 1

    if subcmd in ("reset", "default", "none"):
        colors.reset_all_colors()
        print("Terminal text and prompt colors reset to default.")
        return 0

    # Direct color name: e.g. `color green`, `color cyan`, etc.
    success, msg = colors.set_text_color(subcmd)
    out_stream = sys.stdout if success else sys.stderr
    print(msg, file=out_stream)
    return 0 if success else 1


def builtin_export(args):
    """
    Set environment variables in the parent process.

    Usage:
        export VAR=value
        export VAR="value with spaces"
        export (lists all exported variables)

    Returns:
        int: 0 on success, 1 on invalid identifier.
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

        # Identifier check: must start with letter or underscore, followed by alnum or underscore
        if not key or not (key[0].isalpha() or key[0] == '_') or not all(c.isalnum() or c == '_' for c in key):
            print(f"myshell: export: '{arg}': not a valid identifier", file=sys.stderr)
            exit_code = 1
            continue

        os.environ[key] = val
    return exit_code


def builtin_unset(args):
    """
    Remove environment variables from the shell process.

    Usage:
        unset VAR ...

    Returns:
        int: 0 on success, 1 on invalid identifier.
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

    Returns:
        int: 0
    """
    for k, v in sorted(os.environ.items()):
        print(f"{k}={v}")
    return 0


def setup_history():
    """Load persistent command history from disk on startup with secure file permissions."""
    if readline is None:
        return
    try:
        if os.path.exists(HISTORY_FILE):
            try:
                os.chmod(HISTORY_FILE, 0o600)
            except OSError:
                pass
        readline.read_history_file(HISTORY_FILE)
    except (FileNotFoundError, OSError):
        pass

    import atexit
    def _save():
        try:
            # Set restrictive file permissions (0o600: read/write by owner only)
            if not os.path.exists(HISTORY_FILE):
                try:
                    fd = os.open(HISTORY_FILE, os.O_WRONLY | os.O_CREAT, 0o600)
                    os.close(fd)
                except OSError:
                    pass
            else:
                try:
                    os.chmod(HISTORY_FILE, 0o600)
                except OSError:
                    pass
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

    Returns:
        int: 0 on success, 1 on error.
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


def builtin_source(args):
    """
    Execute commands from a script file within the current shell environment.

    Usage:
        source script.sh
        . script.sh

    Returns:
        int: Exit status of the executed script.
    """
    if not args:
        print("myshell: source: filename argument required", file=sys.stderr)
        return 1

    filepath = os.path.expanduser(args[0])
    from shell import run_script
    return run_script(filepath, echo=True)


def builtin_pwd(args):
    """
    Print the current working directory.

    OS Concept: Retrieves the current working directory from the process control block.
    """
    try:
        print(os.getcwd())
        return 0
    except OSError as e:
        print(f"myshell: pwd: error retrieving current directory: {e}", file=sys.stderr)
        return 1


def builtin_echo(args):
    """
    Display a line of text / arguments.
    Supports -n option (do not output trailing newline).
    """
    if not args:
        print()
        return 0

    trailing_newline = True
    start_idx = 0
    while start_idx < len(args) and args[start_idx] == "-n":
        trailing_newline = False
        start_idx += 1

    output = " ".join(args[start_idx:])
    if trailing_newline:
        print(output)
    else:
        print(output, end="")
        sys.stdout.flush()
    return 0


def builtin_clear(args):
    """
    Clear the terminal screen using standard ANSI escape sequences.
    """
    # ANSI clear screen (\033[2J) and move cursor to home position (\033[H)
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()
    return 0


def builtin_type(args):
    """
    Display information about command type (builtin, alias, or executable file).
    """
    if not args:
        print("myshell: type: missing operand", file=sys.stderr)
        return 1

    status = 0
    for cmd in args:
        if cmd in BUILTINS:
            print(f"{cmd} is a shell builtin")
        else:
            search_path = os.environ.get("PATH") or os.defpath
            resolved = shutil.which(cmd, path=search_path)
            if resolved:
                print(f"{cmd} is {resolved}")
            else:
                print(f"myshell: type: {cmd}: not found", file=sys.stderr)
                status = 1
    return status


def builtin_help(args):
    """
    Display help information about MyShell and its built-in commands.

    Args:
        args (list): Unused, included for consistent function signature.

    Returns:
        int: 0
    """
    help_text = """
╔══════════════════════════════════════════════════════════════════════╗
║                         MyShell — Help                               ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Built-in Commands:                                                  ║
║    cd [dir]             Change directory (default: $HOME)            ║
║    pwd                  Print current working directory              ║
║    echo [text ...]      Display a line of text (supports -n)         ║
║    clear / cls          Clear the terminal screen                    ║
║    type <name ...>      Display command classification and path      ║
║    color [name]         Change terminal text / prompt color          ║
║    export [VAR=val]     Set environment variable(s) or list them     ║
║    unset [VAR ...]      Unset environment variable(s)                ║
║    env                  Display all environment variables            ║
║    history [-c]         Show or clear command history                ║
║    source <file> / .    Execute commands from a script file          ║
║    exit [code]          Exit the shell (default code: 0)             ║
║    help                 Display this help message                    ║
║                                                                      ║
║  Features:                                                           ║
║    command              Execute system binaries (ls, pwd, etc.)      ║
║    cmd1 | cmd2          Pipe output from cmd1 into cmd2              ║
║    command &            Run command asynchronously in background     ║
║    cmd > file           Redirect stdout (overwrite)                  ║
║    cmd >> file          Redirect stdout (append)                     ║
║    cmd < file           Redirect stdin from file                     ║
║    $VAR, $?, $$         Environment variable expansion               ║
║    *, ?                 Wildcard / glob filename expansion           ║
║                                                                      ║
║  Color Options:                                                      ║
║    color list           Show available colors and visual preview     ║
║    color <color>        Set text color (green, cyan, red, blue...)   ║
║    color prompt <color> Set prompt accent color                      ║
║    color reset          Reset terminal colors to default             ║
║                                                                      ║
║  Shortcuts:                                                          ║
║    Ctrl+C               Cancel current input (does not kill shell)   ║
║    Ctrl+D               Exit the shell cleanly                       ║
║    Tab                  Auto-complete commands and file paths        ║
║    Up / Down Arrows     Browse command history                       ║
║                                                                      ║
║  OS Concepts Demonstrated:                                           ║
║    • Process creation        — os.fork()                             ║
║    • Program execution       — os.execvp() / os.execv()              ║
║    • Process synchronization — os.waitpid()                          ║
║    • Inter-process comm.     — os.pipe() + os.dup2()                 ║
║    • Signal handling         — signal.SIGCHLD (zombie prevention)    ║
║    • Address space isolation — why cd must run in parent             ║
║    • Environment inheritance — os.environ block propagation          ║
║    • Terminal escape codes   — ANSI X3.64 / ECMA-48 escape sequences ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""
    print(help_text)
    return 0


# ─── Builtin Dispatch Table ───────────────────────────────────────────
# Maps command name (string) → handler function.
BUILTINS = {
    "cd":      builtin_cd,
    "pwd":     builtin_pwd,
    "echo":    builtin_echo,
    "clear":   builtin_clear,
    "cls":     builtin_clear,
    "type":    builtin_type,
    "color":   builtin_color,
    "colour":  builtin_color,
    "exit":    builtin_exit,
    "help":    builtin_help,
    "export":  builtin_export,
    "unset":   builtin_unset,
    "env":     builtin_env,
    "history": builtin_history,
    "source":  builtin_source,
    ".":       builtin_source,
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
