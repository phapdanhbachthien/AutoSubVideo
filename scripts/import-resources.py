"""Copy reusable resources from the user's extracted v-translate directory."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from autosub.resources import tts_root, verify_bundle


def import_resources(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if destination.exists():
        raise ValueError("Thư mục đích đã tồn tại; chọn thư mục mới để bảo toàn dữ liệu.")
    root = tts_root(source)
    original = root.parent.parent
    verify_bundle(source)
    destination.mkdir(parents=True)
    shutil.copytree(root, destination / "assets/tts", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copyfile(original / "local_tts_manifest.json", destination / "local_tts_manifest.json")
    for filename in ("ffmpeg.exe", "ffprobe.exe", "yt-dlp.exe"):
        path = original / filename
        if path.is_file():
            target = destination / "tools" / filename
            target.parent.mkdir(exist_ok=True)
            shutil.copyfile(path, target)
    if (original / "assets/fonts").is_dir():
        shutil.copytree(original / "assets/fonts", destination / "fonts")
    package = original / "assets/toolkit.pkg"
    inventory = []
    if package.is_file():
        expected = json.loads((original / "assets/toolkit.json").read_text())
        with package.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != expected["sha256"] or package.stat().st_size != expected["size"]:
            raise ValueError("toolkit.pkg không khớp SHA-256 hoặc kích thước gốc.")
        with zipfile.ZipFile(package) as z:
            for info in z.infolist():
                name = info.filename
                inventory.append({"name": name, "size": info.file_size})
                relative = None
                if name.startswith("runtime/Python/Lib/site-packages/rapidocr/models/"):
                    relative = "ocr/rapidocr/models/" + name.rsplit("/", 1)[-1]
                elif name.startswith("runtime/resources/backend/models/"):
                    relative = "ocr/legacy-models/" + name.removeprefix("runtime/resources/backend/models/")
                elif name.startswith("models/"):
                    relative = "ocr/recognition-models/" + name.removeprefix("models/")
                elif name.startswith("runtime/Python/Lib/site-packages/paddleocr/ppocr/utils/") and name.endswith(".txt"):
                    relative = "ocr/dictionaries/" + name.removeprefix("runtime/Python/Lib/site-packages/paddleocr/ppocr/utils/")
                elif name.startswith("scripts/") or name.startswith("runtime/resources/backend/configs/") or name.startswith("runtime/resources/backend/interface/"):
                    relative = "reference/" + name
                elif name in ("runtime/resources/LICENSE", "runtime/resources/README.md", "runtime/resources/README_en.md", "runtime/resources/vtranslate_local_ocr_worker.py", "runtime/resources/detect_text_frames.py"):
                    relative = "reference/" + name
                elif name.endswith("NotoSansCJK-Bold.otf"):
                    relative = "fonts/NotoSansCJK-Bold.otf"
                if relative is not None and not info.is_dir():
                    target = (destination / relative).resolve()
                    if not target.is_relative_to(destination):
                        raise ValueError("Đường dẫn tài nguyên không an toàn: " + name)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(info) as src, target.open("xb") as dst:
                        shutil.copyfileobj(src, dst)
    (destination / "toolkit-inventory.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    records = []
    for path in sorted(destination.rglob("*")):
        if path.is_file():
            with path.open("rb") as stream:
                sha = hashlib.file_digest(stream, "sha256").hexdigest()
            records.append({"path": str(path.relative_to(destination)).replace("\\", "/"), "size": path.stat().st_size, "sha256": sha})
    (destination / "import-manifest.json").write_text(json.dumps({"source": "v-translate-07-11", "files": records}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Imported {len(records)} files; verified {verify_bundle(destination)} TTS entries.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Thư mục v-translate đã giải nén")
    parser.add_argument("--destination", default=str(Path(__file__).resolve().parent.parent / "bundle"))
    args = parser.parse_args()
    import_resources(args.source, args.destination)
