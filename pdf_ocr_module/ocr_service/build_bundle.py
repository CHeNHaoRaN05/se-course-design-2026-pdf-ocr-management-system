"""Build a source-only delivery archive from an explicit allowlist."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

PACKAGE = Path(__file__).resolve().parent


def main():
    target = PACKAGE.parent / "pdf_ocr_module.zip"
    roots = ["configs", "docs", "examples", "tests", "third_party"]
    candidates = list(PACKAGE.glob("*.py")) + list(PACKAGE.glob("*.md")) + list(PACKAGE.glob("*.txt")) + list(PACKAGE.glob("*.ps1"))
    candidates.append(PACKAGE / "models/manifest.json")
    for name in roots:
        candidates.extend((PACKAGE / name).rglob("*"))
    count = 0
    with ZipFile(target, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(set(candidates)):
            if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            archive.write(path, "ocr_service/" + path.relative_to(PACKAGE).as_posix())
            count += 1
    print(f"Created {target.name}: {count} files, {target.stat().st_size} bytes")


if __name__ == "__main__":
    main()
