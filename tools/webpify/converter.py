"""Converts one image to WebP. Writes to a temp file, checks it, and only then
moves it into place."""

from __future__ import annotations

import io
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PIL import Image, ImageCms, ImageOps, ImageSequence

import messages as msg
from models import Settings

Image.MAX_IMAGE_PIXELS = 400_000_000  # generous, but a decompression bomb still errors out

_SRGB_PROFILE = None


@dataclass
class Outcome:
    ok: bool
    detail: str
    new_size: int = 0
    kept_original: bool = False


def _srgb():
    global _SRGB_PROFILE
    if _SRGB_PROFILE is None:
        _SRGB_PROFILE = ImageCms.createProfile("sRGB")
    return _SRGB_PROFILE


def _to_srgb(image: Image.Image) -> Image.Image:
    """Bring the colours to sRGB (what browsers assume) when the file says otherwise."""
    profile_bytes = image.info.get("icc_profile")
    if not profile_bytes:
        return image
    try:
        source = ImageCms.ImageCmsProfile(io.BytesIO(profile_bytes))
        if ImageCms.getProfileDescription(source).strip().lower().startswith("srgb"):
            return image
        mode = "RGBA" if "A" in image.getbands() else "RGB"
        return ImageCms.profileToProfile(image, source, _srgb(), outputMode=mode)
    except (ImageCms.PyCMSError, OSError, ValueError):
        return image  # a broken profile must not stop the conversion


def _normalise_mode(image: Image.Image) -> Image.Image:
    """WebP stores RGB or RGBA only."""
    if image.mode == "P":
        return image.convert("RGBA" if "transparency" in image.info else "RGB")
    if image.mode in ("RGB", "RGBA"):
        return image
    if image.mode in ("LA", "PA") or "transparency" in image.info:
        return image.convert("RGBA")
    if image.mode in ("I", "I;16", "I;16L", "I;16B", "F"):
        image = image.point(lambda value: value * (1 / 256)) if image.mode.startswith("I") else image
        return image.convert("L").convert("RGB")
    return image.convert("RGB")  # L, CMYK, 1, ...


def _resized(image: Image.Image, max_width: Optional[int]) -> tuple[Image.Image, bool]:
    if not max_width or image.width <= max_width:
        return image, False
    height = max(1, round(image.height * max_width / image.width))
    return image.resize((max_width, height), Image.Resampling.LANCZOS), True


def _save_args(settings: Settings) -> dict:
    if settings.lossless:
        return {"lossless": True, "quality": 100, "method": 6}
    return {"lossless": False, "quality": settings.quality, "method": 6, "exact": False}


def _prepare_static(image: Image.Image, settings: Settings) -> tuple[Image.Image, dict, bool]:
    """(image to save, extra save args, was resized)"""
    image = ImageOps.exif_transpose(image)  # apply the camera's rotation before it's discarded
    extra: dict = {}
    if settings.keep_metadata:
        if image.info.get("exif"):
            extra["exif"] = image.info["exif"]
        if image.info.get("icc_profile"):
            extra["icc_profile"] = image.info["icc_profile"]
    else:
        image = _to_srgb(image)
    image = _normalise_mode(image)
    image, resized = _resized(image, settings.max_width)
    return image, extra, resized


def _is_animated(image: Image.Image) -> bool:
    return bool(getattr(image, "is_animated", False)) and getattr(image, "n_frames", 1) > 1


def _write_animated(image: Image.Image, tmp: Path, settings: Settings) -> bool:
    frames, durations, resized_any = [], [], False
    for frame in ImageSequence.Iterator(image):
        durations.append(int(frame.info.get("duration", 100)) or 100)
        rgba = frame.convert("RGBA")
        rgba, resized = _resized(rgba, settings.max_width)
        resized_any = resized_any or resized
        frames.append(rgba)
    args = _save_args(settings)
    args["method"] = 4  # the slowest method is painfully slow over many frames
    frames[0].save(
        tmp, "WEBP", save_all=True, append_images=frames[1:],
        duration=durations, loop=int(image.info.get("loop", 0)), **args,
    )
    return resized_any


def _verify(tmp: Path, animated: bool) -> None:
    with Image.open(tmp) as check:
        if animated and getattr(check, "n_frames", 1) < 2:
            raise ValueError("the animation was lost")
        check.load()
        if check.width < 1 or check.height < 1:
            raise ValueError("the result is empty")


def convert_image(src: Path, dst: Path, settings: Settings, src_size: int) -> Outcome:
    tmp = dst.with_name(f".{dst.name}.webpify-tmp")
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(src) as image:
            before = f"{image.width}x{image.height}"
            animated = _is_animated(image)
            if animated:
                resized = _write_animated(image, tmp, settings)
                after_size = None
            else:
                prepared, extra, resized = _prepare_static(image, settings)
                prepared.save(tmp, "WEBP", **_save_args(settings), **extra)
                after_size = (prepared.width, prepared.height)
        _verify(tmp, animated)

        new_size = tmp.stat().st_size
        # Keep the original when the WebP isn't smaller, unless the user asked
        # for a smaller picture (resizing is the point then).
        if new_size >= src_size and not resized:
            return Outcome(True, msg.DETAIL_NOT_SMALLER, new_size, kept_original=True)

        stat = src.stat()
        os.replace(tmp, dst)
        os.utime(dst, (stat.st_atime, stat.st_mtime))  # keeps caches and sort order sensible
        if animated:
            detail = msg.DETAIL_ANIMATED
        else:
            detail = before if after_size is None or before == f"{after_size[0]}x{after_size[1]}" else f"{before} -> {after_size[0]}x{after_size[1]}"
        return Outcome(True, detail, new_size)
    except Image.DecompressionBombError:
        return Outcome(False, msg.DETAIL_TOO_BIG)
    except Exception as exc:  # noqa: BLE001  (one bad file must not stop the batch)
        return Outcome(False, str(exc) or exc.__class__.__name__)
    finally:
        tmp.unlink(missing_ok=True)
