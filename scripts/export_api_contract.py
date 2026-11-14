"""Regenerate the API contract and route inventory from the mounted application."""
from pathlib import Path
import sys
import tempfile
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"pdf_system"), str(ROOT/"pdf_ocr_module")]
from backend.core.config import Settings
from backend.main import create_app


def main():
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        app = create_app(Settings(_env_file=None, jwt_secret="schema-only-"+"x"*40,
            database_url="sqlite:///"+(temp/"schema.sqlite3").as_posix(), storage_dir=temp/"storage",
            ocr_package_dir=ROOT/"pdf_ocr_module"))
        assert app.state.ocr_mounted
        spec = app.openapi()
        # Describes final route behavior without stale hardcoded response schemas.
        spec["paths"]["/api/v1/ocr/jobs/{job_id}/retry"]["post"]["description"] = "Create a NEW job for failed pages; response id differs. Original reservation is settled before retry."
        spec["paths"]["/api/v1/ocr/files"]["post"]["description"] = "Development-only upload. Hosted deployment returns 409; use /api/v1/files."
        spec["paths"]["/api/v1/search"]["get"]["description"] = "Literal substring search; MySQL uses ngram prefilter. Fixed order updated_at descending then id. Unknown query parameters return 422."
        (ROOT/"docs/api-contract.yaml").write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False),encoding="utf-8")
        operations = [(method.upper(), path, info.get("summary", "")) for path, methods in spec["paths"].items()
                      for method, info in methods.items() if method in {"get","post","put","patch","delete"}]
        rows=["# 当前接口清单", "", "由 scripts/export_api_contract.py 从宿主 OpenAPI 生成。按公开 method + path 计数；不含隐藏别名及框架文档路由。", "",
              f"共 {len(operations)} 个操作，其中 OCR 原生前缀 /api/v1/ocr/ 为 {sum(path.startswith('/api/v1/ocr/') for _,path,_ in operations)} 个。", "", "| 方法 | 路径 | 摘要 |", "|---|---|---|"]
        rows += [f"| {method} | `{path}` | {summary} |" for method,path,summary in sorted(operations)]
        (ROOT/"docs/route-inventory.md").write_text("\n".join(rows)+"\n",encoding="utf-8")
        app.state.ocr_engine.dispose()
        app.state.engine.dispose()


if __name__ == "__main__":
    main()
