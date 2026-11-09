from pathlib import Path
import os
import queue
import threading
import tkinter as tk
import tempfile
from tkinter import ttk, filedialog, messagebox

from .core import read_srt, write_srt, transcribe, translate, render
from .speech import EDGE_VOICES, SpeechSettings, list_voices, narration, preview
from .resources import default_bundle


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        if os.name == "nt":
            from tkinter import font
            for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
                font.nametofont(name).configure(family="Segoe UI", size=10)
        self.title("AutoSubVideo — Phụ đề video")
        self.geometry("930x720")
        self.minsize(780, 600)
        self.events = queue.Queue()
        self.cues = []
        self.busy = False
        self.preview_dir = tempfile.TemporaryDirectory(prefix="autosub-preview-")
        self.bundle = tk.StringVar(value=default_bundle())
        self.bundle.trace_add("write", lambda *_: os.environ.__setitem__("AUTOSUB_BUNDLE", self.bundle.get()))
        self.subtitle_font = tk.StringVar(value="Arial")
        self.subtitle_size = tk.StringVar(value="22")
        self.precision = tk.StringVar(value="fp32")
        self.threads = tk.StringVar(value="2")
        try:
            self.voice_catalog = list_voices("local", self.bundle.get())
            initial_provider = "local"
        except (ValueError, OSError):
            self.voice_catalog = list(EDGE_VOICES)
            initial_provider = "edge"
        self.provider = tk.StringVar(value=initial_provider)
        initial_voice = next((v for v in self.voice_catalog if v.id == "Ngọc Huyền"), self.voice_catalog[0])
        self.voice = tk.StringVar(value=initial_voice.label)
        self.voice_filter = tk.StringVar(value="vi-")
        self.rate = tk.StringVar(value="0")
        self.original_volume = tk.StringVar(value="0")
        self.dub = tk.BooleanVar(value=False)
        self.ocr_top = tk.StringVar(value="65")
        self.ocr_interval = tk.StringVar(value="0.5")
        self.ocr_model = tk.StringVar(value="universal")
        self.ocr_correct = tk.BooleanVar(value=False)
        self.voice_box = None
        menu = tk.Menu(self)
        tools = tk.Menu(menu, tearoff=False)
        tools.add_command(label="Kiểu phụ đề…", command=self.subtitle_style_dialog)
        tools.add_command(label="Giọng và tài nguyên gốc…", command=self.speech_dialog)
        tools.add_command(label="OCR phụ đề trong hình…", command=self.ocr_dialog)
        menu.add_cascade(label="Công cụ", menu=tools)
        self.configure(menu=menu)
        self.values = {}
        form = ttk.Frame(self, padding=16)
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)
        fields = [
            ("video", "Video / âm thanh", ""), ("srt", "Phụ đề SRT", ""),
            ("whisper", "Mô hình Whisper / thư mục", "base"),
            ("source", "Ngôn ngữ nguồn (trống = tự động)", ""),
            ("endpoint", "API dịch tương thích OpenAI", "http://localhost:11434/v1"),
            ("model", "Tên mô hình dịch", ""),
            ("target", "Ngôn ngữ đích", "Tiếng Việt"),
            ("key", "API key (chỉ giữ trong bộ nhớ)", os.getenv("AUTOSUB_API_KEY", "")),
        ]
        for row, (key, label, default) in enumerate(fields):
            self.values[key] = tk.StringVar(value=default)
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=4)
            if key in ("target", "source"):
                choices = ("Tiếng Việt", "English", "中文", "日本語", "한국어", "Français", "Deutsch", "Español", "Русский", "ไทย", "Bahasa Indonesia", "العربية", "हिन्दी") if key == "target" else ("", "vi", "en", "zh", "ja", "ko", "fr", "de", "es", "ru", "th", "id", "ar", "hi")
                field = ttk.Combobox(form, textvariable=self.values[key], values=choices)
            else:
                field = ttk.Entry(form, textvariable=self.values[key], show="•" if key == "key" else "")
            field.grid(row=row, column=1, sticky="ew", padx=8)
            if key in ("video", "srt"):
                ttk.Button(form, text="Chọn…", command=lambda k=key: self.choose(k)).grid(row=row, column=2)
        bar = ttk.Frame(form)
        bar.grid(row=8, column=0, columnspan=3, sticky="w", pady=12)
        self.buttons = []
        for label, action in [("1. Nhận dạng", self.asr), ("Nạp SRT", self.load),
                              ("2. Dịch", self.translation), ("Lưu SRT", self.save),
                              ("3. Xuất video", self.export)]:
            button = ttk.Button(bar, text=label, command=action)
            button.pack(side="left", padx=(0, 8))
            self.buttons.append(button)
        speech_bar = ttk.Frame(form)
        speech_bar.grid(row=9, column=0, columnspan=3, sticky="w", pady=(0, 8))
        for label, action in [("Chọn / nghe giọng đọc…", self.speech_dialog), ("Xuất giọng WAV", self.export_audio), ("OCR chữ trong video…", self.ocr_dialog), ("Tự động toàn bộ…", self.automatic_dialog)]:
            button = ttk.Button(speech_bar, text=label, command=action)
            button.pack(side="left", padx=(0, 8))
            self.buttons.append(button)
        ttk.Checkbutton(speech_bar, text="Lồng giọng khi xuất video", variable=self.dub).pack(side="left")
        self.table = ttk.Treeview(form, columns=("start", "end", "text"), show="headings", selectmode="browse")
        for key, label, width in [("start", "Bắt đầu (giây)", 110), ("end", "Kết thúc (giây)", 110), ("text", "Nội dung — nhấp đôi để sửa", 560)]:
            self.table.heading(key, text=label)
            self.table.column(key, width=width, stretch=key == "text")
        self.table.grid(row=10, column=0, columnspan=3, sticky="nsew")
        form.rowconfigure(10, weight=1)
        self.table.bind("<Double-1>", self.edit)
        self.status = tk.StringVar(value="Sẵn sàng. Nhập SRT để làm việc ngoại tuyến; Whisper cần mô hình.")
        ttk.Label(form, textvariable=self.status, wraplength=850).grid(row=11, column=0, columnspan=3, sticky="w", pady=8)
        self.log = tk.Text(form, height=6, state="disabled", wrap="word")
        self.log.grid(row=12, column=0, columnspan=3, sticky="ew")
        self.after(100, self.poll)
        self.protocol("WM_DELETE_WINDOW", self.close)

    def close(self):
        if self.busy:
            messagebox.showinfo("Đang xử lý", "Hãy chờ tác vụ hoàn tất trước khi đóng ứng dụng.")
        else:
            if os.name == "nt":
                import winsound
                winsound.PlaySound(None, 0)
            self.preview_dir.cleanup()
            self.destroy()

    def choose(self, key):
        path = filedialog.askopenfilename(filetypes=[("SRT", "*.srt")] if key == "srt" else [("Video / âm thanh", "*.mp4 *.mkv *.mov *.avi *.webm *.mp3 *.wav *.m4a *.flac *.ogg *.aac *.wma"), ("Tất cả", "*.*")])
        if path:
            self.values[key].set(path)

    def task(self, work):
        if self.busy:
            return
        self.busy = True
        for button in self.buttons:
            button.configure(state="disabled")
        self.status.set("Đang xử lý…")
        def worker():
            try:
                self.events.put(("done", work()))
            except Exception as exc:
                self.events.put(("error", str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == "log":
                    self.log.configure(state="normal")
                    self.log.insert("end", str(data) + "\n")
                    self.log.see("end")
                    self.log.configure(state="disabled")
                    continue
                self.busy = False
                for button in self.buttons:
                    button.configure(state="normal")
                if kind == "error":
                    self.status.set("Tác vụ thất bại.")
                    messagebox.showerror("Lỗi", data)
                else:
                    if isinstance(data, list):
                        self.cues = data
                        self.refresh()
                    message = f"Hoàn tất — {len(self.cues)} dòng phụ đề."
                    if isinstance(data, dict):
                        if "voices" in data and data.get("voices_provider") == self.provider.get():
                            self.voice_catalog = data["voices"]
                            self.update_voice_choices(reset=True)
                            message = f"Đã tải {len(self.voice_catalog)} giọng; lọc ngôn ngữ để chọn."
                        if "cues" in data:
                            self.cues = data["cues"]
                            self.refresh()
                        if "message" in data:
                            message = data["message"]
                        if "preview" in data:
                            if os.name == "nt":
                                import winsound
                                winsound.PlaySound(data["preview"], winsound.SND_FILENAME | winsound.SND_ASYNC)
                            else:
                                message = "Đã tạo mẫu WAV: " + data["preview"]
                    self.status.set(message)
        except queue.Empty:
            pass
        self.after(100, self.poll)

    def refresh(self):
        self.table.delete(*self.table.get_children())
        for i, c in enumerate(self.cues):
            self.table.insert("", "end", iid=str(i), values=(f"{c.start:.3f}", f"{c.end:.3f}", c.text))

    def asr(self):
        values = {k: v.get() for k, v in self.values.items()}
        if not Path(values["video"]).is_file():
            messagebox.showerror("Thiếu đầu vào", "Hãy chọn video hoặc tệp âm thanh.")
            return
        self.task(lambda: transcribe(Path(values["video"]), values["whisper"], values["source"], lambda s: self.events.put(("log", s))))

    def load(self):
        path = Path(self.values["srt"].get())
        self.task(lambda: read_srt(path))

    def translation(self):
        if not self.cues:
            messagebox.showinfo("Thiếu phụ đề", "Nạp SRT hoặc nhận dạng video trước.")
            return
        v = {k: x.get() for k, x in self.values.items()}
        if not v["model"].strip() or not v["target"].strip():
            messagebox.showerror("Thiếu cấu hình", "Điền tên mô hình dịch và ngôn ngữ đích.")
            return
        cues = list(self.cues)
        self.task(lambda: translate(cues, v["endpoint"], v["model"], v["target"], v["key"], lambda s: self.events.put(("log", s))))

    def save(self):
        if not self.cues:
            return
        path = filedialog.asksaveasfilename(defaultextension=".srt", filetypes=[("SRT", "*.srt")])
        if path:
            try:
                write_srt(Path(path), self.cues)
                self.values["srt"].set(path)
                self.status.set("Đã lưu phụ đề.")
            except Exception as exc:
                messagebox.showerror("Lỗi", str(exc))

    def export(self):
        if not self.cues or not Path(self.values["video"].get()).is_file():
            messagebox.showinfo("Thiếu dữ liệu", "Chọn video và nạp phụ đề trước.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4", "*.mp4")])
        if not path:
            return
        video, cues = Path(self.values["video"].get()), list(self.cues)
        try:
            settings, volume = self.speech_settings(), self.mix_volume()
            font, size = self.subtitle_font.get(), int(self.subtitle_size.get())
        except ValueError as exc:
            messagebox.showerror("Cấu hình giọng đọc", str(exc))
            return
        dubbing = self.dub.get()
        def work():
            with tempfile.TemporaryDirectory() as tmp:
                srt = Path(tmp) / "sub.srt"
                write_srt(srt, cues)
                audio = None
                if dubbing:
                    audio = Path(tmp) / "voice.wav"
                    narration(cues, audio, settings, log=self.report)
                render(video, srt, Path(path), narration_audio=audio, original_volume=volume,
                       subtitle_font=font, subtitle_size=size)
        self.task(work)

    def report(self, text):
        self.events.put(("log", text))

    def speech_settings(self):
        voice_id = self.voice.get().split(" | ")[-1].strip()
        return SpeechSettings(self.provider.get(), voice_id, int(self.rate.get()), self.bundle.get(),
                              self.precision.get(), int(self.threads.get()))

    def mix_volume(self):
        volume = int(self.original_volume.get())
        if not 0 <= volume <= 100:
            raise ValueError("Âm lượng gốc phải từ 0 đến 100%.")
        return volume / 100

    def update_voice_choices(self, reset=False):
        query = self.voice_filter.get().strip().casefold()
        labels = [v.label for v in self.voice_catalog if query in v.label.casefold()]
        if self.voice_box is not None and self.voice_box.winfo_exists():
            self.voice_box.configure(values=labels)
        if reset:
            self.voice.set(labels[0] if labels else "")

    def speech_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("Giọng đọc và lồng tiếng")
        dialog.transient(self)
        dialog.grab_set()
        pane = ttk.Frame(dialog, padding=16)
        pane.pack(fill="both", expand=True)
        ttk.Label(pane, text="local: 25 giọng gốc offline · edge: trực tuyến · windows: SAPI").pack(anchor="w")
        provider = ttk.Combobox(pane, textvariable=self.provider, values=("local", "edge", "windows"), state="readonly")
        provider.pack(fill="x", pady=6)
        ttk.Label(pane, text="Thư mục tài nguyên gốc / bundle (local)").pack(anchor="w")
        resources = ttk.Frame(pane)
        resources.pack(fill="x")
        ttk.Entry(resources, textvariable=self.bundle).pack(side="left", fill="x", expand=True)
        def pick_bundle():
            folder = filedialog.askdirectory(parent=dialog)
            if folder:
                self.bundle.set(folder)
                self.provider.set("local")
                changed()
        ttk.Button(resources, text="Chọn…", command=pick_bundle).pack(side="left")
        tuning = ttk.Frame(pane)
        tuning.pack(fill="x", pady=6)
        ttk.Label(tuning, text="ONNX: ").pack(side="left")
        ttk.Combobox(tuning, textvariable=self.precision, values=("fp32", "int8"), state="readonly", width=7).pack(side="left")
        ttk.Label(tuning, text="  Luồng CPU: ").pack(side="left")
        ttk.Spinbox(tuning, textvariable=self.threads, from_=1, to=16, width=5).pack(side="left")
        def changed(event=None):
            self.voice_catalog = list(EDGE_VOICES) if self.provider.get() == "edge" else []
            self.voice_filter.set("vi-" if self.provider.get() in ("local", "edge") else "")
            self.update_voice_choices(reset=True)
            if self.provider.get() in ("local", "windows"):
                refresh()
        def refresh():
            selected = self.provider.get()
            bundle = self.bundle.get()
            self.task(lambda: {"voices": list_voices(selected, bundle), "voices_provider": selected})
        provider.bind("<<ComboboxSelected>>", changed)
        ttk.Label(pane, text="Lọc giọng theo ngôn ngữ / tên (vi-, en-, zh-, ja-…)").pack(anchor="w")
        search = ttk.Entry(pane, textvariable=self.voice_filter)
        search.pack(fill="x", pady=6)
        search.bind("<KeyRelease>", lambda _: self.update_voice_choices())
        self.voice_box = ttk.Combobox(pane, textvariable=self.voice, width=65)
        self.voice_box.pack(fill="x", pady=6)
        self.update_voice_choices()
        ttk.Button(pane, text="Tải danh sách giọng hiện có", command=refresh).pack(anchor="w")
        for label, variable, low, high in [("Tốc độ đọc (%)", self.rate, -50, 100), ("Âm lượng gốc khi lồng tiếng (%, 0 = thay hoàn toàn)", self.original_volume, 0, 100)]:
            ttk.Label(pane, text=label).pack(anchor="w", pady=(10, 0))
            ttk.Spinbox(pane, textvariable=variable, from_=low, to=high).pack(fill="x")
        ttk.Label(pane, text="Văn bản nghe thử").pack(anchor="w", pady=(10, 0))
        sample = tk.Text(pane, height=3, width=65)
        sample.pack(fill="x")
        sample.insert("1.0", "Xin chào, đây là giọng đọc thử của AutoSubVideo.")
        def listen():
            try:
                settings = self.speech_settings()
            except ValueError as exc:
                messagebox.showerror("Lỗi", str(exc), parent=dialog)
                return
            text = sample.get("1.0", "end").strip()
            if not text:
                return
            import uuid
            output = Path(self.preview_dir.name) / (uuid.uuid4().hex + ".wav")
            def work():
                preview(text, output, settings)
                return {"preview": str(output)}
            self.task(work)
        ttk.Button(pane, text="Nghe thử", command=listen).pack(anchor="w", pady=10)
        ttk.Label(pane, text="Local dùng dữ liệu gốc: Ngọc Huyền, Trúc Ly, Hải Đăng…\nFP32 ưu tiên chất lượng; int8 nhẹ hơn nhưng cần CPU phù hợp.\nEdge gửi văn bản đến Microsoft; Windows dùng giọng SAPI đã cài.", wraplength=550).pack(anchor="w")
        ttk.Button(pane, text="Đóng", command=dialog.destroy).pack(anchor="e", pady=(12, 0))

    def export_audio(self):
        if not self.cues:
            messagebox.showinfo("Thiếu phụ đề", "Nạp SRT hoặc nhận dạng âm thanh trước.")
            return
        try:
            settings = self.speech_settings()
        except ValueError as exc:
            messagebox.showerror("Lỗi", str(exc))
            return
        path = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV", "*.wav")])
        if path:
            cues = list(self.cues)
            self.task(lambda: narration(cues, Path(path), settings, log=self.report))

    def automatic_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("Chạy quy trình tự động")
        dialog.transient(self)
        dialog.grab_set()
        source = tk.StringVar(value="Bảng phụ đề" if self.cues else "Âm thanh/video")
        do_translate = tk.BooleanVar(value=bool(self.values["model"].get().strip()))
        do_speech = tk.BooleanVar(value=self.dub.get())
        do_video = tk.BooleanVar(value=False)
        ttk.Label(dialog, text="Nguồn phụ đề").pack(anchor="w", padx=16, pady=(16, 0))
        ttk.Combobox(dialog, textvariable=source, values=("Âm thanh/video", "Tệp SRT", "Bảng phụ đề", "Chữ trong video (OCR)"), state="readonly").pack(fill="x", padx=16)
        for label, var in [("Dịch sang ngôn ngữ đích đã chọn", do_translate), ("Tạo giọng WAV khớp thời gian phụ đề", do_speech), ("Xuất thêm video có phụ đề (cần đầu vào video)", do_video)]:
            ttk.Checkbutton(dialog, text=label, variable=var).pack(anchor="w", padx=16, pady=6)
        ttk.Label(dialog, text="Luôn lưu SRT. Kết quả được ghi trong thư mục mới;\ngiọng đọc dùng cấu hình tại nút Chọn / nghe giọng đọc.").pack(anchor="w", padx=16, pady=6)
        def start():
            from .workflow import PipelineOptions, process
            try:
                options = PipelineOptions(source=source.get(), translate_text=do_translate.get(),
                                          speak=do_speech.get(), video=do_video.get(),
                                          settings=self.speech_settings(), original_volume=self.mix_volume(),
                                          ocr_top=float(self.ocr_top.get()) / 100, ocr_interval=float(self.ocr_interval.get()),
                                          ocr_model=self.ocr_model.get(),
                                          ocr_correct=self.ocr_correct.get(),
                                          subtitle_font=self.subtitle_font.get(), subtitle_size=int(self.subtitle_size.get()))
                values = {k: v.get() for k, v in self.values.items()}
                if options.translate_text and (not values["model"].strip() or not values["target"].strip()):
                    raise ValueError("Hãy điền mô hình dịch và ngôn ngữ đích ở cửa sổ chính.")
            except ValueError as exc:
                messagebox.showerror("Lỗi", str(exc), parent=dialog)
                return
            directory = filedialog.askdirectory(title="Chọn nơi lưu kết quả", parent=dialog)
            if not directory:
                return
            cues = list(self.cues)
            dialog.destroy()
            self.task(lambda: process(values, cues, Path(directory), options, log=self.report))
        ttk.Button(dialog, text="Chọn nơi lưu và bắt đầu", command=start).pack(padx=16, pady=16)

    def ocr_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("OCR phụ đề trong hình — mô hình gốc")
        dialog.transient(self)
        dialog.grab_set()
        ttk.Label(dialog, text="Đọc chữ đã gắn trong video bằng mô hình OCR đi kèm.\nCần nhập bộ tài nguyên gốc vào bundle trước.").pack(padx=16, pady=12)
        ttk.Label(dialog, text="Bộ nhận dạng gốc (universal: đa ngôn ngữ; compact/quality: Trung)").pack(anchor="w", padx=16)
        ttk.Combobox(dialog, textvariable=self.ocr_model, values=("universal", "universal_medium", "compact", "quality"), state="readonly").pack(padx=16, fill="x")
        ttk.Checkbutton(dialog, text="Sửa lỗi OCR theo từ điển gốc", variable=self.ocr_correct).pack(anchor="w", padx=16, pady=6)
        for label, var in [("Quét từ % chiều cao (65 = phần dưới; 0 = toàn hình)", self.ocr_top), ("Khoảng lấy mẫu (giây, 0.1–5)", self.ocr_interval)]:
            ttk.Label(dialog, text=label).pack(anchor="w", padx=16)
            ttk.Entry(dialog, textvariable=var).pack(fill="x", padx=16, pady=5)
        def start():
            try:
                top, interval = float(self.ocr_top.get()) / 100, float(self.ocr_interval.get())
            except ValueError:
                messagebox.showerror("Lỗi", "Nhập giá trị số hợp lệ.", parent=dialog)
                return
            video, bundle, model, correct = self.values["video"].get(), self.bundle.get(), self.ocr_model.get(), self.ocr_correct.get()
            dialog.destroy()
            from .ocr import extract_captions
            self.task(lambda: extract_captions(video, bundle, top=top, interval=interval, model=model, correct_typos=correct, log=self.report))
        ttk.Button(dialog, text="Đọc phụ đề vào bảng", command=start).pack(padx=16, pady=16)

    def subtitle_style_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("Kiểu phụ đề")
        dialog.transient(self)
        dialog.grab_set()
        ttk.Label(dialog, text="Font chữ khi xuất video").pack(padx=16, pady=(16, 4))
        ttk.Combobox(dialog, textvariable=self.subtitle_font,
                     values=("Arial", "SFU Cooper", "Noto Sans CJK", "DejaVu Sans")).pack(padx=16, fill="x")
        ttk.Label(dialog, text="Cỡ chữ (8–100)").pack(padx=16, pady=(12, 4))
        ttk.Spinbox(dialog, textvariable=self.subtitle_size, from_=8, to=100).pack(padx=16, fill="x")
        ttk.Label(dialog, text="Font gốc trong bundle được nạp khi xuất;\nfont khác cần được cài trên máy.").pack(padx=16, pady=12)
        ttk.Button(dialog, text="Đóng", command=dialog.destroy).pack(padx=16, pady=(0, 16))

    def edit(self, event):
        if self.busy or not self.table.selection():
            return
        from .core import Cue
        i = int(self.table.selection()[0])
        cue = self.cues[i]
        dialog = tk.Toplevel(self)
        dialog.title("Sửa phụ đề")
        dialog.transient(self)
        dialog.grab_set()
        start, end = tk.StringVar(value=str(cue.start)), tk.StringVar(value=str(cue.end))
        for label, var in [("Bắt đầu (giây)", start), ("Kết thúc (giây)", end)]:
            ttk.Label(dialog, text=label).pack(anchor="w", padx=12)
            ttk.Entry(dialog, textvariable=var).pack(fill="x", padx=12)
        text = tk.Text(dialog, width=70, height=8)
        text.pack(padx=12, pady=12)
        text.insert("1.0", cue.text)
        def commit():
            try:
                self.cues[i] = Cue(float(start.get()), float(end.get()), text.get("1.0", "end").strip())
                self.refresh()
                dialog.destroy()
            except ValueError as exc:
                messagebox.showerror("Lỗi", str(exc), parent=dialog)
        ttk.Button(dialog, text="Lưu", command=commit).pack(pady=12)


def main():
    App().mainloop()
