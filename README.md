# christy

A personal CLI ecosystem: one entry point (`christy`) for all your tools.
The core is Rust. Tools can be written in anything and live in `tools/`.

```text
christy/
├── core/                 # Rust core: discovery, registry, setup flow, launcher
├── tools/                # one folder per tool
│   ├── README.md         # how to write a tool (start here)
│   ├── _template/        # copy this to start a new tool
│   └── cleanmeta/        # Python tool: wipe metadata from files
└── scripts/
    ├── setup.sh          # one-time bootstrap
    └── update.sh         # recovery update if the binary itself is broken
```

## Install

Needs `git` and a Rust toolchain (`sudo pacman -S rust` on Arch).

```bash
git clone <your-repo> christy && cd christy
bash scripts/setup.sh
```

This builds the core, links `~/.local/bin/christy`, writes
`~/.config/christy/config.toml` (so christy always knows where the repo is)
and runs `christy doctor`. Tool dependencies are **not** installed here: each
tool offers its own setup the first time you run it.

## Use

```bash
christy -h                  # commands + tools
christy list                # available tools
christy <tool> [args...]    # run a tool (args pass through untouched)
christy <tool> -h           # the tool's own help
christy help <tool>         # same as: christy <tool> --help
christy doctor              # health check of the environment and every tool
christy setup [tool]        # set up a tool, or every tool that needs it
christy update              # git pull, rescan tools, rebuild the core if it changed
```

## Adding a tool

```bash
cp -r tools/_template tools/mytool     # then set name = "mytool" in its manifest
christy mytool
```

That's all. No registration, no core changes. If the tool needs dependencies,
christy offers to run its setup script the first time (a `sudo` password
prompt works in the same terminal). The full guide, with the folder anatomy,
the manifest reference and examples for bash, python, node and compiled tools,
is in [`tools/README.md`](tools/README.md).

On another machine, or after a pull, the same applies: new or changed tools
are picked up automatically, and a changed `requirements.txt` or setup script
makes christy offer setup again.

## Where things live

| What | Where |
|------|-------|
| repo | found via `CHRISTY_HOME`, then `~/.config/christy/config.toml`, then next to the binary |
| state (registry cache, per-tool environments, setup stamps) | `~/.local/share/christy` (override: `CHRISTY_STATE_DIR`) |
| config | `~/.config/christy` (override: `CHRISTY_CONFIG_DIR`) |

## Exit codes

| Code | Meaning |
|------|---------|
| `2` | wrong usage of a built-in command |
| `126` | a tool can't run (invalid manifest, wrong platform, unmet requirements, setup declined) |
| `127` | unknown tool or command |
| `1` | a built-in command failed (setup script failed, git/cargo failed, `doctor` found a problem) |
| other | the tool's own exit code, passed through |

## Development

```bash
cd core && cargo test && cargo build --release
```
