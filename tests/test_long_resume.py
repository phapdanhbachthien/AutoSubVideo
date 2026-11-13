"""Real demux/seek/reopen regressions. Enable THIEN_LONG_MEDIA_TESTS=1."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import struct
import subprocess
from tempfile import TemporaryDirectory
import unittest

from PySide6.QtCore import QSettings
from player.library import time_label
from player.resume import read_resume


@unittest.skipUnless(os.getenv('THIEN_LONG_MEDIA_TESTS') == '1', 'Enable long-media integration fixtures')
class LongResumeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.mp3 = cls.root/'BUI RA MAT NỮ HOÀNG ÂM NHẠC 14h.mp3'
        subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i','anullsrc=r=8000:cl=mono',
                        '-t','50400','-c:a','libmp3lame','-b:a','8k',str(cls.mp3)],check=True,capture_output=True)
        # A real 208-hour PCM stream, stored sparsely to avoid writing 12 GB.
        # RF64 has 64-bit RIFF/data sizes; the holes are valid PCM16 silence.
        cls.wav = cls.root/'Nhạc tiếng Việt 208 giờ.wav'
        samples = 208*3600*8000
        size = samples*2
        header = (b'RF64'+struct.pack('<I',0xffffffff)+b'WAVEds64'+struct.pack('<IQQQI',28,size+72,size,samples,0)
                  +b'fmt '+struct.pack('<IHHIIHH',16,1,1,8000,16000,2,16)+b'data'+struct.pack('<I',0xffffffff))
        with cls.wav.open('wb') as f:
            f.write(header)
            f.seek(len(header)+size-1)
            f.write(b'\0')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def check_reopen(self, source, target, expected_duration):
        path = str(self.root/(source.suffix[1:]+'-settings.ini'))
        settings = QSettings(path,QSettings.IniFormat)
        settings.clear()
        import sys
        settings.sync()
        probe = str(Path(__file__).with_name('resume_probe.py'))
        for mode in ('save','check'):
            result = subprocess.run([sys.executable,probe,path,mode,str(source),str(target)],
                                    capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertAlmostEqual(read_resume(QSettings(path,QSettings.IniFormat),source.as_uri()),target,delta=2000)

    def test_mp3_spaces_and_vietnamese_reopens_at_13_02_21(self):
        self.check_reopen(self.mp3,46941000,50400000)

    def test_rf64_208_hours_reopens_after_hour_200(self):
        target = (200*3600+13*60+21)*1000
        self.assertEqual(time_label(target),'200:13:21')
        self.check_reopen(self.wav,target,208*3600000)
