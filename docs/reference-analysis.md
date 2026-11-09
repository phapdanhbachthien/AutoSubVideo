# Nghiên cứu gói v-translate-07-11

Nguồn: thư mục Google Drive `1jBBvGs73qAjkP5ccjgtayZEyDIu2Nawz`, tệp `1JgiWJQD4VtQFzstcn2cRShS6_tkuR6ai`.

## Đã quan sát

- Gói `v-translate-07-11.7z`, 2.820.551.558 byte; 11.941 mục; tổng dung lượng giải nén 3.917.300.747 byte. 7z dùng LZMA2/BCJ, solid, 2 block.
- `v-translate-07-11.exe` là chương trình Windows đóng gói PyInstaller, kèm Python 3.10 và CustomTkinter.
- Có FFmpeg, FFprobe, yt-dlp, Edge TTS, OpenCV, Selenium, ONNX Runtime và OpenVINO. Sự hiện diện của thư viện chưa chứng minh mỗi tính năng đều được đưa ra giao diện hoặc hoạt động.
- Có mô hình TTS cục bộ ONNX int8 và bộ khác tên `onnx_update`, codec âm thanh, danh sách giọng `voices_v3_turbo.json`, và manifest hash tài nguyên TTS.
- `assets/toolkit.pkg` chiếm 2.255.606.872 byte. `toolkit.json` khai báo schema 4, kích thước và SHA-256 dự kiến. Chưa trích xuất hoặc kiểm chứng toàn bộ tài nguyên này.
- Đã đọc cấu trúc archive PyInstaller và tên module; có `vtranslate_local_tts`, `vtranslate_local_tts_ui`. Tệp launcher tham chiếu `v_translate_07_11_core`.

## Giới hạn nghiên cứu ban đầu và cập nhật

Ban đầu chỉ kiểm tra tĩnh danh sách archive, cấu trúc executable và cấu hình. Sau yêu cầu dùng dữ liệu gốc, đã giải nén TTS, xác minh 48 hash, chạy ONNX tạo giọng Ngọc Huyền thật và gọi các mô hình OCR thật. `toolkit.pkg` là ZIP thông thường, đã xác minh hash/kích thước và kiểm kê 14.513 mục. Không thực thi launcher Windows hoặc vượt kiểm tra bản quyền. Không thể khẳng định tương đương toàn bộ chức năng của ứng dụng cũ từ những kiểm tra này.

## Bản triển khai độc lập

AutoSubVideo hiện có giao diện Tkinter, chỉnh SRT Unicode, adapter faster-whisper CPU, API dịch tương thích OpenAI với máy chủ tùy chọn và FFmpeg xuất MP4 có phụ đề/lồng giọng. Phần xử lý văn bản không có danh sách từ cấm; dịch yêu cầu giữ sắc thái và từ tục. Nhà cung cấp/mô hình quyết định khả năng đáp ứng thực tế.

Phần giọng hiện có 25 preset ONNX gốc (có Ngọc Huyền), cùng Edge và Windows SAPI. Chế độ local đã tạo âm thanh bằng mô hình thật; Edge trong cloud bị chặn 403 và SAPI cần Windows. Xem [bảng tái sử dụng](resource-reuse.md) để phân biệt dữ liệu đang hoạt động với dữ liệu chỉ giữ để tham chiếu.
