"""All user-facing text for treeignore.

Wording lives here and nowhere else, so the tone can change without touching
any logic. Rich markup is allowed in most strings. Templates use str.format
placeholders; anything coming from the user (paths, file names) is escaped by
the caller before it is formatted in.
"""

# --- startup ---
MISSING_DEPENDENCY = (
    "treeignore: missing dependency ({error}).\n"
    "this tool runs in its own venv, run `christy doctor` to sort that out."
)

# --- cli ---
CLI_DESCRIPTION = "print a folder tree, minus the noise (.gitignore aware)"
CLI_EPILOG = (
    "run it with no options and everything is asked interactively.\n"
    "the options are shortcuts for scripts: each one skips its own question."
)
CLI_HELP_PATH = "folder to show (browse for one when omitted)"
CLI_HELP_DEPTH = "how many levels deep to go (default: as deep as it goes)"
CLI_HELP_DIRS_ONLY = "folders only"
CLI_HELP_HIDDEN = "include hidden files and folders"
CLI_HELP_SIZES = "show sizes (folders show their total)"
CLI_HELP_DATES = "show last modified dates"
CLI_HELP_PERMS = "show permissions"
CLI_HELP_PATHS = "show paths relative to the folder instead of just names"
CLI_HELP_COUNTS = "show how many items are inside each folder"
CLI_HELP_SHOW_IGNORED = "mark left-out folders as [ignored] instead of hiding them"
CLI_HELP_ASCII = "draw the tree with plain ASCII characters"
CLI_HELP_LARGEST = "sort largest first"
CLI_HELP_MIXED = "mix folders and files instead of listing folders first"
CLI_HELP_EXCLUDE = "leave out this path, relative to the folder (repeatable: -x node_modules -x docs/build)"
CLI_HELP_ALL = "ignore any .gitignore and show everything"
CLI_HELP_OUTPUT = "write the tree to this file (plain text) instead of printing it"
CLI_HELP_YES = (
    "ask nothing: use the options given (or the defaults), follow a .gitignore "
    "if there is one, overwrite without asking"
)
CLI_DEPTH_INVALID = "{value!r} is not a whole number of 1 or more"

# --- header ---
HEADER_TITLE = "[bold cyan]treeIgnore[/bold cyan]"
HEADER_SUBTITLE = "[dim]see your folders, minus the noise[/dim]"

# --- generic ---
CANCELLED = "[yellow]no worries, cancelled[/yellow]"
PATH_NOT_FOUND = "[bold red]hmm, can't find that:[/bold red] {path}"
NOT_A_FOLDER = "[bold red]that's not a folder:[/bold red] {path}"
NO_BROWSER_TERMINAL = "[dim]no terminal to browse in, using the current folder[/dim]"
SCANNING = "reading the folder..."
UNREADABLE = "[yellow]couldn't read {count} folder(s), they may be missing from the tree[/yellow]"

# --- folder browser ---
BROWSE_QUESTION = "Which folder do you want to see?  ({current})"
BROWSE_EMPTY = "(no subfolders here)"
CHOICE_USE_THIS = "show this folder ({name})"
CHOICE_OPEN = "open a subfolder..."
CHOICE_UP = ".. go up one level"
CHOICE_TYPE_PATH = "type a path instead"
CHOICE_QUIT = "quit"
CHOICE_BACK = "<- back"
OPEN_QUESTION = "Open which subfolder?"
TYPE_PATH_PROMPT = "Paste or type the folder path (tab completes):"
BROWSE_PATH_MISSING = "[red]can't find:[/red] {path}"
BROWSE_PATH_NOT_FOLDER = "[red]that's a file, not a folder:[/red] {path}"
HINT_SHORTCUTS = "(arrows or the number/letter next to an item, enter to pick)"
HINT_SEARCH = "(arrows to move, or just type to filter, enter to pick)"
HINT_ARROWS = "(arrows to move, enter to pick)"

# --- .gitignore decision ---
GITIGNORE_FOUND = "This folder has a .gitignore ({rules} rules). Continue and follow it?"
GITIGNORE_OPT_FOLLOW = "Yes, follow the .gitignore"
GITIGNORE_OPT_MANUAL = "No, ignore it and let me pick what to leave out"
NO_GITIGNORE = "There's no .gitignore in this folder. What now?"
NO_GITIGNORE_OPT_ALL = "Show everything"
NO_GITIGNORE_OPT_PICK = "Let me pick which folders to leave out"
OPT_CANCEL = "Cancel"

# --- manual picker ---
PICK_QUESTION = "Which folders should be left out of the tree?"
PICK_INSTRUCTION = "(up/down to move, space to select, a = all, i = invert, enter when done)"
PICK_NOTHING = "[dim]no subfolders to pick from, so everything will be shown[/dim]"
MEASURING = "measuring folders..."

# --- depth ---
DEPTH_QUESTION = "How deep should the tree go?"
DEPTH_UNLIMITED = "As deep as it goes (unlimited)"
DEPTH_ONE = "1 level (just what's directly inside)"
DEPTH_N = "{count} levels"
DEPTH_LAST = "{count} levels (last time)"
DEPTH_CUSTOM = "Type a number..."
DEPTH_INPUT_PROMPT = "How many levels?"
DEPTH_INVALID = "enter a whole number, 1 or more"

# --- extra options ---
EXTRAS_QUESTION = "Extra options? (all optional)"
EXTRAS_INSTRUCTION = "(up/down to move, space to select, a = all, i = invert, enter when done)"
OPT_DIRS_ONLY = "Folders only"
OPT_HIDDEN = "Include hidden files"
OPT_SIZES = "Show sizes (folders show their total)"
OPT_DATES = "Show last modified date"
OPT_PERMS = "Show permissions"
OPT_PATHS = "Show paths from the folder (src/pkg/mod.py) instead of just names"
OPT_COUNTS = "Show how many items are inside each folder"
OPT_SHOW_IGNORED = "Mark left-out folders as [ignored] instead of hiding them"
OPT_ASCII = "Draw with plain ASCII lines (|-- instead of the box characters)"
OPT_LARGEST = "Sort largest first"
OPT_MIXED = "Mix folders and files (don't list folders first)"

# --- tree text ---
TAG_IGNORED = "[ignored]"
TAG_EXCLUDED = "[excluded]"
ITEM_ONE = "1 item"
ITEM_MANY = "{count} items"
SUMMARY_DIR_ONE = "1 directory"
SUMMARY_DIR_MANY = "{count} directories"
SUMMARY_FILE_ONE = "1 file"
SUMMARY_FILE_MANY = "{count} files"
SUMMARY_LEFT_OUT = "{count} left out"
SUMMARY_TOTAL_SIZE = "{size} total"
SUMMARY_DEPTH = " (depth {depth})"

# --- long output ---
LONG_QUESTION = "This tree is {lines} lines long. What now?"
LONG_OPT_SAVE = "Save it as a .txt file"
LONG_OPT_PRINT = "Print it here anyway"
LONG_OPT_DEPTH = "Pick a shallower depth"
SAVE_NAME_PROMPT = "Save as:"
SAVE_NAME_EMPTY = "give it a name"
CONFIRM_OVERWRITE = "{path} already exists. Overwrite it?"
OVERWRITE_REFUSED = (
    "[bold red]{path} already exists.[/bold red] "
    "use -y to overwrite it, or -o to pick another name."
)
OUTPUT_IS_FOLDER = "[bold red]that's a folder, not a file:[/bold red] {path}"
WRITE_FAILED = "[bold red]couldn't write the file:[/bold red] {error}"
SAVED = "[green]saved[/green] {lines} lines to {path}"
