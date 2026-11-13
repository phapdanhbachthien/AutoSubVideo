"""Assemble an independent Windows x64 Python/Qt portable directory."""
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


def pe(path):
    with path.open('rb') as stream:
        if stream.read(2)!=b'MZ':
            raise ValueError('Not a PE file: '+str(path))
        stream.seek(0x3c);offset=struct.unpack('<I',stream.read(4))[0]
        stream.seek(offset)
        if stream.read(4)!=b'PE\0\0':
            raise ValueError('Invalid PE signature')
        machine=struct.unpack('<H',stream.read(2))[0]
        stream.seek(offset+24+68);subsystem=struct.unpack('<H',stream.read(2))[0]
    return machine,subsystem


def install_wheel(wheel, python_dir):
    site=python_dir/'Lib/site-packages'
    with zipfile.ZipFile(wheel) as archive:
        metadata_path=next(n for n in archive.namelist() if n.endswith('.dist-info/METADATA'))
        metadata=BytesParser().parsebytes(archive.read(metadata_path))
        tags=archive.read(metadata_path.replace('METADATA','WHEEL')).decode()
        if 'win_amd64' not in tags and 'none-any' not in tags:
            raise ValueError('Expected Windows x64 or pure Python wheel')
        records={r[0]:r for r in csv.reader(io.StringIO(archive.read(metadata_path.replace('METADATA','RECORD')).decode()))}
        for info in archive.infolist():
            if info.is_dir():continue
            name=info.filename;row=records[name]
            if row[1]:
                algorithm,expected=row[1].split('=',1)
                with archive.open(info) as stream:
                    actual=base64.urlsafe_b64encode(hashlib.file_digest(stream,algorithm).digest()).decode().rstrip('=')
                if actual!=expected:raise ValueError('Wheel hash mismatch: '+name)
            relative=Path(name);base=site
            if relative.parts[0].endswith('.data'):
                category=relative.parts[1];relative=Path(*relative.parts[2:])
                if category in ('purelib','platlib'):base=site
                elif category=='data':base=python_dir
                elif category=='scripts':base=python_dir/'Scripts'
                else:continue
            destination=(base/relative).resolve()
            if not destination.is_relative_to(python_dir.resolve()):raise ValueError('Unsafe wheel path')
            destination.parent.mkdir(parents=True,exist_ok=True)
            if destination.exists():
                # PySide6 meta/Essentials/Addons deliberately share identical files.
                with destination.open('rb') as stream:
                    existing=hashlib.file_digest(stream,'sha256').digest()
                with archive.open(info) as stream:
                    incoming=hashlib.file_digest(stream,'sha256').digest()
                if existing!=incoming:raise ValueError('Conflicting wheel file: '+name)
            else:
                with archive.open(info) as source,destination.open('xb') as output:
                    shutil.copyfileobj(source,output)
        return dict(name=metadata['Name'],version=metadata['Version'],wheel=wheel.name)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--python-root',required=True,help='Trusted Windows x64 CPython 3.12 runtime')
    parser.add_argument('--wheels',required=True)
    parser.add_argument('--launcher',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parent.parent
    output=Path(args.output).resolve();python_dir=output/'python'
    if output.exists():raise ValueError('Output already exists')
    if pe(Path(args.launcher))!=(0x8664,2):raise ValueError('Launcher must be AMD64 Windows GUI')
    source=Path(args.python_root).resolve()
    if pe(source/'pythonw.exe')[0]!=0x8664:raise ValueError('Python must be Windows x64')
    python_dir.mkdir(parents=True)
    for path in source.rglob('*'):
        rel=path.relative_to(source)
        if not path.is_file() or rel.parts[:2]==('Lib','site-packages'):continue
        if rel.parts[0] in ('tcl','libs','Scripts','include'):continue
        if any(p in ('__pycache__','test','tests','idlelib') for p in rel.parts) or path.suffix=='.pyc':continue
        target=python_dir/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
    (python_dir/'python312._pth').write_text('python312.zip\n.\nLib\nLib/site-packages\nDLLs\nimport site\n',encoding='utf-8')
    packages=[]
    for wheel in sorted(Path(args.wheels).glob('*.whl')):
        packages.append(install_wheel(wheel,python_dir))
        print('Installed and verified '+wheel.name,flush=True)
    shutil.copytree(root/'player',output/'player',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copytree(root/'assets',output/'assets')
    shutil.copyfile(root/'scripts/portable-bootstrap.py',output/'launch.py')
    shutil.copyfile(root/'scripts/portable-diagnose.py',output/'diagnose.py')
    shutil.copyfile(args.launcher,output/'ThienMediaPlayer.exe')
    for name in ('README.md','THIRD_PARTY.md'):
        shutil.copyfile(root/name,output/name)
    (output/'Kiem-tra.cmd').write_bytes(b'@echo off\r\ncd /d "%~dp0"\r\n"python\\python.exe" "diagnose.py"\r\npause\r\n')
    (output/'HUONG-DAN.txt').write_text(
        'THIỆN MEDIA PLAYER — Windows 10/11 x64\n\n'
        'Giải nén TOÀN BỘ ZIP, mở ThienMediaPlayer.exe. Không cần cài Python riêng.\n'
        'Giữ thư mục python và player cạnh executable.\n'
        'Mở tệp / thư mục hoặc kéo thả nhạc, video. Space: phát/tạm dừng; F11: toàn màn hình.\n'
        'Âm lượng 0–500%, Ctrl+0 về 100%. Logo Bách Thiện Audio.\n'
        'Có đủ nút tua hai chiều 5s, 10s, 30s, 1/5/10 phút và danh sách phát.\n\n'
        'Hỗ trợ nguồn 8K; độ mượt tùy phần cứng, codec và bitrate.\n'
        'Đã thử giải mã khung hình Full HD và 8K trên Linux; chưa chạy gói Windows thực tế.\n'
        'Nếu không mở được: chạy Kiem-tra.cmd. Log: %LOCALAPPDATA%\\ThienMediaPlayer\\logs\\startup.log.\n',encoding='utf-8-sig')
    checked=0
    for path in output.rglob('*'):
        if path.suffix.lower() in ('.exe','.dll','.pyd'):
            if pe(path)[0]!=0x8664:raise ValueError('Unexpected native architecture: '+str(path))
            checked+=1
    (output/'windows-package.json').write_text(json.dumps(dict(application='ThienMediaPlayer',
        platform='Windows x64',windows_execution_tested=False,pe_files_verified=checked,packages=packages),indent=2),encoding='utf-8')
    print(f'Portable prepared; {checked} AMD64 native files checked.',flush=True)


if __name__=='__main__':main()
