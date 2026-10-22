import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import urllib.request

from .config import Settings

DETECTOR_URL = "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_pretrained_model/PP-OCRv5_mobile_det_pretrained.pdparams"


def main():
    parser = argparse.ArgumentParser(description="Standalone OCR module management")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init-db")
    commands.add_parser("download-detector")
    commands.add_parser("download-models")
    commands.add_parser("openapi")
    commands.add_parser("mysql-ddl")
    token = commands.add_parser("dev-token", help="Local development only; not a login endpoint")
    token.add_argument("--user", default="student-1")
    token.add_argument("--role", choices=["user", "viewer", "admin"], default="user")
    worker = commands.add_parser("worker")
    worker.add_argument("--once", action="store_true")
    args = parser.parse_args()
    cfg = Settings()
    if args.command == "init-db":
        from .db import Base, database
        engine, _ = database(cfg)
        Base.metadata.create_all(engine)
        engine.dispose()
        print("OCR tables initialized (existing tables are not migrated)")
    elif args.command == "dev-token":
        import jwt
        if len(cfg.jwt_secret) < 32:
            parser.error("Set OCR_JWT_SECRET to at least 32 random characters")
        stamp = datetime.now(timezone.utc)
        print(jwt.encode(dict(sub=args.user, role=args.role, iss=cfg.jwt_issuer, aud=cfg.jwt_audience,
                              iat=stamp, exp=stamp+timedelta(hours=2)), cfg.jwt_secret, algorithm="HS256"))
    elif args.command == "worker":
        from .worker import main as run
        run(args.once)
    elif args.command in {"download-detector", "download-models"}:
        manifest = json.loads((Path(__file__).parent / "models/manifest.json").read_text(encoding="utf-8"))
        for name, target in [("detector", cfg.detector_weights), ("recognizer", cfg.recognizer_weights)]:
            if args.command == "download-detector" and name != "detector":
                continue
            metadata = manifest[name]
            if target.exists():
                if hashlib.sha256(target.read_bytes()).hexdigest() != metadata["sha256"]:
                    raise ValueError(f"Model checksum mismatch: {target}")
                print("Verified model:", name)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            partial = target.with_suffix(".download")
            try:
                with urllib.request.urlopen(metadata["url"], timeout=60) as response, partial.open("wb") as output:
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
                if hashlib.sha256(partial.read_bytes()).hexdigest() != metadata["sha256"]:
                    raise ValueError(f"Downloaded model checksum mismatch: {name}")
                partial.replace(target)
                print("Downloaded verified model:", name)
            finally:
                partial.unlink(missing_ok=True)
    elif args.command == "openapi":
        from .api import create_app
        # Schema generation has no authentication side effect and never issues a token.
        cfg.jwt_secret = "schema-generation-only-" + "x" * 32
        app = create_app(cfg)
        destination = Path(__file__).parent / "docs/openapi.json"
        destination.parent.mkdir(exist_ok=True)
        destination.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2), encoding="utf-8")
        app.state.ocr_engine.dispose()
        print(destination)
    elif args.command == "mysql-ddl":
        from sqlalchemy import create_mock_engine
        from .db import Base
        statements = ["-- Generated from ocr_service.db; run in an empty MySQL 8+ utf8mb4 database.", "SET NAMES utf8mb4;"]
        def emit(sql, *args, **kwargs):
            statements.append(str(sql.compile(dialect=engine.dialect)).strip() + ";")
        engine = create_mock_engine("mysql+pymysql://", emit)
        Base.metadata.create_all(engine)
        destination = Path(__file__).parent / "docs/mysql-schema.sql"
        destination.parent.mkdir(exist_ok=True)
        destination.write_text("\n\n".join(statements), encoding="utf-8")
        print(destination)


if __name__ == "__main__":
    main()
