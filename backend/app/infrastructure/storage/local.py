from pathlib import Path
import re
import shutil
from typing import BinaryIO
from uuid import uuid4


class LocalDocumentStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def store(self, stream: BinaryIO) -> str:
        self.root.mkdir(parents=True, exist_ok=True)
        key = uuid4().hex
        path = self.root / key
        # Exclusive creation prevents overwriting any existing object.
        target = path.open("xb")
        try:
            with target:
                shutil.copyfileobj(stream, target, length=64 * 1024)
        except BaseException:
            # Includes flush/close failures (for example a full disk).
            path.unlink(missing_ok=True)
            raise
        return key

    def delete(self, storage_key: str) -> None:
        if not re.fullmatch(r"[a-f0-9]{32}", storage_key):
            raise ValueError("Invalid storage key")
        (self.root / storage_key).unlink(missing_ok=True)

    def open(self, storage_key: str) -> BinaryIO:
        if not re.fullmatch(r"[a-f0-9]{32}", storage_key):
            raise ValueError("Invalid storage key")
        return (self.root / storage_key).open("rb")
