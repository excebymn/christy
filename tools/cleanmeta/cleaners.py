"""Per-format cleaners. Each one takes (src, dst) and returns (ok, detail)."""

from __future__ import annotations

import os
import shutil
import zipfile
from pathlib import Path
from typing import Callable

import pikepdf
from PIL import Image

import messages as msg
from scanner import ODF_EXTS, OOXML_EXTS

CleanResult = tuple[bool, str]

# Fixed timestamp for rewritten zip entries, so entry times don't leak anything.
ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)

# Empty-but-valid replacements. The parts are replaced rather than deleted
# because the package relationships still point at them; a missing part makes
# Office / LibreOffice complain that the file is corrupt.
OOXML_BLANKS = {
    "docProps/core.xml": (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<cp:coreProperties'
        ' xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"'
        ' xmlns:dc="http://purl.org/dc/elements/1.1/"'
        ' xmlns:dcterms="http://purl.org/dc/terms/"'
        ' xmlns:dcmitype="http://purl.org/dc/dcmitype/"'
        ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"/>'
    ),
    "docProps/app.xml": (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"/>'
    ),
    "docProps/custom.xml": (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"/>'
    ),
}
ODF_BLANKS = {
    "meta.xml": (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<office:document-meta'
        ' xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
        ' office:version="1.2"><office:meta/></office:document-meta>'
    ),
}


def clean_image(src: Path, dst: Path) -> CleanResult:
    try:
        with Image.open(src) as img:
            if getattr(img, "is_animated", False):
                return False, msg.DETAIL_IMAGE_ANIMATED
            fmt = img.format
            pixels = img
            if img.mode == "P":
                # Palette is metadata-adjacent state that paste() would drop.
                pixels = img.convert("RGBA" if "transparency" in img.info else "RGB")
            # A fresh image carries over pixels only, nothing from img.info.
            clean = Image.new(pixels.mode, pixels.size)
            clean.paste(pixels)

        save_kwargs: dict = {"format": fmt} if fmt else {}
        if fmt in ("JPEG", "WEBP"):
            save_kwargs["quality"] = 95
        dst.parent.mkdir(parents=True, exist_ok=True)
        clean.save(dst, **save_kwargs)
        return True, msg.DETAIL_IMAGE_OK
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def clean_pdf(src: Path, dst: Path) -> CleanResult:
    try:
        with pikepdf.open(src) as pdf:
            with pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
                meta.clear()
            for key in list(pdf.docinfo.keys()):
                del pdf.docinfo[key]
            dst.parent.mkdir(parents=True, exist_ok=True)
            pdf.save(dst)
        return True, msg.DETAIL_PDF_OK
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _rewrite_zip(src: Path, dst: Path, blanks: dict[str, str]) -> None:
    """Copy a zip entry by entry, swapping blanked parts for empty valid ones.

    Entry order and compression type are preserved; ODF needs its `mimetype`
    entry first and stored uncompressed.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(dst, "w") as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename in blanks:
                data = blanks[item.filename].encode("utf-8")
            info = zipfile.ZipInfo(item.filename, ZIP_EPOCH)
            info.compress_type = item.compress_type
            info.external_attr = item.external_attr
            zout.writestr(info, data)


def clean_ooxml(src: Path, dst: Path) -> CleanResult:
    try:
        _rewrite_zip(src, dst, OOXML_BLANKS)
        return True, msg.DETAIL_OOXML_OK
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def clean_odf(src: Path, dst: Path) -> CleanResult:
    try:
        _rewrite_zip(src, dst, ODF_BLANKS)
        return True, msg.DETAIL_ODF_OK
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def clean_document(src: Path, dst: Path) -> CleanResult:
    ext = src.suffix.lower()
    if ext == ".pdf":
        return clean_pdf(src, dst)
    if ext in OOXML_EXTS:
        return clean_ooxml(src, dst)
    if ext in ODF_EXTS:
        return clean_odf(src, dst)
    return False, msg.DETAIL_DOC_UNSUPPORTED


def clean_code(src: Path, dst: Path) -> CleanResult:
    try:
        if src != dst:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        removed = 0
        if hasattr(os, "listxattr"):
            try:
                for attr in os.listxattr(dst):
                    try:
                        os.removexattr(dst, attr)
                        removed += 1
                    except OSError:
                        pass
            except OSError:
                pass
        if removed:
            return True, msg.DETAIL_CODE_REMOVED.format(count=removed)
        return True, msg.DETAIL_CODE_NONE
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


CLEANERS: dict[str, Callable[[Path, Path], CleanResult]] = {
    "image": clean_image,
    "document": clean_document,
    "code": clean_code,
}


def clean_file(category: str, src: Path, dst: Path) -> CleanResult:
    """Run the right cleaner. Overwrites go through a temp file + atomic replace.

    Writing straight over a file that is still open for reading truncates it
    (zip) or is refused (pikepdf), so in-place cleaning never targets src.
    """
    cleaner = CLEANERS[category]
    if src != dst or category == "code":
        return cleaner(src, dst)

    tmp = dst.with_name(f".{dst.name}.cleanmeta-tmp")
    try:
        ok, detail = cleaner(src, tmp)
        if ok:
            shutil.copymode(src, tmp)
            os.replace(tmp, dst)
        return ok, detail
    finally:
        tmp.unlink(missing_ok=True)
