"""
OSS上传测试脚本
"""
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

import config
from src.oss_uploader import OSSUploader

def test_oss_upload():
    """测试OSS上传"""

    # 检查配置
    print("=" * 50)
    print("OSS配置检查:")
    print(f"  Access Key ID: {config.OSS_ACCESS_KEY_ID[:8]}... (已设置: {bool(config.OSS_ACCESS_KEY_ID)})")
    print(f"  Access Key Secret: {'已设置' if config.OSS_ACCESS_KEY_SECRET else '未设置'}")
    print(f"  Bucket Name: {config.OSS_BUCKET_NAME}")
    print(f"  Endpoint: {config.OSS_ENDPOINT}")
    print(f"  Prefix: {config.OSS_PREFIX}")
    print("=" * 50)

    if not all([config.OSS_ACCESS_KEY_ID, config.OSS_ACCESS_KEY_SECRET,
                config.OSS_BUCKET_NAME, config.OSS_ENDPOINT]):
        print("错误: OSS配置不完整，请检查.env文件")
        return False

    # 创建测试文件
    test_dir = Path("charts")
    test_dir.mkdir(exist_ok=True)
    test_file = test_dir / "test_upload.png"

    # 创建一个简单的PNG文件（1x1像素）
    import struct
    import zlib

    def create_minimal_png(filename):
        """创建最小PNG文件"""
        width, height = 100, 100

        # PNG文件头
        signature = b'\x89PNG\r\n\x1a\n'

        # IHDR chunk
        ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
        ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff
        ihdr = struct.pack('>I', 13) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc)

        # IDAT chunk (简单填充)
        raw_data = b'\x00' + b'\xff\xff\xff' * width  # 一行白色像素
        compressed = zlib.compress(raw_data * height)
        idat_crc = zlib.crc32(b'IDAT' + compressed) & 0xffffffff
        idat = struct.pack('>I', len(compressed)) + b'IDAT' + compressed + struct.pack('>I', idat_crc)

        # IEND chunk
        iend_crc = zlib.crc32(b'IEND') & 0xffffffff
        iend = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc)

        with open(filename, 'wb') as f:
            f.write(signature + ihdr + idat + iend)

    create_minimal_png(test_file)
    print(f"创建测试文件: {test_file}")

    # 上传测试
    uploader = OSSUploader()

    print("\n开始上传测试...")
    oss_url = uploader.upload_chart(str(test_file), "test_oss_upload.png")

    if oss_url:
        print(f"\n上传成功!")
        print(f"OSS URL: {oss_url}")
        print("\n请在浏览器中访问上述URL验证图片是否可访问")
        return True
    else:
        print("\n上传失败!")
        return False

if __name__ == "__main__":
    success = test_oss_upload()
    exit(0 if success else 1)