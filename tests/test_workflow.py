from pathlib import Path
from tempfile import TemporaryDirectory
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import subprocess
import threading
import unittest

from autosub.core import Cue, read_srt, write_srt, timestamp, translate, render, media_info


class SubtitleTests(unittest.TestCase):
    def test_multiline_unicode_and_profanity_roundtrip(self):
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "lời thoại.srt"
            cues = [Cue(0.9996, 2.5, "Địt mẹ!\nKeep the exact words."), Cue(3601.2, 3602, "Xin chào")]
            write_srt(p, cues)
            result = read_srt(p)
            self.assertEqual(result[0].text, cues[0].text)
            self.assertEqual(result[0].start, 1)
            self.assertEqual(result[1], cues[1])
            self.assertEqual(timestamp(59.9996), "00:01:00,000")

    def test_reject_malformed_input(self):
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.srt"
            for content in ["", "1\n00:00:03,000 --> 00:00:01,000\nText", "1\n00:70:00,000 --> 00:71:00,000\nText"]:
                p.write_text(content)
                with self.assertRaises(ValueError):
                    read_srt(p)
        with self.assertRaises(ValueError):
            Cue(float("nan"), 4, "Text")

    def test_translation_request_and_response_contract(self):
        requests = []
        response = ["Khốn kiếp!"]
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"choices": [{"message": {"content": json.dumps(response)}}]}).encode())
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/v1"
            cues = [Cue(1, 2, "Damn!")]
            translated = translate(cues, url, "test", "Vietnamese", log=lambda _: None)
            self.assertEqual(translated, [Cue(1, 2, "Khốn kiếp!")])
            self.assertEqual(json.loads(requests[0]["messages"][1]["content"]), ["Damn!"])
            response.clear()
            with self.assertRaises(ValueError):
                translate(cues, url, "test", "Vietnamese", log=lambda _: None)
            self.assertEqual(cues[0].text, "Damn!")
        finally:
            server.shutdown()
            server.server_close()

    def test_real_video_render_unicode_path_and_audio(self):
        with TemporaryDirectory(prefix="video tiếng Việt ") as tmp:
            base = Path(tmp)
            video, srt, output = base / "nguồn.mp4", base / "phụ đề.srt", base / "kết quả.mp4"
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=320x240:d=2", "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-c:v", "libx264", "-c:a", "aac", str(video)], check=True, capture_output=True)
            write_srt(srt, [Cue(0, 1.8, "Xin chào — lời thoại nguyên văn!")])
            render(video, srt, output)
            info = media_info(output)
            self.assertEqual({s["codec_type"] for s in info["streams"]}, {"video", "audio"})
            self.assertAlmostEqual(float(info["format"]["duration"]), 2, delta=0.2)
            frame = subprocess.run(["ffmpeg", "-v", "error", "-ss", "0.5", "-i", str(output), "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"], check=True, capture_output=True).stdout
            # Black source has no bright pixels; rendered caption must add visible pixels.
            self.assertGreater(sum(v > 120 for v in frame), 25)
            with self.assertRaises(ValueError):
                render(video, srt, video)
            with self.assertRaises(ValueError):
                render(video, srt, output)


if __name__ == "__main__":
    unittest.main()
