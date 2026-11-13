# Thành phần đi kèm

- Python 3.12 Windows: giữ LICENSE.txt của runtime. Gói thử được lắp từ runtime Windows đã kiểm tra trong workspace; có thể thay bằng CPython 3.12 x64 tương thích khi tái tạo.
- PySide6 / Qt 6.8.3 / shiboken6: dùng bản wheel chính thức từ PyPI; giữ metadata và các giấy phép trong distribution. Qt/PySide có điều khoản LGPL/GPL/commercial tùy thành phần; xem tệp giấy phép đi kèm bản phân phối.
- FFmpeg trong Qt Multimedia: giữ nguyên các DLL và thông tin giấy phép của wheel. Codec khả dụng và hỗ trợ phần cứng phụ thuộc bản build/nền tảng.
- Native launcher được biên dịch bằng Zig 0.14.1; mã C nằm trong scripts/windows-launcher.c.

Gói dùng liên kết động. Không đổi trọng số TTS, không chứa AutoSubVideo hoặc dữ liệu giọng vì đây là ứng dụng media riêng.
