"""Resolve pinned, approved theme assets without executing asset content."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path


_ASSET_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_VERSION = re.compile(r"^v[0-9]{3}$")
_CATEGORY = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_EXECUTABLE_SUFFIXES = {
    ".py", ".pyc", ".pyo", ".sh", ".bash", ".zsh", ".fish", ".exe",
    ".com", ".bat", ".cmd", ".ps1", ".psm1", ".dll", ".so", ".dylib",
    ".wasm", ".jar", ".class", ".msi", ".app", ".deb", ".rpm",
}
_SAFE_MIME_BY_SUFFIX = {
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".webp": {"image/webp"},
    ".ttf": {"font/ttf", "application/x-font-ttf", "application/font-sfnt"},
    ".otf": {"font/otf", "application/vnd.ms-opentype", "application/font-sfnt"},
    ".woff": {"font/woff", "application/font-woff"},
    ".woff2": {"font/woff2", "font/woff2"},
    ".wav": {"audio/wav", "audio/x-wav"},
    ".mp3": {"audio/mpeg"},
    ".flac": {"audio/flac", "audio/x-flac"},
    ".mp4": {"video/mp4"},
    ".json": {"application/json"},
}


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid theme asset JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Theme asset metadata must be an object: {path}")
    return value


def _contained_path(root: Path, relative: str, *, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ValueError(f"Missing {label} path")
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise ValueError(f"Unsafe {label} path: {relative}")
    root = root.resolve()
    path = (root / raw).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"{label} path escapes kit root: {relative}")
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_asset(kit_root: Path, asset_id: str, version: str, *, allow_draft: bool = False) -> dict:
    """Resolve an exact hash-pinned asset; draft resolution requires explicit review opt-in."""
    root = Path(kit_root).resolve()
    if not isinstance(asset_id, str) or not _ASSET_ID.fullmatch(asset_id):
        raise ValueError(f"Invalid theme asset id: {asset_id!r}")
    if not isinstance(version, str) or not _VERSION.fullmatch(version):
        raise ValueError(f"Invalid theme asset version: {version!r}")

    index_path = root / "library" / "index.json"
    index = _read_json(index_path)
    if index.get("schema_version") != 1 or not isinstance(index.get("assets"), list):
        raise ValueError("Unsupported or invalid library/index.json")
    matches = [entry for entry in index["assets"]
               if isinstance(entry, dict) and entry.get("id") == asset_id]
    if not matches:
        raise ValueError(f"Unknown theme asset id: {asset_id}")
    exact = [entry for entry in matches if entry.get("version") == version]
    if not exact:
        raise ValueError(f"Theme asset version is not pinned in library index: {asset_id}/{version}")
    if len(exact) != 1:
        raise ValueError(f"Duplicate theme asset index entry: {asset_id}/{version}")
    entry = exact[0]
    status = entry.get("status")
    if status != "approved" and not (allow_draft and status == "draft"):
        raise ValueError(f"Theme asset is not approved: {asset_id}/{version}")
    category = entry.get("category")
    if not isinstance(category, str) or not _CATEGORY.fullmatch(category):
        raise ValueError(f"Invalid theme asset category: {category!r}")

    metadata_rel = entry.get("metadata")
    metadata_path = _contained_path(root, metadata_rel, label="asset metadata")
    library_root = (root / "library").resolve()
    if not metadata_path.is_relative_to(library_root):
        raise ValueError("Asset metadata must be inside the kit library")
    expected = Path("library") / category / asset_id / version / "asset.json"
    if metadata_path != (root / expected).resolve():
        raise ValueError(f"Unexpected metadata path for {asset_id}/{version}")
    metadata = _read_json(metadata_path)
    if (metadata.get("id"), metadata.get("category"), metadata.get("version")) != (asset_id, category, version):
        raise ValueError(f"Asset metadata identity mismatch: {asset_id}/{version}")
    if metadata.get("status") != status:
        raise ValueError(f"Asset metadata status mismatch: {asset_id}/{version}")
    approval = metadata.get("approval")
    if not isinstance(approval, dict) or not approval.get("evidence"):
        raise ValueError(f"Asset approval evidence is missing: {asset_id}/{version}")
    if status == "approved" and not approval.get("approved_by"):
        raise ValueError(f"Approved asset evidence is missing: {asset_id}/{version}")
    if status == "draft" and (approval.get("approved_by") is not None or approval.get("status") != "pending"):
        raise ValueError(f"Draft asset approval state is invalid: {asset_id}/{version}")

    files = metadata.get("files")
    primary = metadata.get("primary_file")
    if not isinstance(files, list) or not isinstance(primary, str):
        raise ValueError(f"Asset file manifest is missing: {asset_id}/{version}")
    file_entries = [item for item in files if isinstance(item, dict) and item.get("path") == primary]
    if len(file_entries) != 1:
        raise ValueError(f"Asset primary file must appear exactly once: {asset_id}/{version}")
    file_entry = file_entries[0]
    asset_root = metadata_path.parent.resolve()
    file_path = _contained_path(asset_root, primary, label="asset file")
    if not file_path.is_relative_to(asset_root) or not file_path.is_relative_to(root):
        raise ValueError(f"Asset file escapes kit/library root: {primary}")
    if not file_path.is_file():
        raise ValueError(f"Theme asset file is missing: {asset_id}/{version}/{primary}")
    suffix = file_path.suffix.lower()
    if suffix in _EXECUTABLE_SUFFIXES or suffix not in _SAFE_MIME_BY_SUFFIX:
        raise ValueError(f"Executable or unsupported theme asset file: {primary}")
    if os.stat(file_path).st_mode & 0o111:
        raise ValueError(f"Executable permission is forbidden for theme asset: {primary}")
    mime = file_entry.get("mime")
    if not isinstance(mime, str) or mime not in _SAFE_MIME_BY_SUFFIX[suffix]:
        raise ValueError(f"Theme asset MIME does not match file type: {primary}")
    expected_hash = file_entry.get("sha256")
    if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        raise ValueError(f"Invalid theme asset SHA-256 metadata: {primary}")
    actual_hash = _sha256(file_path)
    if actual_hash != expected_hash:
        raise ValueError(f"Theme asset SHA-256 mismatch: {asset_id}/{version}/{primary}")

    return {
        "id": asset_id,
        "category": category,
        "version": version,
        "path": file_path,
        "metadata_path": metadata_path,
        "sha256": actual_hash,
        "mime": mime,
        "status": status,
    }
