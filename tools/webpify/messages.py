"""All user-facing text for webpify.

Wording lives here and nowhere else, so the tone can change without touching
any logic. Rich markup is allowed in strings printed with the console, but not
in prompt text (questionary shows it literally). Templates use str.format
placeholders; anything coming from the user (paths, file names) is escaped by
the caller before it is formatted in.
"""

# --- startup / cli ---
MISSING_DEPENDENCY = (
    "webpify: missing dependency ({error}).\n"
    "this tool runs in its own venv, run `christy doctor` to sort that out."
)
NO_WEBP_SUPPORT = (
    "[bold red]this Pillow build can't write WebP.[/bold red]\n"
    "reinstall it from a wheel: pip install --force-reinstall --only-binary :all: Pillow"
)
CLI_DESCRIPTION = "compress images and convert them to WebP, ready for the web"
CLI_EPILOG = (
    "run it with no options and everything is asked interactively.\n"
    "the options are shortcuts for scripts: each one skips its own question."
)
CLI_HELP_PATH = "image or folder (browse for one when omitted)"
CLI_HELP_QUALITY = "WebP quality, 1 to 100 (default: 80)"
CLI_HELP_LOSSLESS = "lossless WebP (bigger files, pixel-perfect)"
CLI_HELP_WIDTH = "shrink images wider than this many pixels (never enlarges)"
CLI_HELP_NO_SUBFOLDERS = "don't look inside subfolders"
CLI_HELP_KEEP_METADATA = "keep EXIF and colour profile data (stripped by default)"
CLI_HELP_OVERWRITE = "overwrite WebP files that already exist"
CLI_HELP_INCLUDE_WEBP = "also recompress images that are already WebP"
CLI_HELP_OUTPUT = "write the results into this folder"
CLI_HELP_BESIDE = "write each WebP next to its original"
CLI_HELP_REPLACE = "replace the originals with the WebP files (always asks in a terminal)"
CLI_HELP_DRY_RUN = "only show what would be converted (the list goes to stdout)"
CLI_HELP_YES = (
    "ask nothing: use the options given (or the defaults). Replacing originals "
    "is still confirmed in a terminal, and needs -y when there is none."
)
CLI_NUMBER_INVALID = "{value!r} is not a whole number in the allowed range"

# --- header / generic ---
HEADER_TITLE = "[bold cyan]webpify[/bold cyan]"
HEADER_SUBTITLE = "[dim]lighter images, ready for the web[/dim]"
CANCELLED = "[yellow]no worries, cancelled[/yellow]"
PATH_NOT_FOUND = "[bold red]hmm, can't find that:[/bold red] {path}"
NOT_AN_IMAGE = "[bold red]that's not an image webpify can read:[/bold red] {path}"
NO_BROWSER_TERMINAL = "[dim]no terminal to browse in, using the current folder[/dim]"
SCANNING = "looking for images..."
NOTHING_FOUND = "[yellow]no images found there[/yellow]"
NOTHING_TO_CONVERT = "[yellow]nothing to convert: every image was skipped[/yellow]"
HINT_SHORTCUTS = "(arrows or the number/letter next to an item, enter to pick)"
HINT_SEARCH = "(arrows to move, or just type to filter, enter to pick)"
HINT_ARROWS = "(arrows to move, enter to pick)"
NUMBER_INVALID = "that's not a whole number"
NUMBER_RANGE = "pick a number between {low} and {high}"

# --- picker ---
BROWSE_QUESTION = "Which image or folder?  ({current})"
BROWSE_EMPTY = "(nothing to pick here)"
BROWSE_MORE = "(...and {count} more images, type a path to pick one of them)"
CHOICE_USE_THIS = "convert this whole folder ({name}, {count} images)"
CHOICE_OPEN = "open a subfolder..."
CHOICE_UP = ".. go up one level"
CHOICE_TYPE_PATH = "type a path instead"
CHOICE_QUIT = "quit"
CHOICE_BACK = "<- back"
OPEN_QUESTION = "Open which subfolder?"
TYPE_PATH_PROMPT = "Paste or type the path to an image or folder (tab completes):"
BROWSE_PATH_MISSING = "[red]can't find:[/red] {path}"

# --- quality ---
QUALITY_QUESTION = "How much should the images be compressed?"
QUALITY_BALANCED = "Balanced for the web (quality 80)"
QUALITY_SMALLER = "Smaller files (quality 70)"
QUALITY_HIGH = "High quality (quality 90)"
QUALITY_LOSSLESS = "Lossless (pixel-perfect, bigger files)"
QUALITY_LAST = "Quality {value} (last time)"
QUALITY_CUSTOM = "Type a number..."
QUALITY_PROMPT = "Quality, 1 to 100:"

