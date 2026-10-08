from threading import Event
from uuid import uuid4

import pytest

from app.infrastructure.jobs.in_process import InProcessDispatcher


def test_bounded_runner_releases_capacity_and_drains_on_close():
    entered, release = Event(), Event()
    seen = []
    def execute(run_id):
        entered.set()
        assert release.wait(5)
        seen.append(run_id)
    dispatcher = InProcessDispatcher(execute, capacity=1)
    run_id = uuid4()
    try:
        dispatcher.enqueue(run_id)
        assert entered.wait(5)
        with pytest.raises(RuntimeError, match="capacity"):
            dispatcher.enqueue(uuid4())
    finally:
        release.set()
        dispatcher.close()
    assert seen == [run_id]
    # Failed submission after shutdown also releases its slot.
    with pytest.raises(RuntimeError):
        dispatcher.enqueue(uuid4())
    assert dispatcher.slots.acquire(blocking=False)
