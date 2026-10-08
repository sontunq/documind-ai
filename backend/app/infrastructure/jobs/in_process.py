from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
import logging
from threading import BoundedSemaphore
from uuid import UUID

logger = logging.getLogger(__name__)


class InProcessDispatcher:
    """One CPU worker and a bounded number of accepted jobs; no durable queue."""
    def __init__(self, execute: Callable[[UUID], None], capacity: int = 8) -> None:
        self.execute = execute
        self.slots = BoundedSemaphore(capacity)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="documind-ocr")

    def enqueue(self, run_id: UUID) -> None:
        if not self.slots.acquire(blocking=False):
            raise RuntimeError("Local processing capacity reached")
        try:
            future = self.executor.submit(self.execute, run_id)
        except BaseException:
            self.slots.release()
            raise
        future.add_done_callback(self._finished)

    def _finished(self, future: Future) -> None:
        self.slots.release()
        if future.exception() is not None:
            # No exception text: database/provider failures may contain secrets.
            logger.error("OCR job could not finish or persist its failure; run offline recovery before retrying")

    def close(self) -> None:
        self.executor.shutdown(wait=True)
