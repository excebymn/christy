"""All user-facing text for zipignore.

Wording lives here and nowhere else, so the tone can change without touching
any logic. Rich markup is allowed in most strings. Templates use str.format
placeholders; anything coming from the user (paths, file names) is escaped by
the caller before it is formatted in.
"""

# --- startup ---
MISSING_DEPENDENCY = (
    "zipignore: missing dependency ({error}).\n"
    "this tool runs in its own venv, run `christy doctor` to sort that out."
)

# --- cli ---
CLI_DESCRIPTION = "zip a folder while respecting its .gitignore"
CLI_EPILOG = (
    "with no path you get a folder browser. if the folder has no .gitignore\n"
    "you can zip everything or pick which folders to leave out."
)
CLI_HELP_PATH = "folder to zip (browse for one when omitted)"
CLI_HELP_OUTPUT = "where to write the zip (default: <folder name>.zip in the current directory)"
CLI_HELP_EXCLUDE = "leave out this path, relative to the folder (repeatable: -x node_modules -x docs/build)"
CLI_HELP_ALL = "zip everything and ignore any .gitignore"
CLI_HELP_FLAT = "put the contents at the root of the zip instead of inside a folder named after the source"
CLI_HELP_DRY_RUN = "only show what would be zipped (file list goes to stdout), write nothing"
CLI_HELP_YES = "skip all confirmations, including overwriting an existing zip"

# --- header ---
HEADER_TITLE = "[bold cyan]zipIgnore[/bold cyan]"
HEADER_SUBTITLE = "[dim]zip it up, minus the junk[/dim]"

# --- generic ---
CANCELLED = "[yellow]no worries, cancelled[/yellow]"
PATH_NOT_FOUND = "[bold red]hmm, can't find that:[/bold red] {path}"
NOT_A_FOLDER = "[bold red]that's not a folder:[/bold red] {path}"
NEEDS_TERMINAL = (
    "[bold red]there's no .gitignore here and no terminal to ask you in.[/bold red]\n"
    "pass --all to zip everything, or -x NAME to leave something out."
)
WRITE_FAILED = "[bold red]couldn't write the zip:[/bold red] {error}"
NO_BROWSER_TERMINAL = "[dim]no terminal to browse in, using the current folder[/dim]"

# --- folder browser ---
BROWSE_QUESTION = "Which folder do you want to zip?  ({current})"
BROWSE_EMPTY = "(no subfolders here)"
CHOICE_USE_THIS = "zip this folder ({name})"
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

# --- .gitignore decision ---
GITIGNORE_FOUND = "This folder has a .gitignore ({rules} rules). Continue and follow it?"
GITIGNORE_OPT_FOLLOW = "Yes, follow the .gitignore"
GITIGNORE_OPT_MANUAL = "No, ignore it and let me pick what to leave out"
NO_GITIGNORE = "There's no .gitignore in this folder. What now?"
NO_GITIGNORE_OPT_ALL = "Zip the whole folder"
NO_GITIGNORE_OPT_PICK = "Let me pick which folders to leave out"
OPT_CANCEL = "Cancel"

# --- manual picker ---
PICK_QUESTION = "Which folders should be left out of the zip?"
PICK_INSTRUCTION = "(up/down to move, space to select, a = all, i = invert, enter when done)"
PICK_NOTHING = "[dim]no subfolders to pick from, so everything will be zipped[/dim]"
MEASURING = "measuring folders..."

# --- secrets warning ---
SENSITIVE_WARNING = (
    "\n[bold yellow]heads up:[/bold yellow] these look like secrets, "
    "and nothing is keeping them out of the zip:"
)
SENSITIVE_MORE = "  [dim]...and {count} more[/dim]"
SENSITIVE_QUESTION = "What should I do with them?"
SENSITIVE_OPT_KEEP = "Zip them anyway"
SENSITIVE_OPT_LEAVE = "Leave those files out"

# --- scan / preview ---
SCANNING = "looking through the folder..."
NOTHING_TO_ZIP = "[yellow]nothing left to zip after the exclusions[/yellow]"
UNREADABLE = "[yellow]couldn't read {count} folder(s), they're not in the zip[/yellow]"
PREVIEW_TITLE = "ready to zip"
ROW_SOURCE = "Source"
ROW_RULES = "Rules"
ROW_FILES = "Files"
ROW_SIZE = "Size"
ROW_OUTPUT = "Output"
RULES_GITIGNORE = "following .gitignore ({count} file(s))"
RULES_PICK = "your picks"
RULES_ALL = "everything"
RULES_EXTRA = " + {count} extra exclusion(s)"
LEFT_OUT_TITLE = "left out"
COL_ITEM = "Item"
COL_WHY = "Why"
REASON_GITIGNORE_LABEL = "[yellow].gitignore[/yellow]"
REASON_PICKED_LABEL = "[cyan]your pick[/cyan]"
REASON_BUILTIN_LABEL = "[dim]always skipped[/dim]"
REASON_SYMLINK_LABEL = "[dim]symlink[/dim]"
LEFT_OUT_MORE = "[dim]...and {count} more kind(s) of item[/dim]"
GROUP_COUNT = "{name} x{count}"

# --- confirmations ---
CONFIRM_ZIP = "Create the zip now?"
CONFIRM_OVERWRITE = "{path} already exists. Overwrite it?"
OVERWRITE_REFUSED = (
    "[bold red]{path} already exists.[/bold red] "
    "use -y to overwrite it, or -o to pick another name."
)
OUTPUT_IS_FOLDER = "[bold red]the output path is a folder:[/bold red] {path}"

# --- progress / summary ---
PROGRESS_LABEL = "Zipping"
SUMMARY_TITLE = "all zipped up"
ROW_ZIPPED = "Files zipped"
ROW_ORIGINAL = "Original size"
ROW_ZIP_SIZE = "Zip size"
ROW_SAVED = "Saved"
SAVED_VALUE = "{percent}%"
TOTAL_LINE = (
    "\n[bold]total:[/bold] {total}  "
    "[green]zipped: {zipped}[/green]  "
    "[red]errors: {errors}[/red]"
)
ERRORS_TITLE = "couldn't add these"
COL_FILE = "File"
COL_PROBLEM = "Problem"
ERRORS_MORE = "[dim]...and {count} more[/dim]"
ZIP_LOCATION = "[dim]your zip is here: {path}[/dim]"
NO_ZIP_WRITTEN = "[red]no zip was written[/red]"
