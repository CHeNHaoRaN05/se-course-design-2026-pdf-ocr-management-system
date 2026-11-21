import io
import pytest
from openpyxl import load_workbook
from ocr_service.evaluate import evaluate, main
from ocr_service.exports import export_pages, spreadsheet_safe
from ocr_service.tables import assign_cells, ruled_tables
from ocr_service.queue import claim, save_page
from .test_inventory_workflow import upload, enqueue


@pytest.mark.parametrize("seconds", [float("inf"), float("-inf"), True, -1, 2**1024])
def test_invalid_measurements_are_validation_errors(seconds):
    with pytest.raises(ValueError, match="Invalid seconds"):
        evaluate({"a":{"text":"x"}}, {"a":{"text":"x", "seconds":seconds}}, min_pages=1)


def test_partial_timings_and_sample_threshold_are_explicit():
    refs = {str(i): {"text":"中文"} for i in range(200)}
    preds = {k:{"text":"中文", "seconds":1} for k in refs}
    preds["199"].pop("seconds")
    report = evaluate(refs, preds)
    assert report["timing"]["p95_seconds"] == 1
    assert report["timing"]["measured_pages"] == 199 and not report["timing"]["complete"]
    assert report["acceptance_page_threshold_met"]
    assert report["accuracy_acceptance_passed"] is None
    report = evaluate({"a":{"text":"中文"}}, {"a":{"text":"中文"}}, min_pages=1)
    assert not report["acceptance_page_threshold_met"] and report["min_pages"] == 1


def test_empty_labels_cannot_inflate_page_count():
    refs = {str(i): {"text":""} for i in range(200)}
    refs["0"]["text"] = "x"
    with pytest.raises(ValueError, match="contain text"):
        evaluate(refs, refs)


@pytest.mark.parametrize("value", ["=1+1", "\u200b=1+1", "\ufeff=1+1", ";=1+1", "\t@SUM(1)"])
def test_csv_formula_protection(value):
    assert spreadsheet_safe(value).startswith("'")


def page(text="=1+1"):
    return [{"page_no":1, "result":{"text":text, "width":100, "height":100,
        "blocks":[{"id":1,"text":text,"confidence":1,"bbox":[0,0,1,1]}],
        "tables":[{"id":"bad/name:*"*10,"cells":[["CELL_MARKER"]]}]}}]


def test_xlsx_preserves_literal_and_csv_includes_tables():
    data, _ = export_pages(page(), "xlsx")
    book = load_workbook(io.BytesIO(data))
    assert book["OCR文本"]["C2"].value == "=1+1" and book["OCR文本"]["C2"].data_type == "s"
    assert book["P1_T1"]["A1"].value == "CELL_MARKER"
    data, _ = export_pages(page(), "csv")
    assert b"CELL_MARKER" in data


def test_bad_results_and_oversized_exports_are_rejected():
    from ocr_service.result_validation import validate_result
    with pytest.raises(ValueError):
        validate_result({"text":"x", "tables":[{}]}, require_geometry=True)
    with pytest.raises(ValueError, match="8 MiB"):
        export_pages(page("x" * (9*1024*1024)), "json")
    with pytest.raises(ValueError, match="XLSX"):
        export_pages(page("bad\x00text"), "xlsx")


def test_missing_page_and_empty_save_are_controlled(service):
    ident = enqueue(service, upload(service))
    lease = claim(service.sessions, service.config)
    assert not save_page(service.sessions, *lease, 99, result={"text":"orphan"})
    with pytest.raises(ValueError):
        save_page(service.sessions, *lease, 1)


def test_cross_cell_assignment_and_order():
    table = {"x_lines":[0,50,100],"y_lines":[0,50,100]}
    blocks=[{"id":2,"text":"second","bbox":[.1,.2,.2,.3]},
            {"id":1,"text":"first","bbox":[.1,.1,.6,.2]}]
    assert assign_cells(table, blocks, 100, 100)[0][0] == "first\nsecond"
    assert table["warnings"]


def test_large_grid_has_explicit_warning():
    from PIL import Image, ImageDraw
    image = Image.new("RGB", (1200,400), "white")
    draw = ImageDraw.Draw(image)
    for x in range(40,1121,20):
        draw.line((x,40,x,360),fill="black",width=3)
    for y in range(40,361,80):
        draw.line((40,y,1120,y),fill="black",width=3)
    warnings=[]
    assert ruled_tables(image, [], warnings) == []
    assert any("exceeds" in w for w in warnings)


def test_model_checksum_mismatch_is_explicit(tmp_path):
    from ocr_service.model_files import verify_file
    p = tmp_path / "model.pdparams"
    p.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="checksum"):
        verify_file(p, "0"*64)


def test_standalone_is_not_a_production_auth_bypass(tmp_path):
    from ocr_service.api import create_app
    from ocr_service.config import Settings
    with pytest.raises(ValueError, match="development-only"):
        create_app(Settings(storage=tmp_path, jwt_secret="x"*40, development_mode=False))


def test_invalid_min_pages_and_cer_resource_bounds():
    from ocr_service.evaluate import edit_distance
    for count in (0, -1, True):
        with pytest.raises(ValueError, match="positive integer"):
            evaluate({"a":{"text":"x"}}, {"a":{"text":"x"}}, min_pages=count)
    with pytest.raises(ValueError, match="computation limit"):
        edit_distance("x"*10001, "y")


def test_cli_small_sample_requires_explicit_development_flag(tmp_path, monkeypatch):
    import json
    import sys
    labels=tmp_path/"labels.jsonl"
    labels.write_text('{"id":"a","text":"real label"}\n',encoding="utf-8")
    output=tmp_path/"report.json"
    args=["evaluate",str(labels),"--predictions",str(labels),"--min-pages","1","--output",str(output)]
    monkeypatch.setattr(sys,"argv",args)
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code==2 and not output.exists()
    monkeypatch.setattr(sys,"argv",args+["--development-sample"])
    main()
    assert json.loads(output.read_text())["acceptance_page_threshold_met"] is False
