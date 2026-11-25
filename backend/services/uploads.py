
"""
Safe image uploads.

Public images:
- Validated and processed with Pillow.
- Uploaded to Cloudinary when configured.
- Use local storage in development and tests when Cloudinary is not configured.
- Return a secure Cloudinary URL or a local /uploads/ path.

Private verification images:
- Use Cloudinary authenticated delivery in hosted production environments.
- Are fetched through an administrator-authorized backend endpoint.
- Use local private storage only for development and legacy local files.
"""

import io
import re
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

import cloudinary
import cloudinary.uploader
import httpx

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps

from config import get_settings


settings = get_settings()

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_PIXELS = 40_000_000
MAX_SIDE = 1600

PRIVATE_CLOUDINARY_PREFIX = (
    "find-skilled-worker/private-verification/"
)


def _configure_cloudinary():
    """Configure Cloudinary using backend environment variables."""

    if not _cloudinary_is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Image storage is not configured. Please contact support.",
        )

    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )


def _cloudinary_is_configured() -> bool:
    """Check whether all required Cloudinary settings are available."""

    return all(
        (
            settings.CLOUDINARY_CLOUD_NAME,
            settings.CLOUDINARY_API_KEY,
            settings.CLOUDINARY_API_SECRET,
        )
    )


def _private_root() -> Path:
    """Return the root directory for private local files."""

    return Path(settings.UPLOAD_DIR) / "private"


def _public_root() -> Path:
    """Return the root directory for public local files."""

    return Path(settings.UPLOAD_DIR) / "public"


def save_image(
    upload: UploadFile,
    folder: str,
    private: bool = False,
    max_side: int = MAX_SIDE,
) -> str:
    """
    Validate and store an image.

    Public images return a Cloudinary HTTPS URL when Cloudinary is
    configured. In development and tests, they can use local storage.

    Private images return either an authenticated Cloudinary key or
    a local private key such as:

        private/verification/abc.jpg
    """

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    data = upload.file.read(max_bytes + 1)

    if not data:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "The file is empty",
        )

    if len(data) > max_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Image is too large. The limit is {settings.MAX_UPLOAD_MB} MB",
        )

    # Validate the uploaded image.
    try:
        probe = Image.open(io.BytesIO(data))
        probe.verify()

        img = Image.open(io.BytesIO(data))

    except Exception:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "That file is not a valid image. Upload a JPG, PNG or WebP photo",
        )

    if img.format not in ALLOWED_FORMATS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Only JPG, PNG and WebP images are allowed",
        )

    if img.width * img.height > MAX_PIXELS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Image dimensions are too large",
        )

    # Normalize, resize and re-encode the image.
    try:
        img = ImageOps.exif_transpose(img)
        img.thumbnail((max_side, max_side))

        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")

            background = Image.new(
                "RGB",
                img.size,
                (255, 255, 255),
            )

            background.paste(
                img,
                mask=img.split()[-1],
            )

            img = background

        else:
            img = img.convert("RGB")

        output = io.BytesIO()

        img.save(
            output,
            format="JPEG",
            quality=85,
            optimize=True,
        )

        image_bytes = output.getvalue()

    except Exception:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "We could not process that image. Try a different photo",
        )

    name = uuid.uuid4().hex

    # ---------------------------------------------------------
    # PRIVATE VERIFICATION DOCUMENTS
    # ---------------------------------------------------------

    if private:
        if _cloudinary_is_configured():
            try:
                _configure_cloudinary()

                public_id = f"{PRIVATE_CLOUDINARY_PREFIX}{name}"

                result = cloudinary.uploader.upload(
                    io.BytesIO(image_bytes),
                    public_id=public_id,
                    resource_type="image",
                    type="authenticated",
                    overwrite=False,
                    format="jpg",
                )

                stored_id = result.get("public_id")

                if not stored_id:
                    raise RuntimeError(
                        "Cloudinary did not return a public ID"
                    )

                return f"cloudinary:authenticated:{stored_id}"

            except HTTPException:
                raise

            except Exception:
                raise HTTPException(
                    status.HTTP_502_BAD_GATEWAY,
                    "Secure document storage is temporarily unavailable. "
                    "Please try again.",
                )

        # Local private storage is only allowed outside production.
        if settings.ENVIRONMENT.lower() == "production":
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Secure document storage is not configured. "
                "Please contact support.",
            )

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
                "Could not save the private document",
            )

    # ---------------------------------------------------------
    # PUBLIC IMAGES
    # ---------------------------------------------------------

    cloudinary_configured = _cloudinary_is_configured()

    # Local public storage is allowed in tests and development.
    # Production must use Cloudinary.
    if not cloudinary_configured:
        if settings.ENVIRONMENT.lower() == "production":
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Image storage is not configured. Please contact support.",
            )

        try:
            target_dir = _public_root() / folder
            target_dir.mkdir(parents=True, exist_ok=True)

            filename = f"{name}.jpg"
            target_path = target_dir / filename

            target_path.write_bytes(image_bytes)

            return f"/uploads/{folder}/{filename}"

        except Exception:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Could not save the image",
            )

    # Use Cloudinary when configured.
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
            raise RuntimeError(
                "Cloudinary did not return a secure URL"
            )

        return secure_url

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Image upload failed. Please try again",
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


