# AutoSubVideo

Ứng dụng desktop hướng tới Windows: tạo phụ đề từ video/âm thanh, dịch đa ngôn ngữ, tạo giọng đọc và lồng tiếng. Phần điều phối và giao diện được viết mới; các giọng, mô hình ONNX và dữ liệu phù hợp từ gói v-translate của bạn được nhập vào thư mục `bundle` và sử dụng trực tiếp.

## Các chức năng

| Chức năng | Cách dùng |
| --- | --- |
| Tự động tạo phụ đề từ âm thanh/video | Whisper đa ngôn ngữ, nhận diện ngôn ngữ tự động hoặc chọn mã nguồn |
| Nhập phụ đề có sẵn | SRT UTF-8, sửa nội dung và thời gian, xuất SRT |
| Dịch sang tiếng Việt hoặc ngôn ngữ khác | Chọn ngôn ngữ đích hoặc nhập tên tùy ý; API tương thích OpenAI, gồm máy chủ cục bộ như Ollama |
| Giọng đọc | **25 giọng gốc offline, có Ngọc Huyền**; Edge TTS đa ngôn ngữ; SAPI Windows |
| OCR phụ đề trong hình | Mô hình ONNX gốc, 4 bộ nhận dạng, lấy mẫu vùng phụ đề và tạo SRT |
| Chọn/nghe giọng | Lọc ngôn ngữ/tên, tải danh sách hiện có, nghe thử, điều chỉnh tốc độ |
| Tạo lời đọc từ SRT | Xuất WAV, giữ khoảng nghỉ, tăng tốc khi lời đọc dài hơn mốc phụ đề |
| Lồng tiếng vào video | Thay âm thanh gốc hoặc trộn ở âm lượng 0–100%, ghép phụ đề vào hình |
| Quy trình tự động | Âm thanh/video → SRT → dịch tùy chọn → WAV tùy chọn → video tùy chọn; cũng nhận SRT hoặc bảng đang sửa |

Phần mềm không tự che từ tục bằng dấu sao; prompt dịch yêu cầu giữ nghĩa, sắc thái và từ ngữ. Mô hình/dịch vụ AI có giới hạn riêng và có thể từ chối hoặc sửa nội dung; ứng dụng không bảo đảm đầu ra “uncensored” của nhà cung cấp.

## Cài và chạy trên Windows

1. Cài **Python 3.12** có Tcl/Tk và **FFmpeg** có bộ lọc `subtitles`/libass. Thêm `ffmpeg` và `ffprobe` vào PATH.
2. Mở terminal tại repository:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m autosub
```

Kiểm tra FFmpeg bằng `ffmpeg -version`, `ffprobe -version`. Nhập/sửa SRT và ghép video chỉ cần thư viện chuẩn Python cùng FFmpeg. Có thể cài riêng `requirements-asr.txt` hoặc `requirements-tts.txt` nếu chỉ cần một chức năng.

### Nhập bộ dữ liệu gốc

Bản đầy đủ kèm thư mục `bundle`: giải nén và giữ thư mục này cạnh mã nguồn hoặc file `.exe`. Ứng dụng tự chọn **local / Ngọc Huyền** khi tìm thấy dữ liệu. Bản ZIP mã nguồn nhỏ không chứa các mô hình lớn.

Nếu đã có bộ v-translate cũ, giải nén `.7z`, rồi chạy:

```powershell
.venv\Scripts\python scripts\import-resources.py "D:\duong-dan\v-translate-07-11"
```

Importer kiểm tra 48 SHA-256 TTS cùng SHA-256/kích thước `toolkit.pkg`, chỉ đọc gói gốc và tạo thư mục `bundle` mới. Không chạy launcher cũ. Dữ liệu gồm cả FP32/int8, codec, 25 giọng, runtime TTS, các bộ OCR, từ điển, font và công cụ Windows. Thư mục đích đã tồn tại sẽ được từ chối để bảo toàn dữ liệu.

Trong cửa sổ giọng đọc, chọn `local` và thư mục `bundle` hoặc thư mục v-translate đã giải nén. TTS có thể dùng trực tiếp thư mục cũ; OCR cần thư mục `bundle` do importer chuẩn bị. Có thể đặt biến `AUTOSUB_BUNDLE` để dùng một vị trí khác.

### Nhận dạng và dịch

- Chọn MP4/MKV/MOV/WebM hoặc MP3/WAV/M4A/FLAC/OGG/AAC/WMA. Bấm **Nhận dạng** với Whisper `base`, `small`… hoặc đường dẫn thư mục mô hình CTranslate2. Lần đầu cần tải mô hình; sau đó nhận dạng trên CPU int8, không gửi âm thanh lên API.
- Ngôn ngữ nguồn: để trống để tự phát hiện hoặc chọn `vi`, `en`, `zh`, `ja`, `ko`… Whisper hỗ trợ các ngôn ngữ của mô hình được chọn; chất lượng phụ thuộc âm thanh/mô hình.
- Hoặc chọn SRT rồi bấm **Nạp SRT**. Nhấp đôi một dòng để sửa.
- Điền API kết thúc bằng `/v1`, tên mô hình và ngôn ngữ đích. Ví dụ Ollama: `http://localhost:11434/v1`. Cần cài/chạy Ollama và tải mô hình riêng. Máy chủ từ xa cần HTTPS. API key chỉ giữ trong bộ nhớ hoặc lấy từ `AUTOSUB_API_KEY`.
- Bấm **Dịch**, rồi **Lưu SRT**. Ứng dụng giữ mốc thời gian và kiểm tra số dòng trả về. Văn bản phụ đề được gửi đến API bạn chọn; dùng máy chủ cục bộ nếu cần xử lý riêng tư.

