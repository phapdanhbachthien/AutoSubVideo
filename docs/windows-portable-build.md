# Windows x64 portable

Đã tạo native launcher `AutoSubVideo.exe` với Zig 0.14.1 trên Linux, target `x86_64-windows-gnu`, subsystem Windows GUI. Launcher chạy Python 3.12 Windows đi kèm và `launch.py`; đây không phải bản PyInstaller one-file.

Gói portable gồm Python/Tcl/Tk từ `toolkit.pkg` đã đối chiếu SHA-256/kích thước, 54 Windows/pure-Python wheels từ PyPI được kiểm tra RECORD, mã ứng dụng và bundle 25 giọng gốc. Các dependency theo marker Windows (colorama, pyreadline3) được bổ sung. `huggingface-hub` được chọn phiên bản 1.33.0 để thỏa tokenizers `<2.0`; không cài các wheel ứng viên không thuộc tập đã chọn.

Kiểm tra đã thực hiện: quan hệ Requires-Dist theo Windows/Python 3.12, cú pháp Python, cấu trúc PE AMD64 của 195 executable/DLL/PYD, subsystem GUI của launcher và các tệp runtime/Tcl/Tk bắt buộc. Các import DLL nằm ngoài gói được kiểm kê là các thư viện hệ thống Windows. Đây là kiểm tra tĩnh, không chứng minh mọi DLL đã load hoặc ứng dụng đã chạy trên Windows.

**Chưa chạy thử gói portable trên Windows.** Mở `AutoSubVideo.exe` sau khi giải nén toàn bộ ZIP. Chạy `Kiem-tra.cmd` trên Windows để thực hiện kiểm tra native imports và màn hình Tcl/Tk; kết quả ở `diagnostics.json`. Lỗi khởi động được ghi tại `%LOCALAPPDATA%\AutoSubVideo\logs\startup.log`.

## Tái tạo

1. Chuẩn bị bundle bằng `scripts/import-resources.py`.
2. Tải wheel Windows x64 cho Python 3.12 theo `requirements.txt`, thêm colorama/pyreadline3; chọn một phiên bản mỗi distribution và kiểm tra Requires-Dist theo marker Windows. Các phiên bản của gói đã tạo nằm trong `scripts/requirements-windows.lock`.
3. Build launcher:

```sh
python -m pip install ziglang==0.14.1
python -m ziglang cc -target x86_64-windows-gnu -municode -Wl,--subsystem,windows -O2 -s scripts/windows-launcher.c -o AutoSubVideo.exe -luser32
```

4. Gọi `scripts/package-windows-portable.py --help` để cung cấp toolkit, toolkit.json, danh sách đường dẫn wheel đã chọn, launcher và thư mục đầu ra mới. Script xác minh checksum, giải nén runtime và lắp gói; từ chối ghi đè thư mục đã tồn tại.
5. Đóng ZIP cả thư mục đầu ra. Giữ `python`, `autosub`, `bundle` cạnh `.exe`. Xác minh ZIP CRC và thử gói trên máy Windows trước khi coi bản phát hành đã được kiểm chứng.
