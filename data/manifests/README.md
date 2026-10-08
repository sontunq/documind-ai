# Classification dataset v1

`classification-v1.json` is the authoritative, versioned dataset: `classification-synthetic-en-v1`.
It contains 63 original, generated English documents, with 21 examples each of invoice, contract,
and form. The source and license are recorded per sample (synthetic, CC0-1.0); names and
transactions are fictional. No private documents or external corpus were used.

Text is representative OCR-like text, **not measured OCR output**. Each sample embeds its text
and a reference to that JSON field. Keep these texts small and reviewable. Model artifacts belong
in ignored `.runtime/classification`, not in this directory.

## Splits and leakage

- The fixed manual split was assigned before fitting: 15 training and 6 test documents per class
  (45 train / 18 test). There is no validation split, hyperparameter search, or threshold tuning.
- Each text is separately authored for a distinct logical document. Test subjects are separate
  from training subjects; no numeric/name substitutions of one document span train and test.
- `logical_document_id` groups variants if any are added. The loader rejects a logical ID across
  splits, duplicate sample IDs, missing provenance, and cross-split text duplicates after
  normalizing case, punctuation, whitespace and numeric differences. This automated check does
  not establish semantic independence: new samples also need human inspection.
- All splits must retain their assignments. Revise the dataset version when editing samples.
  Training fits the vectorizer and classifier on **train only**. Evaluation accepts only the
  exact manifest digest recorded by the model and scores **test only**.
- Smoke-test documents are generated separately by `backend/scripts/smoke_classification.py`;
  they are not added to training or the held-out metrics.

## Interpretation and limitations

The labels follow the purpose of the document: a request for payment is an invoice, an agreement
with mutual obligations is a contract, and a template collecting information is a form.
This is a closed three-class task. It has no unknown/receipt/letter class. Nonempty unrelated text
still receives a model argmax; its low score can flag review, but this is not a reliable
out-of-distribution detector. Empty/non-alphanumeric OCR text receives no invented label.

The balanced, small synthetic corpus has obvious lexical cues, shared author style, little
layout diversity and limited OCR corruption (including one `INVOlCE` test heading). Forms are
mostly unfilled, and contracts are short excerpts. Test results do not estimate performance on
arbitrary real invoices, long contracts, filled forms, handwriting, or multilingual documents.
Real OCR can omit underscores or alter words; the real form smoke sample is correctly classified
but below the review threshold. More diverse independently sourced data is needed before any
real-world quality claim. No class imbalance exists in this version; future data may differ.

See the repository README for training/evaluation commands and `docs/progress.md` for actual
measured metrics and model identity. The 0.60 threshold is an untuned demonstration policy,
not an estimated error rate or calibrated business-risk cutoff.
