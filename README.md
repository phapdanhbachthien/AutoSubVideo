# Thiện Media Player // Cyber Edition

[Tải Windows EXE portable (~217 MB)](https://github.com/phapdanhbachthien/AutoSubVideo/releases/download/thien-media-player-cyber-v0.2.0-preview/ThienMediaPlayer-Cyber-v0.2.0-Windows-x64.zip) · [Mã nguồn ZIP](https://github.com/phapdanhbachthien/AutoSubVideo/releases/download/thien-media-player-cyber-v0.2.0-preview/ThienMediaPlayer-Cyber-v0.2.0-source.zip) · [Ảnh giao diện](https://github.com/phapdanhbachthien/AutoSubVideo/releases/download/thien-media-player-cyber-v0.2.0-preview/ThienMediaPlayer-Cyber-v0.2.0-preview.png)

Ứng dụng Windows riêng để nghe nhạc và xem video, không phụ thuộc AutoSubVideo. Giao diện cyberpunk tiếng Việt: nền lưới đen tím, neon cyan/hồng, khung vát góc và nút phát vàng neon. Qt 6 / FFmpeg xử lý media; hiệu ứng giao diện tĩnh không che vùng video.

## Bản 0.2.0

- Sửa đúng tên **Thiện**, gồm tiêu đề cửa sổ, giao diện và thông tin file EXE.
- Thêm logo dựa trên ảnh Bách Thiện Audio người dùng cung cấp: header, màn hình nhạc, icon cửa sổ/taskbar và icon nhúng trong EXE.
- Âm lượng lên đến 500% bằng xử lý PCM trước QAudioSink; không dùng mẹo đổi nhãn thanh trượt bị Qt chặn ở 100%.
- Tín hiệu nhỏ giữ đúng gain x5; đỉnh lớn được nén mềm để tránh tràn mẫu. Mức 500% không thể khiến mọi nguồn đều nghe to gấp 5 lần vì giới hạn đỉnh và thiết bị.
- Tốc độ phát dùng lấy mẫu lại trong đường PCM, có thể thay đổi cao độ. Bản này chưa có time-stretch giữ cao độ.

## Chức năng

- Phát/tạm dừng/dừng; chuyển bài trước/sau; mở nhiều tệp hoặc cả thư mục; kéo thả.
- Danh sách phát: tìm kiếm, kéo để đổi thứ tự, bỏ mục, xóa danh sách, sắp xếp A–Z, lưu/mở M3U/M3U8 UTF-8. Bỏ khỏi playlist không xóa tệp trên máy.
- **Tua tiến và lùi: 5 giây, 10 giây, 30 giây, 1 phút, 5 phút, 10 phút**. Thanh tua kéo/nhấp; đi đến số giây cụ thể.
- Phát ngẫu nhiên, lặp danh sách hoặc một bài; tự chuyển bài khi hết; nhớ playlist và vị trí xem (có thể tắt).
- Âm lượng **0–500%** bằng khuếch đại PCM thật, giới hạn đỉnh mềm chống tràn mẫu, tắt tiếng; tốc độ 0,25×–4×. `Ctrl+0` đưa âm lượng về 100%.
- Toàn màn hình, luôn nổi trên cùng, tỉ lệ gốc/lấp đầy/kéo giãn; chụp khung hình PNG gốc; xem codec/độ phân giải/FPS.
- Chọn luồng âm thanh và phụ đề nhúng; mở SRT UTF-8 ngoài, chỉnh sớm/muộn đến 60 giây.
- Mở HTTP(S) trực tiếp tới tệp/luồng tương thích, không phải tải/trích video từ trang web.

## Chất lượng video

Không giới hạn giao diện ở Full HD: engine có thể giải mã nguồn Full HD, 4K, 8K theo codec được hỗ trợ. Windows dùng tăng tốc phần cứng khi Qt/FFmpeg, GPU và driver hỗ trợ; nếu không sẽ dùng CPU khi có decoder tương thích. Ứng dụng không tự nâng video độ phân giải thấp lên chi tiết 8K và không giải mã DRM.

**Không bảo đảm 8K 30/60 fps trên mọi máy.** Đã thử giải mã thực tế H.264 1920×1080 và FFV1 7680×4320 (một khung hình 8K). Phép thử này xác minh kích thước giải mã, không chứng minh phát video thương mại 8K bitrate cao mượt hoặc xuất HDR đúng trên mọi màn hình.

Các định dạng thông dụng: MP4/MKV/MOV/AVI/WebM/WMV/MPEG/TS; MP3/FLAC/WAV/OGG/Opus/M4A/AAC/WMA… Khả năng đọc một tệp cụ thể phụ thuộc container, codec và dữ liệu tệp.

## Dùng gói Windows portable

1. Giải nén toàn bộ `ThienMediaPlayer-Cyber-v0.2.0-Windows-x64.zip`.
2. Mở `ThienMediaPlayer.exe`. Giữ thư mục `python` và `player` cạnh file EXE; không cần cài Python riêng.
3. Bấm **Mở tệp**, **Mở thư mục** hoặc kéo nhạc/video vào cửa sổ. Playlist mở bài bằng nhấp đôi hoặc Enter.
4. Nếu có lỗi khởi động, chạy `Kiem-tra.cmd`; kết quả ở `diagnostics.json`. Log ở `%LOCALAPPDATA%\ThienMediaPlayer\logs\startup.log`.

Đóng bản cũ và giải nén vào **thư mục mới**. Windows 10/11 64-bit. Gói có native launcher và runtime Python/Qt/FFmpeg đi kèm; không phải EXE một tệp độc lập. **Chưa chạy thử trực tiếp gói trên Windows.**

## Phím tắt

| Phím | Chức năng |
| --- | --- |
| Space / S | Phát hoặc tạm dừng / Dừng |
| N, PageDown / P, PageUp | Bài tiếp / Bài trước |
| ← / → | Tua 5 giây |
| Ctrl + ← / → | Tua 10 giây |
| Alt + ← / → | Tua 30 giây |
| Shift + ← / → | Tua 1 phút |
| Ctrl + Shift + ← / → | Tua 5 phút |
| Alt + Shift + ← / → | Tua 10 phút |
| ↑ / ↓ / M | Tăng, giảm âm lượng / Tắt tiếng |
| F, F11 / Esc | Toàn màn hình / Thoát toàn màn hình |
| Home / Ctrl+G | Về đầu / Đi đến thời gian |
| Ctrl+O / Ctrl+Shift+O | Mở tệp / Mở thư mục |
| Ctrl+L / Ctrl+Shift+S | Mở / Lưu playlist |
| Ctrl+S / Ctrl+I | Chụp khung hình / Thông tin media |
| Delete | Bỏ các mục đã chọn khỏi playlist |

Phím điều khiển không chặn việc gõ chữ vào ô tìm kiếm.

## Chạy mã nguồn / build

Python 3.12:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python run.py
```

Build PyInstaller trên máy Windows:

```powershell
powershell -File scripts\build-windows.ps1
```

Hoặc dùng `scripts/package-portable.py` với Windows CPython 3.12 x64, 4 wheel PySide6/shiboken6 Windows và launcher native được biên dịch từ `scripts/windows-launcher.c`. Builder kiểm tra hash RECORD của wheel, kiến trúc PE và từ chối ghi đè thư mục đầu ra. Các thư viện Qt có mặt đầy đủ để tránh bỏ nhầm plugin codec.

## Kiểm thử

```sh
python -m unittest discover -s tests -v
```

Cần FFmpeg CLI cho việc tạo tệp thử; người dùng bản portable không cần FFmpeg CLI riêng. Đã chạy **16/16 bài kiểm tra** trên Linux/Xorg, gồm kiểm tra pixel video hiển thị thật, lớp phụ đề hiển thị trên video, playlist/lặp/ngẫu nhiên, SRT và Unicode, 12 nút tua bằng GUI với tệp 12 phút, thanh tua/phím tắt, chuyển bài/toàn màn hình, đồng hồ phát âm thanh và khung hình giải mã Full HD/8K thật. Môi trường thử không có loa: chưa kiểm chứng âm thanh phát ra thiết bị vật lý, tăng tốc GPU Windows, HDR hoặc độ mượt 8K.

Thiết lập cá nhân lưu qua QSettings, gồm playlist/vị trí khi bật nhớ. Khi phát triển có thể đặt `THIEN_PLAYER_CONFIG` tới tệp INI riêng. Các định dạng có DRM, Blu-ray/DVD menu, truyền Chromecast và cân bằng âm thanh EQ chưa nằm trong bản này.


## Kiểm tra âm thanh 500%

Ngoài kiểm tra dữ liệu PCM, đã ghi lại đầu ra thật của QAudioSink qua thiết bị PulseAudio ảo trên Linux: RMS 100% = 0.06268189, RMS 500% = 0.31340778, tỉ lệ **4.99997 lần**. Đây là đo đường âm thanh phần mềm, không phải đo độ to vật lý của loa Windows. Các mẫu kiểm tra bao gồm mute, giới hạn đỉnh, tốc độ và xóa bộ đệm khi tua.
