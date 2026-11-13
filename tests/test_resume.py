import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PySide6.QtCore import QSettings, QUrl

from player.resume import resume_key, read_resume, write_resume


class ResumeStorageTests(unittest.TestCase):
    def test_spaces_unicode_and_url_escaping_share_one_bookmark(self):
        for raw in ['file:///C:/Nhạc/BUI RA MAT NỮ HOÀNG.mp3',
                    'file:///C:/Nhạc/100% hay #1 + nhạc.mp3']:
            url = QUrl(raw)
            self.assertEqual(resume_key(url), resume_key(url.toString(QUrl.FullyEncoded)))
            self.assertEqual(resume_key(url), resume_key(url.toString()))
        self.assertNotEqual(resume_key('file:///C:/one.mp3'), resume_key('file:///C:/two.mp3'))

    def test_migrate_old_writer_key_and_preserve_200_hours_and_beyond(self):
        with TemporaryDirectory() as folder:
            path = str(Path(folder)/'settings.ini')
            settings = QSettings(path, QSettings.IniFormat)
            uri = QUrl('file:///C:/Nhạc/BUI RA MAT NỮ HOÀNG.mp3')
            oldkey = 'resume/' + hashlib.sha256(uri.toString().encode()).hexdigest()
            settings.setValue(oldkey, 46941000)  # 13:02:21
            self.assertEqual(read_resume(settings, uri.toString(QUrl.FullyEncoded)), 46941000)
            self.assertTrue(settings.contains(resume_key(uri)))
            for position in (720000000, 748799000, 3600000000):
                write_resume(settings, uri, position)
                settings.sync()
                self.assertEqual(read_resume(QSettings(path, QSettings.IniFormat), uri), position)
            write_resume(settings, uri, 0)
            self.assertEqual(read_resume(settings, uri), 0, 'A new zero must override the migrated old bookmark')

    def test_corrupt_bookmark_does_not_crash(self):
        with TemporaryDirectory() as folder:
            settings = QSettings(str(Path(folder)/'settings.ini'), QSettings.IniFormat)
            settings.setValue(resume_key('file:///C:/test.mp3'), 'invalid')
            self.assertEqual(read_resume(settings, 'file:///C:/test.mp3'), 0)
