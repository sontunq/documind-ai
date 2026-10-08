from dataclasses import replace
from datetime import datetime
from io import BytesIO
from math import inf, nan
from uuid import uuid4

import pytest

from app.application.classify_document import ClassifyDocument
from app.application.errors import ApplicationError
from app.domain.classification import ClassificationContext, ClassScores, DocumentType
from app.domain.documents import DocumentStatus as S
from classification_fakes import FakeClassifier
from conftest import make_image
from test_processing import processing, processing_client  # Shared deterministic fixtures.


def prediction(scores=None):
    return FakeClassifier(scores).predict(None, ClassificationContext(uuid4(), uuid4()))


@pytest.mark.parametrize("label", list(DocumentType))
def test_supported_class_and_threshold_boundary(label):
    scores = {item.value: .2 for item in DocumentType}
    scores[label.value] = .6
    result = prediction(scores)
    assert result.predicted_type == label
    assert not result.needs_review and result.document_status == S.COMPLETED
    low = replace(result, threshold=.61)
    assert low.needs_review and low.document_status == S.NEEDS_REVIEW


@pytest.mark.parametrize("value", [-.1, 1.1, inf, nan])
def test_invalid_probabilities_and_threshold(value):
    with pytest.raises(ValueError):
        ClassScores(value, .1, .1)
    with pytest.raises(ValueError):
        replace(prediction(), threshold=value)
    with pytest.raises(ValueError):
        replace(prediction(), confidence=value)


@pytest.mark.parametrize("changes", [
    {"predicted_type": "receipt"}, {"predicted_type": DocumentType.FORM},
    {"confidence": .7}, {"model_version": ""}, {"dataset_version": ""},
    {"config_version": ""}, {"created_at": datetime(2026, 1, 1)}, {"document_id": "invalid"},
])
def test_invalid_prediction_contract(changes):
    with pytest.raises(ValueError):
        replace(prediction(), **changes)
    with pytest.raises(ValueError):
        ClassScores(.3, .3, .3)
    with pytest.raises(TypeError):
        ClassScores(invoice=.8, contract=.2)


def saved_ocr(service, processing):
    document = service.create(BytesIO(make_image()), "synthetic.png")
    run = processing.scheduling.schedule(document.id)
    processing.worker.execute(run.id)
    return document, processing.repository.results(document.id).current_run


def test_missing_ocr_does_not_invoke_classifier():
    fake = FakeClassifier()
    with pytest.raises(ApplicationError) as error:
        ClassifyDocument(fake).execute(None, ClassificationContext(uuid4(), uuid4()))
    assert error.value.code == "CLASSIFICATION_OCR_MISSING"
    assert fake.calls == 0


@pytest.mark.parametrize("text", ["", "  \n ", "... ---"])
def test_empty_ocr_explicit_failure_retains_ocr(service, processing, monkeypatch, text):
    p = processing
    recognize = p.provider.recognize
    def empty(pages, context):
        result = recognize(pages, context)
        line = replace(result.pages[0].lines[0], text=text)
        return replace(result, pages=(replace(result.pages[0], text=text, lines=(line,)),))
    monkeypatch.setattr(p.provider, "recognize", empty)
    doc = service.create(BytesIO(make_image()), "blank.png")
    run = p.scheduling.schedule(doc.id)
    p.worker.execute(run.id)
    results = p.repository.results(doc.id)
    assert results.status == S.FAILED
    assert results.latest_run.error_code == "CLASSIFICATION_EMPTY_TEXT"
    assert results.latest_run.result is not None
    assert results.latest_run.classification is None and results.current_run is None
    assert p.classifier.calls == 0
    with service.storage.open(results.latest_run.result.raw_output_reference) as raw:
        assert raw.read()