# --- size ---
WIDTH_QUESTION = "Shrink big images? (smaller ones are never enlarged)"
WIDTH_KEEP = "Keep the original size"
WIDTH_N = "At most {value} pixels wide"
WIDTH_LAST = "At most {value} pixels wide (last time)"
WIDTH_CUSTOM = "Type a number..."
WIDTH_PROMPT = "Maximum width in pixels:"

# --- extra options ---
EXTRAS_QUESTION = "Extra options? (all optional)"
EXTRAS_INSTRUCTION = "(up/down to move, space to select, a = all, i = invert, enter when done)"
OPT_RECURSIVE = "Include subfolders"
OPT_KEEP_METADATA = "Keep metadata such as EXIF and location (leave off to strip it, better for the web)"
OPT_OVERWRITE = "Overwrite WebP files that already exist"
OPT_INCLUDE_WEBP = "Also recompress images that are already WebP"

# --- destination ---
DEST_QUESTION = "Where should the results go?"
DEST_FOLDER = "A new 'webp' folder (originals untouched)"
DEST_BESIDE = "Next to each original (originals untouched)"
DEST_CUSTOM = "Another folder... (originals untouched)"
DEST_REPLACE = "Replace the originals with the WebP files (asks you to confirm)"
CUSTOM_DIR_PROMPT = "Folder to write the results into (tab completes):"
CUSTOM_DIR_EMPTY = "give a folder"

# --- preview ---
PREVIEW_TITLE = "ready to convert"
ROW_SOURCE = "Source"
ROW_IMAGES = "Images"
ROW_SIZE = "Total size now"
ROW_QUALITY = "Quality"
ROW_WIDTH = "Max width"
ROW_DEST = "Results go to"
ROW_OPTIONS = "Options"
ROW_SKIPPED = "Skipped"
QUALITY_LABEL = "{value}"
QUALITY_LOSSLESS_LABEL = "lossless"
WIDTH_ORIGINAL = "original size"
WIDTH_LABEL = "{value} px"
DEST_LABEL_FOLDER = "{path}  (originals untouched)"
DEST_LABEL_BESIDE = "next to each original  (originals untouched)"
DEST_LABEL_CUSTOM = "{path}  (originals untouched)"
DEST_LABEL_REPLACE = "[bold red]replacing the originals[/bold red]"
OPTIONS_NONE = "none"
OPTION_TAGS = {
    "recursive": "subfolders",
    "keep_metadata": "keep metadata",
    "overwrite": "overwrite existing",
    "include_webp": "recompress WebP",
}
SKIPPED_LINE = "{count} x {reason}"

# --- confirmations ---
CONFIRM_START = "Convert {count} image(s) now?"
CONFIRM_REPLACE = (
    "This REPLACES {count} original image(s) ({size}) with WebP files. "
    "Each original is deleted only after its WebP is written and checked. Continue?"
)
NEEDS_YES_REPLACE = "[bold red]replacing originals needs a confirmation.[/bold red] there's no terminal, so pass -y to confirm in advance."

# --- progress / summary ---
PROGRESS_LABEL = "Converting"
SUMMARY_TITLE = "here's what happened"
COL_FILE = "File"
COL_BEFORE = "Before"
COL_AFTER = "After"
COL_SAVED = "Saved"
COL_RESULT = "Result"
RESULT_CONVERTED = "[green]converted[/green]"
RESULT_KEPT = "[yellow]kept original[/yellow]"
RESULT_SKIPPED = "[dim]skipped[/dim]"
RESULT_ERROR = "[red]error[/red]"
SUMMARY_MORE = "[dim]...and {count} more not shown[/dim]"
TOTAL_LINE = (
    "\n[bold]total:[/bold] {total}  "
    "[green]converted: {converted}[/green]  "
    "[yellow]kept: {kept}[/yellow]  "
    "[dim]skipped: {skipped}[/dim]  "
    "[red]errors: {errors}[/red]"
)
SAVED_LINE = "[bold]saved:[/bold] {saved} ({percent}%), {before} -> {after}"
RESULTS_LOCATION = "[dim]results are in: {path}[/dim]"
REPLACED_NOTE = "[dim]originals were replaced by the WebP files[/dim]"
ORIGINAL_NOT_DELETED = "converted, but the original couldn't be deleted: {error}"

# --- per-file details ---
DETAIL_NOT_SMALLER = "the WebP wasn't smaller, so the original stays"
DETAIL_ANIMATED = "animated"
DETAIL_TOO_BIG = "image is too large to process safely"
