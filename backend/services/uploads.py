
"""
Safe image uploads.

Public images:
- Validated and processed with Pillow.
- Uploaded to Cloudinary.
- Return a secure Cloudinary URL.

Private images:
- Remain on local private storage.
- Never receive a public Cloudinary URL.
"""

import io
import re
import uuid
from pathlib import Path
from urllib.parse import urlparse

import cloudinary
import cloudinary.uploader

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps

from config import get_settings

settings = get_settings()

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_PIXELS = 40_000_000
MAX_SIDE = 1600


def _configure_cloudinary():
    """Configure Cloudinary using backend environment variables."""

    if not all([
        settings.CLOUDINARY_CLOUD_NAME,
        settings.CLOUDINARY_API_KEY,
        settings.CLOUDINARY_API_SECRET,
    ]):
        raise HTTPException(
            status_code=503,
            detail="Image storage is not configured. Please contact support."
        )

    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )


def _private_root() -> Path:
    return Path(settings.UPLOAD_DIR) / "private"


def save_image(
    upload: UploadFile,
    folder: str,
    private: bool = False,
    max_side: int = MAX_SIDE,
) -> str:
    """
    Validate and store an image.

    Public images return a Cloudinary HTTPS URL.

    Private images return a local private key such as:
    private/verification/abc.jpg
    """

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024

    data = upload.file.read(max_bytes + 1)

    if not data:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "The file is empty"
        )

    if len(data) > max_bytes:
        raise HTTPException(
            413,
            f"Image is too large. The limit is {settings.MAX_UPLOAD_MB} MB"
        )

    try:
        probe = Image.open(io.BytesIO(data))
        probe.verify()

        img = Image.open(io.BytesIO(data))

    except Exception:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "That file is not a valid image. Upload a JPG, PNG or WebP photo"
        )

    if img.format not in ALLOWED_FORMATS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Only JPG, PNG and WebP images are allowed"
        )

    if img.width * img.height > MAX_PIXELS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Image dimensions are too large"
        )

    try:
        img = ImageOps.exif_transpose(img)
        img.thumbnail((max_side, max_side))

        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")

            background = Image.new(
                "RGB",
                img.size,
                (255, 255, 255)
            )

            background.paste(
                img,
                mask=img.split()[-1]
            )

            img = background
        else:
            img = img.convert("RGB")

        output = io.BytesIO()

        img.save(
            output,
            format="JPEG",
            quality=85,
            optimize=True
        )

        image_bytes = output.getvalue()

    except Exception:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "We could not process that image. Try a different photo"
        )

    name = uuid.uuid4().hex

    # Keep private verification documents outside public Cloudinary storage.
    if private:
        try:
            target_dir = _private_root() / folder
            target_dir.mkdir(parents=True, exist_ok=True)

            filename = f"{name}.jpg"
            target_path = target_dir / filename

            target_path.write_bytes(image_bytes)

            return f"private/{folder}/{filename}"

        except Exception:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Could not save the private document"
            )

    # Upload public images to Cloudinary.
    try:
        _configure_cloudinary()

        result = cloudinary.uploader.upload(
            io.BytesIO(image_bytes),
            folder=f"find-skilled-worker/{folder}",
            public_id=name,
            resource_type="image",
            overwrite=False,
            format="jpg",
        )

        secure_url = result.get("secure_url")

        if not secure_url:
            raise RuntimeError("Cloudinary did not return a secure URL")

        return secure_url

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Image upload failed. Please try again"
        )


def private_path(key: str | None) -> Path | None:
    """
    Resolve a private key to a real file,
    refusing anything outside the private folder.
    """

    if not key or not key.startswith("private/"):
        return None

    root = _private_root().resolve()

    target = (
        root / key.removeprefix("private/")
    ).resolve()

    return (
        target
        if root in target.parents and target.is_file()
        else None
    )


def _cloudinary_public_id(image_url: str) -> str | None:
    """Extract the Cloudinary public ID from an uploaded image URL."""

    try:
        parsed = urlparse(image_url)

        if not parsed.hostname or not parsed.hostname.endswith("cloudinary.com"):
            return None

        marker = "/image/upload/"

        if marker not in parsed.path:
            return None

        public_path = parsed.path.split(marker, 1)[1]

        # Remove the Cloudinary version segment, e.g. v1234567890/
        public_path = re.sub(
            r"^v\d+/",
            "",
            public_path
        )

        # Remove the file extension.
        public_id = str(Path(public_path).with_suffix(""))

        return public_id or None

    except Exception:
        return None


def delete_image(path: str | None) -> None:
    """
    Delete a Cloudinary public image or local private image.
    """

    if not path:
        return

    # Delete public Cloudinary image.
    if path.startswith("https://"):
        public_id = _cloudinary_public_id(path)

        if not public_id:
            return

        try:
            _configure_cloudinary()

            cloudinary.uploader.destroy(
                public_id,
                resource_type="image",
                invalidate=True,
            )

        except Exception:
            # Do not silently claim that the Cloudinary asset was deleted.
            raise RuntimeError(
                "Could not delete the image from Cloudinary"
            )

        return

    # Delete local private image.
    target = private_path(path)

    if target:
        target.unlink(missing_ok=True)
