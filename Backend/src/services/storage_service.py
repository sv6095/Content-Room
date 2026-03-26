"""
Storage Service for ContentOS

AWS S3-first with Firebase and local fallback:
1. AWS S3 - PRIMARY for production
2. Firebase Storage - Great fallback with free tier
3. Local filesystem - Ultimate fallback

Handles media uploads for social media publishing.
"""
import logging
import os
import uuid
import mimetypes
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, BinaryIO, Tuple
from abc import ABC, abstractmethod
from urllib.parse import unquote, urlparse

from config import settings

logger = logging.getLogger(__name__)


def parse_s3_bucket_and_key(reference: str) -> Optional[Tuple[str, str]]:
    """
    Extract (bucket, key) from s3:// URIs or common HTTPS S3 URL shapes.

    Supports virtual-hosted URLs (bucket.s3.region.amazonaws.com/key) and
    path-style (s3.region.amazonaws.com/bucket/key). Path-style must be
    distinguished from virtual-hosted — the latter incorrectly used the full
    path as the object key when the bucket was private.
    """
    if not reference or not str(reference).strip():
        return None
    raw = str(reference).strip()
    if raw.startswith("s3://"):
        rest = raw[5:]
        slash = rest.find("/")
        if slash == -1:
            ub = unquote(rest)
            return (ub, "") if ub else None
        b, k = rest[:slash], rest[slash + 1 :]
        b, k = unquote(b), unquote(k)
        return (b, k) if b and k else None

    if not raw.lower().startswith("http"):
        return None
    try:
        parsed = urlparse(raw)
        host = (parsed.netloc or "").strip().lower()
        path = unquote((parsed.path or "").lstrip("/"))
        if not host or not path:
            return None
        # Virtual-hosted: mybucket.s3.ap-south-1.amazonaws.com/object/key
        if ".s3." in host and not (host.startswith("s3.") or host.startswith("s3-")):
            bucket = host.split(".s3.", 1)[0]
            return (bucket, path) if bucket else None
        # Path-style: s3.ap-south-1.amazonaws.com/bucket/object/key
        if host.startswith("s3.") or host.startswith("s3-"):
            parts = path.split("/", 1)
            if len(parts) == 2 and parts[0] and parts[1]:
                return (parts[0], unquote(parts[1]))
    except Exception:
        return None
    return None


# ============================================
# Storage Errors
# ============================================

class StorageError(Exception):
    """Base exception for storage errors."""
    pass


class UploadError(StorageError):
    """Upload failed."""
    pass


class DownloadError(StorageError):
    """Download failed."""
    pass


# ============================================
# Abstract Base Provider
# ============================================

