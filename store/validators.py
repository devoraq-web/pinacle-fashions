import io
import os
import re
import uuid
from PIL import Image, UnidentifiedImageError
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
ALLOWED_PILLOW_FORMATS = {'JPEG', 'PNG', 'WEBP'}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB limit per uploaded image


def validate_image_file(file_obj, max_size_bytes=MAX_IMAGE_SIZE_BYTES):
    """
    Validates uploaded image by extension, byte size, and actual binary image structure via Pillow.
    Blocks SVG, HTML, executables, oversized payloads, and spoofed MIME types.
    """
    if not file_obj:
        raise ValidationError("No file provided.")

    if hasattr(file_obj, 'size') and file_obj.size > max_size_bytes:
        max_mb = max_size_bytes // (1024 * 1024)
        raise ValidationError(f"Image size must not exceed {max_mb} MB.")

    ext = os.path.splitext(getattr(file_obj, 'name', ''))[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError("Unsupported file format. Only JPG, JPEG, PNG, and WEBP images are permitted.")

    # Verify image content using Pillow (cannot be bypassed by renaming .html/.exe to .jpg)
    try:
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)
        with Image.open(file_obj) as img:
            img_format = (img.format or '').upper()
            img.verify()
        if img_format not in ALLOWED_PILLOW_FORMATS:
            raise ValidationError("Invalid image binary format. Allowed formats: JPEG, PNG, WEBP.")
    except ValidationError:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise ValidationError("The uploaded file is corrupted or is not a valid image.")
    finally:
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)


def sanitize_and_optimize_image(file_obj, max_dim=1600, quality=88):
    """
    Validates, strips EXIF/embedded metadata, resizes oversized images for web speed,
    re-encodes cleanly, and assigns an unpredictable UUID filename.
    Returns a Django ContentFile ready for ImageField storage.
    """
    validate_image_file(file_obj)

    if hasattr(file_obj, 'seek'):
        file_obj.seek(0)

    with Image.open(file_obj) as img:
        orig_format = (img.format or 'JPEG').upper()

        # Convert palette/RGBA images appropriately
        if orig_format == 'PNG':
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGBA')
            target_format = 'PNG'
            target_ext = '.png'
        elif orig_format == 'WEBP':
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')
            target_format = 'WEBP'
            target_ext = '.webp'
        else:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            target_format = 'JPEG'
            target_ext = '.jpg'

        # Resize proportionally if larger than max_dim
        if max(img.width, img.height) > max_dim:
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

        # Re-save to clean buffer without EXIF or appended payload bytes
        output = io.BytesIO()
        save_kwargs = {'optimize': True}
        if target_format in ('JPEG', 'WEBP'):
            save_kwargs['quality'] = quality
        img.save(output, format=target_format, **save_kwargs)

    safe_name = f"{uuid.uuid4().hex}{target_ext}"
    return ContentFile(output.getvalue(), name=safe_name)


def sanitize_csv_cell(value):
    """
    Prevents CSV / Excel formula injection by prefixing risky leading characters with an apostrophe.
    """
    if value is None:
        return ''
    text = str(value)
    if text and text[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + text
    return text


def get_safe_redirect_url(request, target_url, fallback='store:home'):
    """
    Validates an external/query/referer redirect URL against allowed hosts to prevent Open Redirect attacks.
    """
    if target_url and url_has_allowed_host_and_scheme(
        url=target_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return target_url
    return reverse(fallback)


def normalize_phone_number(raw_phone):
    """
    Validates Indian/international phone digits (10 to 15 digits, allowing optional +91 prefix or spaces).
    Returns normalized digit/plus string or raises ValidationError.
    """
    cleaned = re.sub(r'[\s\-\(\)]+', '', (raw_phone or '').strip())
    if cleaned.startswith('+91'):
        digits = cleaned[3:]
        if len(digits) == 10 and digits.isdigit() and digits[0] in '6789':
            return cleaned
    if cleaned.isdigit() and 10 <= len(cleaned) <= 15:
        if len(cleaned) == 10 and cleaned[0] not in '6789':
            raise ValidationError("Please enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9.")
        return cleaned
    raise ValidationError("Please enter a valid mobile number (10 digits, e.g. 9876543210 or +919876543210).")


def get_client_ip(request):
    """Safely extracts client IP address for audit logging and login throttling."""
    remote_addr = request.META.get('REMOTE_ADDR', '') or '0.0.0.0'
    return remote_addr.strip()[:45]

