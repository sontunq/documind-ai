"""Comprehensive unit tests for evaluation metrics, manifest validation, and leakage detection."""
from pathlib import Path
import pytest

from app.evaluation.manifest import (
    check_data_leakage,
    load_evaluation_manifest,
    validate_evaluation_manifest,
)
from app.evaluation.metrics import (
    character_error_rate,
    classification_metrics,
    corpus_ocr_metrics,
    extraction_metrics,
    field_match_equals,
    levenshtein_distance,
    word_error_rate,
)


def test_levenshtein_distance_hand_calculated() -> None:
    # 1. Identical strings
    assert levenshtein_distance("", "") == 0
    assert levenshtein_distance("abc", "abc") == 0

    # 2. Classic textbook example: kitten -> sitting (3 operations)
    # k -> s (sub), e -> i (sub), append g (ins)
    assert levenshtein_distance("kitten", "sitting") == 3

    # 3. Pure deletion and insertion
    assert levenshtein_distance("hello", "") == 5
    assert levenshtein_distance("", "world") == 5

    # 4. Single edit types
    assert levenshtein_distance("cat", "hat") == 1  # substitution
    assert levenshtein_distance("cat", "cats") == 1  # insertion
    assert levenshtein_distance("cats", "cat") == 1  # deletion

    # 5. List of tokens
    assert levenshtein_distance(["the", "quick", "fox"], ["the", "brown", "fox"]) == 1


def test_character_error_rate_hand_calculated() -> None:
    # Exact match
    assert character_error_rate("ABCDE", "ABCDE") == 0.0

    # 1 error in 5 characters = 0.20
    assert character_error_rate("ABCDE", "ABXDE") == pytest.approx(0.20)

    # 2 errors in 10 characters = 0.20
    assert character_error_rate("0123456789", "0123XX6789") == pytest.approx(0.20)

    # Empty inputs
    assert character_error_rate("", "") == 0.0


def test_word_error_rate_hand_calculated() -> None:
    ref = "the quick brown fox"
    hyp = "the fast brown fox"
    # 1 substitution out of 4 words = 0.25
    assert word_error_rate(ref, hyp) == pytest.approx(0.25)

    # 1 insertion out of 2 words = 0.5
    assert word_error_rate("hello world", "hello beautiful world") == pytest.approx(0.5)

    # 1 deletion out of 3 words = 1/3
    assert word_error_rate("one two three", "one three") == pytest.approx(1 / 3)


def test_corpus_ocr_metrics() -> None:
    pairs = [
        ("clean text", "clean text"),  # 10 chars, 2 words, 0 dist
        ("hello world", "hello word"),  # 11 chars, 2 words, 1 char dist ('l' deleted), 1 word dist
    ]
    res = corpus_ocr_metrics(pairs)
    # total chars = 10 + 11 = 21, char dist = 1 => CER = 1/21
    assert res["total_chars"] == 21
    assert res["char_edit_distance"] == 1
    assert res["cer"] == pytest.approx(1 / 21)

    # total words = 2 + 2 = 4, word dist = 1 => WER = 1/4 = 0.25
    assert res["total_words"] == 4
    assert res["word_edit_distance"] == 1
    assert res["wer"] == pytest.approx(0.25)


def test_classification_metrics_hand_calculated() -> None:
    actual = ["invoice", "invoice", "contract", "contract", "form", "form"]
    # 1 invoice misclassified as contract
    predicted = ["invoice", "contract", "contract", "contract", "form", "form"]

    metrics = classification_metrics(actual, predicted, labels=["contract", "form", "invoice"])

    # 5 out of 6 correct = 5/6
    assert metrics["accuracy"] == pytest.approx(5 / 6)

    # Invoice: TP=1, FP=0, FN=1 -> Prec = 1.0, Rec = 0.5, F1 = 2/3
    inv_stats = metrics["per_class"]["invoice"]
    assert inv_stats["precision"] == 1.0
    assert inv_stats["recall"] == pytest.approx(0.5)
    assert inv_stats["f1"] == pytest.approx(2 / 3)

    # Contract: TP=2, FP=1, FN=0 -> Prec = 2/3, Rec = 1.0, F1 = 4/5
    ctr_stats = metrics["per_class"]["contract"]
    assert ctr_stats["precision"] == pytest.approx(2 / 3)
    assert ctr_stats["recall"] == 1.0
    assert ctr_stats["f1"] == pytest.approx(0.8)

    # Form: TP=2, FP=0, FN=0 -> Prec = 1.0, Rec = 1.0, F1 = 1.0
    form_stats = metrics["per_class"]["form"]
    assert form_stats["precision"] == 1.0
    assert form_stats["recall"] == 1.0
    assert form_stats["f1"] == 1.0

    # Confusion matrix
    # labels order: contract, form, invoice
    # row 0 (contract): [2, 0, 0]
    # row 1 (form):     [0, 2, 0]
    # row 2 (invoice):  [1, 0, 1]
    cm = metrics["confusion_matrix"]
    assert cm == [
        [2, 0, 0],
        [0, 2, 0],
        [1, 0, 1],
    ]


