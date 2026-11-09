"""Speech providers and subtitle-aligned narration, without bundled model assets."""
from dataclasses import dataclass
from pathlib import Path
import asyncio
import json
import math
import os
import tempfile
import wave

from .core import Cue, publish_file, run_process
from .resources import default_bundle, original_catalog


@dataclass(frozen=True)
class Voice:
    id: str
    locale: str
    gender: str

    @property
    def label(self):
        return f"{self.locale} | {self.gender} | {self.id}"


# Starter choices; the refresh button retrieves the current service catalog.
EDGE_VOICES = [Voice(*v) for v in [
    ("vi-VN-HoaiMyNeural", "vi-VN", "Nữ"),
    ("vi-VN-NamMinhNeural", "vi-VN", "Nam"),
    ("en-US-JennyNeural", "en-US", "Nữ"),
    ("en-US-GuyNeural", "en-US", "Nam"),
    ("zh-CN-XiaoxiaoNeural", "zh-CN", "Nữ"),
    ("zh-CN-YunxiNeural", "zh-CN", "Nam"),
    ("ja-JP-NanamiNeural", "ja-JP", "Nữ"),
    ("ko-KR-SunHiNeural", "ko-KR", "Nữ"),
    ("fr-FR-DeniseNeural", "fr-FR", "Nữ"),
    ("de-DE-KatjaNeural", "de-DE", "Nữ"),
    ("es-ES-ElviraNeural", "es-ES", "Nữ"),
    ("th-TH-PremwadeeNeural", "th-TH", "Nữ"),
]]


@dataclass(frozen=True)
class SpeechSettings:
    provider: str = "edge"
    voice: str = "vi-VN-HoaiMyNeural"
    rate: int = 0
    bundle: str = ""
    precision: str = "fp32"
    threads: int = 2

    def __post_init__(self):
        if self.provider not in ("local", "edge", "windows") or not self.voice.strip():
            raise ValueError("Chọn nhà cung cấp và giọng đọc hợp lệ.")
        if not -50 <= self.rate <= 100:
            raise ValueError("Tốc độ giọng đọc phải từ -50 đến +100%.")
        if self.precision not in ("fp32", "int8") or not 1 <= self.threads <= 16:
            raise ValueError("Chọn độ chính xác fp32/int8 và số luồng từ 1 đến 16.")


def windows_request(payload):
    if os.name != "nt":
        raise RuntimeError("Giọng Windows ngoại tuyến chỉ dùng trên Windows có cài giọng SAPI.")
    script = Path(__file__).with_name("windows_speech.ps1")
    with tempfile.TemporaryDirectory(prefix="autosub-sapi-") as tmp:
        request = Path(tmp) / "request.json"
        request.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return run_process(["powershell.exe", "-NoProfile", "-NonInteractive", "-File", str(script), str(request)], timeout=180)


