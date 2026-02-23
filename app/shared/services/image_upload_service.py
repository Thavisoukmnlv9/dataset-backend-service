"""Reusable image upload service with existing file cleanup functionality"""
import logging
from typing import Optional, Tuple
from fastapi import HTTPException, status, UploadFile
from app.shared.services.infrastructure.storage import storage_service

logger = logging.getLogger(__name__)


async def upload_image_with_cleanup(
    new_image_file: UploadFile,
    existing_image_url: Optional[str],
    upload_folder: str,
    deleted_folder: str,
    error_message: str = "Failed to upload image"
) -> Tuple[Optional[str], bool]:
    """
    Upload a new image file and handle cleanup of existing image.
    
    Args:
        new_image_file: The new image file to upload
        existing_image_url: URL of existing image to clean up (optional)
        upload_folder: Folder path for new image upload (e.g., "business/logos")
        deleted_folder: Folder path for moved deleted images (e.g., "business/deleted-logos")
        error_message: Custom error message for upload failures
        
    Returns:
        Tuple of (new_image_url, success_flag)
        - new_image_url: The object name of the uploaded image (None if upload failed)
        - success_flag: True if upload was successful, False otherwise
    """
    try:
        # Handle cleanup of existing image
        if existing_image_url:
            try:
                # Extract object path from URL if it's a full URL
                existing_path = storage_service.extract_object_name_from_url(existing_image_url)
                await storage_service.move_delete_file(existing_path, deleted_folder)
                logger.info(f"Moved existing image to {deleted_folder}: {existing_image_url}")
            except Exception as e:
                # If file doesn't exist or can't be moved, just log warning and continue
                logger.warning(f"Failed to move delete existing image {existing_image_url}: {str(e)}")

        # Upload new image
        image_upload_result = await storage_service.upload_file(new_image_file, upload_folder)
        
        if image_upload_result.success:
            new_image_url = image_upload_result.data["object_name"]
            logger.info(f"Successfully uploaded image to {upload_folder}: {new_image_url}")
            return new_image_url, True
        else:
            logger.error(f"Image upload failed: {image_upload_result}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_message
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error during image upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process image upload: {str(e)}"
        )


async def upload_multiple_images_with_cleanup(
    new_image_files: list[UploadFile],
    existing_image_urls: Optional[list[str]],
    upload_folder: str,
    deleted_folder: str,
    error_message: str = "Failed to upload images"
) -> Tuple[list[str], bool]:
    """
    Upload multiple new image files and handle cleanup of existing images.
    
    Args:
        new_image_files: List of new image files to upload
        existing_image_urls: List of existing image URLs to clean up (optional)
        upload_folder: Folder path for new image uploads (e.g., "business/gallery")
        deleted_folder: Folder path for moved deleted images (e.g., "business/deleted-gallery")
        error_message: Custom error message for upload failures
        
    Returns:
        Tuple of (new_image_urls, success_flag)
        - new_image_urls: List of object names of uploaded images
        - success_flag: True if upload was successful, False otherwise
    """
    try:
        # Handle cleanup of existing images
        if existing_image_urls:
            for existing_url in existing_image_urls:
                if existing_url:
                    try:
                        existing_path = storage_service.extract_object_name_from_url(existing_url)
                        await storage_service.move_delete_file(existing_path, deleted_folder)
                        logger.info(f"Moved existing image to {deleted_folder}: {existing_url}")
                    except Exception as e:
                        logger.warning(f"Failed to move delete existing image {existing_url}: {str(e)}")

        # Upload new images
        if not new_image_files:
            return [], True
            
        image_upload_result = await storage_service.upload_multiple_image(new_image_files, upload_folder)
        
        if image_upload_result.success:
            new_image_urls = [img["object_name"] for img in image_upload_result.data["files"]]
            logger.info(f"Successfully uploaded {len(new_image_urls)} images to {upload_folder}")
            return new_image_urls, True
        else:
            logger.error(f"Multiple image upload failed: {image_upload_result}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_message
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error during multiple image upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process multiple image upload: {str(e)}"
        )


