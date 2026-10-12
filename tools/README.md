# Writing a tool

Everything in `tools/` is a tool. Adding one is only this:

```bash
cp -r tools/_template tools/mytool
# edit tools/mytool/manifest.toml: set name = "mytool", then write your tool
christy mytool
```

There is nothing to register and the core never changes. christy notices the
new folder on its next run. If the tool needs dependencies, christy offers to
install them the first time you run it.

## Anatomy of a tool folder

```text
tools/mytool/
├── manifest.toml        required  describes the tool to christy
├── run.sh               required  the entry point (any name; set via `entry`)
├── setup.sh             optional  installs what the tool needs
├── requirements.txt     optional  example of a file the setup script uses
└── ...                  anything else the tool needs (modules, assets, ...)
```

| File | Required | Purpose |
|------|----------|---------|
| `manifest.toml` | yes | Name, runtime, entry point, requirements. The only file christy reads. |
| entry file | yes | What gets launched. Its path is `entry` in the manifest. |
| setup script | no | Prepares the environment. Run by christy when something is missing. |
| everything else | no | Yours. Reach it through `$CHRISTY_TOOL_DIR`. |

Folder names matter:

- The folder name **must equal** `name` in the manifest.
- Folders starting with `_` or `.` are ignored. `_template` is one. To switch a
  tool off without deleting it, rename it to `_mytool`.
- Loose files directly inside `tools/` (like this README) are ignored.

## manifest.toml

```toml
schema = 1                       # required, manifest format version
name = "mytool"                  # required, must match the folder name
version = "0.1.0"                # optional, shown by `christy list`
description = "What it does"     # required, one line

runtime = "bash"                 # required: python | node | bash | binary
entry = "run.sh"                 # required, path inside the folder
platforms = ["linux"]            # optional, empty or missing = anywhere

[requires]                       # optional
bins = ["jq"]                    # commands that must be in PATH
paths = ["node_modules"]         # paths (relative to the folder) that must exist

[setup]                          # optional
script = "setup.sh"              # required inside [setup]
watch = ["requirements.txt"]     # files whose changes re-trigger setup
```

| Field | Rules |
|-------|-------|
| `schema` | Must be `1`. A newer schema than the installed core understands is rejected with a clear message. |
| `name` | Lowercase letters, digits, `-`, `_`; must start with a letter or digit. Can't be a built-in command (`list`, `help`, `doctor`, `setup`, `update`, `version`). |
| `runtime` | See the next section. |
| `entry` | Relative path, no `..`. Must exist, except for `binary` (it may be built by setup). |
| `platforms` | Any of `linux`, `macos`. On another OS the tool is skipped with a clear message. |
| `requires.bins` | Plain command names, looked up in PATH. |
| `requires.paths` | Relative paths that must exist (a built artifact, `node_modules`, ...). |
| `setup.script` | Relative path to the setup script. Must exist. |
| `setup.watch` | Relative paths of existing files. The setup script itself is always watched. |

Unknown fields are errors, so a typo like `[requries]` shows up in
`christy doctor` instead of being silently ignored.

## Runtimes

`runtime` says how christy launches `entry`. A tool in Rust, Go or anything
compiled is just `binary`.

