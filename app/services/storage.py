"""File-storage adapter with secure local-volume implementation."""
from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Protocol

from app.config import settings

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".csv", ".txt", ".md", ".png", ".jpg", ".jpeg"}
SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class StoredFile:
    storage_key: str
    original_name: str
    size_bytes: int
    sha256: str
    media_type: str


class StorageAdapter(Protocol):
    def save(self, stream: BinaryIO, filename: str, media_type: str, size_bytes: int) -> StoredFile: ...
    def open(self, storage_key: str) -> BinaryIO: ...
    def delete(self, storage_key: str) -> None: ...


class LocalVolumeStorage:
    def __init__(self, root: str | Path | None = None, max_mb: int | None = None) -> None:
        self.root = Path(root or settings.upload_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_bytes = int(max_mb or settings.max_upload_mb) * 1024 * 1024

    def save(self, stream: BinaryIO, filename: str, media_type: str, size_bytes: int) -> StoredFile:
        if size_bytes > self.max_bytes:
            raise ValueError(f"File exceeds {self.max_bytes // (1024 * 1024)} MB limit")
        clean = SAFE_NAME.sub("_", Path(filename).name).strip("._") or "attachment"
        extension = Path(clean).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise ValueError(f"File type '{extension or 'unknown'}' is not allowed")
        key = f"{uuid.uuid4()}-{clean}"
        target = (self.root / key).resolve()
        if self.root.resolve() not in target.parents:
            raise ValueError("Invalid storage path")
        digest = hashlib.sha256()
        written = 0
        with target.open("wb") as output:
            while chunk := stream.read(1024 * 1024):
                written += len(chunk)
                if written > self.max_bytes:
                    output.close()
                    target.unlink(missing_ok=True)
                    raise ValueError("File exceeded size limit while streaming")
                digest.update(chunk)
                output.write(chunk)
        return StoredFile(key, filename, written, digest.hexdigest(), media_type)

    def open(self, storage_key: str) -> BinaryIO:
        target = (self.root / Path(storage_key).name).resolve()
        if self.root.resolve() not in target.parents or not target.exists():
            raise FileNotFoundError(storage_key)
        return target.open("rb")

    def delete(self, storage_key: str) -> None:
        target = (self.root / Path(storage_key).name).resolve()
        if self.root.resolve() not in target.parents:
            raise ValueError("Invalid storage key")
        target.unlink(missing_ok=True)
