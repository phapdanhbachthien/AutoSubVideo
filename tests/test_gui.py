"""Run with a display (DISPLAY on Linux or a normal Windows desktop)."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import os
import time
import unittest

from autosub.core import Cue, write_srt


@unittest.skipUnless(os.name == "nt" or os.getenv("DISPLAY"), "A graphical display is required")
class GuiTests(unittest.TestCase):
    def test_load_srt_and_voice_picker(self):
        import tkinter as tk
        from autosub.gui import App
        app = App()
        try:
            with TemporaryDirectory() as tmp:
                path = Path(tmp) / "test.srt"
                write_srt(path, [Cue(0, 2, "Xin chào!")])
                app.values["srt"].set(str(path))
                app.load()
                deadline = time.monotonic() + 10
                while app.busy and time.monotonic() < deadline:
                    app.update()
                    time.sleep(.01)
                self.assertFalse(app.busy)
                self.assertEqual(app.cues, [Cue(0, 2, "Xin chào!")])
                self.assertEqual(len(app.table.get_children()), 1)
                app.speech_dialog()
                app.update()
                self.assertGreaterEqual(len(app.voice_box['values']), 2)
                if app.provider.get() == "local":
                    self.assertTrue(any("Ngọc Huyền" in label for label in app.voice_box['values']))
                    app.provider.set("edge")
                    from autosub.speech import EDGE_VOICES
                    app.voice_catalog = list(EDGE_VOICES)
                app.voice.set("vi-VN | Nam | vi-VN-NamMinhNeural")
                self.assertEqual(app.speech_settings().voice, "vi-VN-NamMinhNeural")
                app.voice_filter.set("en-")
                app.update_voice_choices()
                self.assertGreaterEqual(len(app.voice_box['values']), 2)
                for child in app.winfo_children():
                    if isinstance(child, tk.Toplevel):
                        child.destroy()
                app.automatic_dialog()
                app.update()
                self.assertTrue(any(isinstance(c, tk.Toplevel) for c in app.winfo_children()))
        finally:
            app.close()
