import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_MEDIA_BACKEND', 'ffmpeg')

from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import time
import unittest

from PySide6.QtCore import Qt, QUrl, QSettings, QPoint
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtMultimedia import QMediaPlayer, QVideoSink

from player.app import MainWindow
from player.library import Caption

APP = QApplication.instance() or QApplication([])
APP.setQuitOnLastWindowClosed(False)


def until(condition, seconds=15):
    end = time.monotonic()+seconds
    while time.monotonic() < end:
        APP.processEvents()
        if condition():
            return True
        QTest.qWait(20)
    return False


class PlaybackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = TemporaryDirectory()
        cls.base = Path(cls.files.name)
        for filename, source, encoding in [
            ('full-hd.mp4', 'testsrc2=size=1920x1080:rate=2:duration=2', ['-c:v','libx264','-preset','ultrafast']),
            ('eight-k.mkv', 'color=c=blue:size=7680x4320:rate=1:duration=1', ['-c:v','ffv1','-threads','2']),
            ('long.mp4', 'color=c=black:size=64x64:rate=1:duration=720', ['-c:v','libx264','-preset','ultrafast']),
            ('song.wav', 'sine=frequency=440:duration=3', []),
        ]:
            subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i',source,*encoding,str(cls.base/filename)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.files.cleanup()

    def decode(self, filename):
        player, sink = QMediaPlayer(), QVideoSink()
        received = []
        sink.videoFrameChanged.connect(lambda frame: received.append((frame.width(),frame.height())) if frame.isValid() else None)
        player.setVideoOutput(sink)
        player.setSource(QUrl.fromLocalFile(str(self.base/filename)))
        player.play()
        try:
            self.assertTrue(until(lambda: bool(received)), player.errorString())
            return received[0]
        finally:
            player.stop()
            player.setSource(QUrl())

    def test_real_full_hd_and_8k_decoded_frame_dimensions(self):
        self.assertEqual(self.decode('full-hd.mp4'), (1920,1080))
        self.assertEqual(self.decode('eight-k.mkv'), (7680,4320))

    def test_real_audio_loading_and_clock_progress(self):
        player = QMediaPlayer()
        player.setSource(QUrl.fromLocalFile(str(self.base/'song.wav')))
        player.play()
        try:
            self.assertTrue(until(lambda: player.duration()>0 and player.position()>200), player.errorString())
            self.assertTrue(player.hasAudio())
            self.assertAlmostEqual(player.duration(),3000,delta=100)
            player.pause()
            QTest.qWait(80)
            position=player.position()
            QTest.qWait(150)
            self.assertEqual(player.position(),position)
        finally:
            player.stop()
            player.setSource(QUrl())

    def make_window(self):
        settings=QSettings(str(self.base/'settings.ini'), QSettings.IniFormat)
        settings.clear()
        window=MainWindow(settings)
        window.show()
        APP.processEvents()
        return window

    def test_real_gui_seek_buttons_slider_and_keyboard(self):
        w=self.make_window()
        try:
            w.add_sources([self.base/'long.mp4'], autoplay=True)
            self.assertTrue(until(lambda:w.player.isSeekable() and w.player.duration()==720000),w.player.errorString())
            w.player.pause()
            self.assertEqual(len(w.seeking_buttons),12)
            for button in w.seeking_buttons:
                w.player.setPosition(60000 if button.property('seekDelta')>0 else 660000)
                APP.processEvents()
                before=w.player.position()
                QTest.mouseClick(button,Qt.LeftButton)
                self.assertEqual(w.player.position(),before+button.property('seekDelta'))
            w.player.setPosition(100000)
            w.video.setFocus()
            w.activateWindow()
            APP.processEvents()
            QTest.keyClick(w.video,Qt.Key_Right,Qt.ControlModifier)
            self.assertEqual(w.player.position(),110000)
            w.search.setFocus()
            QTest.keyClicks(w.search,'hello world')
            self.assertEqual(w.search.text(),'hello world')
            QTest.mouseClick(w.timeline,Qt.LeftButton,pos=QPoint(w.timeline.width()//2,w.timeline.height()//2))
            self.assertFalse(w.scrubbing)
            self.assertAlmostEqual(w.player.position(),360000,delta=10000)
        finally:
            w.close();APP.processEvents()

    def test_gui_playlist_tracks_subtitles_and_fullscreen(self):
        w=self.make_window()
        try:
            w.add_sources([self.base/'long.mp4',self.base/'song.wav'],autoplay=True)
            self.assertTrue(until(lambda:w.player.duration()==720000))
            w.player.pause()
            w.next_track(1)
            self.assertTrue(until(lambda:w.player.hasAudio() and w.player.duration()==3000))
            w.next_track(-1)
            self.assertTrue(until(lambda:w.player.duration()==720000))
            w.player.pause()
            w.captions=[Caption(1000,3000,'Phụ đề tiếng Việt')]
            w.position_changed(1500)
            self.assertEqual(w.subtitle.text(),'Phụ đề tiếng Việt')
            w.position_changed(4000)
            self.assertEqual(w.subtitle.text(),'')
            w.toggle_fullscreen();APP.processEvents()
            self.assertTrue(w.isFullScreen())
            w.toggle_fullscreen();APP.processEvents()
            self.assertFalse(w.isFullScreen())
            w.list.clearSelection();w.list.item(1).setSelected(True)
            w.remove_selected()
            self.assertEqual(len(w.queue.items),1)
        finally:
            w.close();APP.processEvents()
