# 🐚 MyShell v2.0 — A Custom Unix Shell

A custom command-line interface built from scratch in **Python 3**. MyShell interfaces directly with the Linux kernel through low-level system calls to demonstrate core and advanced operating system concepts.

---

## 🚀 How to Run

### Interactive Mode (REPL)
```bash
# Navigate to the project directory
cd myshell/

# Run the shell
python3 shell.py
```

You'll see the colorized MyShell prompt:
```
user@myshell:myshell$ 
```

Type `help` for a list of available builtins and OS concepts.

### Batch Script Mode
```bash
# Run a script file directly
python3 shell.py script.sh
```

---

## ✨ Features (v2.0)

### 1. Basic Command Execution
```bash
user@myshell:~$ ls -la
user@myshell:~$ pwd
user@myshell:~$ echo "Hello from MyShell"
user@myshell:~$ date
user@myshell:~$ whoami
```

### 2. Built-in Commands
```bash
user@myshell:~$ cd /tmp              # Change directory
user@myshell:tmp$ cd ~               # Go to home directory
user@myshell:~$ help                 # Show help and OS concepts
user@myshell:~$ history              # List past executed commands
user@myshell:~$ source script.sh     # Execute script in current session
user@myshell:~$ exit                 # Exit the shell cleanly
```

### 3. I/O Redirection (`>`, `>>`, `<`)
```bash
user@myshell:~$ ls -la > files.txt           # Overwrite stdout to file
user@myshell:~$ echo "new log entry" >> log   # Append stdout to file
user@myshell:~$ sort < unsorted.txt          # Redirect file into stdin
user@myshell:~$ cat < in.txt > out.txt       # Combined input and output redirection
```

### 4. Environment Variables (`$VAR`, `export`, `unset`, `env`)
```bash
user@myshell:~$ export PROJECT_NAME="MyShell v2"
user@myshell:~$ echo "Running $PROJECT_NAME on $USER"
user@myshell:~$ echo "Previous exit code: $? (PID: $$)"
user@myshell:~$ env
user@myshell:~$ unset PROJECT_NAME
```

### 5. Logical Operators (`&&`, `||`)
```bash
user@myshell:~$ mkdir test_dir && cd test_dir     # cd runs only if mkdir succeeds
user@myshell:~$ cat missing.txt || echo "fail"    # echo runs only if cat fails
user@myshell:~$ true && echo "yes" || echo "no"   # Conditional chaining
```

### 6. Wildcard / Glob Expansion (`*`, `?`)
```bash
user@myshell:~$ ls *.py                           # Expands to all Python files
user@myshell:~$ cat test_?.txt                    # Expands single-character patterns
```

### 7. Command Chaining with Pipes (`|`)
```bash
user@myshell:~$ ls -l | grep ".py"
user@myshell:~$ cat /etc/passwd | grep root | wc -l
user@myshell:~$ ls -la /etc | head -5
```

### 8. Background Process Execution (`&`)
```bash
user@myshell:~$ sleep 10 &
[bg] started process 12345
user@myshell:~$                                  # Prompt returns immediately!
```

### 9. Usability Polish
- **Tab Completion:** Auto-completes executables in PATH, builtins, and filesystem paths.
- **Persistent Command History:** Saved across sessions in `~/.myshell_history` using `readline`.
- **ANSI Colorized Interface:** Colorized prompt (`user@myshell:dir$`), banner, background notifications, and error reporting.

---

## 🏗️ Architecture

```text
myshell/
│
├── shell.py          # Main REPL, batch mode, signal setup, dispatch loop
├── parser.py         # Tokenization (shlex), conditional (&&, ||) and pipe splitting
├── builtin_cmds.py   # Built-in commands: cd, exit, help, export, unset, env, history, source
├── executor.py       # Single command execution (fork + execv + waitpid, exit codes)
├── pipes.py          # Multi-stage pipeline execution (pipe + dup2 + fork)
├── redirects.py      # I/O redirection parser and file descriptor setup (open + dup2)
├── variables.py      # Environment variable expansion ($VAR, $?, $$)
├── colors.py         # ANSI color palette and prompt formatting
├── completion.py     # Tab completion logic (readline + glob)
├── globbing.py       # Wildcard / glob expansion (*, ?)
│
├── test_commands.txt # Comprehensive test script for all v2.0 features
├── requirements.txt  # System dependencies (Python standard library only)
└── README.md         # Documentation
```

---

## 🔬 OS Concepts Demonstrated

| Feature | OS Concept | System Call / Library |
|---|---|---|
| Running external commands | Process Creation | `os.fork()` |
| Executing programs | Process Image Replacement | `os.execv()` / `shutil.which()` |
| Process synchronization | Parent-Child Coordination | `os.waitpid()` |
| Output redirection (`>`, `>>`) | File-level fd redirection | `os.open()` + `os.dup2()` |
| Input redirection (`<`) | File-level stdin redirection | `os.open()` + `os.dup2()` |
| Command piping (`\|`) | Inter-Process Communication | `os.pipe()` + `os.dup2()` |
| Environment variables | Process environment inheritance | `os.environ` |
| Logical operators (`&&`, `\|\|`) | Exit status evaluation | `os.WIFEXITED()` / `os.WEXITSTATUS()` |
| Wildcard expansion | Shell-side pattern matching | `glob.glob()` |
| Background execution (`&`) | Asynchronous Processes | Fork without parent wait |
| Zombie prevention | Signal Handling | `signal.SIGCHLD` → `SIG_IGN` |
| Command history | Terminal line editing | `readline` + `atexit` |
| Tab completion | Terminal raw I/O control | `readline` completer |
| Colored prompt | Terminal escape sequences | ANSI codes |
| Batch execution | Batch processing | File I/O + REPL dispatch |

---

## 🛡️ Error Handling

| Scenario | Behavior |
|---|---|
| Empty input (just Enter) | Silently continues to next prompt |
| Unknown command | Prints "command not found", returns exit code 127 |
| Permission denied binary | Prints "permission denied", returns exit code 126 |
| Invalid directory for `cd` | Prints error, returns exit code 1 |
| Unmatched quotes | Prints syntax error, continues |
| Nonexistent file for `<` | Prints "No such file or directory", fails gracefully |
| Ctrl+C | Cancels current input, preserves shell |
| Ctrl+D | Exits the shell cleanly |
| Background process ends | Automatically reaped by kernel (no zombies) |

---

## 🧰 Technology Stack

- **Language:** Python 3.8+ (tested on Python 3.12)
- **OS:** Linux (POSIX system calls required)
- **Dependencies:** **100% Python Standard Library** (`os`, `sys`, `shlex`, `signal`, `shutil`, `readline`, `glob`, `atexit`, `re`)

---

## 📝 Testing

Run the test suite in `test_commands.txt`:

```bash
cd myshell
python3 shell.py
# Follow the test cases in test_commands.txt
```
