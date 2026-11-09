# Tái sử dụng tài nguyên gốc

Nguồn: `v-translate-07-11.7z` do người dùng cung cấp qua Google Drive. Giữ nguyên tên giọng và dữ liệu; không đổi tên giọng Edge thành giọng gốc.

| Thành phần trong gói cũ | Cách sử dụng trong AutoSubVideo |
| --- | --- |
| 25 preset `voices_v3_turbo.json`, embedding 192 chiều và mã âm học | Đọc trực tiếp, hiển thị đủ giọng, giữ mô tả/vùng miền/alias; Ngọc Huyền là lựa chọn mặc định khi có bundle |
| ONNX FP32 `onnx_update` và int8 `onnx_int8` | Chọn trong giao diện; inference CPU không cần tải mạng |
| MOSS codec ONNX 48 kHz | Giải mã giọng thực tế từ mã âm học; sample được xuất WAV để nghe/ghép |
| Runtime `voice_runtime` và `voice_runtime_utils` | Dùng engine ONNX đã kiểm tra cùng chuẩn hóa, phát âm, chia câu, khoảng nghỉ và kiểm soát lặp; không đổi trọng số |
| Manifest TTS | Kiểm tra toàn vẹn 48 tệp trước khi nạp engine |
| Mô hình phát hiện chữ, phân loại hướng và nhận dạng PP-OCRv6 | OCR phụ đề trong video, tạo SRT để dịch và lồng giọng |
| 4 mô hình nhận dạng compact/quality/universal/universal_medium | Chọn trong OCR; kiểm tra SHA-256 theo manifest gốc |
| Font SFU Cooper Black, Noto Sans CJK | Nạp trong FFmpeg, chọn font/cỡ chữ khi xuất |
| Từ điển `typoMap.json` | Tùy chọn sửa lỗi OCR; mặc định tắt |
| Từ điển đa ngôn ngữ và các trọng số Paddle cũ | Giữ trong bundle để tham chiếu/chuyển đổi; chưa chạy các backend Paddle cũ trong luồng mới |
| FFmpeg/FFprobe Windows | Ứng dụng tự tìm và dùng trong bundle trên Windows |
| yt-dlp Windows | Giữ sẵn trong bundle; chưa có luồng tải URL trong giao diện |
| Worker OCR/quét chữ, script cũ, cấu hình và tài liệu/giấy phép đi kèm | Giữ trong `bundle/reference`; không tự chạy launcher cũ hoặc khẳng định đã tích hợp mọi chức năng cũ |
| Python nhúng, DLL nền tảng, CUDA/OpenVINO trùng lặp, cache/log cũ | Không sao chép vào runtime hoạt động; thay bằng dependency phù hợp với nền tảng mới |

`bundle/toolkit-inventory.json` ghi toàn bộ 14.513 mục của toolkit để không bỏ sót kiểm kê. `bundle/import-manifest.json` ghi kích thước/SHA-256 của các tệp đã nhập. Importer xác minh toolkit theo SHA-256 và kích thước trong `toolkit.json` trước khi đọc dữ liệu.

## Đã kiểm tra bằng dữ liệu thật

- Ngọc Huyền đã tạo WAV ngoại tuyến bằng embedding/codes gốc và mô hình FP32, không gọi Edge/Microsoft.
- OCR bằng các mô hình gốc đã đọc hình thử nghiệm; cả compact, quality, universal và universal_medium đều trả về chữ.
- Bài kiểm tra OCR video xác minh ghép các lần xuất hiện của cùng câu thành một khoảng phụ đề.
- Bộ kiểm tra FFmpeg xác minh thời lượng, phụ đề hiển thị và thay/trộn âm thanh.
- Đã chạy `scripts/check-original-voices.py`: **25/25 giọng** tạo được mẫu WAV thật, có [báo cáo từng giọng](voice-validation.json); kiểm tra tệp âm thanh hợp lệ không thay thế việc người nghe đánh giá chất lượng.

Chưa chạy ứng dụng cũ, bản build Windows hoặc mọi backend GPU/Paddle. Không tuyên bố mô hình TTS Việt gốc đọc tốt tất cả ngôn ngữ; dùng giọng Edge/ngôn ngữ phù hợp khi cần đọc tiếng khác.
