"""Locate and inspect the user's original, extracted resource bundle."""
from pathlib import Path
import hashlib
import json
import os
import sys


def app_root():
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent


def default_bundle():
    return os.getenv("AUTOSUB_BUNDLE", str(app_root() / "bundle"))


def tts_root(bundle):
    root = Path(bundle).expanduser().resolve()
    for path in (root, root / "assets/tts", root / "_internal/assets/tts", root / "v-translate-07-11/_internal/assets/tts"):
        if (path / "models/voices_v3_turbo.json").is_file() and (path / "src/voice_runtime").is_dir():
            return path
    raise ValueError("Không tìm thấy bộ giọng gốc. Chọn thư mục bundle hoặc v-translate đã giải nén.")


def original_catalog(bundle):
    path = tts_root(bundle) / "models/voices_v3_turbo.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("presets"), dict) or not data["presets"]:
        raise ValueError("Danh sách giọng gốc không hợp lệ.")
    return data


def verify_bundle(bundle):
    root = tts_root(bundle)
    manifest = root.parent.parent / "local_tts_manifest.json"
    # Imported minimal bundles keep the original manifest at their root.
    if not manifest.is_file():
        manifest = Path(bundle) / "local_tts_manifest.json"
    if not manifest.is_file():
        raise ValueError("Thiếu local_tts_manifest.json để kiểm tra dữ liệu gốc.")
    entries = json.loads(manifest.read_text(encoding="utf-8"))
    checked = 0
    for name, expected in entries.items():
        if not name.startswith("assets/tts/"):
            continue
        path = root / name.removeprefix("assets/tts/")
        if not path.is_file():
            raise ValueError(f"Thiếu dữ liệu: {name}")
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != expected:
            raise ValueError(f"Dữ liệu không khớp SHA-256: {name}")
        checked += 1
    return checked


def bundled_tool(name, bundle=None):
    if os.name != "nt":
        return name
    root = Path(bundle or default_bundle())
    for folder in (root / "tools", root / "_internal", root / "v-translate-07-11/_internal"):
        path = folder / (name + ".exe")
        if path.is_file():
            return str(path.resolve())
    return name


def font_directory(bundle=None):
    root = Path(bundle or default_bundle())
    for folder in (root / "fonts", root / "_internal/assets/fonts", root / "v-translate-07-11/_internal/assets/fonts"):
        if folder.is_dir():
            return folder
    return None
