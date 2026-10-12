"""All user-facing text for cleanmeta.

Wording lives here and nowhere else, so the tone can change without touching
any logic. Rich markup is allowed. Templates use str.format placeholders.
"""

# --- startup ---
MISSING_DEPENDENCY = (
    "cleanmeta: missing dependency ({error}).\n"
    "this tool runs in its own venv, run `christy doctor` to sort that out."
)

# --- cli ---
CLI_DESCRIPTION = "wipe metadata from files in a directory"
CLI_HELP_PATH = "directory or file to clean"
CLI_HELP_YES = "skip the overwrite confirmation"

# --- header ---
HEADER_TITLE = "[bold cyan]Metadata Cleaner[/bold cyan]"
HEADER_SUBTITLE = "[dim]let's scrub some hidden metadata[/dim]"

# --- generic ---
CANCELLED = "[yellow]no worries, cancelled[/yellow]"
PATH_NOT_FOUND = "[bold red]hmm, can't find that:[/bold red] {path}"

# --- directory browser ---
BROWSE_EMPTY = "[dim](empty, or can't read it)[/dim]"
BROWSE_MORE = "  [dim]...and {count} more, not shown[/dim]"
BROWSE_HINT = (
    "\n[dim]type a number to open it  ·  'u' = use this folder  ·  "
    "'..' = go up  ·  'p' = type a path instead  ·  'q' = quit[/dim]"
)
BROWSE_PROMPT = "go where"
BROWSE_TYPE_PATH_PROMPT = "paste/type the path"
BROWSE_PATH_MISSING = "[red]can't find:[/red] {path}"
BROWSE_BAD_CHOICE = "[red]didn't get that, try again[/red]"

# --- type selection ---
TYPES_TITLE = "\n[bold]what do you want cleaned?[/bold]"
TYPES_OPTIONS = (
    "just images",
    "just documents",
    "just code files",
    "everything",
)
PICK_ONE = "pick one"

# --- mode selection ---
MODE_TITLE = "\n[bold]how should I save the results?[/bold]"
MODE_OPTIONS = (
    "overwrite the originals",
    "put clean copies in a new 'metadata_cleaned' folder",
)
CONFIRM_OVERWRITE = "[bold red]this'll overwrite the originals, you sure?[/bold red]"

# --- run info ---
LOOKING_IN = "\n[bold]looking in:[/bold] {target}"
TYPES_LABEL = "[bold]types:[/bold] {types}"
MODE_LABEL = "[bold]mode:[/bold] {mode}\n"

# --- scan results ---
NOTHING_FOUND = "[yellow]didn't find anything matching in there[/yellow]"
WRONG_TYPE = "[yellow]that file type isn't in your selected categories[/yellow]"

# --- progress / summary ---
PROGRESS_LABEL = "Cleaning"
SUMMARY_TITLE = "here's what happened"
COL_FILE = "File"
COL_CATEGORY = "Category"
COL_STATUS = "Status"
COL_DETAIL = "Detail"
STATUS_CLEANED = "[green]cleaned[/green]"
STATUS_ERROR = "[red]error[/red]"
TOTAL_LINE = (
    "\n[bold]total:[/bold] {total}  "
    "[green]cleaned: {cleaned}[/green]  "
    "[red]errors: {errors}[/red]"
)
COPIES_LOCATION = "[dim]clean copies are sitting in: {out_dir}[/dim]"

# --- per-file details (shown in the summary table) ---
DETAIL_IMAGE_OK = "EXIF/metadata removed"
DETAIL_IMAGE_ANIMATED = "animated images aren't supported yet"
DETAIL_PDF_OK = "doc info & XMP metadata wiped"
DETAIL_OOXML_OK = "core/app/custom properties wiped"
DETAIL_ODF_OK = "meta.xml wiped"
DETAIL_DOC_UNSUPPORTED = "unsupported document type"
DETAIL_CODE_REMOVED = "{count} extended attribute(s) removed"
DETAIL_CODE_NONE = "nothing to remove"
