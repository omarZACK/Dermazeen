import os
import uuid
from django.core.files.storage import default_storage
from PIL import Image
import hashlib

def generate_upload_path(instance, filename):
    """
    Generate upload path for files based on model and instance
    """
    model_name = instance.__class__.__name__.lower()
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4().hex}.{ext}"
    return f"{model_name}/{filename}"

def resize_image(image_path, max_width=1024, max_height=1024, quality=85):
    """
    Resize image while maintaining aspect ratio
    """
    with Image.open(image_path) as img:
        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        img.save(image_path, optimize=True, quality=quality)


def generate_unique_filename(original_filename):
    """
    Generate unique filename while preserving extension
    """
    name, ext = os.path.splitext(original_filename)
    unique_name = f"{uuid.uuid4().hex}{ext}"
    return unique_name


def calculate_file_hash(file_path):
    """
    Calculate SHA256 hash of a file
    """
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def validate_image_file(file):
    """
    Validate uploaded image file
    """
    valid_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
    ext = os.path.splitext(file.name)[1].lower()

    if ext not in valid_extensions:
        raise ValueError("Invalid file format. Only JPG, JPEG, PNG, and BMP are allowed.")

    # Check file size (max 10MB)
    if file.size > 10 * 1024 * 1024:
        raise ValueError("File size too large. Maximum size is 10MB.")

    return True


def safe_delete_file(file_path):
    """
    Safely delete a file if it exists
    """
    if default_storage.exists(file_path):
        default_storage.delete(file_path)
        return True
    return False