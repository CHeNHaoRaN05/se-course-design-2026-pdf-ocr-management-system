import pytest

from ocr_service.evaluate import edit_distance, evaluate, normalize, read_rows


@pytest.mark.parametrize("reference,prediction,expected", [
    ("", "abc", 3), ("中文测试", "中文测式", 1), ("kitten", "sitting", 3),
    ("abcd", "acd", 1), ("相同", "相同", 0),
])
def test_distance(reference, prediction, expected):
    assert edit_distance(reference, prediction) == expected


def test_weighted_metrics_and_normalization():
    reference = {"a": {"text": "中文测试", "category": "中文"}, "b": {"text": "Ａ B", "category": "英文"}}
    prediction = {"a": {"text": "中文测式", "seconds": 1}, "b": {"text": "AB", "seconds": 2}}
    result = evaluate(reference, prediction, min_pages=2)
    assert result["overall"]["cer"] == pytest.approx(1 / 6)
    assert result["categories"]["中文"]["character_accuracy"] == .75
    assert result["categories"]["英文"]["character_accuracy"] == 1
    assert result["timing"]["p95_seconds"] == 2
    assert normalize("Ａ B", keep_whitespace=True) == "A B"


def test_incomplete_dataset_cannot_pass():
    with pytest.raises(ValueError, match="200"):
        evaluate({"a": {"text": "x"}}, {"a": {"text": "x"}})
    with pytest.raises(ValueError, match="exactly match"):
        evaluate({"a": {"text": "x"}}, {}, min_pages=1)
    with pytest.raises(ValueError, match="contain text"):
        evaluate({"a": {"text": ""}}, {"a": {"text": ""}}, min_pages=1)
    with pytest.raises(ValueError, match="Invalid seconds"):
        evaluate({"a": {"text": "x"}}, {"a": {"text": "x", "seconds": float("nan")}}, min_pages=1)


def test_duplicate_ids_are_rejected(tmp_path):
    source = tmp_path / "labels.jsonl"
    source.write_text('{"id":"a","text":"one"}\n{"id":"a","text":"two"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate"):
        read_rows(source)
