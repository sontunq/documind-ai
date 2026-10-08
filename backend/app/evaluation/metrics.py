"""Evaluation metric calculations for IDP AI stages: OCR, Classification, and Extraction."""
from math import isfinite


def levenshtein_distance(seq1: list | str, seq2: list | str) -> int:
    """Compute the Levenshtein edit distance between two sequences."""
    n, m = len(seq1), len(seq2)
    if n == 0:
        return m
    if m == 0:
        return n
    dp = [list(range(m + 1))] + [[i] + [0] * m for i in range(1, n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if seq1[i - 1] == seq2[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,       # deletion
                dp[i][j - 1] + 1,       # insertion
                dp[i - 1][j - 1] + cost  # substitution
            )
    return dp[n][m]


def character_error_rate(reference: str, hypothesis: str) -> float:
    """Compute Character Error Rate (CER) between reference and hypothesis text."""
    if not reference and not hypothesis:
        return 0.0
    dist = levenshtein_distance(reference, hypothesis)
    return float(dist / max(1, len(reference)))


def word_error_rate(reference: str, hypothesis: str) -> float:
    """Compute Word Error Rate (WER) between reference and hypothesis text."""
    ref_words = reference.split()
    hyp_words = hypothesis.split()
    if not ref_words and not hyp_words:
        return 0.0
    dist = levenshtein_distance(ref_words, hyp_words)
    return float(dist / max(1, len(ref_words)))


def corpus_ocr_metrics(pairs: list[tuple[str, str]]) -> dict[str, float | int]:
    """Compute aggregated corpus-level CER and WER across multiple document pages."""
    if not pairs:
        return {"cer": 0.0, "wer": 0.0, "total_chars": 0, "total_words": 0, "pairs_count": 0}

    total_char_dist = 0
    total_ref_chars = 0
    total_word_dist = 0
    total_ref_words = 0

    for ref, hyp in pairs:
        total_char_dist += levenshtein_distance(ref, hyp)
        total_ref_chars += len(ref)

        ref_words = ref.split()
        hyp_words = hyp.split()
        total_word_dist += levenshtein_distance(ref_words, hyp_words)
        total_ref_words += len(ref_words)

    cer = float(total_char_dist / max(1, total_ref_chars))
    wer = float(total_word_dist / max(1, total_ref_words))

    return {
        "cer": cer,
        "wer": wer,
        "total_chars": total_ref_chars,
        "total_words": total_ref_words,
        "char_edit_distance": total_char_dist,
        "word_edit_distance": total_word_dist,
        "pairs_count": len(pairs),
    }


def field_match_equals(val1: object, val2: object) -> bool:
    """Normalized equality comparison for extracted field values."""
    if val1 is None and val2 is None:
        return True
    if val1 is None or val2 is None:
        return False
    # If both can be cast to float, compare numerically with small tolerance
    try:
        f1, f2 = float(str(val1).replace(",", "").strip()), float(str(val2).replace(",", "").strip())
        if isfinite(f1) and isfinite(f2):
            return abs(f1 - f2) < 1e-4
    except (ValueError, TypeError):
        pass
    # Normalized monetary amount comparison if amounts contain currency symbols or formats
    try:
        from app.infrastructure.extraction.normalization import normalize_amount
        a1, a2 = normalize_amount(str(val1)), normalize_amount(str(val2))
        if a1 is not None and a2 is not None and abs(a1 - a2) < 1e-4:
            return True
    except Exception:
        pass
    # Otherwise compare string canonicalized
    s1 = str(val1).strip().lower()
    s2 = str(val2).strip().lower()
    return s1 == s2



def extraction_metrics(
    eval_samples: list[dict],
) -> dict:
    """Compute exact match, precision, recall, and F1 across structured fields.
    
    Each sample dict has:
    - 'document_type': str
    - 'ground_truth': dict[str, Any]
    - 'predicted': dict[str, Any]
    """
    per_field: dict[str, dict[str, int]] = {}
    doc_types: set[str] = set()

    total_exact_match = 0
    total_fields_evaluated = 0

    for sample in eval_samples:
        doc_type = sample.get("document_type", "unknown")
        doc_types.add(doc_type)
        gt = sample.get("ground_truth", {})
        pred = sample.get("predicted", {})

        all_keys = set(gt.keys()) | set(pred.keys())
        for key in all_keys:
            if key not in per_field:
                per_field[key] = {"tp": 0, "fp": 0, "fn": 0, "total_gt": 0}

            gt_val = gt.get(key)
            pred_val = pred.get(key)

            if gt_val is not None:
                per_field[key]["total_gt"] += 1

            if gt_val is not None and pred_val is not None:
                total_fields_evaluated += 1
                if field_match_equals(gt_val, pred_val):
                    per_field[key]["tp"] += 1
                    total_exact_match += 1
                else:
                    per_field[key]["fp"] += 1
                    per_field[key]["fn"] += 1
            elif pred_val is not None and gt_val is None:
                per_field[key]["fp"] += 1
                total_fields_evaluated += 1
            elif gt_val is not None and pred_val is None:
                per_field[key]["fn"] += 1
                total_fields_evaluated += 1

    field_results: dict[str, dict[str, float | int]] = {}
    p_sum, r_sum, f1_sum = 0.0, 0.0, 0.0
    field_count = 0

    for key, counts in per_field.items():
        tp = counts["tp"]
        fp = counts["fp"]
        fn = counts["fn"]

        precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        p_sum += precision
        r_sum += recall
        f1_sum += f1
        field_count += 1

        field_results[key] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "support": counts["total_gt"],
        }

    macro_precision = p_sum / max(1, field_count)
    macro_recall = r_sum / max(1, field_count)
    macro_f1 = f1_sum / max(1, field_count)
    exact_match_ratio = float(total_exact_match / max(1, total_fields_evaluated))

    return {
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "exact_match_ratio": exact_match_ratio,
        "total_samples": len(eval_samples),
        "total_fields": total_fields_evaluated,
        "document_types": sorted(doc_types),
        "per_field": field_results,
    }


def classification_metrics(
    actual: list[str],
    predicted: list[str],
    labels: list[str] | None = None,
) -> dict:
    """Compute accuracy, macro & per-class precision, recall, F1, and confusion matrix."""
    if not actual or len(actual) != len(predicted):
        raise ValueError("Actual and predicted label lists must be non-empty and aligned")

    target_labels = list(labels) if labels is not None else sorted(set(actual) | set(predicted))
    total_samples = len(actual)
    correct_count = sum(1 for a, p in zip(actual, predicted, strict=True) if a == p)
    accuracy = float(correct_count / max(1, total_samples))

    label_to_idx = {lbl: i for i, lbl in enumerate(target_labels)}
    num_labels = len(target_labels)
    cm = [[0] * num_labels for _ in range(num_labels)]

    per_class: dict[str, dict[str, float | int]] = {}
    p_sum, r_sum, f1_sum = 0.0, 0.0, 0.0

    for a, p in zip(actual, predicted, strict=True):
        if a in label_to_idx and p in label_to_idx:
            cm[label_to_idx[a]][label_to_idx[p]] += 1

    for i, lbl in enumerate(target_labels):
        tp = cm[i][i]
        fp = sum(cm[row][i] for row in range(num_labels) if row != i)
        fn = sum(cm[i][col] for col in range(num_labels) if col != i)
        support = sum(cm[i][col] for col in range(num_labels))

        prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        rec = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = float(2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

        per_class[lbl] = {
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "support": support,
        }
        p_sum += prec
        r_sum += rec
        f1_sum += f1

    macro_precision = p_sum / max(1, num_labels)
    macro_recall = r_sum / max(1, num_labels)
    macro_f1 = f1_sum / max(1, num_labels)

    return {
        "accuracy": accuracy,
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "per_class": per_class,
        "confusion_matrix_labels": target_labels,
        "confusion_matrix": cm,
    }