def list_voices(provider="edge", bundle=None):
    if provider == "local":
        presets = original_catalog(bundle or default_bundle())["presets"]
        return [Voice(k, "vi-VN", v.get("description") or (("Nữ" if v.get("gender") == "female" else "Nam") + " · " + v.get("region", "")))
                for k, v in sorted(presets.items(), key=lambda kv: (kv[1].get("featured") is None, kv[1].get("featured") or 0))]
    if provider == "windows":
        data = json.loads(windows_request({"action": "voices"}))
        return [Voice(v["id"], v["locale"], v["gender"]) for v in data]
    if provider != "edge":
        raise ValueError("Nhà cung cấp giọng đọc không hợp lệ.")
    edge_tts = edge_module()
    async def fetch():
        return await asyncio.wait_for(edge_tts.list_voices(proxy=os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")), timeout=45)
    data = asyncio.run(fetch())
    return sorted([Voice(v["ShortName"], v["Locale"], v["Gender"]) for v in data], key=lambda v: v.label)


def edge_module():
    try:
        import edge_tts
    except ImportError as exc:
        raise RuntimeError("Cần cài giọng Edge: python -m pip install -r requirements-tts.txt") from exc
    # The pinned library explicitly uses certifi rather than Python's default CA
    # paths. Add the environment's supplied CA without disabling verification.
    ca_file = os.getenv("SSL_CERT_FILE") or os.getenv("REQUESTS_CA_BUNDLE")
    if ca_file:
        import importlib
        for name in ("edge_tts.communicate", "edge_tts.voices"):
            module = importlib.import_module(name)
            module._SSL_CTX.load_verify_locations(cafile=ca_file)
    return edge_tts


def synthesize(text: str, output: Path, settings: SpeechSettings):
    if settings.provider == "local":
        from .local_tts import synthesize_original
        synthesize_original(text, output, settings)
    elif settings.provider == "windows":
        windows_request({"action": "speak", "voice": settings.voice, "text": text,
                         "output": str(output.resolve()), "rate": settings.rate})
    else:
        edge_tts = edge_module()
        async def generate():
            speech = edge_tts.Communicate(text, voice=settings.voice, rate=f"{settings.rate:+d}%",
                                         proxy=os.getenv("HTTPS_PROXY") or os.getenv("https_proxy"),
                                         connect_timeout=20, receive_timeout=90)
            await speech.save(str(output))
        asyncio.run(generate())
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("Dịch vụ không trả về âm thanh.")


def tempo_filter(ratio):
    parts = []
    while ratio < .5:
        parts.append("atempo=0.5")
        ratio *= 2
    while ratio > 2:
        parts.append("atempo=2")
        ratio /= 2
    return ",".join(parts + [f"atempo={ratio:.9f}"])


def narration(cues: list[Cue], output: Path, settings=SpeechSettings(), *, log=print, synthesizer=None):
    """Fit speech to each cue and stream silence into a mono PCM WAV timeline."""
    if not cues:
        raise ValueError("Chưa có phụ đề để đọc.")
    output = output.resolve()
    if output.exists():
        raise ValueError("Tệp giọng đọc đã tồn tại. Hãy chọn tên mới.")
    previous = 0
    for cue in cues:
        if cue.start < previous - 0.0001:
            raise ValueError("Phụ đề bị chồng thời gian hoặc sai thứ tự. Sửa thời gian trước khi tạo giọng đọc.")
        previous = cue.end
    make_speech = synthesizer or synthesize
    sr = 24000
    with tempfile.TemporaryDirectory(prefix="autosub-voice-") as tmp:
        base = Path(tmp)
        stage = base / "timeline.wav"
        with wave.open(str(stage), "wb") as track:
            track.setparams((1, 2, sr, 0, "NONE", "not compressed"))
            cursor = 0
            def silence(frames):
                while frames:
                    size = min(frames, sr)
                    track.writeframesraw(b"\0\0" * size)
                    frames -= size
            for index, cue in enumerate(cues, 1):
                start, end = round(cue.start * sr), round(cue.end * sr)
                if end <= start:
                    raise ValueError("Phụ đề quá ngắn để tạo âm thanh.")
                silence(max(0, start - cursor))
                raw, normalized = base / "speech.audio", base / "speech.wav"
                make_speech(cue.text, raw, settings)
                duration = float(json.loads(run_process(["ffprobe", "-v", "error", "-show_format", "-of", "json", str(raw)]))["format"]["duration"])
                if not math.isfinite(duration) or duration <= 0:
                    raise ValueError("Giọng đọc có thời lượng không hợp lệ.")
                slot = (end - start) / sr
                ratio = max(1, duration / slot)
                if ratio > 2:
                    log(f"Dòng {index}: cần tăng tốc {ratio:.1f} lần để khớp thời gian; cân nhắc nới mốc phụ đề.")
                run_process(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", str(raw),
                             "-af", tempo_filter(ratio), "-ac", "1", "-ar", str(sr), "-c:a", "pcm_s16le", str(normalized)])
                with wave.open(str(normalized), "rb") as clip:
                    remaining = end - start
                    while remaining:
                        chunk = clip.readframes(min(sr, remaining))
                        if not chunk:
                            break
                        track.writeframesraw(chunk)
                        remaining -= len(chunk) // 2
                    silence(remaining)
                cursor = end
                log(f"Đã tạo giọng {index}/{len(cues)} dòng.")
        publish_file(stage, output)


def preview(text: str, output: Path, settings=SpeechSettings()):
    # A generous slot avoids forced speeding-up for the preview.
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "preview.audio"
        synthesize(text, raw, settings)
        stage = Path(tmp) / "preview.wav"
        run_process(["ffmpeg", "-nostdin", "-v", "error", "-i", str(raw), "-ac", "1", "-ar", "24000", str(stage)])
        publish_file(stage, output)
