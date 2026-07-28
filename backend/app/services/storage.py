"""
对象存储服务 — MinIO (S3 兼容)
负责原始 HTML、截图等大文件的存储与读取
懒初始化 — MinIO 不可用时降级为内存缓存
"""
import io
from typing import Optional
from app.core.config import settings


class StorageService:
    """MinIO 存储封装，懒初始化"""

    def __init__(self):
        self._client = None
        self._fallback: dict[str, bytes] = {}  # 内存降级缓存

    def _get_client(self):
        if self._client is None:
            import boto3
            from botocore.config import Config
            self._client = boto3.client(
                "s3",
                endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
                aws_access_key_id=settings.MINIO_ACCESS_KEY,
                aws_secret_access_key=settings.MINIO_SECRET_KEY,
                config=Config(connect_timeout=5, read_timeout=30),
            )
            # 确保 bucket 存在
            try:
                self._client.head_bucket(Bucket=settings.MINIO_BUCKET)
            except Exception:
                try:
                    self._client.create_bucket(Bucket=settings.MINIO_BUCKET)
                except Exception:
                    pass
        return self._client

    def put(self, key: str, data: bytes, content_type: str = "text/html") -> bool:
        """上传文件；裸跑默认写本地目录，MinIO 可用时再双写。"""
        local_ok = self._put_local(key, data)
        if self._prefer_local_only():
            self._fallback[key] = data
            return local_ok or True

        try:
            client = self._get_client()
            client.put_object(
                Bucket=settings.MINIO_BUCKET,
                Key=key,
                Body=io.BytesIO(data),
                ContentType=content_type,
            )
            self._fallback.pop(key, None)
            return True
        except Exception:
            self._fallback[key] = data
            return True

    def get(self, key: str) -> Optional[bytes]:
        """下载文件：先内存，再本地目录，再 MinIO"""
        if key in self._fallback:
            return self._fallback[key]
        local = self._get_local(key)
        if local is not None:
            return local
        if self._prefer_local_only():
            return None
        try:
            client = self._get_client()
            response = client.get_object(Bucket=settings.MINIO_BUCKET, Key=key)
            return response["Body"].read()
        except Exception:
            return None

    def _prefer_local_only(self) -> bool:
        endpoint = (settings.MINIO_ENDPOINT or "").strip().lower()
        return endpoint in {"", "minio", "minio:9000", "127.0.0.1:0"}

    def _put_local(self, key: str, data: bytes) -> bool:
        try:
            from pathlib import Path

            path = Path(settings.LOCAL_OBJECT_STORE_DIR) / key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            return True
        except Exception:
            return False

    def _get_local(self, key: str) -> Optional[bytes]:
        try:
            from pathlib import Path

            path = Path(settings.LOCAL_OBJECT_STORE_DIR) / key
            if path.is_file():
                return path.read_bytes()
        except Exception:
            return None
        return None

    def delete(self, key: str):
        """删除文件"""
        self._fallback.pop(key, None)
        try:
            client = self._get_client()
            client.delete_object(Bucket=settings.MINIO_BUCKET, Key=key)
        except Exception:
            pass


# 全局单例
storage = StorageService()
