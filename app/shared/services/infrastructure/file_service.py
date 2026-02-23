"""MinIO service for file uploads and management"""
import os
import uuid
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import UploadFile, HTTPException, status
from minio import Minio
from minio.error import S3Error
from minio.commonconfig import CopySource
from app.core.config import settings
from app.shared.schemas.base import ResponseModel
from PIL import Image
import io
from urllib.parse import urlparse


class MinIOService:
    """MinIO service for handling file uploads and management"""

    @staticmethod
    def _sanitize_endpoint(endpoint: str) -> str:
        """
        Sanitize MinIO endpoint to remove protocol and path components.
        MinIO client expects format: hostname:port (e.g., 'localhost:9000')
        """
        if not endpoint:
            raise ValueError("MinIO endpoint cannot be empty")
        
        # Remove protocol if present
        if '://' in endpoint:
            parsed = urlparse(endpoint)
            if not parsed.hostname:
                raise ValueError(f"Invalid MinIO endpoint format: {endpoint}")
            endpoint = f"{parsed.hostname}:{parsed.port}" if parsed.port else parsed.hostname
        else:
            # Remove any path component if accidentally included
            endpoint = endpoint.split('/')[0].split('?')[0]
        
        return endpoint.strip()

    def __init__(self):
        # Sanitize endpoint to ensure it's in the correct format (hostname:port)
        sanitized_endpoint = self._sanitize_endpoint(settings.minio_endpoint)
        
        self.client = Minio(
            endpoint=sanitized_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        self.bucket_name = "dataset-media"
        self._ensure_bucket_exists()
        self._presigned_cache = {}
        self._resized_cache = {}  # Cache for resized image URLs
        self._image_cache = {}    # Cache for processed images

        # Automatic resizing configuration
        self.auto_resize_config = {
            "enabled": True,
            "sizes": {
                "thumbnail": (150, 150),
                "small": (300, 300),
                "medium": (600, 600),
                "large": (1200, 1200)
            },
            "quality": {
                "thumbnail": 80,
                "small": 85,
                "medium": 90,
                "large": 95
            },
            "formats": {
                "thumbnail": "jpeg",
                "small": "jpeg",
                "medium": "jpeg",
                "large": "jpeg"
            },
        }

    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if it doesn't"""
        try:
            if not self.client.bucket_exists(bucket_name=self.bucket_name):
                self.client.make_bucket(bucket_name=self.bucket_name)
                print(f"Created bucket: {self.bucket_name}")
        except S3Error as e:
            print(f"Error creating bucket: {e}")

    def _generate_object_name(self, file: UploadFile, folder: str = "files") -> str:
        """Generate a unique object name for the file"""
        file_extension = os.path.splitext(
            file.filename)[1] if file.filename else ""
        unique_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{folder}/{timestamp}_{unique_id}{file_extension}"

    def _validate_file(self, file: UploadFile) -> None:
        """Validate file before upload with optimized checks"""
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No filename provided"
            )

        # Optimized content type detection
        detected_content_type = file.content_type
        if not detected_content_type:
            # Fast filename-based detection
            filename_lower = file.filename.lower()
            if filename_lower.endswith('.png'):
                detected_content_type = 'image/png'
            elif filename_lower.endswith(('.jpg', '.jpeg')):
                detected_content_type = 'image/jpeg'
            elif filename_lower.endswith('.gif'):
                detected_content_type = 'image/gif'
            elif filename_lower.endswith('.webp'):
                detected_content_type = 'image/webp'
            else:
                detected_content_type = 'application/octet-stream'

        # Optimized file size check - avoid reading content if possible
        file_size = file.size if hasattr(file, 'size') and file.size else 0
        if file_size == 0:
            # Only read content if size is not available
            current_pos = file.file.tell()
            file.file.seek(0, 2)  # Seek to end
            file_size = file.file.tell()
            file.file.seek(current_pos)  # Reset to original position

        if file_size > settings.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {settings.max_file_size} bytes"
            )

        # Fast file type validation using set lookup
        allowed_types_set = set(settings.allowed_file_types)
        if detected_content_type not in allowed_types_set:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type: {detected_content_type}. Allowed types: {settings.allowed_file_types}"
            )

    def _validate_video_file(self, file: UploadFile) -> None:
        """Validate video file before upload with optimized checks"""
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No filename provided"
            )

        # Optimized content type detection for videos
        detected_content_type = file.content_type
        if not detected_content_type:
            # Fast filename-based detection for videos
            filename_lower = file.filename.lower()
            if filename_lower.endswith('.mp4'):
                detected_content_type = 'video/mp4'
            elif filename_lower.endswith('.avi'):
                detected_content_type = 'video/avi'
            elif filename_lower.endswith('.mov'):
                detected_content_type = 'video/mov'
            elif filename_lower.endswith('.wmv'):
                detected_content_type = 'video/wmv'
            elif filename_lower.endswith('.flv'):
                detected_content_type = 'video/flv'
            elif filename_lower.endswith('.webm'):
                detected_content_type = 'video/webm'
            else:
                detected_content_type = 'application/octet-stream'

        # Optimized file size check - avoid reading content if possible
        file_size = file.size if hasattr(file, 'size') and file.size else 0
        if file_size == 0:
            # Only read content if size is not available
            current_pos = file.file.tell()
            file.file.seek(0, 2)  # Seek to end
            file_size = file.file.tell()
            file.file.seek(current_pos)  # Reset to original position

        if file_size > settings.max_video_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Video file too large. Maximum size: {settings.max_video_file_size} bytes ({settings.max_video_file_size // (1024*1024)}MB)"
            )

        # Video-specific file type validation
        allowed_video_types = {
            'video/mp4', 'video/avi', 'video/mov', 'video/wmv',
            'video/flv', 'video/webm'
        }
        if detected_content_type not in allowed_video_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid video file type: {detected_content_type}. Allowed video types: {list(allowed_video_types)}"
            )

    async def upload_file(self, file: UploadFile, folder: str = "files", auto_resize: bool = True) -> ResponseModel:
        """Upload a file to MinIO with automatic image resizing (default enabled)"""
        return await self.upload_file_with_auto_resize(file, folder, auto_resize)

    async def upload_multiple_image(self, files: List[UploadFile], folder: str = "files", auto_resize: bool = True) -> ResponseModel:
        """Upload multiple files to MinIO with automatic image resizing (default enabled)"""
        return await self.upload_multiple_image_with_auto_resize(files, folder, auto_resize)

    async def upload_file_without_resize(self, file: UploadFile, folder: str = "files") -> ResponseModel:
        """Upload a file to MinIO without any resizing (for videos and other non-image files)"""
        try:
            # Use video validation for video files, regular validation for others
            if file.content_type and file.content_type.startswith('video/'):
                self._validate_video_file(file)
            else:
                self._validate_file(file)

            # Detect content type
            detected_content_type = file.content_type
            if not detected_content_type:
                if file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm')):
                    detected_content_type = 'video/mp4'
                elif file.filename.lower().endswith(('.pdf', '.doc', '.docx')):
                    detected_content_type = 'application/pdf' if file.filename.lower().endswith('.pdf') else 'application/msword'
                else:
                    detected_content_type = 'application/octet-stream'

            object_name = self._generate_object_name(file, folder)

            # Read file content
            file.file.seek(0)
            content = file.file.read()
            file_size = len(content)

            # Upload file using content directly
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=io.BytesIO(content),
                length=file_size,
                content_type=detected_content_type
            )

            # Generate public URL
            public_url = f"{settings.minio_public_url}/{self.bucket_name}/{object_name}"

            return ResponseModel(
                success=True,
                data={
                    "object_name": object_name,
                    "filename": file.filename,
                    "content_type": detected_content_type,
                    "size": file_size,
                    "url": public_url,
                    "uploaded_at": datetime.utcnow().isoformat()
                },
                message="File uploaded successfully without resizing"
            )

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"File upload failed: {str(e)}"
            )

    async def upload_multiple_video(self, files: List[UploadFile], folder: str = "files") -> ResponseModel:
        """Upload multiple video files to MinIO without resizing"""
        try:
            uploaded_files = []

            for file in files:
                upload_result = await self.upload_file_without_resize(file, folder)
                if upload_result.success:
                    uploaded_files.append(upload_result.data)

            return ResponseModel(
                success=True,
                data={
                    "files": uploaded_files,
                    "count": len(uploaded_files),
                    "uploaded_at": datetime.utcnow().isoformat()
                },
                message=f"Successfully uploaded {len(uploaded_files)} video files"
            )

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Multiple video upload failed: {str(e)}"
            )

    async def delete_file(self, object_name: str) -> ResponseModel:
        """Delete a file from MinIO"""
        try:
            self.client.remove_object(bucket_name=self.bucket_name, object_name=object_name)

            return ResponseModel(
                success=True,
                data={
                    "object_name": object_name,
                    "deleted_at": datetime.utcnow().isoformat()
                },
                message="File deleted successfully"
            )

        except S3Error as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"MinIO error: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Delete failed: {str(e)}"
            )

    async def move_delete_file(self, object_name: str, folder: str = "deleted_files") -> ResponseModel:
        try:    
            # Extract filename from object_name
            # Handle both paths like "users/filename.jpg" and just "filename.jpg"
            path_parts = object_name.split('/')
            filename = path_parts[-1]
            
            new_object_name = f"{folder}/{filename}"

            # MinIO Python client uses copy_object for S3-compatible copy operation
            # We need to check if object exists first
            try:
                # Check if source object exists
                self.client.stat_object(bucket_name=self.bucket_name, object_name=object_name)

                # Copy the object to new location using CopySource
                copy_source = CopySource(self.bucket_name, object_name)
                self.client.copy_object(
                    bucket_name=self.bucket_name,
                    object_name=new_object_name,
                    source=copy_source
                )

                # Delete the original object after successful copy
                self.client.remove_object(bucket_name=self.bucket_name, object_name=object_name)

                return ResponseModel(
                    success=True,
                    data={
                        "original_object_name": object_name,
                        "moved_to": new_object_name,
                        "moved_at": datetime.utcnow().isoformat()
                    },
                    message="File moved to deleted folder successfully"
                )

            except S3Error as stat_error:
                if stat_error.code == 'NoSuchKey':
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"File not found: {object_name}"
                    )
                else:
                    raise

        except HTTPException:
            raise
        except S3Error as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"MinIO error: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Move delete failed: {str(e)}"
            )

    async def get_file_url(self, object_name: str, expires_in_hours: int = 24) -> str:
        """
        Get a presigned URL for a file.
        
        Note: Presigned URLs are generated using the MinIO endpoint configuration.
        For local development, ensure minio_endpoint matches the public URL base.
        The presigned URL signature is cryptographically tied to the exact URL format.
        """
        try:
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=timedelta(hours=expires_in_hours)
            )
            return url
        except S3Error as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"MinIO error: {str(e)}"
            )

    def extract_object_name_from_url(self, url: str) -> str:
        """Extract object name from MinIO URL (handles both public URLs and presigned URLs)"""
        try:
            if not url:
                return url
            
            # Remove query parameters if present (for presigned URLs)
            if '?' in url:
                url = url.split('?')[0]
            
            # Handle full URLs (with http:// or https://)
            if url.startswith('http://') or url.startswith('https://'):
                # Extract path after bucket name
                bucket_prefix = f"/{self.bucket_name}/"
                if bucket_prefix in url:
                    # Find the position after bucket name
                    idx = url.find(bucket_prefix) + len(bucket_prefix)
                    return url[idx:]
                # If bucket name not found, try to extract from minio_public_url pattern
                base_url = f"{settings.minio_public_url}/{self.bucket_name}/"
                if url.startswith(base_url):
                    return url.replace(base_url, "")
                # Fallback: try parsing as URL
                try:
                    parsed = urlparse(url)
                    path = parsed.path
                    if path.startswith(f"/{self.bucket_name}/"):
                        return path.replace(f"/{self.bucket_name}/", "", 1)
                except Exception:
                    pass
            
            # If it's already just an object name/path (no protocol), return as-is
            return url
        except Exception:
            return url

    async def get_presigned_urls_for_file(self, image_urls: List[str], expires_in_hours: int = 24) -> List[str]:
        """Generate presigned URLs for a list of image URLs with parallel processing"""
        try:
            if not image_urls:
                return []

            tasks = []
            for url in image_urls:
                if url:
                    # Check cache first
                    cache_key = f"presigned_{url}_{expires_in_hours}"
                    if cache_key in self._presigned_cache:
                        tasks.append(asyncio.create_task(
                            self._get_cached_presigned(url, cache_key)))
                    else:
                        tasks.append(asyncio.create_task(
                            self._get_single_presigned_url(url, expires_in_hours)))
                else:
                    tasks.append(asyncio.create_task(self._return_none()))

            # Execute all tasks in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results and handle exceptions
            presigned_urls = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    # Only log as warning if it's not a NoSuchKey error (file moved to deleted folder)
                    if "NoSuchKey" not in str(result):
                        print(
                            f"Warning: Failed to get presigned URL for {image_urls[i]}: {str(result)}")
                    presigned_urls.append(None)
                else:
                    presigned_urls.append(result)
                    # Cache successful results
                    if result and image_urls[i]:
                        cache_key = f"presigned_{image_urls[i]}_{expires_in_hours}"
                        self._presigned_cache[cache_key] = result

            return presigned_urls
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate presigned URLs: {str(e)}"
            )

    async def _get_single_presigned_url(self, url: str, expires_in_hours: int) -> Optional[str]:
        """Get presigned URL for a single image"""
        try:
            object_name = self.extract_object_name_from_url(url)
            # Check if object exists before generating presigned URL
            try:
                self.client.stat_object(bucket_name=self.bucket_name, object_name=object_name)
                # Generate presigned URL with expiration
                presigned_url = await self.get_file_url(object_name, expires_in_hours)
                return presigned_url
            except S3Error as e:
                if e.code == 'NoSuchKey':
                    # This is expected when files have been moved to deleted folders
                    # Don't log as warning since it's normal behavior
                    return None
                else:
                    print(
                        f"Warning: MinIO error for object {object_name}: {str(e)}")
                    return None
        except HTTPException as e:
            # If file doesn't exist, log the error and return None
            print(f"Warning: File not found in MinIO: {url} - {str(e)}")
            return None

    async def _get_cached_presigned(self, url: str, cache_key: str) -> Optional[str]:
        """Get cached presigned URL"""
        return self._presigned_cache.get(cache_key)

    async def _return_none(self) -> None:
        """Helper method to return None for empty URLs"""
        return None

    def _is_image_file(self, content_type: str, filename: str = None) -> bool:
        """Check if file is an image based on content type and filename"""
        image_types = ['image/jpeg', 'image/jpg',
                       'image/png', 'image/gif', 'image/webp']
        if content_type in image_types:
            return True

        if filename:
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            return any(filename.lower().endswith(ext) for ext in image_extensions)

        return False

    async def _generate_resized_images(self, image_data: bytes, original_object_name: str) -> Dict[str, str]:
        """Generate multiple resized versions of an image with parallel processing and memory optimization"""
        try:
            # Check cache first
            cache_key = f"processed_{original_object_name}"
            if cache_key in self._image_cache:
                return self._image_cache[cache_key]

            # Open original image once
            original_image = Image.open(io.BytesIO(image_data))

            # Convert to RGB if necessary (optimized)
            if original_image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new(
                    'RGB', original_image.size, (255, 255, 255))
                if original_image.mode == 'P':
                    original_image = original_image.convert('RGBA')
                background.paste(original_image, mask=original_image.split(
                )[-1] if original_image.mode == 'RGBA' else None)
                original_image = background
            elif original_image.mode != 'RGB':
                original_image = original_image.convert('RGB')

            # Generate all sizes in parallel
            tasks = []
            size_configs = list(self.auto_resize_config["sizes"].items())

            for size_name, (width, height) in size_configs:
                tasks.append(
                    asyncio.create_task(
                        self._generate_single_resized_image(
                            original_image, original_object_name, size_name, width, height
                        )
                    )
                )

            # Execute all tasks in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            resized_objects = {}
            for i, result in enumerate(results):
                size_name = size_configs[i][0]
                if isinstance(result, Exception):
                    print(
                        f"Warning: Failed to generate {size_name} size for {original_object_name}: {str(result)}")
                elif result:
                    resized_objects[size_name] = result

            # Cache the result
            self._image_cache[cache_key] = resized_objects

            # Clean up memory
            original_image.close()
            del original_image

            return resized_objects

        except Exception as e:
            print(
                f"Error generating resized images for {original_object_name}: {str(e)}")
            return {}

    async def _generate_single_resized_image(self, original_image: Image.Image, original_object_name: str,
                                             size_name: str, width: int, height: int) -> Optional[str]:
        """Generate a single resized image with memory optimization"""
        try:
            # Create resized image
            resized_image = original_image.copy()
            resized_image.thumbnail((width, height), Image.Resampling.LANCZOS)

            # Convert to bytes with optimization
            output_format = self.auto_resize_config["formats"][size_name].upper(
            )
            quality = self.auto_resize_config["quality"][size_name]

            resized_io = io.BytesIO()
            resized_image.save(
                resized_io,
                format=output_format,
                quality=quality,
                optimize=True,
                progressive=True  # Better compression for web
            )
            resized_io.seek(0)

            # Generate object name for resized image
            resized_object_name = self._generate_resized_object_name(
                original_object_name, size_name)

            # Upload resized image
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=resized_object_name,
                data=resized_io,
                length=resized_io.getbuffer().nbytes,
                content_type=f'image/{self.auto_resize_config["formats"][size_name]}'
            )

            # Clean up memory
            resized_image.close()
            del resized_image
            resized_io.close()

            return resized_object_name

        except Exception as e:
            print(
                f"Error generating {size_name} for {original_object_name}: {str(e)}")
            return None

    def _generate_resized_object_name(self, original_object_name: str, size_name: str) -> str:
        """Generate object name for resized image"""
        path_parts = original_object_name.split('/')
        if len(path_parts) > 1:
            folder = '/'.join(path_parts[:-1])
            filename = path_parts[-1]
        else:
            folder = "resized"
            filename = original_object_name

        name, ext = os.path.splitext(filename)
        resized_filename = f"{name}_{size_name}.{self.auto_resize_config['formats'][size_name]}"

        return f"{folder}/resized/{resized_filename}"

    async def upload_file_with_auto_resize(self, file: UploadFile, folder: str = "files", auto_resize: bool = True) -> ResponseModel:
        """Upload a file to MinIO with automatic image resizing"""
        try:
            self._validate_file(file)

            # Detect content type
            detected_content_type = file.content_type
            if not detected_content_type:
                if file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    detected_content_type = 'image/png' if file.filename.lower().endswith('.png') else 'image/jpeg'
                else:
                    detected_content_type = 'application/octet-stream'

            object_name = self._generate_object_name(file, folder)

            # Optimized file handling - read content once
            file.file.seek(0)
            content = file.file.read()
            file_size = len(content)
            # Don't reset file pointer - we'll use content directly

            # Upload original file using content directly
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=io.BytesIO(content),
                length=file_size,
                content_type=detected_content_type
            )

            # Generate public URL for original
            public_url = f"{settings.minio_public_url}/{self.bucket_name}/{object_name}"

            response_data = {
                "object_name": object_name,
                "filename": file.filename,
                "content_type": detected_content_type,
                "size": file_size,
                "url": public_url,
                "uploaded_at": datetime.utcnow().isoformat()
            }

            # Generate resized versions if it's an image and auto_resize is enabled
            if auto_resize and self.auto_resize_config["enabled"] and self._is_image_file(detected_content_type, file.filename):
                try:
                    resized_objects = await self._generate_resized_images(content, object_name)
                    if resized_objects:
                        response_data["resized_versions"] = {}
                        for size_name, resized_object_name in resized_objects.items():
                            resized_url = f"{settings.minio_public_url}/{self.bucket_name}/{resized_object_name}"
                            response_data["resized_versions"][size_name] = {
                                "object_name": resized_object_name,
                                "url": resized_url,
                                "size": self.auto_resize_config["sizes"][size_name]
                            }
                except Exception as e:
                    print(
                        f"Warning: Auto-resize failed for {object_name}: {str(e)}")
                    # Continue without resized versions

            return ResponseModel(
                success=True,
                data=response_data,
                message="File uploaded successfully with auto-resizing" if auto_resize and self._is_image_file(
                    detected_content_type, file.filename) else "File uploaded successfully"
            )

        except HTTPException:
            raise
        except S3Error as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"MinIO error: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Upload failed: {str(e)}"
            )

    async def upload_multiple_image_with_auto_resize(self, files: List[UploadFile], folder: str = "files", auto_resize: bool = True) -> ResponseModel:
        """Upload multiple files to MinIO with automatic image resizing"""
        try:
            uploaded_files = []

            for file in files:
                upload_result = await self.upload_file_with_auto_resize(file, folder, auto_resize)
                if upload_result.success:
                    uploaded_files.append(upload_result.data)

            return ResponseModel(
                success=True,
                data={
                    "files": uploaded_files,
                    "count": len(uploaded_files),
                    "uploaded_at": datetime.utcnow().isoformat()
                },
                message=f"Successfully uploaded {len(uploaded_files)} files with auto-resizing" if auto_resize else f"Successfully uploaded {len(uploaded_files)} files"
            )

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Multiple file upload failed: {str(e)}"
            )

    async def get_resized_image_url(self, original_url: str, size: str = "medium", expires_in_hours: int = 24) -> Optional[str]:
        """Get URL for a specific resized version of an image"""
        try:
            if not original_url:
                return None

            object_name = self.extract_object_name_from_url(original_url)
            resized_object_name = self._generate_resized_object_name(
                object_name, size)

            # Check if resized version exists
            try:
                self.client.stat_object(bucket_name=self.bucket_name, object_name=resized_object_name)
                return await self.get_file_url(resized_object_name, expires_in_hours)
            except S3Error as e:
                if e.code == 'NoSuchKey':
                    # Try to generate the resized version
                    try:
                        # Download original image
                        response = self.client.get_object(
                            bucket_name=self.bucket_name, object_name=object_name)
                        image_data = response.read()
                        response.close()
                        response.release_conn()

                        # Generate resized versions
                        resized_objects = await self._generate_resized_images(image_data, object_name)
                        if size in resized_objects:
                            return await self.get_file_url(resized_objects[size], expires_in_hours)
                        else:
                            return None
                    except Exception as gen_e:
                        print(
                            f"Warning: Failed to generate resized version for {original_url}: {str(gen_e)}")
                        return None
                else:
                    raise e

        except Exception as e:
            print(
                f"Warning: Failed to get resized image URL for {original_url}: {str(e)}")
            return None

    async def get_resized_image_urls(self, original_url: str, expires_in_hours: int = 24) -> Dict[str, Optional[str]]:
        """Get URLs for all available resized versions of an image with caching and parallel processing"""
        try:
            if not original_url:
                return {}

            # Check cache first
            cache_key = f"resized_{original_url}_{expires_in_hours}"
            if cache_key in self._resized_cache:
                return self._resized_cache[cache_key]

            # Generate all resized URLs in parallel
            tasks = []
            size_names = list(self.auto_resize_config["sizes"].keys())

            for size_name in size_names:
                tasks.append(
                    asyncio.create_task(
                        self.get_resized_image_url(
                            original_url, size_name, expires_in_hours)
                    )
                )

            # Execute all tasks in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Build result dictionary
            urls = {}
            for i, result in enumerate(results):
                size_name = size_names[i]
                if isinstance(result, Exception):
                    print(
                        f"Warning: Failed to get {size_name} for {original_url}: {str(result)}")
                    urls[size_name] = None
                else:
                    urls[size_name] = result

            # Cache the result
            self._resized_cache[cache_key] = urls

            return urls

        except Exception as e:
            print(
                f"Warning: Failed to get resized image URLs for {original_url}: {str(e)}")
            return {}

    def configure_auto_resize(self, enabled: bool = None, sizes: Dict[str, tuple] = None,
                              quality: Dict[str, int] = None, formats: Dict[str, str] = None,
                              image_types: Dict[str, Dict] = None) -> None:
        """Configure automatic resizing settings"""
        if enabled is not None:
            self.auto_resize_config["enabled"] = enabled

        if sizes is not None:
            self.auto_resize_config["sizes"].update(sizes)

        if quality is not None:
            self.auto_resize_config["quality"].update(quality)

        if formats is not None:
            self.auto_resize_config["formats"].update(formats)

    def get_auto_resize_status(self) -> Dict[str, Any]:
        """Get current auto-resize configuration status"""
        return {
            "enabled": self.auto_resize_config["enabled"],
            "available_sizes": list(self.auto_resize_config["sizes"].keys()),
            "configuration": self.auto_resize_config,
            "cache_stats": {
                "presigned_cache_size": len(self._presigned_cache),
                "resized_cache_size": len(self._resized_cache),
                "image_cache_size": len(self._image_cache)
            }
        }

    def clear_caches(self) -> None:
        """Clear all caches to free memory"""
        self._presigned_cache.clear()
        self._resized_cache.clear()
        self._image_cache.clear()
        print("All caches cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics for monitoring"""
        return {
            "presigned_cache_size": len(self._presigned_cache),
            "resized_cache_size": len(self._resized_cache),
            "image_cache_size": len(self._image_cache),
            "total_cache_entries": len(self._presigned_cache) + len(self._resized_cache) + len(self._image_cache)
        }

    async def get_batch_resized_urls(self, image_urls: List[str], expires_in_hours: int = 24) -> List[Dict[str, Optional[str]]]:
        """Get resized URLs for multiple images in parallel for better performance"""
        try:
            if not image_urls:
                return []

            # Process all images in parallel
            tasks = []
            for url in image_urls:
                if url:
                    tasks.append(
                        asyncio.create_task(
                            self.get_resized_image_urls(url, expires_in_hours)
                        )
                    )
                else:
                    tasks.append(asyncio.create_task(asyncio.sleep(0)))

            # Execute all tasks in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            batch_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(
                        f"Warning: Failed to get resized URLs for {image_urls[i]}: {str(result)}")
                    batch_results.append({})
                else:
                    batch_results.append(result)

            return batch_results

        except Exception as e:
            print(f"Warning: Failed to get batch resized URLs: {str(e)}")
            return [{} for _ in image_urls]


# Lazy singleton for legacy/direct MinIO usage. Prefer storage_service for app code.
_minio_instance: Optional["MinIOService"] = None


def _get_minio_service() -> "MinIOService":
    global _minio_instance
    if _minio_instance is None:
        _minio_instance = MinIOService()
    return _minio_instance


# Backward compat: expose same interface so "from file_service import minio_service" still works.
class _MinioServiceProxy:
    """Proxy so minio_service.upload_file() etc. work without instantiating MinIO until first use."""

    def __getattr__(self, name: str):
        return getattr(_get_minio_service(), name)


minio_service = _MinioServiceProxy()
