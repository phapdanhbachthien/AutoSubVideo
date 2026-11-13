$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
py -3.12 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Không tạo được môi trường Python" }
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller==6.16.0
if ($LASTEXITCODE -ne 0) { throw "Không cài được thư viện" }
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --name ThienMediaPlayer --collect-all PySide6 --collect-all shiboken6 run.py
if ($LASTEXITCODE -ne 0) { throw "Build thất bại" }
Write-Host "Mở dist\ThienMediaPlayer\ThienMediaPlayer.exe; giữ toàn bộ thư mục đi kèm."
