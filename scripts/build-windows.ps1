$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
py -3.12 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Không tạo được venv" }
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw "Không cài được dependency" }
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --name AutoSubVideo --collect-all faster_whisper --collect-all ctranslate2 --collect-all tokenizers --collect-all edge_tts --collect-all onnxruntime --collect-all soundfile --collect-all sea_g2p --collect-all rapidocr --add-data "autosub/windows_speech.ps1;autosub" run.py
if ($LASTEXITCODE -ne 0) { throw "Build thất bại" }
if (Test-Path bundle) {
    Copy-Item -Path bundle -Destination dist\AutoSubVideo\bundle -Recurse
}
Write-Host "Ứng dụng: dist\AutoSubVideo\AutoSubVideo.exe. Bộ dữ liệu gốc nằm trong bundle nếu đã nhập."