| runtime | What christy runs | Implicit requirement |
|---------|-------------------|----------------------|
| `python` | `<state>/envs/<name>/bin/python <entry> args...` (the tool's **own venv**, never the system python) | the venv must exist |
| `node` | `node <entry> args...` | `node` in PATH |
| `bash` | `bash <entry> args...` (no executable bit needed) | `bash` in PATH |
| `binary` | `<entry> args...` | the file must exist and be executable |

## What happens when you run a tool

```text
christy mytool args...
   │
   ├─ find it in the registry (cached, rescanned automatically when tools/ changes)
   ├─ platform supported?        no  → error, nothing is offered
   ├─ requirements met?          (runtime needs + requires.bins + requires.paths
   │                              + "setup files changed since last setup")
   │     no → "mytool needs a few things... Run its setup script now? [Y/n]"
   │            yes → runs the setup script, then checks again
   └─ exec: the tool replaces christy (same terminal, signals and exit code)
```

Without a terminal (cron, a pipe) christy never prompts. It prints what's
missing and tells you to run `christy setup mytool`.

## The setup script

Declared in `[setup]`. christy runs it as `bash setup.sh` (for a `.sh` file) with:

- the terminal attached, so `sudo` and package manager prompts work normally
- the working directory set to the tool folder
- these environment variables:

| Variable | Value |
|----------|-------|
| `CHRISTY_HOME` | repo root |
| `CHRISTY_TOOL_DIR` | this tool's folder |
| `CHRISTY_STATE_DIR` | christy's state folder (default `~/.local/share/christy`) |
| `CHRISTY_VERSION` | christy version |

Rules for a good setup script:

1. **Idempotent.** Running it twice must be safe. christy runs it again when
   `requirements.txt` or the script itself changes.
2. **Exit non-zero on failure.** That's how christy knows it failed.
3. **Use the variables**, not guessed paths.
4. **Install only what this tool needs.** Nothing global the tool doesn't use.
5. **Put per-tool environments under `$CHRISTY_STATE_DIR/envs/<name>/`.** For
   python tools that's required: christy looks for
   `$CHRISTY_STATE_DIR/envs/<name>/bin/python`.

After a successful run christy remembers the state of the script and the
`watch` files. If a `git pull` changes one of them, the next run offers setup
again. A tool christy never set up (done by hand) is never nagged about this.

You can also run it yourself: `christy setup mytool` (always runs the script),
or `christy setup` (every tool that currently needs it).

## What a tool must do

- **Answer `--help`.** `christy help mytool` is shorthand for `christy mytool --help`.
- **Take arguments as given.** christy passes them through untouched, flags included.
- **Work relative to the current directory.** christy doesn't change it, so
  `christy mytool photos/` means the user's `photos/`. Find your own files with
  `$CHRISTY_TOOL_DIR`.
- **Return a proper exit code.** `0` for success. It reaches the shell as is.
  Avoid `2`, `126` and `127` for your own errors, since christy uses those.
- **Talk to the terminal normally.** Prompts, colors and progress bars all work
  because the tool owns the terminal.
- **Keep stdout for output.** Send messages and errors to stderr so
  `christy mytool | other` stays clean.

## Examples

### Bash

```toml
schema = 1
name = "hello"
description = "Say hello"
runtime = "bash"
entry = "run.sh"
```

Just `manifest.toml` and `run.sh`. No setup needed.

### Python (own venv)

```text
tools/pytool/
├── manifest.toml
├── main.py
├── requirements.txt
└── setup.sh
```

```toml
schema = 1
name = "pytool"
description = "A python tool"
runtime = "python"
entry = "main.py"

[requires]
bins = ["python3"]

[setup]
script = "setup.sh"
watch = ["requirements.txt"]
```

```bash
#!/usr/bin/env bash
set -euo pipefail
VENV="$CHRISTY_STATE_DIR/envs/pytool"
python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install -q -r "$CHRISTY_TOOL_DIR/requirements.txt"
```

`tools/cleanmeta` is a complete real example of this shape.

### System dependency (installed on first use)

```toml
[requires]
bins = ["ffmpeg"]

[setup]
script = "setup.sh"
```

```bash
#!/usr/bin/env bash
set -euo pipefail
command -v ffmpeg >/dev/null || sudo pacman -S --needed ffmpeg
```

Run the tool and, if `ffmpeg` is missing, christy asks, runs the script, and
`sudo` prompts for the password in the same terminal.

### Rust or Go (binary)

```toml
schema = 1
name = "fast"
description = "A compiled tool"
runtime = "binary"
entry = "target/release/fast"

[setup]
script = "setup.sh"
watch = ["Cargo.toml"]
```

```bash
#!/usr/bin/env bash
set -euo pipefail
cargo build --release --manifest-path "$CHRISTY_TOOL_DIR/Cargo.toml"
```

`entry` doesn't have to exist beforehand for a `binary` tool. christy sees it
missing and offers setup, which builds it. For Go, build with
`go build -o bin/fast` and set `entry = "bin/fast"`.

### Node

```toml
schema = 1
name = "nodetool"
description = "A node tool"
runtime = "node"
entry = "index.js"

[requires]
bins = ["node", "npm"]
paths = ["node_modules"]

[setup]
script = "setup.sh"
watch = ["package-lock.json"]
```

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$CHRISTY_TOOL_DIR" && npm ci
```

`requires.paths` is what makes christy notice a missing `node_modules`.

## Checking your work

```bash
christy doctor       # every tool: ready / needs setup / invalid / skipped
christy list         # tools christy can run
```

Typical problems `doctor` reports for a tool:

| Message | Fix |
|---------|-----|
| `name 'x' doesn't match its folder name 'y'` | Make `name` equal the folder name. |
| `entry file 'x' doesn't exist` | Fix `entry`, or create the file. |
| `manifest.toml not found` | The folder has no manifest. Add one, or rename the folder to start with `_`. |
| `name 'x' is reserved for a built-in command` | Pick another name. |
| `manifest.toml has an invalid field: unknown field ...` | A typo or an unsupported field. |
| `watched file 'x' (setup.watch) doesn't exist` | Create the file or remove it from `watch`. |

Everything under `.git` is yours to commit. Build output like `target/`,
`node_modules/` and `__pycache__/` is not (see the repo `.gitignore`).
