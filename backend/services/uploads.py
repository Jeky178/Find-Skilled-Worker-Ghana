"""
Safe image uploads.

We never trust the filename or the Content-Type header. Every upload is:
  1. size-limited,
  2. opened with Pillow to prove it is really an image (JPEG / PNG / WebP only),
  3. checked for absurd dimensions (decompression bombs),
  4. rotated per EXIF, resized, and RE-ENCODED as JPEG (this strips metadata such as GPS location),
  5. saved under a random name.
"""
import io
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps

from config import get_settings

settings = get_settings()

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_PIXELS = 40_000_000
MAX_SIDE = 1600


def _public_root() -> Path:
    return Path(settings.UPLOAD_DIR) / "public"


def _private_root() -> Path:
    return Path(settings.UPLOAD_DIR) / "private"


def save_image(upload: UploadFile, folder: str, private: bool = False, max_side: int = MAX_SIDE) -> str:
    """
    Validate and store an image.
    Public images return a URL path like /uploads/profiles/abc.jpg.
    Private images (ID documents) return a key like private/verification/abc.jpg that is NOT web-accessible;
    only code that checks permissions may read it (see private_path).
    """
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    data = upload.file.read(max_bytes + 1)
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The file is empty")
    if len(data) > max_bytes:
        raise HTTPException(413, f"Image is too large. The limit is {settings.MAX_UPLOAD_MB} MB")

    try:
        probe = Image.open(io.BytesIO(data))
        probe.verify()                      # raises if the file is corrupt or not an image
        img = Image.open(io.BytesIO(data))  # verify() invalidates the object, so reopen
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That file is not a valid image. Upload a JPG, PNG or WebP photo")

    if img.format not in ALLOWED_FORMATS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only JPG, PNG and WebP images are allowed")
    if img.width * img.height > MAX_PIXELS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Image dimensions are too large")

    try:
        img = ImageOps.exif_transpose(img)
        img.thumbnail((max_side, max_side))
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        else:
            img = img.convert("RGB")
        target_dir = (_private_root() if private else _public_root()) / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        name = f"{uuid.uuid4().hex}.jpg"
        img.save(target_dir / name, "JPEG", quality=85, optimize=True)
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "We could not process that image. Try a different photo")
    return f"private/{folder}/{name}" if private else f"/uploads/{folder}/{name}"


def private_path(key: str | None) -> Path | None:
    """Resolve a private key to a real file, refusing anything outside the private folder."""
    if not key or not key.startswith("private/"):
        return None
    root = _private_root().resolve()
    target = (root / key.removeprefix("private/")).resolve()
    return target if root in target.parents and target.is_file() else None


def delete_image(path: str | None) -> None:
    """Remove a stored image (public URL path or private key). Ignores anything outside the upload folders."""
    if not path:
        return
    if path.startswith("/uploads/"):
        root = _public_root().resolve()
        target = (root / path.removeprefix("/uploads/")).resolve()
        if root in target.parents and target.is_file():
            target.unlink(missing_ok=True)
    else:
        target = private_path(path)
        if target:
            target.unlink(missing_ok=True)
