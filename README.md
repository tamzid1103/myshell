# 🐚 MyShell — A Custom Unix Shell

A custom command-line interface built from scratch in **Python 3**, developed as an **Operating System Lab** course project. MyShell interfaces directly with the Linux kernel through low-level system calls to demonstrate core operating system concepts.

---

## 📋 Project Description

> **OS Lab Project 11:** *Develop a Shell or Command Line Interface — Develop a basic command-line interface using C or Python. Implement commands like listing files, navigating directories, and handling simple processes. Add support for command chaining (using pipes) and background process handling.*

MyShell fulfills all project requirements while demonstrating clean, modular architecture and comprehensive error handling.

---

## 🚀 How to Run

```bash
# Navigate to the project directory
cd myshell/

# Run the shell
python3 shell.py
```

You'll see the MyShell prompt:

```
myshell [myshell]>
```

Type `help` for a list of available commands.

---

## ✨ Features

### Basic Command Execution
```
myshell [~]> ls -la
myshell [~]> pwd
myshell [~]> echo "Hello from MyShell"
myshell [~]> date
myshell [~]> whoami
```

### Built-in Commands
```
myshell [~]> cd /tmp          # Change directory
myshell [tmp]> cd ~           # Go to home directory
myshell [~]> help             # Show help and OS concepts
myshell [~]> exit             # Exit the shell
```

### Command Chaining with Pipes (`|`)
```
myshell [~]> ls -l | grep ".py"
myshell [~]> cat /etc/passwd | grep root | wc -l
myshell [~]> ls -la /etc | head -5
```

### Background Process Execution (`&`)
```
myshell [~]> sleep 10 &
[bg] started process 12345
myshell [~]>                  # Prompt returns immediately!
```

---

## 🏗️ Architecture

```
myshell/
│
├── shell.py          # Main REPL loop, signal setup, command dispatch
├── parser.py         # Input tokenization (shlex), operator detection
├── builtins.py       # Built-in commands: cd, exit, help
├── executor.py       # Process creation (fork + execvp + waitpid)
├── pipes.py          # Pipeline execution (pipe + dup2 + fork)
│
├── test_commands.txt # Test script with expected behaviors
└── README.md         # This file
```

### Shell Workflow

```
[Start] ──→ Print Prompt ──→ Read Input ──→ Parse (shlex.split)
                                                    │
                                                    ▼
                                         ┌──── Is Builtin? ────┐
                                         │                      │
                                        YES                    NO
                                         │                      │
                                   Run in Parent          Contains '|'?
                                         │               /          \
                                         │             YES          NO
                                         │              │            │
                                         │        Setup Pipes   os.fork()
                                         │        Fork Children      │
                                         │        Route fds     Background?
                                         │              │        /       \
                                         │              │      YES       NO
                                         │              │       │         │
                                         │              │  Print PID  waitpid()
                                         │              │       │         │
                                         └──────────────┴───────┴─────────┘
                                                        │
                                                        ▼
                                                  [Loop Restart]
```

---

## 🔬 OS Concepts Demonstrated

| Feature | OS Concept | System Call |
|---|---|---|
| Running external commands | Process Creation | `os.fork()` |
| Executing programs | Process Image Replacement | `os.execvp()` |
| Waiting for commands | Process Synchronization | `os.waitpid()` |
| `cd` as a builtin | Address Space Isolation | `os.chdir()` |
| Command piping (`\|`) | Inter-Process Communication | `os.pipe()` + `os.dup2()` |
| Background execution (`&`) | Asynchronous Processes | Fork without `waitpid()` |
| Zombie prevention | Signal Handling | `signal.SIGCHLD` → `SIG_IGN` |
| Input parsing | Shell Tokenization | `shlex.split()` |

---

## 🛡️ Error Handling

| Scenario | Behavior |
|---|---|
| Empty input (just Enter) | Silently continues to next prompt |
| Unknown command | Prints "command not found", continues |
| Invalid directory for `cd` | Prints error, continues |
| Unmatched quotes | Prints syntax error, continues |
| Ctrl+C | Cancels current input, shows new prompt |
| Ctrl+D | Exits the shell cleanly |
| Background process ends | Automatically reaped (no zombies) |
| Pipe with invalid command | Reports error for the specific failed command |

---

## 🧰 Technology Stack

- **Language:** Python 3.12+
- **OS:** Linux (required for `os.fork()` and POSIX system calls)
- **Dependencies:** None — 100% Python standard library (`os`, `sys`, `shlex`, `signal`)

---

## 📝 Testing

A comprehensive test script is provided in `test_commands.txt`. Run MyShell and execute the commands listed there to verify all features:

```bash
python3 shell.py
# Then follow the test cases in test_commands.txt
```

---

*Developed as part of the Operating System Lab course — Project 11.*