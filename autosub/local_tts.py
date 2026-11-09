"""Adapter for the reviewed ONNX CPU engine supplied in the user's bundle."""
from functools import lru_cache
from pathlib import Path
import sys
import threading

from .resources import original_catalog, tts_root, verify_bundle

_lock = threading.RLock()


@lru_cache(maxsize=1)
def engine_for(bundle: str, precision: str, threads: int):
    root = tts_root(bundle)
    verify_bundle(bundle)
    source = str(root / "src")
    # Keep one bundle's module graph per process; changing models within the same
    # bundle is supported, switching engine source bundles requires a restart.
    loaded = sys.modules.get("voice_runtime")
    if loaded and Path(loaded.__file__).resolve().parent != Path(source) / "voice_runtime":
        raise RuntimeError("Đã nạp một bộ máy TTS khác. Khởi động lại ứng dụng để đổi thư mục tài nguyên.")
    if source not in sys.path:
        sys.path.insert(0, source)
    try:
        from voice_runtime._v3_turbo_engine.onnx_runtime_lite import OnnxV3LiteEngine
    except ImportError as exc:
        raise RuntimeError("Cài bộ TTS gốc: python -m pip install -r requirements-local.txt") from exc
    folder = "onnx_int8" if precision == "int8" else "onnx_update"
    return OnnxV3LiteEngine(onnx_dir=str(root / "models" / folder),
                           codec_dir=str(root / "models/codec"),
                           checkpoint_path=str(root / "models"), threads=threads)


def synthesize_original(text, output, settings):
    import numpy as np
    import soundfile as sf
    catalog = original_catalog(settings.bundle)
    name = settings.voice
    if name not in catalog["presets"]:
        name = next((k for k, v in catalog["presets"].items() if name in v.get("aliases", [])), name)
    if name not in catalog["presets"]:
        raise ValueError("Giọng không có trong bộ dữ liệu gốc: " + settings.voice)
    preset = catalog["presets"][name]
    with _lock:
        engine = engine_for(str(Path(settings.bundle).resolve()), settings.precision, settings.threads)
        from voice_runtime_utils.phonemize_text import normalize_to_chunks_v3_with_gaps, phonemize_text_with_emotions
        from voice_runtime_utils.core_utils import strip_encoder_pad_frame, join_audio_chunks, gaps_to_silence
        speaker = np.asarray(preset["speaker_emb"], dtype=np.float32)
        codes = strip_encoder_pad_frame(np.asarray(preset["codes"], dtype=np.int64))
        chunks, gaps = normalize_to_chunks_v3_with_gaps(text, max_chars=256)
        if not chunks:
            raise ValueError("Văn bản không có nội dung để đọc.")
        waves = [engine.infer(phonemes=phonemize_text_with_emotions(chunk), speaker_emb=speaker,
                              ref_codes=codes, use_ref_codes=True) for chunk in chunks]
        audio = join_audio_chunks(waves, 48000, silence_ps=gaps_to_silence(gaps))
        if not len(audio) or not np.isfinite(audio).all():
            raise RuntimeError("Mô hình gốc không tạo được âm thanh hợp lệ.")
        # Apply requested tempo in a separate FFmpeg pass; the original voice's
        # speaker embedding and acoustic reference codes remain unchanged.
        if settings.rate:
            import tempfile
            from .core import run_process
            from .speech import tempo_filter
            with tempfile.TemporaryDirectory() as tmp:
                raw = Path(tmp) / "voice.wav"
                sf.write(str(raw), audio, 48000)
                run_process(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", str(raw), "-af",
                             tempo_filter(1 + settings.rate / 100), "-f", "wav", str(output)])
        else:
            sf.write(str(output), audio, 48000, format="WAV")