class BaseStorageProvider(ABC):
    """Base class for storage providers."""
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is configured and available."""
        pass
    
    @abstractmethod
    async def upload(
        self, 
        file_data: bytes, 
        filename: str, 
        content_type: str,
        folder: str = "uploads"
    ) -> Dict[str, Any]:
        """Upload a file and return URL and metadata."""
        pass
    
    @abstractmethod
    async def delete(self, file_path: str) -> bool:
        """Delete a file."""
        pass
    
    @abstractmethod
    async def get_url(self, file_path: str, expires_in: int = 3600) -> str:
        """Get a URL to access the file."""
        pass


# ============================================
# AWS S3 Provider
# ============================================

class S3StorageProvider(BaseStorageProvider):
    """AWS S3 storage provider."""
    
    def __init__(self):
        self.client = None
        self.bucket_name = getattr(settings, 's3_bucket_name', None)
        
        if settings.aws_configured and self.bucket_name:
            try:
                import boto3
                self.client = boto3.client(
                    's3',
                    region_name=settings.aws_region,
                )
                logger.info(f"AWS S3 initialized with bucket: {self.bucket_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize AWS S3: {e}")
    
    def is_available(self) -> bool:
        return self.client is not None and self.bucket_name is not None
    
    async def upload(
        self, 
        file_data: bytes, 
        filename: str, 
        content_type: str,
        folder: str = "uploads"
    ) -> Dict[str, Any]:
        if not self.is_available():
            raise StorageError("S3 not configured")
        
        try:
            # Generate unique key
            ext = Path(filename).suffix
            unique_name = f"{uuid.uuid4().hex}{ext}"
            key = f"{folder}/{datetime.now().strftime('%Y/%m/%d')}/{unique_name}"
            
            # Upload to S3
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_data,
                ContentType=content_type,
            )
            
            # Generate URL
            url = f"https://{self.bucket_name}.s3.{settings.aws_region}.amazonaws.com/{key}"
            
            return {
                "url": url,
                "key": key,
                "provider": "s3",
                "bucket": self.bucket_name,
                "size": len(file_data),
                "content_type": content_type,
            }
            
        except Exception as e:
            logger.error(f"S3 upload error: {e}")
            raise UploadError(f"S3 upload failed: {e}")
    
    async def delete(self, file_path: str) -> bool:
        if not self.is_available():
            return False
        
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=file_path)
            return True
        except Exception as e:
            logger.error(f"S3 delete error: {e}")
            return False
    
    async def get_url(self, file_path: str, expires_in: int = 3600) -> str:
        if not self.is_available():
            raise StorageError("S3 not configured")
        
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': file_path},
                ExpiresIn=expires_in
            )
            return url
        except Exception as e:
            logger.error(f"S3 URL generation error: {e}")
            raise StorageError(f"Failed to generate URL: {e}")

    async def get_presigned_url_for_bucket_key(
        self, bucket: str, key: str, expires_in: int = 3600
    ) -> str:
        """Presign GET for an explicit bucket/key (any bucket the caller can access)."""
        if not self.client:
            raise StorageError("S3 not configured")
        if not bucket or not key:
            raise StorageError("bucket and key are required")
        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        except Exception as e:
            logger.error(f"S3 presign for bucket=%s key=%s: {e}", bucket, key[:80])
            raise StorageError(f"Failed to generate URL: {e}")

    async def create_presigned_upload_url(
        self,
        filename: str,
        content_type: str,
        folder: str = "uploads",
        expires_in: int = 900,
    ) -> Dict[str, Any]:
        if not self.is_available():
            raise StorageError("S3 not configured")
        ext = Path(filename).suffix
        unique_name = f"{uuid.uuid4().hex}{ext}"
        key = f"{folder}/{datetime.now().strftime('%Y/%m/%d')}/{unique_name}"
        url = self.client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket_name, "Key": key, "ContentType": content_type},
            ExpiresIn=expires_in,
        )
        return {"upload_url": url, "key": key, "provider": "s3"}


# ============================================
# Firebase Storage Provider
# ============================================

class FirebaseStorageProvider(BaseStorageProvider):
    """Firebase Storage provider - Great free tier fallback."""
    
    def __init__(self):
        self.bucket = None
        self.firebase_bucket = getattr(settings, 'firebase_storage_bucket', None)
        self.firebase_credentials = getattr(settings, 'firebase_credentials_path', None)
        
        if self.firebase_bucket:
            try:
                import firebase_admin
                from firebase_admin import credentials, storage
                
                # Initialize Firebase if not already done
                if not firebase_admin._apps:
                    if self.firebase_credentials and Path(self.firebase_credentials).exists():
                        cred = credentials.Certificate(self.firebase_credentials)
                        firebase_admin.initialize_app(cred, {
                            'storageBucket': self.firebase_bucket
                        })
                    else:
                        # Try default credentials (works in Google Cloud)
                        firebase_admin.initialize_app(options={
                            'storageBucket': self.firebase_bucket
                        })
                
                self.bucket = storage.bucket()
                logger.info(f"Firebase Storage initialized: {self.firebase_bucket}")
                
            except Exception as e:
                logger.warning(f"Failed to initialize Firebase Storage: {e}")
    
    def is_available(self) -> bool:
        return self.bucket is not None
    
    async def upload(
        self, 
        file_data: bytes, 
        filename: str, 
        content_type: str,
        folder: str = "uploads"
    ) -> Dict[str, Any]:
        if not self.is_available():
            raise StorageError("Firebase Storage not configured")
        
        try:
            # Generate unique path
            ext = Path(filename).suffix
            unique_name = f"{uuid.uuid4().hex}{ext}"
            blob_path = f"{folder}/{datetime.now().strftime('%Y/%m/%d')}/{unique_name}"
            
            # Upload to Firebase
            blob = self.bucket.blob(blob_path)
            blob.upload_from_string(file_data, content_type=content_type)
            
            # Make publicly accessible
            blob.make_public()
            
            return {
                "url": blob.public_url,
                "key": blob_path,
                "provider": "firebase",
                "bucket": self.firebase_bucket,
                "size": len(file_data),
                "content_type": content_type,
            }
            
        except Exception as e:
            logger.error(f"Firebase upload error: {e}")
            raise UploadError(f"Firebase upload failed: {e}")
    
    async def delete(self, file_path: str) -> bool:
        if not self.is_available():
            return False
        
        try:
            blob = self.bucket.blob(file_path)
            blob.delete()
            return True
        except Exception as e:
            logger.error(f"Firebase delete error: {e}")
            return False
    
    async def get_url(self, file_path: str, expires_in: int = 3600) -> str:
        if not self.is_available():
            raise StorageError("Firebase Storage not configured")
        
        try:
            blob = self.bucket.blob(file_path)
            url = blob.generate_signed_url(
                expiration=timedelta(seconds=expires_in)
            )
            return url
        except Exception as e:
            # Fallback to public URL if signing fails
            logger.warning(f"Signed URL failed, using public URL: {e}")
            blob = self.bucket.blob(file_path)
            return blob.public_url


# ============================================
# Local Filesystem Provider
# ============================================

class LocalStorageProvider(BaseStorageProvider):
    """Local filesystem storage - Ultimate fallback."""
    
    def __init__(self):
        self.storage_path = Path(getattr(settings, 'storage_path', './uploads'))
        self.base_url = getattr(settings, 'storage_base_url', '/uploads')
        
        # Ensure directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Local storage initialized: {self.storage_path}")
    
    def is_available(self) -> bool:
        return True  # Always available
    
    async def upload(
        self, 
        file_data: bytes, 
        filename: str, 
        content_type: str,
        folder: str = "uploads"
    ) -> Dict[str, Any]:
        try:
            # Generate unique path
            ext = Path(filename).suffix
            unique_name = f"{uuid.uuid4().hex}{ext}"
            date_folder = datetime.now().strftime('%Y/%m/%d')
            
            # Create directory structure
            target_dir = self.storage_path / folder / date_folder
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Save file
            file_path = target_dir / unique_name
            file_path.write_bytes(file_data)
            
            # Generate relative path
            relative_path = f"{folder}/{date_folder}/{unique_name}"
            
            return {
                "url": f"{self.base_url}/{relative_path}",
                "key": relative_path,
                "provider": "local",
                "path": str(file_path.absolute()),
                "size": len(file_data),
                "content_type": content_type,
            }
            
        except Exception as e:
            logger.error(f"Local storage error: {e}")
            raise UploadError(f"Local storage failed: {e}")
    
    async def delete(self, file_path: str) -> bool:
        try:
            full_path = self.storage_path / file_path
            if full_path.exists():
                full_path.unlink()
                return True
            return False
        except Exception as e:
            logger.error(f"Local delete error: {e}")
            return False
    
    async def get_url(self, file_path: str, expires_in: int = 3600) -> str:
        # Local files don't expire
        return f"{self.base_url}/{file_path}"


# ============================================
# Main Storage Service
# ============================================

class StorageService:
    """
    Storage service with automatic fallback.
    Priority: S3 → Firebase → Local
    """
    
    def __init__(self):
        s3_provider = ("s3", S3StorageProvider())
        if settings.media_private_only:
            self.providers = [s3_provider]
        else:
            self.providers = [
                s3_provider,
                ("firebase", FirebaseStorageProvider()),
                ("local", LocalStorageProvider()),
            ]
    
    def get_available_provider(self) -> tuple:
        """Get the first available provider."""
        for name, provider in self.providers:
            if provider.is_available():
                return name, provider
        raise StorageError("No storage providers available")
    
    async def upload(
        self, 
        file_data: bytes, 
        filename: str, 
        content_type: Optional[str] = None,
        folder: str = "uploads",
        preferred_provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a file with automatic fallback.
        
        Args:
            file_data: File contents as bytes
            filename: Original filename
            content_type: MIME type (auto-detected if not provided)
            folder: Folder to upload to
            preferred_provider: Specific provider to use
            
        Returns:
            Dict with url, key, provider, size, content_type
        """
        # Auto-detect content type
        if not content_type:
            content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        
        # Try preferred provider first
        if preferred_provider:
            for name, provider in self.providers:
                if name == preferred_provider and provider.is_available():
                    try:
                        return await provider.upload(file_data, filename, content_type, folder)
                    except UploadError:
                        logger.warning(f"Preferred provider {name} failed, trying fallbacks")
                        break
        
        # Try all providers in order
        errors = []
        for name, provider in self.providers:
            if not provider.is_available():
                continue
            
            try:
                logger.info(f"Uploading to {name}")
                result = await provider.upload(file_data, filename, content_type, folder)
                return result
            except UploadError as e:
                errors.append(f"{name}: {e}")
                logger.warning(f"Provider {name} failed, trying next")
                continue
        
        raise UploadError(f"All providers failed: {'; '.join(errors)}")
    
    async def delete(self, file_key: str, provider: str) -> bool:
        """Delete a file from the specified provider."""
        for name, prov in self.providers:
            if name == provider:
                return await prov.delete(file_key)
        return False
    
    async def get_url(self, file_key: str, provider: str, expires_in: int = 3600) -> str:
        """Get URL for a file from the specified provider."""
        for name, prov in self.providers:
            if name == provider:
                return await prov.get_url(file_key, expires_in)
        raise StorageError(f"Provider {provider} not found")

    async def get_presigned_url_for_file_reference(
        self, file_ref: str, expires_in: int = 3600
    ) -> str:
        """
        Return a presigned HTTPS URL for any S3 reference (s3:// or HTTPS S3 URL).
        Uses bucket and key from the reference so private buckets and
        MediaConvert/Nova outputs in alternate buckets are still accessible.
        """
        parsed = parse_s3_bucket_and_key(file_ref)
        if not parsed:
            raise StorageError("Not a recognized S3 URL or reference")
        bucket, key = parsed
        for name, prov in self.providers:
            if name == "s3" and prov.is_available():
                return await prov.get_presigned_url_for_bucket_key(
                    bucket, key, expires_in=expires_in
                )
        raise StorageError("S3 is not configured")
    
    def get_status(self) -> Dict[str, bool]:
        """Get availability status of all providers."""
        return {name: provider.is_available() for name, provider in self.providers}

    async def create_presigned_upload_url(
        self,
        filename: str,
        content_type: str,
        folder: str = "uploads",
        expires_in: int = 900,
    ) -> Dict[str, Any]:
        for name, provider in self.providers:
            if name == "s3" and provider.is_available():
                return await provider.create_presigned_upload_url(
                    filename=filename,
                    content_type=content_type,
                    folder=folder,
                    expires_in=expires_in,
                )
        raise StorageError("S3 provider is required for presigned uploads")


# ============================================
# Singleton Instance
# ============================================

_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get or create the storage service singleton."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
