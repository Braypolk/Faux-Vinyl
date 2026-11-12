"""Validate cover uploads and store normalized, immutable WebP artwork."""
import hashlib
import io
import os
from pathlib import Path
import tempfile

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_UPLOAD_PIXELS = 12_000_000


def prepare_cover(upload):
    content = upload.stream.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError('Each cover must be 8 MB or smaller.')
    try:
        # Restrict decoders, check dimensions before loading, and never preserve
        # client filenames, animation, or metadata in the served file.
        with Image.open(io.BytesIO(content), formats=['JPEG', 'PNG', 'WEBP']) as image:
            if image.width * image.height > MAX_UPLOAD_PIXELS:
                raise ValueError('Each cover must be 12 megapixels or smaller.')
            if getattr(image, 'is_animated', False):
                raise ValueError('Use a still image for the cover.')
            image.load()
            normalized = ImageOps.exif_transpose(image)
            normalized.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
            pixels = normalized.convert('RGBA' if 'A' in normalized.getbands() or
                'transparency' in normalized.info else 'RGB')
            pixels.info.clear()
            output = io.BytesIO()
            pixels.save(output, 'WEBP', quality=85, method=4)
            return output.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ValueError('Choose a valid JPEG, PNG, or WebP image.') from None


def save_cover(directory, content):
    filename = hashlib.sha256(content).hexdigest() + '.webp'
    path = Path(directory) / filename
    # Content-addressed files can be safely shared between records and retained
    # when replaced; no request can delete another record's artwork.
    if not path.exists():
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=directory, delete=False) as out:
                temporary = out.name
                out.write(content)
            os.replace(temporary, path)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
    return filename