### Giọng đọc và lồng tiếng

Mở **Chọn / nghe giọng đọc…**:

- `local`: dùng **đúng dữ liệu 25 giọng gốc**, có **Ngọc Huyền, Trúc Ly, Mai Anh, Hải Đăng, Ngọc Trân, Thùy Dung…** Chạy offline, không cần Microsoft hoặc API key. Giữ nguyên tên, vùng miền, mô tả và alias cũ. [Danh sách đầy đủ](docs/original-voices.json).
- Chọn **FP32** để ưu tiên chất lượng hoặc **int8** để giảm dung lượng làm việc/tăng tốc trên CPU phù hợp. Số luồng CPU 1–16, mặc định 2. Model được nạp một lần rồi dùng lại cho các câu tiếp theo; đổi thư mục runtime đã nạp cần khởi động lại ứng dụng.

- `edge`: giọng trực tuyến Microsoft, không cần API key, cần Internet. Có sẵn lựa chọn **Hoài My (nữ)** và **Nam Minh (nam)** cho tiếng Việt, cùng giọng Anh, Trung, Nhật, Hàn, Pháp, Đức, Tây Ban Nha, Thái. Đây là tên giọng dịch vụ, không phải mô hình đã đóng gói trong ứng dụng. Bấm **Tải danh sách giọng hiện có** để lấy danh mục mới nhất.
- `windows`: bấm tải danh sách để lấy các giọng SAPI đang cài trên máy Windows. Không phải mọi giọng trong cài đặt Windows đều được SAPI/System.Speech nhận diện; ứng dụng chỉ liệt kê giọng mà backend thực sự thấy. Không tự cài thêm giọng hoặc giả định có sẵn giọng Việt.
- Lọc theo `vi-`, `en-`, `zh-`, tên hoặc giới tính, chọn giọng, nhập câu và bấm **Nghe thử**. Trên Windows âm thanh phát qua loa. Tốc độ từ -50 đến +100%; backend Windows quy đổi sang mức tốc độ SAPI.
- **Xuất giọng WAV** đọc bảng phụ đề hiện tại, bao gồm nội dung đã dịch. Mỗi câu được đặt tại mốc bắt đầu; lời đọc quá dài sẽ tăng tốc để vừa mốc kết thúc, lời ngắn được nối khoảng nghỉ. Khi cần tăng tốc trên 2 lần ứng dụng ghi cảnh báo trong nhật ký để bạn nới mốc thời gian.
- Bật **Lồng giọng khi xuất video** rồi bấm **Xuất video**. Âm lượng gốc 0% thay hoàn toàn, 20% giữ nền nhỏ, 100% trộn nguyên âm lượng gốc. Trộn không tách riêng giọng gốc khỏi nhạc nền.

Phụ đề chồng thời gian hoặc không theo thứ tự cần được sửa trước khi tạo giọng đọc. Không clone giọng, không đồng bộ khẩu hình. Dịch vụ Edge có thể thay đổi hoặc tạm ngừng; chọn Windows để dùng các giọng SAPI cục bộ sẵn có.

### OCR phụ đề đã gắn trong hình

Bấm **OCR chữ trong video…**, chọn `universal`, `universal_medium`, `compact` hoặc `quality`. Hai bộ universal dùng PP-OCRv6 đa ngôn ngữ; compact/quality dùng PP-OCRv4 thiên về chữ Trung. Cả 4 mô hình được lấy từ gói cũ và đã gọi thử nhận dạng thực tế.

Mặc định quét phần dưới từ 65% chiều cao, mỗi 0,5 giây. Đổi thành 0 để quét toàn hình. Có thể bật sửa lỗi theo từ điển `typoMap.json` gốc. Sau OCR, kiểm tra lại chữ và thời gian trên bảng rồi dịch/tạo giọng như với SRT. Mốc OCR có độ phân giải theo khoảng lấy mẫu; đây không phải căn thời gian chính xác từng từ.

Mục **Công cụ → Kiểu phụ đề…** cho chọn font và cỡ chữ. Font SFU Cooper Black và Noto Sans CJK từ gói cũ được nạp khi xuất video. Trên Windows, FFmpeg/FFprobe gốc trong bundle được dùng tự động, không cần cài chúng vào PATH nếu đã nhập đủ.