async def upload_multiple_videos_with_cleanup(
    new_video_files: list[UploadFile],
    existing_video_urls: Optional[list[str]],
    upload_folder: str,
    deleted_folder: str,
    error_message: str = "Failed to upload video files"
) -> Tuple[list[str], bool]:
    """
    Upload multiple video files and return their object names.

    Args:
        new_video_files: List of new video files to upload
        upload_folder: Folder path for new video uploads (e.g., "attractions")
        error_message: Custom error message for upload failures

    Returns:
        Tuple of (new_video_urls, success_flag)
    """
    try:
        # Handle cleanup of existing videos
        if existing_video_urls:
            for existing_url in existing_video_urls:
                if existing_url:
                    try:
                        existing_path = storage_service.extract_object_name_from_url(existing_url)
                        await storage_service.move_delete_file(existing_path, deleted_folder)
                        logger.info(f"Moved existing video to {deleted_folder}: {existing_url}")
                    except Exception as e:
                        logger.warning(f"Failed to move delete existing video {existing_url}: {str(e)}")

        # Upload new videos
        if not new_video_files:
            return [], True
        
        upload_result = await storage_service.upload_multiple_video(new_video_files, upload_folder)
        if upload_result.success:
            new_video_urls = [video["object_name"] for video in upload_result.data["files"]]
            logger.info(f"Successfully uploaded {len(new_video_urls)} videos to {upload_folder}")
            return new_video_urls, True
        else:
            logger.error(f"Multiple video upload failed: {upload_result}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_message
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during multiple video upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process multiple video upload: {str(e)}"
        )


async def process_existing_gallery_images_urls(
    existing_image_urls: list[str],
    expected_folder: str = "business/gallery"
) -> list[str]:
    """
    Process existing gallery image URLs and extract object paths.
    Handles both full URLs with query params and plain object paths.
    
    Args:
        existing_image_urls: List of existing image URLs to process
        expected_folder: Expected folder path for validation (e.g., "business/gallery")
        
    Returns:
        List of processed object paths
    """
    processed_paths = []
    
    if not existing_image_urls:
        return processed_paths
        
    logger.info(f"Processing {len(existing_image_urls)} existing images from gallery URLs")
    
    for image_url in existing_image_urls:
        if not image_url:
            continue
            
        object_name = storage_service.extract_object_name_from_url(image_url)
        
        # If extraction didn't work properly (still a URL), manually extract
        if object_name.startswith('http://') or object_name.startswith('https://'):
            # Strip query parameters first
            if '?' in image_url:
                path_part = image_url.split('?')[0]
            else:
                path_part = image_url
            
            # Extract path after bucket name
            if '/dataset-media/' in path_part:
                path_part = path_part.split('/dataset-media/')[-1]
                # Ensure it starts with expected folder
                if not path_part.startswith(f'{expected_folder}/'):
                    # Extract just the filename and prepend the expected path
                    filename = path_part.split('/')[-1]
                    path_part = f'{expected_folder}/{filename}'
            
            if path_part and path_part.strip():
                processed_paths.append(path_part)
        else:
            # Already extracted correctly as a path
            processed_paths.append(object_name)
    
    return processed_paths


async def cleanup_removed_files(
    old_image_urls: list[str],
    new_image_urls: list[str],
    deleted_folder: str
) -> None:
    """
    Clean up images that are no longer needed by moving them to deleted folder.
    
    Args:
        old_image_urls: List of existing image URLs
        new_image_urls: List of new image URLs to keep
        deleted_folder: Folder path for moved deleted images
    """
    if not old_image_urls:
        return
        
    # Find images to delete (in old but not in new)
    images_to_delete = []
    for old_image_url in old_image_urls:
        if old_image_url and old_image_url not in new_image_urls:
            images_to_delete.append(old_image_url)
    
    # Move deleted images to deleted folder
    for image_url in images_to_delete:
        try:
            object_name = storage_service.extract_object_name_from_url(image_url)
            await storage_service.move_delete_file(object_name, deleted_folder)
            logger.info(f"Moved deleted image to {deleted_folder}: {image_url}")
        except Exception as e:
            logger.warning(f"Failed to move delete image {image_url}: {str(e)}")