def test_low_confidence_persistence_idempotency_and_reprocess(service, processing):
    p = processing
    p.classifier.scores = {"invoice": .4, "contract": .35, "form": .25}
    doc, first = saved_ocr(service, p)
    assert p.repository.results(doc.id).status == S.NEEDS_REVIEW
    assert first.status == S.COMPLETED  # Stage ran successfully; document is flagged.
    assert first.classification.needs_review
    assert first.classification.run_id == first.result.run_id == first.id
    assert p.scheduling.schedule(doc.id).id == first.id
    p.worker.execute(first.id)
    assert p.classifier.calls == 1
    second = p.scheduling.schedule(doc.id, reprocess=True)
    p.classifier.scores = {"invoice": .1, "contract": .8, "form": .1}
    p.worker.execute(second.id)
    current = p.repository.results(doc.id).current_run
    assert current.id == second.id and current.classification.predicted_type == DocumentType.CONTRACT
    assert p.repository.runs[first.id].classification == first.classification
    assert p.repository.results(doc.id).status == S.COMPLETED


def test_classifier_failure_keeps_prior_classification_and_new_ocr(service, processing):
    p = processing
    doc, first = saved_ocr(service, p)
    second = p.scheduling.schedule(doc.id, reprocess=True)
    p.classifier.fail = True
    p.worker.execute(second.id)
    results = p.repository.results(doc.id)
    assert results.current_run.id == first.id
    assert results.current_run.classification == first.classification
    assert results.latest_run.result and results.latest_run.classification is None
    assert results.latest_run.error_code == "CLASSIFICATION_FAILED"
    assert "SECRET" not in results.latest_run.error_message
    with service.storage.open(results.latest_run.result.raw_output_reference) as raw:
        assert raw.read()
    p.classifier.fail = False
    third = p.scheduling.schedule(doc.id)
    p.worker.execute(third.id)
    assert p.repository.results(doc.id).current_run.id == third.id


def test_ocr_failure_does_not_call_classifier(service, processing):
    processing.provider.fail = True
    doc = service.create(BytesIO(make_image()), "test.png")
    run = processing.scheduling.schedule(doc.id)
    processing.worker.execute(run.id)
    assert processing.classifier.calls == 0
    assert processing.repository.results(doc.id).latest_run.error_code == "OCR_FAILED"


@pytest.mark.parametrize("bad_result", [None, "not a result", prediction()])
def test_invalid_adapter_result_fails_stage(service, processing, monkeypatch, bad_result):
    monkeypatch.setattr(processing.classifier, "predict", lambda *args: bad_result)
    doc = service.create(BytesIO(make_image()), "test.png")
    run = processing.scheduling.schedule(doc.id)
    processing.worker.execute(run.id)
    results = processing.repository.results(doc.id)
    assert results.latest_run.error_code == "CLASSIFICATION_FAILED"
    assert results.latest_run.classification is None


def test_classification_api_empty_low_and_missing(processing_client, processing):
    client = processing_client
    response = client.post("/api/v1/documents", files={"file": ("synthetic.png", make_image())})
    base = f"/api/v1/documents/{response.json()['id']}"
    assert client.get(base + "/results").json()["current_run"] is None
    processing.classifier.scores = {"invoice": .4, "contract": .3, "form": .3}
    client.post(base + "/process")
    processing.worker.execute(processing.dispatcher.pending[-1])
    result = client.get(base + "/results")
    assert result.status_code == 200
    body = result.json()
    assert body["status"] == "NEEDS_REVIEW"
    prediction = body["current_run"]["classification"]
    assert prediction["predicted_type"] == "invoice" and prediction["needs_review"]
    assert prediction["scores"] == processing.classifier.scores
    assert prediction["created_at"].endswith("Z")
    assert prediction["run_id"] == body["current_run"]["result"]["run_id"]
    assert "joblib" not in result.text and "reference" not in result.text
    assert client.get(f"/api/v1/documents/{uuid4()}/results").status_code == 404


def test_mismatched_ocr_context_rejected(service, processing):
    doc, run = saved_ocr(service, processing)
    with pytest.raises(ValueError):
        ClassifyDocument(FakeClassifier()).execute(run.result, ClassificationContext(doc.id, uuid4()))