def test_classification_metrics_validation() -> None:
    with pytest.raises(ValueError, match="aligned"):
        classification_metrics(["invoice"], ["invoice", "contract"])
    with pytest.raises(ValueError, match="non-empty"):
        classification_metrics([], [])


def test_field_match_equals() -> None:
    # Both None
    assert field_match_equals(None, None) is True
    # One None
    assert field_match_equals("val", None) is False
    assert field_match_equals(None, "val") is False

    # String case-insensitive and whitespace
    assert field_match_equals("INV-001", "  inv-001  ") is True
    assert field_match_equals("Acme Corp", "ACME CORP") is True

    # Numeric tolerance
    assert field_match_equals(1250.0, "1250.0") is True
    assert field_match_equals("1,250.00", 1250.0) is True
    assert field_match_equals("$150,000.00 USD", 150000.0) is True
    assert field_match_equals("50.000.000 VNĐ", 50000000.0) is True


def test_extraction_metrics_hand_calculated() -> None:
    samples = [
        {
            "document_type": "invoice",
            "ground_truth": {"invoice_number": "INV-1", "total": 100.0},
            "predicted": {"invoice_number": "INV-1", "total": 100.0},
        },
        {
            "document_type": "invoice",
            "ground_truth": {"invoice_number": "INV-2", "total": 200.0},
            "predicted": {"invoice_number": "INV-2", "total": 999.0},  # total wrong
        },
    ]

    metrics = extraction_metrics(samples)
    # Total evaluated opportunities: 4 fields
    # Exact match: 3 / 4 = 0.75
    assert metrics["exact_match_ratio"] == pytest.approx(0.75)

    # invoice_number: TP=2, FP=0, FN=0 -> Prec=1.0, Rec=1.0, F1=1.0
    inv_f = metrics["per_field"]["invoice_number"]
    assert inv_f["precision"] == 1.0
    assert inv_f["recall"] == 1.0

    # total: TP=1, FP=1, FN=1 -> Prec = 0.5, Rec = 0.5, F1 = 0.5
    tot_f = metrics["per_field"]["total"]
    assert tot_f["precision"] == 0.5
    assert tot_f["recall"] == 0.5
    assert tot_f["f1"] == 0.5


def test_evaluation_manifest_validation() -> None:
    valid_manifest = {
        "dataset_version": "eval-v1",
        "evaluation_tracks": ["ocr", "classification", "extraction"],
        "ocr_samples": [{"id": "ocr-1", "reference_text": "A", "hypothesis_text": "A"}],
        "classification_samples": [{"id": "cls-1", "text": "invoice text", "label": "invoice"}],
        "extraction_samples": [
            {
                "id": "ext-1",
                "document_type": "invoice",
                "ground_truth": {"invoice_number": "1"},
                "ocr_lines": [{"text": "1", "box": {"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.05}}],
            }
        ],
    }
    # Should not raise
    validate_evaluation_manifest(valid_manifest)

    # Missing dataset_version
    bad1 = {**valid_manifest, "dataset_version": ""}
    with pytest.raises(ValueError, match="dataset_version"):
        validate_evaluation_manifest(bad1)

    # Duplicate sample IDs
    bad2 = {
        **valid_manifest,
        "ocr_samples": [
            {"id": "dup-1", "reference_text": "A", "hypothesis_text": "A"},
            {"id": "dup-1", "reference_text": "B", "hypothesis_text": "B"},
        ],
    }
    with pytest.raises(ValueError, match="Duplicate sample ID"):
        validate_evaluation_manifest(bad2)


def test_data_leakage_checker() -> None:
    train_manifest = {
        "samples": [
            {"id": "train-01", "split": "train", "text": "CONFIDENTIAL AGREEMENT BETWEEN ALICE AND BOB"},
        ]
    }
    eval_clean = {
        "classification_samples": [
            {"id": "test-01", "text": "COMMERCIAL INVOICE FROM SUPPLIER TO CUSTOMER"},
        ]
    }
    # Clean check
    violations = check_data_leakage(eval_clean, train_manifest)
    assert len(violations) == 0

    # ID Leakage
    eval_leak_id = {
        "classification_samples": [
            {"id": "train-01", "text": "DIFFERENT TEXT"},
        ]
    }
    violations_id = check_data_leakage(eval_leak_id, train_manifest)
    assert len(violations_id) == 1
    assert "Sample ID leakage" in violations_id[0]

    # Content Leakage
    eval_leak_text = {
        "classification_samples": [
            {"id": "test-99", "text": "confidential agreement between alice and bob."},
        ]
    }
    violations_text = check_data_leakage(eval_leak_text, train_manifest)
    assert len(violations_text) == 1
    assert "Content leakage" in violations_text[0]
