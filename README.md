# 🐚 MyShell v2.0 — A Custom Unix Shell

A custom command-line interface built from scratch in **Python 3**. MyShell interfaces directly with the Linux kernel through low-level POSIX system calls to recreate and demonstrate core and advanced operating system concepts.

---

## 🚀 How to Run

### Interactive REPL Mode
```bash
# Navigate to the project directory
cd myshell/

# Run the shell
python3 shell.py
```

You'll see the colorized MyShell welcome banner and prompt:

```text
user@myshell:myshell$ 
```

Type `help` for a list of available commands and OS concepts.

### Batch Script Mode
Execute commands from a script file directly:
```bash
python3 shell.py script.sh
```

---

## ✨ Features & Commands

### 1. Basic Command Execution
Execute any system utility or external program directly via `fork()` + `execv()`:
```bash
user@myshell:~$ ls -la
user@myshell:~$ pwd
user@myshell:~$ echo "Hello from MyShell"
user@myshell:~$ date
user@myshell:~$ whoami
```

Direct and relative executable paths are supported with full validation:
```bash
user@myshell:~$ /bin/uname -a
user@myshell:~$ ./my_script.sh
```

---

### 2. Built-in Commands
Commands that alter the parent shell process or provide shell-internal utilities:

| Command | Arguments | Description | Example |
|---|---|---|---|
| `cd` | `[directory]` | Change working directory (defaults to `$HOME`) | `cd /tmp`, `cd ~`, `cd ..` |
| `pwd` | — | Print the current working directory | `pwd` |
| `echo` | `[-n] [text ...]` | Display text to stdout (supports `-n` without newline) | `echo "Hello"`, `echo -n "user: "` |
| `clear` / `cls` | — | Clear terminal screen using ANSI escape sequences | `clear`, `cls` |
| `type` | `<name ...>` | Display command classification and resolved binary path | `type cd`, `type ls`, `type pwd` |
| `color` / `colour` | `[name \| list \| prompt \| reset]` | Customize shell text and prompt colors | `color green`, `color list` |
| `export` | `[VAR=val ...]` | Set process environment variable(s) or list them | `export FOO="bar"`, `export` |
| `unset` | `[VAR ...]` | Remove variable(s) from shell environment | `unset FOO` |
| `env` | — | Display all exported environment variables | `env` |
| `history` | `[-c]` | Display numbered command history or clear it | `history`, `history -c` |
| `source` / `.` | `<script_file>` | Execute commands from a file in current shell | `source script.sh`, `. test.sh` |
| `exit` | `[code]` | Exit the shell cleanly with optional status code | `exit`, `exit 0`, `exit 1` |
| `help` | — | Display built-in command list and OS concepts | `help` |

#### Detailed Color Customization (`color` / `colour`):
MyShell features full ANSI escape sequence color customization for the terminal:
```bash
user@myshell:~$ color list            # Display visual palette with live samples
user@myshell:~$ color green           # Change terminal text color to green
user@myshell:~$ colour cyan           # Change terminal text color to cyan
user@myshell:~$ color prompt yellow   # Change prompt accent color to yellow
user@myshell:~$ color reset           # Reset text and prompt to terminal defaults
user@myshell:~$ color                 # Show current color settings
```
Supported colors: `green`, `cyan`, `blue`, `yellow`, `red`, `magenta` (or `purple`), `white`, `black`, `reset`.

---

### 3. I/O Redirection (`>`, `>>`, `<`)
Redirect file descriptors using `os.open()`, `os.dup2()`, and `os.close()`:
```bash
user@myshell:~$ ls -la > files.txt           # Redirect stdout to file (overwrite)
user@myshell:~$ echo "new log entry" >> log   # Redirect stdout to file (append)
user@myshell:~$ sort < unsorted.txt          # Redirect file into stdin
user@myshell:~$ cat < in.txt > out.txt       # Combined input and output redirection
```

---

### 4. Environment Variables (`$VAR`, `$?`, `$$`)
Process environment management and variable expansion:
```bash
user@myshell:~$ export PROJECT="MyShell v2"
user@myshell:~$ echo "Running $PROJECT on user: $USER"
user@myshell:~$ echo "Previous exit code: $? (Current PID: $$)"
```

---

### 5. Logical Operators (`&&`, `||`)
Conditional execution based on exit status codes:
```bash
user@myshell:~$ mkdir test_dir && cd test_dir     # cd runs only if mkdir succeeds
user@myshell:~$ cat missing.txt || echo "fail"    # echo runs only if cat fails
user@myshell:~$ true && echo "yes" || echo "no"   # Conditional chaining
```

---

### 6. Wildcard / Glob Expansion (`*`, `?`)
Pattern matching against directory entries using `glob.glob()`:
```bash
user@myshell:~$ ls *.py                           # Expands to all Python files
user@myshell:~$ cat test_?.txt                    # Expands single-character patterns
```

---

### 7. Command Chaining with Pipes (`|`)
Connect multiple commands via unidirectional IPC pipes (`os.pipe()`) and `os.dup2()`:
```bash
user@myshell:~$ ls -l | grep ".py"
user@myshell:~$ cat /etc/passwd | grep root | wc -l
user@myshell:~$ ls -la /etc | head -5
user@myshell:~$ help | grep cd                   # Builtins work inside pipelines!
```

---

### 8. Background Process Execution (`&`)
Run programs asynchronously without blocking the parent shell. Background jobs are reaped non-blocking via `os.waitpid(-1, os.WNOHANG)`:
```bash
user@myshell:~$ sleep 10 &
[bg] started process 12345
user@myshell:~$                                  # Prompt returns immediately!
```

