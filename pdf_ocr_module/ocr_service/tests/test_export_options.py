import csv
import io

from openpyxl import load_workbook
import pytest

from ocr_service.worker import Worker
from .test_inventory_workflow import API, InventoryEngine, enqueue, upload


@pytest.mark.parametrize("fmt", ["txt", "json", "csv", "html", "xlsx"])
def test_select_pages_and_omit_coordinates(service, fmt):
    task = enqueue(service, upload(service, pdf=True))
    Worker(service.config, service.sessions, InventoryEngine()).run_once()
    response = service.client.get(f"{API}/jobs/{task}/export",
                                  params={"format": fmt, "pages": [3, 1, 3], "include_coordinates": False})
    assert response.status_code == 200
    assert response.headers["x-ocr-exported-pages"] == "2"
    assert response.headers["x-ocr-total-pages"] == "2"
    assert "filename*=UTF-8''inventory-" in response.headers["content-disposition"]
    if fmt == "json":
        assert [page["page_no"] for page in response.json()] == [1, 3]
        assert "bbox" not in response.json()[0]["result"]["blocks"][0]
        original = service.client.get(f"{API}/jobs/{task}/pages/1").json()
        assert "bbox" in original["result"]["blocks"][0]  # never mutate saved data
    if fmt == "csv":
        assert len(next(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))) == 4
    if fmt == "xlsx":
        assert load_workbook(io.BytesIO(response.content))["OCR文本"].max_column == 4


def test_export_rejects_unrecognized_selection(service):
    task = enqueue(service, upload(service))
    assert service.client.get(f"{API}/jobs/{task}/export?pages=2").status_code == 422
    assert service.client.get(f"{API}/jobs/{task}/export?pages=0").status_code == 422
    assert service.client.get(f"{API}/jobs/{task}/export?allow_partial=true").status_code == 409