def read_private_image(key: str | None) -> bytes | None:
    """
    Read a private verification image from Cloudinary
    or legacy local storage.

    Callers must enforce administrator authorization
    before invoking this helper.

    Cloudinary assets are authenticated and downloaded
    server-to-server using a short-lived signed URL.
    The browser never receives that signed URL.
    """

    if not key:
        return None

    prefix = "cloudinary:authenticated:"

    if key.startswith(prefix):
        public_id = key[len(prefix):].strip()

        if not re.fullmatch(
                r"find-skilled-worker/private-verification/[0-9a-f]{32}",
                public_id,
        ):
            return None

        try:
            _configure_cloudinary()

            signed_url = cloudinary.utils.private_download_url(
                public_id,
                "jpg",
                resource_type="image",
                type="authenticated",
                expires_at=int(time.time()) + 90,
                attachment=False,
            )

            response = httpx.get(
                signed_url,
                timeout=20.0,
                follow_redirects=True,
            )

            if response.status_code == 404:
                return None

            response.raise_for_status()

            return response.content

        except HTTPException:
            raise

        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None

            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                "The secure document provider could not return this document.",
            ) from exc

        except Exception as exc:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                "Could not retrieve the secure document. Please try again.",
            ) from exc

    # Backward compatibility for legacy local private documents.
    path = private_path(key)

    return path.read_bytes() if path else None


def _cloudinary_public_id(image_url: str) -> str | None:
    """Extract the Cloudinary public ID from an uploaded image URL."""

    try:
        parsed = urlparse(image_url)

        if (
            not parsed.hostname
            or not parsed.hostname.endswith("cloudinary.com")
        ):
            return None

        marker = "/image/upload/"

        if marker not in parsed.path:
            return None

        public_path = parsed.path.split(marker, 1)[1]

        # Remove the Cloudinary version segment, e.g. v1234567890/
        public_path = re.sub(
            r"^v\d+/",
            "",
            public_path,
        )

        # Remove the file extension.
        public_id = str(Path(public_path).with_suffix(""))

        return public_id or None

    except Exception:
        return None


def _local_public_path(path: str) -> Path | None:
    """Resolve a local /uploads/ URL safely inside the public folder."""

    prefix = "/uploads/"

    if not path.startswith(prefix):
        return None

    relative_path = path[len(prefix):]

    root = _public_root().resolve()
    target = (root / relative_path).resolve()

    if root in target.parents and target.is_file():
        return target

    return None


def delete_image(path: str | None) -> None:
    """
    Delete a Cloudinary public image, authenticated private image,
    or locally stored image.
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

        except Exception as exc:
            raise RuntimeError(
                "Could not delete the image from Cloudinary"
            ) from exc

        return

    # Delete authenticated Cloudinary verification document.
    cloud_prefix = "cloudinary:authenticated:"

    if path.startswith(cloud_prefix):
        public_id = path[len(cloud_prefix):].strip()
        if not re.fullmatch(
                r"find-skilled-worker/private-verification/[0-9a-f]{32}",
                public_id,
        ):
            return

        if not public_id.startswith(PRIVATE_CLOUDINARY_PREFIX):
            return

        try:
            _configure_cloudinary()

            result = cloudinary.uploader.destroy(
                public_id,
                resource_type="image",
                type="authenticated",
                invalidate=True,
            )

            if result.get("result") not in {"ok", "not found"}:
                raise RuntimeError(
                    "Cloudinary did not confirm document deletion"
                )

        except Exception as exc:
            raise RuntimeError(
                "Could not delete the private document from Cloudinary"
            ) from exc

        return

    # Delete legacy local private image.
    target = private_path(path)

    if target:
        target.unlink(missing_ok=True)
        return

    # Delete local public image used in tests and development.
    public_target = _local_public_path(path)

    if public_target:
        public_target.unlink(missing_ok=True)