---

### 9. Quoted Strings & Syntax Handling
Input is safely parsed using `shlex.split()` to preserve quotes, nested quotes, and escape sequences:
```bash
user@myshell:~$ echo "Hello World"
user@myshell:~$ echo 'Single quoted string'
user@myshell:~$ echo "It's working"
```

---

## 🏗️ Architecture

```text
myshell/
│
├── shell.py          # REPL loop, banner, batch execution, and execution dispatch
├── parser.py         # Lexical tokenization (shlex), logical operators (&&, ||), pipes
├── builtin_cmds.py   # Builtins: cd, pwd, echo, clear, type, color, export, unset, env, history, source, exit, help
├── colors.py         # ANSI color codes, dynamic text coloring, palette, styled prompt
├── executor.py       # Single-command execution (fork + execv + waitpid + path validation)
├── pipes.py          # Multi-stage pipeline execution (pipe + dup2 + fork + subshell builtins)
├── redirects.py      # I/O redirection parsing and file descriptor duplication
├── variables.py      # Environment variable and special parameter expansion ($VAR, $?, $$)
├── globbing.py       # Wildcard and pattern expansion (*, ?)
├── completion.py     # GNU Readline autocompletion for binaries and file paths
│
├── test_commands.txt # Comprehensive test script for lab verification
├── requirements.txt  # Python environment notes (100% standard library)
└── README.md         # Project documentation
```

---

## 🔬 OS Concepts Demonstrated

| Feature | OS Concept | System Call / Mechanism |
|---|---|---|
| Running external commands | Process Creation | `os.fork()` |
| Executing programs | Process Image Replacement | `os.execv()` + `shutil.which()` |
| Foreground synchronization | Process Synchronization | `os.waitpid()` |
| Directory navigation | Address Space Isolation | `os.chdir()` (must run in parent) |
| Pipeline chaining (`\|`) | Inter-Process Communication | `os.pipe()` / `os.pipe2(O_CLOEXEC)` + `os.dup2()` |
| I/O Redirection (`>`, `<`, `>>`) | File Descriptor Manipulation | `os.open()` + `os.dup2()` + `os.close()` |
| Environment variables | Process Environment Block | `os.environ` inheritance |
| Background execution (`&`) | Asynchronous Execution | Non-blocking reaping via `os.waitpid(-1, os.WNOHANG)` |
| Exit code inspection (`$?`) | Process Termination Status | `os.WEXITSTATUS()` / `os.WIFEXITED()` |
| Logical operators (`&&`, `\|\|`) | Exit Status Branching | Short-circuit evaluation based on exit codes |
| Terminal text & prompt colors | Terminal Escape Sequences | ANSI X3.64 / ECMA-48 escape codes |
| Prompt line editing & history | Readline Delimiters | `\001` and `\002` markers + `readline` library |
| Safe input tokenization | Shell Lexical Analysis | `shlex.split()` with quote & escape handling |

---

## 🛡️ Error Handling & Defensive Hardening

| Scenario | Shell Behavior |
|---|---|
| Empty input (pressing Enter) | Silently prompts again without error |
| Unknown command | Prints `myshell: command not found: <cmd>`, returns exit code 127 |
| Unset / empty `$PATH` | Falls back safely to standard system path (`/bin:/usr/bin`) via `os.defpath` |
| Destructive file removal (`rm -rf /`, `/etc`, etc.) | Intercepted and blocked before execution, protecting core system directories |
| Destructive redirection overwrite (`> /etc/passwd`) | Intercepted and blocked before opening, safeguarding sensitive system files |
| Recursive script sourcing loop (`source a.sh` -> `b.sh` -> `a.sh`) | Cycle and call-stack depth detected (`MAX_SOURCE_DEPTH = 16`); aborts safely |
| Command history file privacy | Sets restrictive user-only permissions (`0o600`) on `~/.myshell_history` |
| Directory executed as command | Prints `myshell: <path>: Is a directory`, returns exit code 126 |
| File without execute permissions | Prints `myshell: permission denied: <path>`, returns exit code 126 |
| Nonexistent path execution | Prints `myshell: <path>: No such file or directory`, returns exit code 127 |
| Invalid directory for `cd` | Prints descriptive OS error without crashing parent shell |
| Too many arguments for `cd` / `exit` | Warns user on `stderr` and prevents invalid execution |
| Unmatched quotes / syntax error | Prints syntax error, continues cleanly |
| Embedded null byte (`\0`) | Caught by parser guard before execution, preventing Python crashes |
| Broken / detached terminal | Catches `OSError` on `input()` and exits cleanly |
| Ctrl+C (`SIGINT`) | Cancels current line input and restores terminal colors; doesn't kill shell |
| Ctrl+D (`EOF`) | Restores terminal colors, prints goodbye, and exits cleanly (code 0) |
| Pipeline depth limit | Enforces `MAX_PIPELINE_DEPTH = 32` to prevent fork-bomb style DoS |
| Child process error stream | Error messages correctly routed to `sys.stderr` |

---

## 🧰 Technology Stack

- **Language:** Python 3.8+ (tested on Python 3.12)
- **Target OS:** POSIX-compatible system (Linux / macOS / WSL)
- **External Dependencies:** **None** — built entirely using Python's standard library (`os`, `sys`, `shlex`, `signal`, `shutil`, `readline`, `glob`, `atexit`, `re`).

---

## 📝 Testing

A complete test script is provided in `test_commands.txt`. Run MyShell and execute the commands step-by-step:

```bash
python3 shell.py
# Paste or type commands from test_commands.txt
```
