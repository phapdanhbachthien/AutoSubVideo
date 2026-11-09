from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import unittest
import wave

from autosub.resources import default_bundle, original_catalog, verify_bundle


@unittest.skipUnless((Path(default_bundle()) / "local_tts_manifest.json").is_file(), "Original resource bundle required")
class OriginalResourcesTests(unittest.TestCase):
    def test_original_catalog_and_checksums(self):
        catalog = original_catalog(default_bundle())
        self.assertEqual(len(catalog["presets"]), 25)
        self.assertIn("Ngọc Huyền", catalog["presets"])
        self.assertEqual(len(catalog["presets"]["Ngọc Huyền"]["speaker_emb"]), 192)
        self.assertEqual(verify_bundle(default_bundle()), 48)

    def test_real_ngoc_huyen_onnx_synthesis(self):
        from autosub.speech import SpeechSettings, preview
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "Ngọc Huyền.wav"
            preview("Xin chào, đây là giọng Ngọc Huyền.", output,
                    SpeechSettings("local", "Ngọc Huyền", 0, default_bundle()))
            with wave.open(str(output)) as wav:
                self.assertEqual(wav.getframerate(), 24000)
                self.assertGreater(wav.getnframes(), 24000)
                self.assertTrue(any(wav.readframes(wav.getnframes())))

    def test_real_original_ocr_on_video(self):
        from PIL import Image, ImageDraw, ImageFont
        import subprocess
        from autosub.ocr import extract_captions
        with TemporaryDirectory() as tmp:
            image = Image.new("RGB", (1024, 576), "black")
            font = ImageFont.truetype(str(Path(default_bundle()) / "fonts/NotoSansCJK-Bold.otf"), 36)
            ImageDraw.Draw(image).text((120, 450), "XIN CHAO VIET NAM", font=font, fill="white")
            frame, video = Path(tmp) / "frame.png", Path(tmp) / "video.mp4"
            image.save(frame)
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-loop", "1", "-i", str(frame), "-t", "2", "-r", "10", "-pix_fmt", "yuv420p", str(video)], check=True, capture_output=True)
            cues = extract_captions(video, default_bundle(), log=lambda _: None)
            self.assertEqual(len(cues), 1)
            self.assertIn("CHAO", cues[0].text)
            self.assertIn("NAM", cues[0].text)
            self.assertEqual(cues[0].start, 0)
            self.assertAlmostEqual(cues[0].end, 2, delta=.1)
