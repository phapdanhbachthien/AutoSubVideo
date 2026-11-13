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
from player.resume import resume_key
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

    def test_restart_restores_last_video_and_each_file_position(self):
        import sys, json
        settings = str(self.base/'process-resume.ini')
        probe = str(Path(__file__).with_name('resume_probe.py'))
        video, audio = str(self.base/'long.mp4'), str(self.base/'song.wav')
        disk = QSettings(settings,QSettings.IniFormat)
        disk.setValue('playlist',json.dumps([QUrl.fromLocalFile(video).toString(QUrl.FullyEncoded),
                                             QUrl.fromLocalFile(audio).toString(QUrl.FullyEncoded)]))
        for index, mode, source, position in [(0,'save',video,125000),(0,'check',video,125000),
                                               (1,'save',audio,1500),(1,'check',audio,1500),
                                               (0,'check',video,125000)]:
            disk.setValue('index',index)
            disk.sync()
            result = subprocess.run([sys.executable,probe,settings,mode,source,str(position)],
                                    capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_pause_and_periodic_save_persist_and_remember_can_be_disabled(self):
        w = self.make_window()
        try:
            w.add_sources([self.base/'long.mp4'], autoplay=True)
            self.assertTrue(until(lambda: w.player.isSeekable()))
            w.set_position(45000)
            w.player.pause()
            disk = QSettings(w.settings.fileName(), QSettings.IniFormat)
            self.assertEqual(int(disk.value('index')), 0)
            self.assertIn('45000', str(disk.value(resume_key(w.player.source()))))
            w.player.play()
            w.set_position(90000)
            w.resume_timer.setInterval(50)
            self.assertTrue(until(lambda: int(QSettings(w.settings.fileName(), QSettings.IniFormat).value(resume_key(w.player.source()))) >= 90000))
            QTest.qWait(100)
            w.stop()
            w.save_session()
            self.assertGreaterEqual(int(w.settings.value(resume_key(w.player.source()))), 90000)
            w.remember.setChecked(False)
            w.close()
            reopened = MainWindow(QSettings(w.settings.fileName(), QSettings.IniFormat))
            try:
                self.assertEqual(reopened.queue.items, [])
                self.assertTrue(reopened.player.source().isEmpty())
            finally:
                reopened.close()
        finally:
            w.close()
            APP.processEvents()

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

    @unittest.skipUnless(os.getenv('DISPLAY') and os.getenv('QT_QPA_PLATFORM')=='xcb', 'Visible X11 display required')
    def test_video_is_visible_on_the_actual_window(self):
        w=self.make_window()
        try:
            w.move(0,0)
            w.add_sources([self.base/'full-hd.mp4'],autoplay=True)
            self.assertTrue(until(lambda:w.video.videoSink().videoFrame().isValid()))
            w.player.pause()
            QTest.qWait(300)
            image=w.screen().grabWindow(0).toImage()
            colors=[]
            for fx in (.2,.4,.6,.8):
                position=w.video.mapToGlobal(QPoint(int(w.video.width()*fx),int(w.video.height()*.5)))
                color=image.pixelColor(position)
                colors.append(max(color.red(),color.green(),color.blue())-min(color.red(),color.green(),color.blue()))
            self.assertGreater(sum(value>100 for value in colors),2,'Decoded video must be visible rather than a black surface')
        finally:
            w.close();APP.processEvents()

    @unittest.skipUnless(os.getenv('DISPLAY') and os.getenv('QT_QPA_PLATFORM')=='xcb', 'Visible X11 display required')
    def test_subtitle_is_visible_above_native_video_surface(self):
        w=self.make_window()
        try:
            w.move(0,0);w.activateWindow()
            w.add_sources([self.base/'long.mp4'],autoplay=True)
            self.assertTrue(until(lambda:w.video.videoSink().videoFrame().isValid()))
            w.player.pause()
            w.captions=[Caption(0,5000,'PHU DE TIENG VIET')]
            w.position_changed(1000)
            QTest.qWait(250)
            self.assertTrue(w.subtitle.isVisible())
            area=w.subtitle.geometry()
            def white_pixels():
                image=w.screen().grabWindow(0).toImage()
                return sum(1 for x in range(area.left()+8,area.right()-8,2)
                           for y in range(area.top()+4,area.bottom()-4,2)
                           if min(image.pixelColor(x,y).red(),image.pixelColor(x,y).green(),image.pixelColor(x,y).blue())>210)
            self.assertGreater(white_pixels(),25)
            w.clear_subtitles();QTest.qWait(80)
            self.assertFalse(w.subtitle.isVisible())
            self.assertLess(white_pixels(),5)
        finally:
            w.close();APP.processEvents()

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

    def test_real_decoded_audio_is_amplified_five_times_and_ui_reaches_500(self):
        from array import array
        import math
        w=self.make_window()
        try:
            self.assertEqual(w.volume.maximum(),500)
            levels=[]
            for percent in (100,500):
                data=[]
                def receive(raw):data.append(raw)
                w.audio.processedBuffer.connect(receive)
                w.volume.setValue(percent)
                w.add_sources([self.base/'song.wav'],autoplay=True)
                self.assertTrue(until(lambda:sum(len(x) for x in data)>100000))
                w.player.pause()
                w.audio.processedBuffer.disconnect(receive)
                samples=array('f');samples.frombytes(b''.join(data))
                levels.append(math.sqrt(sum(x*x for x in samples)/len(samples)))
                w.stop()
            self.assertAlmostEqual(levels[1]/levels[0],5,delta=.1)
            self.assertEqual(w.audio.volume(),5)
            self.assertEqual(w.audio.clock_output.volume(),0)
            self.assertEqual(w.volume_label.text(),'500%')
            self.assertIn('Thiện',w.windowTitle())
            self.assertFalse(w.windowIcon().isNull())
        finally:
            w.close();APP.processEvents()

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
