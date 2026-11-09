"""Assemble Windows wheels and the verified original embedded Python runtime.

The launcher is built separately using Zig or a Windows C compiler. This does
not claim that a package assembled on Linux has been executed on Windows.
"""
from pathlib import Path
from email.parser import BytesParser
import argparse
import base64
import csv
import hashlib
import io
import json
import shutil
import struct
import zipfile


def pe_info(path):
    with path.open("rb") as f:
        if f.read(2) != b"MZ":
            raise ValueError(f"Not a PE executable: {path}")
        f.seek(0x3C)
        offset = struct.unpack("<I", f.read(4))[0]
        f.seek(offset)
        if f.read(4) != b"PE\0\0":
            raise ValueError(f"Invalid PE header: {path}")
        machine = struct.unpack("<H", f.read(2))[0]
        f.seek(offset + 24 + 68)
        subsystem = struct.unpack("<H", f.read(2))[0]
    return machine, subsystem


def copy_tree(source, destination):
    shutil.copytree(source, destination, copy_function=shutil.copyfile,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def install_wheel(path, python_dir):
    site = python_dir / "Lib/site-packages"
    with zipfile.ZipFile(path) as archive:
        metadata_name = next(n for n in archive.namelist() if n.endswith(".dist-info/METADATA"))
        metadata = BytesParser().parsebytes(archive.read(metadata_name))
        wheel_info = archive.read(metadata_name.replace("METADATA", "WHEEL")).decode()
        if "win_amd64" not in wheel_info and "none-any" not in wheel_info:
            raise ValueError("Not a Windows x64 or pure Python wheel: " + str(path))
        record_name = metadata_name.replace("METADATA", "RECORD")
        records = {r[0]: r for r in csv.reader(io.StringIO(archive.read(record_name).decode()))}
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = info.filename
            row = records.get(name)
            if not row:
                raise ValueError("Wheel member missing from RECORD: " + name)
            if row[1]:
                algorithm, expected = row[1].split("=", 1)
                with archive.open(info) as stream:
                    actual = base64.urlsafe_b64encode(hashlib.file_digest(stream, algorithm).digest()).decode().rstrip("=")
                if actual != expected:
                    raise ValueError("Wheel RECORD hash mismatch: " + name)
            parts = Path(name).parts
            relative = Path(name)
            base = site
            if parts[0].endswith(".data"):
                category = parts[1]
                relative = Path(*parts[2:])
                if category in ("purelib", "platlib"):
                    base = site
                elif category == "data":
                    base = python_dir
                elif category == "scripts":
                    base = python_dir / "Scripts"
                else:
                    continue
            target = (base / relative).resolve()
            if not target.is_relative_to(python_dir.resolve()):
                raise ValueError("Unsafe wheel member path: " + name)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output)
        return {"name": metadata["Name"], "version": metadata["Version"], "wheel": path.name}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--toolkit", required=True)
    parser.add_argument("--toolkit-config", required=True)
    parser.add_argument("--selected-wheels", required=True)
    parser.add_argument("--launcher", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    output, toolkit = Path(args.output).resolve(), Path(args.toolkit)
    if output.exists():
        raise ValueError("Output already exists; use a new directory.")
    expected = json.loads(Path(args.toolkit_config).read_text())
    with toolkit.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != expected["sha256"] or toolkit.stat().st_size != expected["size"]:
        raise ValueError("Original toolkit checksum/size mismatch.")
    if pe_info(Path(args.launcher)) != (0x8664, 2):
        raise ValueError("Launcher must be a Windows x64 GUI executable.")
    output.mkdir(parents=True)
    python_dir = output / "python"
    python_dir.mkdir()
    count = 0
    with zipfile.ZipFile(toolkit) as archive:
        for info in archive.infolist():
            prefix = "runtime/Python/"
            if not info.filename.startswith(prefix) or info.is_dir():
                continue
            relative = Path(info.filename.removeprefix(prefix))
            if relative.parts[:2] == ("Lib", "site-packages"):
                continue
            if any(p in ("__pycache__", "test", "tests", "idle_test") for p in relative.parts) or relative.suffix == ".pyc":
                continue
            target = (python_dir / relative).resolve()
            if not target.is_relative_to(python_dir):
                raise ValueError("Unsafe runtime path.")
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("xb") as destination:
                shutil.copyfileobj(source, destination)
            count += 1
    (python_dir / "python312._pth").write_text("python312.zip\n.\nLib\nLib/site-packages\nDLLs\nimport site\n", encoding="utf-8")
    print(f"Extracted {count} Windows Python runtime files.", flush=True)
    wheels = []
    for line in Path(args.selected_wheels).read_text().splitlines():
        if line.strip():
            wheels.append(install_wheel(Path(line), python_dir))
    print(f"Installed {len(wheels)} Windows wheels with RECORD validation.", flush=True)
    copy_tree(root / "autosub", output / "autosub")
    copy_tree(root / "bundle", output / "bundle")
    copy_tree(root / "docs", output / "docs")
    shutil.copyfile(args.launcher, output / "AutoSubVideo.exe")
    shutil.copyfile(root / "scripts/portable-bootstrap.py", output / "launch.py")
    shutil.copyfile(root / "scripts/portable-diagnose.py", output / "diagnose.py")
    shutil.copyfile(root / "README.md", output / "README.md")
    (output / "Kiem-tra.cmd").write_bytes(b'@echo off\r\ncd /d "%~dp0"\r\n"python\\python.exe" "diagnose.py"\r\npause\r\n')
    (output / "HUONG-DAN.txt").write_text(
        "AutoSubVideo portable — Windows 10/11 64-bit\n\n"
        "1. Giải nén TOÀN BỘ ZIP vào thư mục riêng.\n"
        "2. Mở AutoSubVideo.exe. Không tách exe khỏi python, autosub và bundle.\n"
        "3. Giọng gốc local mặc định Ngọc Huyền; đã có đủ 25 giọng trong bundle.\n"
        "4. Nếu không mở được, chạy Kiem-tra.cmd; xem diagnostics.json và log tại "
        "%LOCALAPPDATA%\\AutoSubVideo\\logs\\startup.log.\n\n"
        "Gói đã được kiểm tra cấu trúc, checksum và thư viện Windows trên Linux; "
        "chưa được chạy thử trên Windows. Chưa ký số executable.\n"
        "Whisper cần mô hình riêng lần đầu; dịch cần API/mô hình bạn chọn.\n",
        encoding="utf-8-sig")
    (output / "windows-package.json").write_text(json.dumps({
        "architecture": "windows-x86_64", "runtime_source": "original verified toolkit.pkg",
        "runtime_execution_tested": False, "runtime_files": count,
        "launcher_pe": {"machine": "AMD64", "subsystem": "Windows GUI"}, "wheels": wheels,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Portable directory prepared: " + str(output), flush=True)


if __name__ == "__main__":
    main()
