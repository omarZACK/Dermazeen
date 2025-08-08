import os
from django.core.files.storage import default_storage
import uuid
import hashlib

def safe_delete_file(file_path):
    """
    Safely delete a file if it exists
    """
    if default_storage.exists(file_path):
        default_storage.delete(file_path)
        return True
    return False


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

def generate_upload_path(instance, filename):
    """
    Generate upload path for files based on model and instance
    """
    model_name = instance.__class__.__name__.lower()
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4().hex}.{ext}"
    return f"{model_name}/{filename}"

