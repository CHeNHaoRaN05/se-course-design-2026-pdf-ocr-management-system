"""文件内容校验与存储（负责人：甲，供乙的文件模块与丙的 OCR 适配层共用）。

说明：OCR 模块为了实现"独立可部署"自带一份 media.py，这里保留主系统自己的一份，
两者输入输出契约一致（media_type / page_count / sha256 / size），属于有意重复，
任何一侧修改校验规则时都必须同步另一侧（契约 C2）。
"""
import hashlib
import threading
import warnings
from pathlib import Path

from PIL import Image, ImageOps

# PDFium 非线程安全；FastAPI 的同步接口运行在线程池中，必须加锁。
PDFIUM_LOCK = threading.RLock()


class MediaError(ValueError):
    pass


def safe_path(storage: Path, key: str) -> Path:
    path = (storage / key).resolve()
    if not path.is_relative_to(storage.resolve()):
        raise MediaError("invalid_storage_key")
    return path


def inspect_media(path: Path, *, max_pages: int, max_pixels: int) -> tuple[str, int]:
    """按真实内容判断类型，返回 (media_type, page_count)。客户端 MIME 与扩展名不作数。"""
    with open(path, "rb") as handle:
        header = handle.read(8)
    if header.startswith(b"%PDF-"):
        import pypdfium2 as pdfium
        try:
            with PDFIUM_LOCK, pdfium.PdfDocument(str(path)) as pdf:
                count = len(pdf)
                if not 1 <= count <= max_pages:
                    raise MediaError("pdf_page_limit")
            return "application/pdf", count
        except MediaError:
            raise
        except Exception as exc:
            raise MediaError("invalid_or_encrypted_pdf") from exc
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as image:
                if image.format not in {"JPEG", "PNG"}:
                    raise MediaError("only_pdf_png_jpeg_supported")
                if image.width * image.height > max_pixels:
                    raise MediaError("image_pixel_limit")
                media_type = "image/png" if image.format == "PNG" else "image/jpeg"
                image.verify()
        return media_type, 1
    except MediaError:
        raise
    except Exception as exc:
        raise MediaError("invalid_image") from exc


def save_upload(*, storage: Path, key: str, stream, max_upload_bytes: int) -> tuple[int, str]:
    """流式落盘并同时计算 SHA256，超限立即中断。"""
    target = safe_path(storage, key)
    target.parent.mkdir(parents=True, exist_ok=True)
    size, digest = 0, hashlib.sha256()
    try:
        with target.open("xb") as output:
            while chunk := stream.read(1024 * 1024):
                size += len(chunk)
                if size > max_upload_bytes:
                    raise MediaError("upload_size_limit")
                digest.update(chunk)
                output.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return size, digest.hexdigest()


def render_page(path: Path, media_type: str, page_no: int, dpi: int, max_pixels: int) -> Image.Image:
    if media_type == "application/pdf":
        import pypdfium2 as pdfium
        with PDFIUM_LOCK, pdfium.PdfDocument(str(path)) as pdf:
            page = pdf[page_no - 1]
            try:
                width, height = page.get_size()
                scale = dpi / 72
                if width * height * scale * scale > max_pixels:
                    raise MediaError("render_pixel_limit")
                bitmap = page.render(scale=scale)
                try:
                    return bitmap.to_pil().convert("RGB")
                finally:
                    bitmap.close()
            finally:
                page.close()
    with Image.open(path) as image:
        if image.width * image.height > max_pixels:
            raise MediaError("image_pixel_limit")
        return ImageOps.exif_transpose(image).convert("RGB")
