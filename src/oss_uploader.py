"""
阿里云OSS上传模块
"""
import logging
import os
import time
from pathlib import Path
from typing import Optional

import oss2

import config

logger = logging.getLogger(__name__)


class OSSUploader:
    """阿里云OSS上传器"""

    def __init__(self):
        self.access_key_id = config.OSS_ACCESS_KEY_ID
        self.access_key_secret = config.OSS_ACCESS_KEY_SECRET
        self.bucket_name = config.OSS_BUCKET_NAME
        self.endpoint = config.OSS_ENDPOINT
        self.prefix = config.OSS_PREFIX

        self._bucket = None
        self._initialized = False

    def _init_bucket(self) -> bool:
        """初始化OSS Bucket"""
        if self._initialized:
            return self._bucket is not None

        if not all([self.access_key_id, self.access_key_secret,
                    self.bucket_name, self.endpoint]):
            logger.warning("OSS配置不完整，跳过上传")
            self._initialized = True
            return False

        try:
            auth = oss2.Auth(self.access_key_id, self.access_key_secret)
            self._bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)
            self._initialized = True
            logger.info(f"OSS Bucket初始化成功: {self.bucket_name}")
            return True
        except Exception as e:
            logger.error(f"OSS初始化失败: {e}")
            self._initialized = True
            return False

    def upload_chart(self, file_path: str, custom_name: Optional[str] = None) -> Optional[str]:
        """
        上传图表文件到OSS

        Args:
            file_path: 本地文件路径
            custom_name: 自定义文件名（可选）

        Returns:
            OSS公开访问URL，失败返回None
        """
        if not self._init_bucket():
            return None

        path = Path(file_path)
        if not path.exists():
            logger.warning(f"文件不存在: {file_path}")
            return None

        # 生成OSS文件名
        if custom_name:
            oss_key = f"{self.prefix}{custom_name}"
        else:
            timestamp = int(time.time())
            oss_key = f"{self.prefix}{path.stem}_{timestamp}{path.suffix}"

        try:
            # 上传文件
            result = self._bucket.put_object_from_file(oss_key, file_path)

            if result.status == 200:
                # 构建公开访问URL（假设bucket已设置为公开读）
                url = f"https://{self.bucket_name}.{self.endpoint}/{oss_key}"
                logger.info(f"上传成功: {url}")
                return url
            else:
                logger.warning(f"上传失败，状态码: {result.status}")
                return None

        except Exception as e:
            logger.error(f"上传异常: {e}")
            return None

    def is_available(self) -> bool:
        """检查OSS是否可用"""
        return self._init_bucket()


def create_uploader() -> OSSUploader:
    """创建OSS上传器实例"""
    return OSSUploader()