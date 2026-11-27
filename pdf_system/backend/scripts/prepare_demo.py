"""准备验收演示所需的账号与样本文件。

用法（在 pdf_system 目录，激活装了 requirements.txt 的解释器）：

    python -m backend.scripts.prepare_demo                 # 只建账号 + 生成样本
    python -m backend.scripts.prepare_demo --seed          # 额外通过 API 灌 14 个文件
    python -m backend.scripts.prepare_demo --api http://127.0.0.1:8000

账号口令统一由 --password 指定（默认 Demo12345），角色直接写库：
注册接口只发 user，首任 admin 无法从接口产生，这是唯一可复现的提权路径。
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

from PIL import Image, ImageDraw
from sqlalchemy import select

from backend.core.config import get_settings
from backend.core.database import build_engine, build_session_factory
from backend.core.security import hash_password
from backend.models import User

ACCOUNTS = (
    ("demo-user", "user"),
    ("demo-viewer", "viewer"),
    ("demo-admin", "admin"),
)


def _pdf_bytes(pages: int, label: str, width: int = 595, height: int = 842) -> bytes:
    """按页生成带页码文字的 PDF；文字画在位图上，保证 OCR 有内容可识别。"""
    images = []
    for index in range(1, pages + 1):
        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)
        draw.text((60, 60), f"{label} page {index}/{pages}", fill="black")
        draw.text((60, 100), "software engineering course design sample", fill="black")
        images.append(image)
    buf = io.BytesIO()
    images[0].save(buf, format="PDF", save_all=True, append_images=images[1:], resolution=72)
    return buf.getvalue()


def _encrypted_pdf(pages: int = 2) -> bytes:
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(io.BytesIO(_pdf_bytes(pages, "encrypted-demo")))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt("demo123")
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def make_samples(target: Path, count: int) -> list[Path]:
    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    def save(name: str, payload: bytes) -> None:
        path = target / name
        path.write_bytes(payload)
        written.append(path)

    save("D-01-两页正常.pdf", _pdf_bytes(2, "D-01"))
    save("D-02-多页.pdf", _pdf_bytes(5, "D-02"))
    save("D-03-改扩展名文本.pdf", b"this is plain text, not a pdf")
    save("D-04-损坏.pdf", b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n")
    save("D-05-加密.pdf", _encrypted_pdf())
    for index in range(1, count + 1):
        save(f"document-{index:02d}.pdf", _pdf_bytes(1, f"document-{index:02d}"))
    return written


def ensure_accounts(password: str, *, email_domain: str) -> list[dict]:
    settings = get_settings()
    engine = build_engine(settings)
    sessions = build_session_factory(engine)
    result = []
    with sessions.begin() as session:
        for local, role in ACCOUNTS:
            email = f"{local}@{email_domain}"
            user = session.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(email=email, display_name=local, password_hash=hash_password(password))
                session.add(user)
                session.flush()
            else:
                user.password_hash = hash_password(password)
            user.role = role
            user.disabled = False
            user.token_version = (user.token_version or 0) + 1  # 使旧令牌立即失效
            result.append({"email": email, "role": role, "id": user.id})
    engine.dispose()
    return result


def seed_files(api: str, email: str, password: str, folder: Path, count: int) -> list[str]:
    import httpx

    created: list[str] = []
    with httpx.Client(base_url=api.rstrip("/") + "/api/v1", timeout=60) as client:
        response = client.post("/auth/login", json={"email": email, "password": password})
        response.raise_for_status()
        headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
        for index in range(1, count + 1):
            name = f"document-{index:02d}.pdf"
            path = folder / name
            if not path.exists():
                continue
            with path.open("rb") as handle:
                upload = client.post("/files", headers=headers,
                                     files={"file": (name, handle.read(), "application/pdf")})
            upload.raise_for_status()
            created.append(name)
    return created


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="准备演示账号与样本文件")
    parser.add_argument("--password", default="Demo12345")
    parser.add_argument("--domain", default="example.com")
    parser.add_argument("--out", default="test_materials/demo", help="样本输出目录（相对 pdf_system）")
    parser.add_argument("--count", type=int, default=14, help="document-NN.pdf 的数量，用于分页演示")
    parser.add_argument("--seed", action="store_true", help="登录 demo-user 并上传 document-NN 系列")
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    args = parser.parse_args(argv)

    settings = get_settings()
    folder = Path(args.out)
    if not folder.is_absolute():
        folder = Path(settings.ocr_package_dir).parent.parent / folder
    written = make_samples(folder, args.count)
    accounts = ensure_accounts(args.password, email_domain=args.domain)

    print(f"样本目录：{folder}（{len(written)} 个文件）")
    for item in accounts:
        print(f"账号：{item['email']}  角色：{item['role']}  口令：{args.password}")

    if args.seed:
        names = seed_files(args.api, f"demo-user@{args.domain}", args.password, folder, args.count)
        print(f"已通过 {args.api} 上传 {len(names)} 个分页样本")
    return 0


if __name__ == "__main__":
    sys.exit(main())
