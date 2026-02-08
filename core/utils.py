import base64
import math
import mimetypes
from io import BytesIO
from datetime import datetime
from pathlib import Path

from PIL import Image

from astrbot.api import logger


def get_key_index(current_index: int, item_len: int) -> int:
    """获取key索引"""
    return (current_index + 1) % item_len


def save_images(image_result: list[tuple[str, str]], path_dir: Path) -> list[tuple[str, Path]]:
    """保存图片到本地文件系统，返回 元组(文件名, 文件路径) 列表"""
    # 假设它支持返回多张图片
    saved_paths: list[tuple[str, Path]] = []
    for mime, b64 in image_result:
        if not b64:
            continue
        # 构建文件名
        now = datetime.now()
        current_time_str = (
            now.strftime("%Y%m%d%H%M%S") + f"{int(now.microsecond / 1000):03d}"
        )
        ext = mimetypes.guess_extension(mime) or ".jpg"
        file_name = f"banana_{current_time_str}{ext}"
        # 构建文件保存路径
        save_path = path_dir / file_name
        # 转换成bytes
        image_bytes = base64.b64decode(b64)
        # 保存到文件系统
        with open(save_path, "wb") as f:
            f.write(image_bytes)
        saved_paths.append((file_name, save_path))
        logger.info(f"[BIG BANANA] 图片已保存到 {save_path}")
    return saved_paths


def _encode_image_to_base64(image: Image.Image, mime: str) -> tuple[str, str] | None:
    """将 Pillow 图片编码为 base64，尽量保持原始 MIME"""
    mime_to_format = {
        "image/jpeg": "JPEG",
        "image/jpg": "JPEG",
        "image/png": "PNG",
        "image/webp": "WEBP",
        "image/bmp": "BMP",
    }
    image_format = mime_to_format.get((mime or "").lower(), "PNG")
    output_mime = mime if image_format != "PNG" else "image/png"

    buf = BytesIO()
    try:
        encode_image = image
        if image_format == "JPEG" and image.mode not in ("RGB", "L"):
            encode_image = image.convert("RGB")
        encode_image.save(buf, format=image_format)
        encoded_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return output_mime, encoded_b64
    except Exception as e:
        logger.warning(f"[BIG BANANA] 编码切片图片失败: {e}")
        return None
    finally:
        buf.close()


def _slice_single_image(
    mime: str,
    b64: str,
    max_height: int,
    max_b64_len: int | None,
    max_slices: int,
) -> list[tuple[str, str]]:
    """按高度（和可选大小限制）切片单张图片"""
    if not b64:
        return []

    try:
        image_bytes = base64.b64decode(b64)
    except Exception as e:
        logger.warning(f"[BIG BANANA] 解码图片失败，跳过切片: {e}")
        return [(mime, b64)]

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            if image.height <= 1:
                return [(mime, b64)]

            parts = 1
            if max_height > 0 and image.height > max_height:
                parts = max(parts, math.ceil(image.height / max_height))
            if max_b64_len and max_b64_len > 0 and len(b64) > max_b64_len:
                parts = max(parts, math.ceil(len(b64) / max_b64_len))

            parts = min(max(parts, 1), max_slices)
            if parts <= 1:
                return [(mime, b64)]

            while parts <= max_slices:
                sliced_results: list[tuple[str, str]] = []
                for idx in range(parts):
                    top = image.height * idx // parts
                    bottom = image.height * (idx + 1) // parts
                    if bottom <= top:
                        continue

                    segment = image.crop((0, top, image.width, bottom))
                    encoded = _encode_image_to_base64(segment, mime)
                    segment.close()
                    if not encoded:
                        sliced_results = []
                        break
                    sliced_results.append(encoded)

                if not sliced_results:
                    break

                if max_b64_len and max_b64_len > 0:
                    if any(len(seg_b64) > max_b64_len for _, seg_b64 in sliced_results):
                        if parts >= max_slices:
                            return sliced_results
                        parts = min(parts * 2, max_slices)
                        continue

                return sliced_results
    except Exception as e:
        logger.warning(f"[BIG BANANA] 打开图片失败，跳过切片: {e}")

    return [(mime, b64)]


def slice_images(
    image_result: list[tuple[str, str]],
    max_height: int = 1536,
    max_b64_len: int | None = None,
    max_slices: int = 8,
) -> list[tuple[str, str]]:
    """按配置自动切片图片列表"""
    if not image_result:
        return []

    max_height = max(0, int(max_height))
    max_slices = max(1, int(max_slices))

    sliced_images: list[tuple[str, str]] = []
    for mime, b64 in image_result:
        sliced_images.extend(
            _slice_single_image(
                mime=mime,
                b64=b64,
                max_height=max_height,
                max_b64_len=max_b64_len,
                max_slices=max_slices,
            )
        )

    return sliced_images


def read_file(path, allowed_dir=None) -> tuple[str | None, str | None]:
    """读取文件并返回 (mime_type, base64_data)

    Args:
        path: 文件路径
        allowed_dir: 允许的目录（用于路径穿越防护）
    """
    try:
        # 路径穿越防护
        resolved_path = Path(path).resolve()
        if allowed_dir is not None:
            allowed_resolved = Path(allowed_dir).resolve()
            if not str(resolved_path).startswith(str(allowed_resolved)):
                logger.warning(f"[BIG BANANA] 路径穿越尝试被阻止: {path}")
                return None, None

        # 检查文件名是否包含危险字符
        filename = resolved_path.name
        if ".." in filename or filename.startswith("/"):
            logger.warning(f"[BIG BANANA] 不安全的文件名: {filename}")
            return None, None

        with open(resolved_path, "rb") as f:
            file_data = f.read()
            mime_type, _ = mimetypes.guess_type(str(resolved_path))
            b64_data = base64.b64encode(file_data).decode("utf-8")
            return mime_type, b64_data
    except Exception as e:
        logger.error(f"[BIG BANANA] 读取参考图片 {path} 失败: {e}")
        return None, None


def clear_cache(temp_dir: Path):
    """清理缓存文件，应当在图片发送完成后调用"""
    if not temp_dir.exists():
        logger.warning(f"[BIG BANANA] 缓存目录 {temp_dir} 不存在")
        return
    for file in temp_dir.iterdir():
        try:
            if file.is_file():
                file.unlink()
                logger.debug(f"[BIG BANANA] 已删除缓存文件: {file}")
        except Exception as e:
            logger.error(f"[BIG BANANA] 删除缓存文件 {file} 失败: {e}")


def random_string(length: int) -> str:
    import random
    import string

    letters = string.ascii_letters + string.digits
    return "".join(random.choice(letters) for _ in range(length))
