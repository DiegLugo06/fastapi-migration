"""
Supabase Storage Service
Migrated from Flask app/extensions/supabase.py
"""
from supabase import Client
from typing import Dict, Any, List, Optional
import logging

from app.apps.authentication.utils import get_supabase_client
from app.config import get_env_var

logger = logging.getLogger(__name__)


class SupabaseStorageService:
    def __init__(self):
        self.client: Client = get_supabase_client()
        # Try BUCKET_NAME first (Flask convention), then SUPABASE_BUCKET_NAME
        self.bucket_name = get_env_var("BUCKET_NAME", get_env_var("SUPABASE_BUCKET_NAME", "documents"))

    def list_files(self, path: str) -> List[Dict[str, Any]]:
        """
        List files in a specific path in the Supabase bucket.

        Args:
            path: The path within the bucket to list files from.

        Returns:
            A list of files in the specified path, or empty list if no files are found.
        """
        try:
            response = self.client.storage.from_(self.bucket_name).list(path=path)
            if not response:
                return []
            return response
        except Exception as e:
            logger.error(f"Error listing files in Supabase: {str(e)}")
            return []

    def upload_file(self, file_path: str, file_content: bytes, content_type: str = "application/octet-stream") -> Dict[str, Any]:
        """
        Upload a file to Supabase storage.

        Args:
            file_path: The path where the file should be stored in the bucket.
            file_content: The file content as bytes.
            content_type: The MIME type of the file (default: "application/octet-stream").

        Returns:
            A dictionary with success status and response data, or error information.
        """
        try:
            response = self.client.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=file_content,
                file_options={"content-type": content_type}
            )
            return {"success": True, "data": response}
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            return {"success": False, "error": str(e)}

    def replace_file(self, file_path: str, file_content: bytes, content_type: str = "application/octet-stream") -> Dict[str, Any]:
        """
        Replace a file in Supabase storage. This method first deletes the existing file
        (if it exists) and then uploads the new file.

        Args:
            file_path: The path where the file should be stored in the bucket.
            file_content: The new file content as bytes.
            content_type: The MIME type of the file (default: "application/octet-stream").

        Returns:
            A dictionary with success status and response data, or error information.
        """
        try:
            # First, try to delete the existing file (ignore errors if file doesn't exist)
            try:
                self.client.storage.from_(self.bucket_name).remove([file_path])
            except Exception:
                # File might not exist, which is fine for replacement
                pass

            # Upload the new file
            response = self.client.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=file_content,
                file_options={"content-type": content_type}
            )
            return {"success": True, "data": response}
        except Exception as e:
            logger.error(f"Error replacing file: {str(e)}")
            return {"success": False, "error": str(e)}

    def generate_signed_url(self, file_path: str, expires_in: int = 3600) -> Optional[str]:
        """
        Generate a signed URL for a file in Supabase.

        Args:
            file_path: The path to the file in the bucket.
            expires_in: The expiration time for the signed URL in seconds (default: 3600).

        Returns:
            A signed URL for the file, or None if the operation fails.
        """
        try:
            signed_url_response = self.client.storage.from_(self.bucket_name).create_signed_url(
                file_path, expires_in=expires_in
            )
            if 'signedURL' not in signed_url_response:
                return None
            return signed_url_response['signedURL']
        except Exception as e:
            logger.error(f"Error generating signed URL: {str(e)}")
            return None


# Initialize the Supabase storage service
supabase_storage = SupabaseStorageService()

