from io import BytesIO
from pathlib import Path
from unittest.mock import Mock
from uuid import UUID

import pytest

from app.infrastructure.storage.local import LocalDocumentStorage


def test_storage_roundtrip_and_cleanup(tmp_path):
    storage = LocalDocumentStorage(tmp_path)
    first = storage.store(BytesIO(b"synthetic bytes"))
    second = storage.store(BytesIO(b"synthetic bytes"))
    assert UUID(hex=first).hex == first
    assert first != second
    assert (tmp_path / first).read_bytes() == b"synthetic bytes"
    storage.delete(first)
    storage.delete(first)
    assert not (tmp_path / first).exists()
    assert (tmp_path / second).exists()


def test_partial_write_is_removed(tmp_path):
    class BrokenStream(BytesIO):
        def read(self, size=-1):
            if self.tell():
                raise OSError("read failed")
            return super().read(2)
    with pytest.raises(OSError):
        LocalDocumentStorage(tmp_path).store(BrokenStream(b"abcdef"))
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("key", [
    pytest.param("../outside", id="posix-traversal"),
    pytest.param(r"..\outside", id="windows-traversal"),
    pytest.param("nested/../../outside", id="nested-escape"),
    pytest.param("/synthetic-outside", id="posix-absolute"),
    pytest.param(r"C:\synthetic-outside", id="windows-absolute"),
    pytest.param("C:/synthetic-outside", id="windows-forward-slash"),
    pytest.param("C:synthetic-outside", id="windows-drive-relative"),
    pytest.param(r"\synthetic-outside", id="windows-root-relative"),
    pytest.param(r"\\synthetic-host\share\file", id="windows-unc"),
    pytest.param(r"\\?\C:\synthetic-outside", id="windows-device-path"),
    pytest.param("", id="empty"),
    pytest.param("..", id="parent"),
])
def test_storage_rejects_unsafe_keys(tmp_path, monkeypatch, key):
    storage = LocalDocumentStorage(tmp_path)
    # These are inert strings, never real target paths. Guard OS operations so
    # even a validation regression cannot touch the synthetic absolute targets.
    with monkeypatch.context() as guard:
        for operation in ("resolve", "stat", "lstat", "open", "unlink", "mkdir"):
            guard.setattr(Path, operation, Mock(side_effect=AssertionError(
                "Unsafe keys must be rejected before filesystem access"
            )))
        with pytest.raises(ValueError, match="Invalid storage key"):
            storage.delete(key)
        with pytest.raises(ValueError, match="Invalid storage key"):
            storage.open(key)


def test_escape_cannot_delete_sibling_file(tmp_path):
    # Both the storage root and the potential escape target belong to tmp_path.
    root = tmp_path / "storage"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.write_bytes(b"must survive")
    storage = LocalDocumentStorage(root)
    for key in ("../outside", r"..\outside", str(outside)):
        with pytest.raises(ValueError, match="Invalid storage key"):
            storage.delete(key)
    assert outside.read_bytes() == b"must survive"
    assert list(root.iterdir()) == []