### Tự động toàn bộ

Chọn nguồn **Âm thanh/video**, **Tệp SRT**, **Bảng phụ đề** hoặc **Chữ trong video (OCR)**. Bật các bước dịch, tạo giọng và xuất video theo nhu cầu. Chọn thư mục đích; ứng dụng tạo thư mục mới `AutoSubVideo-*` với:

- `original.srt` và `translated.srt` nếu có dịch.
- `narration.wav` nếu bật giọng đọc.
- `video.mp4` nếu bật xuất video và có đầu vào video.

Đầu vào chỉ có âm thanh/SRT có thể xuất SRT và WAV. Nếu một bước thất bại, nhật ký chỉ ra thư mục kết quả; các bước đã ghi thành công được giữ để dùng lại. Video/WAV đã tồn tại không bị ghi đè.

## Đóng gói Windows

```powershell
powershell -File scripts\build-windows.ps1
```

Chạy theo chính sách script của máy Windows. Script cài dependency và đóng gói PyInstaller cùng script SAPI; đầu ra dự kiến `dist\AutoSubVideo\AutoSubVideo.exe`. Giữ cả thư mục; script sao chép `bundle` vào bản build nếu đã nhập tài nguyên. Nếu không có công cụ gốc trong bundle thì cần FFmpeg/FFprobe trong PATH. Chưa chạy build này trên Windows; PyInstaller Linux không tạo/xác minh được executable Windows.

## Kiểm tra và giới hạn xác minh

```sh
python -m unittest discover -s tests -v
```

Đã chạy **13/13 bài kiểm tra, không bỏ qua bài nào**, gồm tạo giọng Ngọc Huyền ONNX thật, kiểm tra SHA-256 và OCR video thật khi có bundle. Các kiểm tra trên màn hình Xorg bao gồm: mở giao diện/nạp SRT/chọn giọng, đọc/ghi Unicode, adapter Whisper và Edge, dữ liệu API dịch, đồng bộ WAV bằng âm thanh fixture, FFmpeg xuất video, giữ/thay/trộn âm thanh. Thử xuất video kiểm tra luồng âm thanh, thời lượng và pixel phụ đề.

- Kiểm tra adapter Whisper/Edge và API dịch dùng backend giả; một số bài kiểm tra đồng bộ dùng sóng sin. Kiểm tra TTS local và OCR bổ sung dùng mô hình/dữ liệu gốc thật, không giả lập. Kiểm tra âm thanh hợp lệ không thay thế đánh giá chất lượng giọng bằng tai.
- **25/25 giọng gốc đã tạo được WAV thử thực tế**, có [báo cáo từng giọng](docs/voice-validation.json). FP32 và int8 đã chạy tạo giọng; chưa đánh giá bằng tai mọi câu/giọng.
- Cả 4 bộ OCR gốc đã nhận dạng chữ thử nghiệm.
- Gọi trực tiếp tải danh sách giọng và tạo giọng Edge đều bị proxy mạng chặn `403` tại `speech.platform.bing.com`. Cần cho phép tên miền này và kết nối WSS khi chạy trong mạng hạn chế. Không cần thay đổi mạng nếu dùng giọng Windows cục bộ.
- Whisper đã cài và import được; tải mô hình từ `huggingface.co` bị chặn trong môi trường này. Có thể cung cấp thư mục mô hình đã tải hoặc mở quyền cho máy chủ tải và các tên miền chuyển hướng cần thiết.
- Chưa kiểm tra mô hình dịch thực tế, giọng SAPI hoặc `.exe` trên Windows. Màn hình Linux thử nghiệm thiếu font core X11 phù hợp cho một số dấu tiếng Việt; Windows dùng Segoe UI.
- Khi không có DISPLAY, bài kiểm tra GUI được đánh dấu bỏ qua; các bài còn lại vẫn chạy.

Xem [nghiên cứu gói tham khảo](docs/reference-analysis.md). Không có thao tác xuất bản môi trường trong lần bổ sung này.


## Kiểm kê và tái sử dụng

Xem [bảng tái sử dụng dữ liệu gốc](docs/resource-reuse.md). Gói mới giữ các mô hình cũ để tham chiếu/chuyển đổi; không mặc nhiên kích hoạt mọi backend GPU/Paddle chỉ vì dữ liệu có mặt. Launcher cũ, Python/DLL Windows trùng lặp, cache và log cũ không được dùng để khởi động ứng dụng mới.


## Gói Windows portable có EXE

Đã tạo gói Windows x64 gồm native launcher `AutoSubVideo.exe`, runtime Python/54 thư viện và bundle giọng/OCR. Giải nén toàn bộ, mở exe trong thư mục; không cần cài Python riêng. Gói được lắp và kiểm tra tĩnh trên Linux, **chưa chạy thử trên Windows**. Xem [chi tiết bản portable](docs/windows-portable-build.md).
