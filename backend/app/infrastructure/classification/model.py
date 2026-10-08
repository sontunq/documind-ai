"""Trusted local TF-IDF/Logistic Regression artifacts; no online training."""
from datetime import UTC, datetime
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from threading import Lock
from time import perf_counter
import warnings

import joblib
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from app.domain.classification import ClassificationContext, ClassificationResult, ClassScores, DocumentType
from app.domain.ocr import OCRResult
from app.domain.processing import PipelineSpec
from app.infrastructure.classification.dataset import LABELS, distribution, fingerprint, validate_dataset
from app.infrastructure.classification.text import normalize_text

MODEL_IDENTIFIER = "tfidf-logistic-regression"


def training_config(threshold: float = 0.60) -> dict:
    if not 0 <= threshold <= 1:
        raise ValueError("Threshold must be between zero and one")
    return {
        "preprocessing": "lowercase-whitespace-v1",
        "vectorizer": {"ngram_range": [1, 2], "min_df": 1, "max_df": 1.0,
                       "sublinear_tf": True, "norm": "l2", "lowercase": False},
        "classifier": {"C": 1.0, "solver": "lbfgs", "max_iter": 1000,
                       "random_state": 42, "class_weight": None, "tol": 0.0001},
        "threshold": threshold,
        "threshold_rationale": "Untuned demonstration policy: flag max probability below 0.60; not a calibrated risk cutoff.",
    }


def train(dataset: dict, artifact: Path, threshold: float = 0.60) -> dict:
    validate_dataset(dataset)
    config = training_config(threshold)
    vectorizer = {**config["vectorizer"], "ngram_range": tuple(config["vectorizer"]["ngram_range"])}
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(preprocessor=normalize_text, **vectorizer)),
        ("classifier", LogisticRegression(**config["classifier"])),
    ])
    samples = sorted((s for s in dataset["samples"] if s["split"] == "train"), key=lambda s: s["id"])
    start = perf_counter()
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        pipeline.fit([s["text"] for s in samples], [s["label"] for s in samples])
    elapsed = perf_counter() - start
    libraries = {name: version(name) for name in ("scikit-learn", "numpy", "scipy", "joblib")}
    # Changes to code, data, dependency versions or parameters change identity.
    implementation = {name: sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                      for name in ("model.py", "text.py", "dataset.py")}
    identity = {"dataset_version": dataset["dataset_version"], "training_digest": fingerprint(samples),
                "config": config, "libraries": libraries, "implementation": implementation}
    metadata = {
        "model_identifier": MODEL_IDENTIFIER, "model_version": fingerprint(identity),
        "dataset_version": dataset["dataset_version"], "dataset_digest": fingerprint(dataset),
        "config_version": fingerprint(config), "training_identity": identity,
        "training_timestamp": datetime.now(UTC).isoformat(), "training_seconds": elapsed,
        "training_sample_count": len(samples), "training_distribution": distribution(dataset, "train"),
        "label_mapping": list(pipeline.classes_), "config": config, "libraries": libraries,
        "vectorizer_parameters": {k: ("normalize_text" if k == "preprocessor" else str(v) if k == "dtype" else v)
                                  for k, v in pipeline["tfidf"].get_params().items()},
        "classifier_parameters": pipeline["classifier"].get_params(),
    }
    artifact.parent.mkdir(parents=True, exist_ok=True)
    # CLI is an offline operation; restart the backend after replacing artifacts.
    joblib.dump({"pipeline": pipeline, "metadata": metadata}, artifact, compress=3)
    import json
    artifact.with_suffix(".metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


class SklearnDocumentClassifier:
    def __init__(self, artifact: Path) -> None:
        self.artifact = artifact
        self.artifact_digest = sha256(artifact.read_bytes()).hexdigest() if artifact.is_file() else "unavailable"
        self._pipeline = None
        self.metadata: dict = {}
        self.load_seconds = 0.0
        self.last_inference_seconds = 0.0
        self._lock = Lock()

    def load(self) -> None:
        with self._lock:
            if self._pipeline is not None:
                return
            start = perf_counter()
            if sha256(self.artifact.read_bytes()).hexdigest() != self.artifact_digest:
                raise ValueError("Classifier artifact changed; restart backend")
            # Only load locally trained/trusted artifacts. Joblib can execute code.
            bundle = joblib.load(self.artifact)
            metadata, pipeline = bundle["metadata"], bundle["pipeline"]
            if metadata["libraries"]["scikit-learn"] != version("scikit-learn"):
                raise ValueError("Classifier scikit-learn version mismatch; retrain")
            if set(pipeline.classes_) != set(LABELS) or list(pipeline.classes_) != metadata["label_mapping"]:
                raise ValueError("Classifier must contain exactly the three supported classes")
            if metadata["model_version"] != fingerprint(metadata["training_identity"]):
                raise ValueError("Model metadata identity mismatch")
            if metadata["config_version"] != fingerprint(metadata["config"]):
                raise ValueError("Model configuration identity mismatch")
            self.metadata, self._pipeline = metadata, pipeline
            self.load_seconds = perf_counter() - start

    def probabilities(self, texts: list[str]) -> list[dict[str, float]]:
        self.load()
        start = perf_counter()
        probabilities = self._pipeline.predict_proba(texts)
        self.last_inference_seconds = perf_counter() - start
        return [dict(zip(self._pipeline.classes_, map(float, row), strict=True)) for row in probabilities]

    def predict(self, ocr_result: OCRResult, context: ClassificationContext) -> ClassificationResult:
        text = "\n".join(page.text for page in ocr_result.pages)
        if not any(c.isalnum() for c in text):
            raise ValueError("No usable OCR text")
        scores = self.probabilities([text])[0]
        # classes_ order provides deterministic tie handling; never alter scores.
        selected = max(scores, key=scores.get)
        metadata = self.metadata
        return ClassificationResult(
            context.document_id, context.run_id, DocumentType(selected), ClassScores(**scores),
            scores[selected], metadata["config"]["threshold"], metadata["model_identifier"],
            metadata["model_version"], metadata["dataset_version"], metadata["config_version"], datetime.now(UTC),
        )


def classification_pipeline_spec(ocr: PipelineSpec, classifier: SklearnDocumentClassifier) -> PipelineSpec:
    config = {**ocr.config, "classification_model": MODEL_IDENTIFIER,
              "classification_artifact_sha256": classifier.artifact_digest}
    return PipelineSpec("ocr-classification-v1", fingerprint(config), config)
