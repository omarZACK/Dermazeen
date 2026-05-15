import mimetypes
import os
import requests
from django.core.files.base import ContentFile
from apps.shared.utils.file_helpers import generate_upload_path
from PIL import Image


def download_image(instance, image_url):
    response = requests.get(image_url)
    if response.status_code == 200:
        image_data = response.content
        image_name = generate_upload_path(instance, image_url.split('/')[-1])
        content_type = response.headers.get('Content-Type', '')
        file_extension = mimetypes.guess_extension(content_type.split(';')[0])
        image_name = image_name.rsplit('.', 1)[0] + file_extension
        image_file = ContentFile(image_data)
        image_file.name = image_name
        return image_file
    else:
        raise Exception("Failed to download image from URL.")


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


def resize_image(image_path, max_width=1024, max_height=1024, quality=85):
    """
    Resize image while maintaining aspect ratio
    """
    with Image.open(image_path) as img:
        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        img.save(image_path, optimize=True, quality=quality)

