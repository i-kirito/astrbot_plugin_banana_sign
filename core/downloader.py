import asyncio
import base64
import ipaddress
import socket
from functools import lru_cache
from io import BytesIO
from urllib.parse import urlparse

from curl_cffi import AsyncSession
from curl_cffi.requests.exceptions import (
    CertificateVerifyError,
    SSLError,
    Timeout,
)
from PIL import Image

from astrbot.api import logger

from .data import SUPPORTED_FILE_FORMATS, CommonConfig


@lru_cache(maxsize=1024)
def _resolve_hostname(hostname: str) -> str | None:
    """解析域名并做 LRU 缓存，减少重复 DNS 解析开销"""
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        return None


def is_safe_url(url: str) -> bool:
    """检查 URL 是否安全（防止 SSRF 攻击）"""
    try:
        parsed = urlparse(url)
        # 只允许 http 和 https
        if parsed.scheme not in ("http", "https"):
            logger.warning(f"[BIG BANANA] 不安全的 URL scheme: {parsed.scheme}")
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        # 可信域名白名单（跳过 IP 检查）
        trusted_domains = (
            ".qq.com",
            ".qq.com.cn",
            ".qlogo.cn",
            ".gtimg.cn",
            ".qpic.cn",
        )
        if any(hostname.endswith(domain) for domain in trusted_domains):
            return True

        # 解析域名获取 IP（带缓存）
        ip = _resolve_hostname(hostname)
        if ip:
            ip_obj = ipaddress.ip_address(ip)
            # 拒绝私有/保留 IP
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved:
                logger.warning(f"[BIG BANANA] URL 解析到私有/保留 IP: {ip}")
                return False

        return True
    except Exception as e:
        logger.warning(f"[BIG BANANA] URL 安全检查失败: {e}")
        return False


class Downloader:
    def __init__(self, session: AsyncSession, common_config: CommonConfig):
        self.session = session
        self.def_common_config = common_config

    def _get_proxy(self) -> str | None:
        """获取格式化的代理 URL（自动补全 http:// 前缀）"""
        proxy = self.def_common_config.proxy
        if not proxy:
            return None
        proxy = proxy.strip()
        if proxy and "://" not in proxy:
            return f"http://{proxy}"
        return proxy

    async def _fetch_image_with_retry(self, url: str) -> tuple[str, str] | None:
        """下载单张图片（带重试）"""
        for _ in range(3):
            content = await self._download_image(url)
            if content is not None:
                return content
        return None

    async def fetch_image(self, url: str) -> tuple[str, str] | None:
        """下载单张图片并转换为 (mime, base64)"""
        result = await self._fetch_image_with_retry(url)
        if result is None:
            logger.warning(f"[BIG BANANA] fetch_image 失败: {url}")
            return None

        mime, b64 = result
        logger.debug(
            f"[BIG BANANA] fetch_image 成功: mime={mime}, b64_type={type(b64).__name__}, b64_len={len(b64)}"
        )
        return result

    async def fetch_images(self, image_urls: list[str]) -> list[tuple[str, str]]:
        """下载多张图片并转换为 (mime, base64) 列表（并发下载，保持输入顺序）"""
        if not image_urls:
            return []

        max_parallel = min(8, len(image_urls))
        semaphore = asyncio.Semaphore(max_parallel)

        async def _worker(url: str) -> tuple[str, str] | None:
            async with semaphore:
                return await self._fetch_image_with_retry(url)

        results = await asyncio.gather(
            *(_worker(url) for url in image_urls),
            return_exceptions=True,
        )

        image_b64_list: list[tuple[str, str]] = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"[BIG BANANA] 并发下载图片失败: {result}")
                continue
            if result is not None:
                image_b64_list.append(result)

        return image_b64_list

    @staticmethod
    def _handle_image(image_bytes: bytes) -> tuple[str, str] | None:
        """处理图片：验证格式、GIF转PNG、Base64编码（CPU密集，在线程池中执行）"""
        if len(image_bytes) > 36 * 1024 * 1024:
            logger.warning("[BIG BANANA] 图片超过 36MB，跳过处理")
            return None
        try:
            with Image.open(BytesIO(image_bytes)) as img:
                fmt = (img.format or "").lower()
                if fmt not in SUPPORTED_FILE_FORMATS:
                    logger.warning(f"[BIG BANANA] 不支持的图片格式: {fmt}")
                    return None
                # 如果不是 GIF，直接返回原图
                if fmt != "gif":
                    mime = "image/jpeg" if fmt == "jpg" else f"image/{fmt}"
                    b64 = base64.b64encode(image_bytes).decode("utf-8")
                    logger.debug(
                        f"[BIG BANANA] 图片处理完成: fmt={fmt}, mime={mime}, bytes={len(image_bytes)}, b64_len={len(b64)}"
                    )
                    return (mime, b64)
                # 处理 GIF：取第一帧转PNG
                buf = BytesIO()
                img.seek(0)
                img = img.convert("RGBA")
                img.save(buf, format="PNG")
                b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                logger.debug(
                    f"[BIG BANANA] GIF转PNG完成: source_bytes={len(image_bytes)}, png_bytes={len(buf.getvalue())}, b64_len={len(b64)}"
                )
                return ("image/png", b64)
        except Exception as e:
            logger.warning(f"[BIG BANANA] 图片处理失败: {e}")
            return None

    async def _download_image(self, url: str) -> tuple[str, str] | None:
        # SSRF 防护：验证 URL 安全性
        if not is_safe_url(url):
            logger.warning(f"[BIG BANANA] 拒绝不安全的 URL: {url}")
            return None

        # 构造请求头：Referer防盗链 + 压缩 + 连接复用
        parsed = urlparse(url)
        referer = f"{parsed.scheme}://{parsed.netloc}/"
        headers = {
            "Referer": referer,
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Accept": "image/*,*/*;q=0.8",
        }

        try:
            response = await self.session.get(
                url,
                proxy=self._get_proxy(),
                timeout=30,
                headers=headers,
            )
            if response.status_code != 200 or not response.content:
                logger.warning(
                    f"[BIG BANANA] 图片下载失败，状态码: {response.status_code}"
                )
                return None
            logger.debug(
                f"[BIG BANANA] 图片下载成功: status={response.status_code}, content_type={response.headers.get('Content-Type', '')}, bytes={len(response.content)}"
            )
            # 在线程池中处理图片，避免阻塞事件循环
            content = await asyncio.to_thread(Downloader._handle_image, response.content)
            return content
        except (SSLError, CertificateVerifyError):
            # 关闭SSL验证重试
            response = await self.session.get(
                url,
                proxy=self._get_proxy(),
                timeout=30,
                verify=False,
                headers=headers,
            )
            if response.status_code != 200 or not response.content:
                logger.warning(
                    f"[BIG BANANA] 图片下载失败，状态码: {response.status_code}"
                )
                return None
            content = await asyncio.to_thread(Downloader._handle_image, response.content)
            return content
        except Timeout as e:
            logger.error(f"[BIG BANANA] 网络请求超时: {url}，错误信息：{e}")
            return None
        except Exception as e:
            logger.error(f"[BIG BANANA] 下载图片失败: {url}，错误信息：{e}")
            return None
