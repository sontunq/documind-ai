"""Fixed probabilities for tests only; never training/evaluation data."""
from datetime import UTC, datetime

from app.domain.classification import ClassificationResult, ClassScores, DocumentType


class FakeClassifier:
    def __init__(self, scores=None):
        self.scores = scores or {"invoice": .8, "contract": .1, "form": .1}
        self.calls = 0
        self.fail = False

    def predict(self, ocr_result, context):
        self.calls += 1
        if self.fail:
            raise RuntimeError("SECRET C:/private/model.joblib")
        selected = max(self.scores, key=self.scores.get)
        return ClassificationResult(context.document_id, context.run_id, DocumentType(selected),
                                    ClassScores(**self.scores), self.scores[selected], .6,
                                    "TEST ONLY fake classifier", "test-model", "test-dataset", "test-config",
                                    datetime.now(UTC))
