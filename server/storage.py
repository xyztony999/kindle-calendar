"""图片素材：阿里云 OSS。未配置时上传会失败，其余管理功能不受影响。"""

from __future__ import annotations

import logging
import os
import uuid
from io import BytesIO

from PIL import Image, UnidentifiedImageError

log = logging.getLogger(__name__)

MAX_BYTES = 2 * 1024 * 1024
MAX_EDGE = 4096


class AssetError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _prefix() -> str:
    raw = os.environ.get("OSS_PREFIX", "calendar/").strip() or "calendar/"
    if not raw.endswith("/"):
        raw += "/"
    return raw


def configured() -> bool:
    needed = ("OSS_ENDPOINT", "OSS_BUCKET", "OSS_ACCESS_KEY_ID", "OSS_ACCESS_KEY_SECRET")
    return all(os.environ.get(name, "").strip() for name in needed)


def _bucket():
    if not configured():
        raise AssetError("OSS_NOT_CONFIGURED", "未配置阿里云 OSS，暂时不能上传图片")
    try:
        import oss2
    except ImportError as exc:
        raise AssetError("OSS_NOT_CONFIGURED", "服务器未安装 OSS 组件") from exc
    auth = oss2.Auth(os.environ["OSS_ACCESS_KEY_ID"].strip(), os.environ["OSS_ACCESS_KEY_SECRET"].strip())
    return oss2.Bucket(auth, os.environ["OSS_ENDPOINT"].strip(), os.environ["OSS_BUCKET"].strip())


def inspect_image(raw: bytes) -> tuple[str, str]:
    if not raw or len(raw) > MAX_BYTES:
        raise AssetError("ASSET_TOO_LARGE", "图片须小于 2MB")
    try:
        with Image.open(BytesIO(raw)) as img:
            img.verify()
        with Image.open(BytesIO(raw)) as img:
            fmt = (img.format or "").upper()
            width, height = img.size
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise AssetError("ASSET_TYPE_INVALID", "只接受 JPEG 或 PNG") from exc
    if width > MAX_EDGE or height > MAX_EDGE:
        raise AssetError("ASSET_TOO_LARGE", "图片边长不能超过 4096")
    if fmt == "JPEG":
        return "image/jpeg", "jpg"
    if fmt == "PNG":
        return "image/png", "png"
    raise AssetError("ASSET_TYPE_INVALID", "只接受 JPEG 或 PNG")


def put_image(raw: bytes) -> dict:
    content_type, ext = inspect_image(raw)
    asset_id = "a" + uuid.uuid4().hex[:8]
    key = f"{_prefix()}{asset_id}.{ext}"
    try:
        _bucket().put_object(key, raw, headers={"Content-Type": content_type})
    except AssetError:
        raise
    except Exception as exc:
        log.warning("OSS 上传失败: %s", exc)
        raise AssetError("ASSET_STORE_FAILED", "图片上传失败") from exc
    return {"id": asset_id, "key": key, "content_type": content_type}


def get_object(key: str) -> bytes | None:
    if not configured() or not key:
        return None
    try:
        result = _bucket().get_object(key)
        return result.read()
    except Exception as exc:
        log.warning("OSS 读取失败 key=%s: %s", key, exc)
        return None


def delete_object(key: str) -> None:
    if not configured() or not key:
        return
    try:
        _bucket().delete_object(key)
    except Exception as exc:
        log.warning("OSS 删除失败 key=%s: %s", key, exc)
