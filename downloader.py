"""Archive discovery, download, and safe ZIP extraction helpers."""

from __future__ import annotations

import os
import shutil
import stat
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any

import requests

ARCHIVE_LIST_URL = "https://api.cijene.dev/v0/list"
TIMEOUT = (15, 180)
MAX_ARCHIVE_BYTES = 1_000_000_000
MAX_EXTRACTED_BYTES = 20_000_000_000
MAX_ARCHIVE_MEMBERS = 10_000


@dataclass(frozen=True)
class Archive:
    date: date
    url: str
    size: int | None = None


def list_archives(session: requests.Session | None = None) -> list[Archive]:
    client = session or requests.Session()
    response = client.get(ARCHIVE_LIST_URL, timeout=TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("archives"), list):
        raise ValueError("Archive-list response does not contain an archives array")
    result = []
    for item in payload["archives"]:
        if not isinstance(item, dict):
            raise ValueError("Archive list contains a non-object entry")
        try:
            archive_date = date.fromisoformat(item["date"])
            url = item["url"]
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid archive-list entry: {item!r}") from exc
        if not isinstance(url, str) or not url.startswith("https://"):
            raise ValueError(f"Invalid archive HTTPS URL: {url!r}")
        size = item.get("size")
        if size is not None and (not isinstance(size, int) or size <= 0):
            raise ValueError(f"Invalid archive size: {size!r}")
        result.append(Archive(archive_date, url, size))
    if not result:
        raise ValueError("Archive provider returned an empty archive list")
    return sorted(result, key=lambda archive: archive.date)


def newest_archive(archives: list[Archive]) -> Archive:
    if not archives:
        raise ValueError("No archives are available")
    return max(archives, key=lambda archive: archive.date)


def download_archive(archive: Archive, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    temporary = tempfile.NamedTemporaryFile(
        prefix=f"cijene-{archive.date}-", suffix=".zip.part", dir=directory, delete=False
    )
    path = Path(temporary.name)
    downloaded = 0
    try:
        with temporary, requests.get(archive.url, stream=True, timeout=TIMEOUT) as response:
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                downloaded += len(chunk)
                if downloaded > MAX_ARCHIVE_BYTES:
                    raise ValueError("Archive exceeds the configured download limit")
                temporary.write(chunk)
            temporary.flush()
            os.fsync(temporary.fileno())
        if downloaded == 0:
            raise ValueError("Downloaded archive is empty")
        if archive.size is not None and downloaded != archive.size:
            raise ValueError(
                f"Archive size mismatch: expected {archive.size}, downloaded {downloaded}"
            )
        return path
    except Exception:
        path.unlink(missing_ok=True)
        raise


def _member_path(name: str) -> PurePosixPath:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (not normalized or normalized.startswith("/") or path.is_absolute()
            or ".." in path.parts or any(":" in part for part in path.parts)):
        raise ValueError(f"Unsafe ZIP member path: {name!r}")
    return path


def validate_and_extract_zip(archive_path: Path, extraction_directory: Path) -> None:
    extraction_directory.mkdir(parents=True, exist_ok=False)
    try:
        if not zipfile.is_zipfile(archive_path):
            raise ValueError("Downloaded file is not a valid ZIP archive")
        with zipfile.ZipFile(archive_path) as archive:
            members = archive.infolist()
            if not members or len(members) > MAX_ARCHIVE_MEMBERS:
                raise ValueError("ZIP member-count sanity check failed")
            seen: set[str] = set()
            extracted_bytes = 0
            for member in members:
                relative = _member_path(member.filename)
                canonical = relative.as_posix().rstrip("/")
                if canonical in seen:
                    raise ValueError(f"Duplicate ZIP member: {member.filename!r}")
                seen.add(canonical)
                if stat.S_ISLNK(member.external_attr >> 16):
                    raise ValueError(f"ZIP symlinks are not allowed: {member.filename!r}")
                if member.flag_bits & 0x1:
                    raise ValueError(f"Encrypted ZIP member: {member.filename!r}")
                extracted_bytes += member.file_size
                if extracted_bytes > MAX_EXTRACTED_BYTES:
                    raise ValueError("ZIP expands beyond the configured size limit")
            corrupt = archive.testzip()
            if corrupt is not None:
                raise ValueError(f"ZIP CRC validation failed for {corrupt!r}")
            for member in members:
                target = extraction_directory.joinpath(*_member_path(member.filename).parts)
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(member) as source, target.open("wb") as destination:
                        shutil.copyfileobj(source, destination, length=1024 * 1024)
    except Exception:
        shutil.rmtree(extraction_directory, ignore_errors=True)
        raise
