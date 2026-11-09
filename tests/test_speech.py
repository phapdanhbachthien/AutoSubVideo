from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import math
import struct
import subprocess
import sys
import types
import unittest
import wave

from autosub.core import Cue, media_info, read_srt, render, write_srt
from autosub.speech import SpeechSettings, narration, synthesize
from autosub.workflow import PipelineOptions, process


def tone(text, output, settings):
    # Speech fixture with a different duration than the subtitle slot.
    with wave.open(str(output), "wb") as f:
        f.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
        f.writeframes(b"".join(struct.pack('<h', round(12000 * math.sin(2 * math.pi * 660 * i / 24000))) for i in range(36000)))


class SpeechTests(unittest.TestCase):
    def test_narration_fits_slots_and_keeps_silence(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "voice.wav"
            cues = [Cue(0.5, 1, "Dòng ngắn"), Cue(2, 4, "Dòng dài hơn")]
            narration(cues, output, synthesizer=tone, log=lambda _: None)
            with wave.open(str(output)) as f:
                self.assertEqual(f.getnframes(), 4 * 24000)
                self.assertEqual(f.readframes(12000), b"\0\0" * 12000)
                speech = f.readframes(12000)
                self.assertTrue(any(speech))
                self.assertEqual(f.readframes(24000), b"\0\0" * 24000)
                self.assertTrue(any(f.readframes(24000)))
            with self.assertRaises(ValueError):
                narration(cues, output, synthesizer=tone)

    def test_failed_speech_does_not_publish_partial_audio(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "voice.wav"
            def failure(*args):
                raise RuntimeError("Provider unavailable")
            with self.assertRaises(RuntimeError):
                narration([Cue(0, 1, "Hello")], output, synthesizer=failure)
            self.assertFalse(output.exists())
            with self.assertRaises(ValueError):
                narration([Cue(0, 2, "One"), Cue(1, 3, "Two")], output, synthesizer=tone)
            self.assertFalse(output.exists())

    def test_edge_adapter_passes_text_voice_and_rate(self):
        received = {}
        class FakeSpeech:
            def __init__(self, text, **kwargs):
                received.update(text=text, **kwargs)
            async def save(self, path):
                Path(path).write_bytes(b"audio fixture")
        with TemporaryDirectory() as tmp, patch("autosub.speech.edge_module", return_value=types.SimpleNamespace(Communicate=FakeSpeech)):
            synthesize("Lời thoại nguyên văn!", Path(tmp) / "sample.mp3", SpeechSettings(voice="vi-VN-NamMinhNeural", rate=-20))
        self.assertEqual(received["voice"], "vi-VN-NamMinhNeural")
        self.assertEqual(received["rate"], "-20%")
        self.assertEqual(received["text"], "Lời thoại nguyên văn!")

    def test_audio_asr_adapter_uses_requested_language(self):
        received = {}
        class FakeWhisper:
            def __init__(self, model, **kwargs):
                received["model"] = model
            def transcribe(self, filename, **kwargs):
                received.update(filename=filename, **kwargs)
                return iter([types.SimpleNamespace(start=0.1, end=1.2, text=" Hello! ")]), None
        from autosub.core import transcribe
        with patch.dict(sys.modules, {"faster_whisper": types.SimpleNamespace(WhisperModel=FakeWhisper)}):
            result = transcribe(Path("audio.mp3"), "small", "en", log=lambda _: None)
        self.assertEqual(result, [Cue(.1, 1.2, "Hello!")])
        self.assertEqual(received["language"], "en")
        self.assertEqual(received["filename"], "audio.mp3")

    def test_automatic_srt_translate_speech_video_pipeline(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            video, srt = base / "input.mp4", base / "source.srt"
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=320x240:d=3", "-f", "lavfi", "-i", "sine=frequency=440:duration=3", "-c:v", "libx264", "-c:a", "aac", str(video)], check=True, capture_output=True)
            write_srt(srt, [Cue(.5, 2, "Hello")])
            values = dict(video=str(video), srt=str(srt), endpoint="http://127.0.0.1/v1", model="test", target="Tiếng Việt", key="")
            options = PipelineOptions(source="Tệp SRT", translate_text=True, speak=True, video=True, original_volume=.2)
            def fake_translation(cues, *args):
                return [Cue(c.start, c.end, "Xin chào") for c in cues]
            with patch("autosub.workflow.translate", side_effect=fake_translation), patch("autosub.speech.synthesize", side_effect=tone):
                result = process(values, [], base, options, log=lambda _: None)
            folders = list(base.glob("AutoSubVideo-*"))
            self.assertEqual(len(folders), 1)
            folder = folders[0]
            self.assertEqual(read_srt(folder / "original.srt")[0].text, "Hello")
            self.assertEqual(read_srt(folder / "translated.srt")[0].text, "Xin chào")
            info = media_info(folder / "video.mp4")
            self.assertAlmostEqual(float(info["format"]["duration"]), 3, delta=.2)
            self.assertEqual({s["codec_type"] for s in info["streams"]}, {"video", "audio"})
            # Video audio continues after the last cue, thanks to padding.
            audio = next(s for s in info["streams"] if s["codec_type"] == "audio")
            self.assertAlmostEqual(float(audio["duration"]), 3, delta=.2)
            self.assertEqual(result["cues"][0].text, "Xin chào")
            rendered = subprocess.run(["ffmpeg", "-v", "error", "-i", str(folder / "video.mp4"), "-f", "s16le", "-ac", "1", "-ar", "24000", "-"], capture_output=True, check=True).stdout
            # The initial gap contains the original 440 Hz signal when mixing is enabled.
            samples = struct.unpack('<' + 'h' * (len(rendered) // 2), rendered)
            self.assertGreater(max(abs(x) for x in samples[1200:4800]), 100)
            replacement = base / "replace-original.mp4"
            render(video, srt, replacement, narration_audio=folder / "narration.wav", original_volume=0)
            replaced_audio = subprocess.run(["ffmpeg", "-v", "error", "-i", str(replacement), "-f", "s16le", "-ac", "1", "-ar", "24000", "-"], capture_output=True, check=True).stdout
            replaced_samples = struct.unpack('<' + 'h' * (len(replaced_audio) // 2), replaced_audio)
            self.assertLess(max(abs(x) for x in replaced_samples[1200:4800]), 5)
            self.assertGreater(max(abs(x) for x in replaced_samples[18000:24000]), 1000)
            # Replacement must also work with a video that has no audio stream.
            silent = base / "silent.mp4"
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(video), "-an", "-c:v", "copy", str(silent)], check=True, capture_output=True)
            replaced = base / "replacement.mp4"
            render(silent, srt, replaced, narration_audio=folder / "narration.wav", original_volume=.2)
            self.assertTrue(any(s["codec_type"] == "audio" for s in media_info(replaced)["streams"]))


if __name__ == "__main__":
    unittest.main()
