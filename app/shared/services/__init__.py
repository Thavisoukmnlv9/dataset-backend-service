# Import the image upload service for easy access
from .image_upload_service import (
    upload_image_with_cleanup,
    upload_multiple_images_with_cleanup,
    cleanup_removed_files,
    process_existing_gallery_images_urls,
    upload_multiple_videos_with_cleanup
)

__all__ = [
    "upload_image_with_cleanup",
    "upload_multiple_images_with_cleanup", 
    "cleanup_removed_files",
    "process_existing_gallery_images_urls",
    "upload_multiple_videos_with_cleanup"
]