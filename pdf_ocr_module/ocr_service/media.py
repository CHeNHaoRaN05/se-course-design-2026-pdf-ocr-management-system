from pathlib import Path
import warnings
import threading

from PIL import Image, ImageOps

# PDFium is not thread-safe; FastAPI upload validation uses a thread pool.
PDFIUM_LOCK = threading.RLock()


class MediaError(ValueError):
    pass


def safe_path(storage: Path, key: str):
    path = (storage / key).resolve()
    if not path.is_relative_to(storage.resolve()):
        raise MediaError("invalid_storage_key")
    return path


def inspect_media(path, settings):
    with open(path, "rb") as f:
        header = f.read(8)
    if header.startswith(b"%PDF-"):
        import pypdfium2 as pdfium
        try:
            with PDFIUM_LOCK, pdfium.PdfDocument(path) as pdf:
                count = len(pdf)
                if not 1 <= count <= settings.max_pages:
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
                if image.width * image.height > settings.max_pixels:
                    raise MediaError("image_pixel_limit")
                media_type = "image/png" if image.format == "PNG" else "image/jpeg"
                image.verify()
        return media_type, 1
    except MediaError:
        raise
    except Exception as exc:
        raise MediaError("invalid_image") from exc


def render_page(path, media_type, page_no, dpi, max_pixels):
    if media_type == "application/pdf":
        import pypdfium2 as pdfium
        with PDFIUM_LOCK, pdfium.PdfDocument(path) as pdf:
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

