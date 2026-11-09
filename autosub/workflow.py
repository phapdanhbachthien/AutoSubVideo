from dataclasses import dataclass, field
from pathlib import Path
import tempfile

from .core import read_srt, write_srt, transcribe, translate, render, media_info
from .speech import SpeechSettings, narration


@dataclass(frozen=True)
class PipelineOptions:
    source: str = "Âm thanh/video"
    translate_text: bool = False
    speak: bool = False
    video: bool = False
    settings: SpeechSettings = field(default_factory=SpeechSettings)
    original_volume: float = 0.0
    ocr_top: float = .65
    ocr_interval: float = .5
    ocr_model: str = "universal"
    ocr_correct: bool = False
    subtitle_font: str = "Arial"
    subtitle_size: int = 22


def process(values, existing_cues, directory: Path, options=PipelineOptions(), log=print):
    media = Path(values["video"])
    if options.video:
        media_info(media)
    output = Path(tempfile.mkdtemp(prefix="AutoSubVideo-", dir=directory))
    log(f"Thư mục kết quả: {output}")
    if options.source == "Tệp SRT":
        cues = read_srt(Path(values["srt"]))
    elif options.source == "Bảng phụ đề":
        cues = list(existing_cues)
        if not cues:
            raise ValueError("Bảng phụ đề chưa có dữ liệu.")
    elif options.source == "Chữ trong video (OCR)":
        from .ocr import extract_captions
        cues = extract_captions(media, options.settings.bundle, top=options.ocr_top, interval=options.ocr_interval,
                                model=options.ocr_model, correct_typos=options.ocr_correct, log=log)
    elif options.source == "Âm thanh/video":
        if not media.is_file():
            raise ValueError("Hãy chọn tệp âm thanh hoặc video.")
        cues = transcribe(media, values["whisper"], values["source"], log)
    else:
        raise ValueError("Nguồn phụ đề không hợp lệ.")
    write_srt(output / "original.srt", cues)
    srt = output / "original.srt"
    if options.translate_text:
        cues = translate(cues, values["endpoint"], values["model"], values["target"], values["key"], log)
        srt = output / "translated.srt"
        write_srt(srt, cues)
    audio = None
    if options.speak:
        audio = output / "narration.wav"
        narration(cues, audio, options.settings, log=log)
    if options.video:
        render(media, srt, output / "video.mp4", narration_audio=audio, original_volume=options.original_volume,
               subtitle_font=options.subtitle_font, subtitle_size=options.subtitle_size)
    return {"cues": cues, "message": f"Hoàn tất. Kết quả: {output}"}
