from pathlib import Path
import json
import os
import sys

os.environ.setdefault('QT_MEDIA_BACKEND', 'ffmpeg')

from PySide6.QtCore import Qt, QUrl, QTimer, QSettings, QEvent, QSize, QPoint
from PySide6.QtGui import QAction, QKeySequence, QFont, QImage, QIcon, QPixmap
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QSplitter, QSlider, QComboBox, QListWidget,
    QListWidgetItem, QLineEdit, QFileDialog, QMessageBox, QInputDialog, QStackedLayout,
    QAbstractItemView, QStyle, QSpinBox, QDialog, QFormLayout)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaMetaData
from PySide6.QtMultimediaWidgets import QVideoWidget

from .library import (Playlist, MEDIA_EXTENSIONS, SEEK_SECONDS, seek_target, time_label,
                      normalize_source, source_title, read_playlist, write_playlist, read_srt, caption_text)
from .resume import read_resume, write_resume
from .theme import STYLE as CYBER_STYLE, CyberBackground, CyberPanel
from .audio import SoftwareAudioOutput

ASSETS=Path(__file__).resolve().parent.parent/'assets'


class MusicPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet('background: #080c18;')
        layout=QVBoxLayout(self)
        layout.addStretch()
        logo=QLabel()
        logo.setAlignment(Qt.AlignCenter)
        logo.setPixmap(QPixmap(str(ASSETS/'app-icon.png')).scaled(250,250,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        layout.addWidget(logo)
        self.title=QLabel('THIỆN // CYBER PLAYER')
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setWordWrap(True)
        self.title.setTextFormat(Qt.PlainText)
        self.title.setStyleSheet('color: #38dce9; font-size: 22px; padding: 10px;')
        layout.addWidget(self.title)
        tagline=QLabel('BÁCH THIỆN AUDIO  /  NHẠC & VIDEO')
        tagline.setAlignment(Qt.AlignCenter)
        tagline.setStyleSheet('color: #c5a673; font-size: 12px;')
        layout.addWidget(tagline)
        layout.addStretch()

    def setText(self,text):
        self.title.setText(text)


class SeekSlider(QSlider):
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setSliderDown(True)
            width = max(1, self.width() - 14)
            value = QStyle.sliderValueFromPosition(self.minimum(), self.maximum(),
                        max(0, min(width, round(event.position().x()) - 7)), width)
            self.setValue(value)
            self.sliderMoved.emit(value)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setSliderDown(False)
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class VideoSurface(QWidget):
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'caption'):
            self.caption.position_overlay()


class CaptionOverlay(QLabel):
    def __init__(self,anchor,host):
        super().__init__(host,Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
        self.anchor=anchor
        self.host=host
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setTextFormat(Qt.PlainText)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet('background: #05080f; color: white; font-size: 23px; font-weight: 700; padding: 8px;')
        self.hide()
        QApplication.instance().applicationStateChanged.connect(self.application_state_changed)

    def application_state_changed(self,state):
        self.position_overlay()

    def position_overlay(self):
        parent=self.anchor
        height=min(max(48,self.heightForWidth(max(1,parent.width()))+8),max(48,parent.height()//3))
        point=parent.mapToGlobal(QPoint(0,max(0,parent.height()-height)))
        self.setGeometry(point.x(),point.y(),parent.width(),height)
        visible=bool(self.text()) and parent.isVisible() and not self.host.isMinimized() and QApplication.applicationState()==Qt.ApplicationActive and QApplication.activeModalWidget() is None
        self.setVisible(visible)
        if visible:self.raise_()

    def setText(self,text):
        super().setText(text)
        self.position_overlay()

    def clear(self):
        self.setText('')


class MainWindow(QMainWindow):
    def __init__(self, settings=None):
        super().__init__()
        self.setWindowTitle('Thiện Media Player // Cyber Edition')
        self.setWindowIcon(QIcon(str(ASSETS/'app-icon.ico')))
        self.resize(1260, 830)
        self.setMinimumSize(960, 680)
        self.setAcceptDrops(True)
        self.settings = settings or (QSettings(os.environ['THIEN_PLAYER_CONFIG'], QSettings.IniFormat)
                                    if os.getenv('THIEN_PLAYER_CONFIG') else QSettings('BachThien', 'ThienMediaPlayer'))
        self.queue = Playlist()
        self.captions = []
        self.scrubbing = False
        self.pending_position = 0
        self.seeking_buttons = []
        self.player = QMediaPlayer(self)
        self.audio = SoftwareAudioOutput(self.player,self)
        self._build_ui()
        self._menus()
        self._connect()
        self.setStyleSheet(CYBER_STYLE)
        self.audio.setVolume(.7)
        self.restore()
        self.resume_timer = QTimer(self)
        self.resume_timer.setInterval(5000)
        self.resume_timer.timeout.connect(self.save_session)
        self.resume_timer.start()
        QApplication.instance().installEventFilter(self)

    def _button(self, text, callback, layout, tip=''):
        button = QPushButton(text)
        button.setToolTip(tip)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    def _build_ui(self):
        central = CyberBackground()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(18, 12, 18, 12)
        outer.setSpacing(10)
        self.header = QWidget()
        head = QHBoxLayout(self.header)
        head.setContentsMargins(0, 0, 0, 0)
        logo=QLabel()
        logo.setPixmap(QPixmap(str(ASSETS/'app-icon.png')).scaled(42,42,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        head.addWidget(logo)
        brand = QLabel('THIỆN // CYBER PLAYER')
        brand.setStyleSheet('font-size: 23px; font-weight: 700; color: #49f3fa; letter-spacing: 2px;')
        head.addWidget(brand)
        self.quality = QLabel('FULL HD · 4K · 8K')
        self.quality.setStyleSheet('color: #fa78c5; border: 1px solid #68345d; background: #1d122a; padding: 6px 10px;')
        head.addStretch()
        head.addWidget(self.quality)
        self._button('+ Mở tệp', self.open_files, head, 'Ctrl+O · Chọn nhiều tệp nhạc/video')
        self._button('Mở thư mục', self.open_folder, head, 'Ctrl+Shift+O')
        outer.addWidget(self.header)

        self.splitter = QSplitter(Qt.Horizontal)
        self.display_panel = CyberPanel()
        self.display_panel.setObjectName('panel')
        display = QVBoxLayout(self.display_panel)
        display.setContentsMargins(8, 8, 8, 8)
        self.now = QLabel('Chưa có tệp — kéo nhạc hoặc video vào cửa sổ')
        self.now.setTextFormat(Qt.PlainText)
        self.now.setStyleSheet('font-size: 15px; font-weight: 600; color: #b4e5f2; padding: 5px;')
        display.addWidget(self.now)
        self.video_container = VideoSurface()
        self.video_container.setStyleSheet('background: #05080f;')
        layers = QStackedLayout(self.video_container)
        layers.setStackingMode(QStackedLayout.StackAll)
        self.video = QVideoWidget()
        self.video.setMinimumSize(320, 180)
        self.video.setAspectRatioMode(Qt.KeepAspectRatio)
        layers.addWidget(self.video)
        self.music = MusicPanel()
        layers.addWidget(self.music)
        self.subtitle = CaptionOverlay(self.video_container,self)
        self.video_container.caption = self.subtitle
        layers.setCurrentWidget(self.music)
        display.addWidget(self.video_container, 1)
        self.video.installEventFilter(self)
        self.music.installEventFilter(self)
        self.player.setVideoOutput(self.video)
        self.video.hide()
        self.splitter.addWidget(self.display_panel)

        self.list_panel = CyberPanel()
        self.list_panel.setObjectName('panel')
        side = QVBoxLayout(self.list_panel)
        self.count = QLabel('DANH SÁCH PHÁT · 0 tệp')
        self.count.setStyleSheet('font-weight: 700; color: #f47fca; padding: 3px; letter-spacing: 1px;')
        side.addWidget(self.count)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Tìm bài hát / video…')
        side.addWidget(self.search)
        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list.setDragDropMode(QAbstractItemView.InternalMove)
        self.list.setDefaultDropAction(Qt.MoveAction)
        self.list.setToolTip('Nhấp đôi / Enter để phát · kéo để sắp xếp · Delete để bỏ khỏi danh sách')
        side.addWidget(self.list, 1)
        list_buttons = QHBoxLayout()
        self._button('Thêm', self.open_files, list_buttons)
        self._button('Bỏ chọn', self.remove_selected, list_buttons, 'Chỉ bỏ khỏi playlist, không xóa tệp trên máy')
        self._button('Xóa DS', self.clear_queue, list_buttons)
        side.addLayout(list_buttons)
        self.splitter.addWidget(self.list_panel)
        self.splitter.setSizes([900, 320])
        outer.addWidget(self.splitter, 1)

        timeline = QHBoxLayout()
        self.elapsed = QLabel('00:00')
        self.elapsed.setMinimumWidth(62)
        timeline.addWidget(self.elapsed)
        self.timeline = SeekSlider(Qt.Horizontal)
        self.timeline.setRange(0, 0)
        timeline.addWidget(self.timeline, 1)
        self.duration_label = QLabel('00:00')
        self.duration_label.setMinimumWidth(62)
        timeline.addWidget(self.duration_label)
        outer.addLayout(timeline)

        controls = QHBoxLayout()
        self._button('⏮ Bài trước', lambda: self.next_track(-1), controls, 'P / PageUp')
        self.play_button = self._button('▶ Phát', self.toggle_play, controls, 'Space')
        self.play_button.setObjectName('primary')
        self._button('■ Dừng', self.stop, controls, 'S')
        self._button('Bài tiếp ⏭', lambda: self.next_track(1), controls, 'N / PageDown')
        self.shuffle = self._button('Ngẫu nhiên', lambda: None, controls)
        self.shuffle.setCheckable(True)
        self.repeat = QComboBox()
        self.repeat.addItems(['Không lặp', 'Lặp danh sách', 'Lặp một bài'])
        controls.addWidget(self.repeat)
        self.speed = QComboBox()
        self.speed.addItems(['0.25×', '0.5×', '0.75×', '1×', '1.25×', '1.5×', '1.75×', '2×', '3×', '4×'])
        self.speed.setCurrentText('1×')
        self.speed.setToolTip('Tốc độ phát')
        controls.addWidget(self.speed)
        controls.addStretch()
        self.mute = self._button('Âm thanh', self.toggle_mute, controls, 'M · Bật/tắt tiếng')
        self.volume = QSlider(Qt.Horizontal)
        self.volume.setRange(0, 500)
        self.volume.setSingleStep(5)
        self.volume.setPageStep(25)
        self.volume.setToolTip('0–100% bình thường · 100–500% khuếch đại PCM, có giới hạn đỉnh')
        self.volume.setValue(70)
        self.volume.setFixedWidth(110)
        self.volume_label = QLabel('70%')
        controls.addWidget(self.volume)
        controls.addWidget(self.volume_label)
        self._button('Toàn màn hình', self.toggle_fullscreen, controls, 'F11 / F · Esc để thoát')
        outer.addLayout(controls)

        jump_panel = CyberPanel()
        jump_panel.setObjectName('panel')
        jumps = QGridLayout(jump_panel)
        jumps.setContentsMargins(10, 8, 10, 8)
        for row, sign, title in [(0, -1, 'TUA LÙI'), (1, 1, 'TUA TIẾN')]:
            jumps.addWidget(QLabel(title), row, 0)
            for column, seconds in enumerate(SEEK_SECONDS, 1):
                label = f'{seconds}s' if seconds < 60 else f'{seconds // 60} phút'
                button = QPushButton(('− ' if sign < 0 else '+ ') + label)
                button.setProperty('seekDelta', sign * seconds * 1000)
                button.clicked.connect(lambda checked=False, delta=sign*seconds*1000: self.seek_by(delta))
                jumps.addWidget(button, row, column)
                self.seeking_buttons.append(button)
        outer.addWidget(jump_panel)
        self.statusBar().showMessage('Kéo thả tệp · Space: phát/tạm dừng · ←/→: tua 5s · F11: toàn màn hình')

    def _action(self, menu, title, callback, shortcut=None, checkable=False):
        action = QAction(title, self)
        action.setCheckable(checkable)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(callback)
        menu.addAction(action)
        return action

    def _menus(self):
        file = self.menuBar().addMenu('Tệp')
        self._action(file, 'Mở nhạc / video…', self.open_files, 'Ctrl+O')
        self._action(file, 'Thêm thư mục…', self.open_folder, 'Ctrl+Shift+O')
        self._action(file, 'Mở địa chỉ HTTP(S)…', self.open_url)
        file.addSeparator()
        self._action(file, 'Mở playlist M3U/M3U8…', self.load_playlist, 'Ctrl+L')
        self._action(file, 'Lưu playlist…', self.save_playlist, 'Ctrl+Shift+S')
        self._action(file, 'Thoát', self.close, 'Alt+F4')
        playback = self.menuBar().addMenu('Phát')
        self._action(playback, 'Đi đến thời gian…', self.go_to, 'Ctrl+G')
        self._action(playback, 'Sắp xếp playlist A–Z', self.sort_playlist)
        self.remember = self._action(playback, 'Nhớ playlist và vị trí xem', lambda: None, checkable=True)
        self.remember.setChecked(True)
        self.track_menu = self.menuBar().addMenu('Âm thanh / phụ đề')
        self._action(self.track_menu, 'Chọn luồng âm thanh…', self.choose_audio)
        self._action(self.track_menu, 'Âm lượng chuẩn 100%', lambda:self.volume.setValue(100), 'Ctrl+0')
        self._action(self.track_menu, 'Chọn phụ đề có sẵn trong video…', self.choose_embedded_subtitle)
        self._action(self.track_menu, 'Mở phụ đề SRT ngoài…', self.open_subtitles)
        self._action(self.track_menu, 'Tắt phụ đề', self.clear_subtitles)
        self._action(self.track_menu, 'Chỉnh lệch phụ đề SRT…', self.subtitle_offset_dialog)
        view = self.menuBar().addMenu('Hiển thị')
        self._action(view, 'Toàn màn hình', self.toggle_fullscreen, 'F11')
        self.show_list = self._action(view, 'Hiện danh sách phát', lambda checked: self.list_panel.setVisible(checked), checkable=True)
        self.show_list.setChecked(True)
        self._action(view, 'Luôn nổi trên cùng', self.always_on_top, checkable=True)
        self._action(view, 'Tỉ lệ gốc / vừa khung', lambda: self.video.setAspectRatioMode(Qt.KeepAspectRatio))
        self._action(view, 'Lấp đầy / cắt mép', lambda: self.video.setAspectRatioMode(Qt.KeepAspectRatioByExpanding))
        self._action(view, 'Kéo giãn toàn khung', lambda: self.video.setAspectRatioMode(Qt.IgnoreAspectRatio))
        self._action(view, 'Chụp khung hình…', self.snapshot, 'Ctrl+S')
        self._action(view, 'Thông tin tệp', self.media_info, 'Ctrl+I')
        help_menu = self.menuBar().addMenu('Trợ giúp')
        self._action(help_menu, 'Phím tắt / 8K', self.help_dialog)
        self.subtitle_offset = 0

    def _connect(self):
        self.list.itemActivated.connect(lambda item: self.play_index(self.list.row(item)))
        self.list.model().rowsMoved.connect(self.reordered)
        self.search.textChanged.connect(self.filter_list)
        self.timeline.sliderPressed.connect(lambda: setattr(self, 'scrubbing', True))
        self.timeline.sliderReleased.connect(self.release_seek)
        self.timeline.sliderMoved.connect(lambda value: self.elapsed.setText(time_label(value)))
        self.volume.valueChanged.connect(self.set_volume)
        self.speed.currentTextChanged.connect(self.change_rate)
        self.player.durationChanged.connect(self.duration_changed)
        self.player.positionChanged.connect(self.position_changed)
        self.player.playbackStateChanged.connect(self.state_changed)
        self.player.mediaStatusChanged.connect(self.media_status)
        self.player.seekableChanged.connect(self.seekable_changed)
        self.player.hasVideoChanged.connect(self.video_changed)
        self.player.metaDataChanged.connect(self.update_metadata)
        self.player.errorOccurred.connect(lambda error, text: self.statusBar().showMessage('Không phát được: ' + text))
        self.video.videoSink().subtitleTextChanged.connect(self.embedded_text)

    def video_changed(self,has_video):
        self.video.setVisible(has_video)
        self.music.setVisible(not has_video)
        if self.subtitle.text():self.subtitle.raise_()

    def add_sources(self, sources, autoplay=False):
        sources = list(sources)
        self.queue.add(sources)
        self.refresh_list()
        if autoplay and sources:
            self.play_index(self.queue.items.index(normalize_source(sources[0])))

    def refresh_list(self):
        self.list.blockSignals(True)
        self.list.clear()
        for index, uri in enumerate(self.queue.items):
            item = QListWidgetItem(f'{index+1:02}   {source_title(uri)}')
            item.setData(Qt.UserRole, uri)
            item.setToolTip(uri)
            self.list.addItem(item)
        self.list.setCurrentRow(self.queue.index)
        self.list.blockSignals(False)
        self.count.setText(f'DANH SÁCH PHÁT · {len(self.queue.items)} tệp')
        self.filter_list(self.search.text())

    def filter_list(self, text):
        for row in range(self.list.count()):
            item = self.list.item(row)
            item.setHidden(text.casefold() not in item.text().casefold())

    def reordered(self, *args):
        self.queue.reorder([self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())])
        self.refresh_list()

    def play_index(self, index):
        uri = self.queue.select(index)
        if uri:
            self.queue.history.clear()
            self.queue.visited = {index}
            self.play_uri(uri)

    def save_position(self):
        if self.remember.isChecked() and self.player.source().isValid():
            if not self.pending_position and not (self.player.playbackState() == QMediaPlayer.StoppedState and self.player.position() == 0):
                write_resume(self.settings, self.player.source(), self.player.position())

    def save_session(self):
        self.save_position()
        self.settings.setValue('remember', self.remember.isChecked())
        self.settings.setValue('playlist', json.dumps(self.queue.items if self.remember.isChecked() else []))
        self.settings.setValue('index', self.queue.index)
        self.settings.sync()

    def apply_resume(self):
        if (self.pending_position and self.player.duration() > 0 and self.player.isSeekable()
                and self.player.playbackState() == QMediaPlayer.PlayingState
                and self.player.mediaStatus() in (QMediaPlayer.LoadedMedia, QMediaPlayer.BufferedMedia)):
            value = self.pending_position
            self.pending_position = 0
            if value < self.player.duration():
                self.set_position(value)

    def play_uri(self, uri):
        self.save_position()
        self.audio.reset()
        self.captions = []
        self.subtitle.clear()
        self.pending_position = 0
        if self.remember.isChecked():
            self.pending_position = read_resume(self.settings, uri)
        self.now.setText(source_title(uri))
        self.now.setToolTip(uri)
        self.music.setText('♫\n\n' + source_title(uri))
        self.player.setSource(QUrl(uri))
        self.player.play()
        QTimer.singleShot(0, self, self.apply_resume)
        self.list.setCurrentRow(self.queue.index)
        self.statusBar().showMessage('Đang mở: ' + source_title(uri))

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        elif self.player.source().isValid():
            self.player.play()
        elif self.queue.items:
            self.play_index(max(0, self.queue.index))
        else:
            self.open_files()

    def stop(self):
        self.save_session()
        self.audio.reset()
        self.player.stop()
        self.set_position(0)
        self.save_position()

    def next_track(self, direction=1, automatic=False):
        repeat = ('off', 'all', 'one')[self.repeat.currentIndex()]
        uri = self.queue.advance(direction, automatic=automatic, shuffle=self.shuffle.isChecked(), repeat=repeat)
        if uri:
            if self.player.source().toString() == uri:
                self.set_position(0)
                self.player.play()
            else:
                self.play_uri(uri)

    def media_status(self, status):
        if status in (QMediaPlayer.LoadedMedia, QMediaPlayer.BufferedMedia):
            QTimer.singleShot(0, self, self.apply_resume)
        if status == QMediaPlayer.EndOfMedia:
            self.pending_position = 0
            source=self.player.source()
            def advance_if_ended():
                if self.player.source()==source and self.player.mediaStatus()==QMediaPlayer.EndOfMedia:
                    self.next_track(1, automatic=True)
            QTimer.singleShot(self.audio.pending_milliseconds()+10,self,advance_if_ended)

    def state_changed(self, state):
        self.play_button.setText('⏸ Tạm dừng' if state == QMediaPlayer.PlayingState else '▶ Phát')
        if state == QMediaPlayer.PlayingState:
            QTimer.singleShot(0, self, self.apply_resume)
        if state == QMediaPlayer.PausedState:
            self.save_session()

    def duration_changed(self, duration):
        QTimer.singleShot(0, self, self.apply_resume)
        self.timeline.setRange(0, min(duration, 2147483647))
        self.duration_label.setText(time_label(duration))

    def position_changed(self, position):
        if not self.scrubbing:
            self.timeline.setValue(position)
            self.elapsed.setText(time_label(position))
        if self.captions:
            self.subtitle.setText(caption_text(self.captions, position - self.subtitle_offset))

    def release_seek(self):
        self.set_position(self.timeline.value())
        self.scrubbing = False

    def seek_by(self, milliseconds):
        if self.player.isSeekable():
            self.set_position(seek_target(self.player.position(), milliseconds, self.player.duration()))

    def set_position(self,value):
        self.audio.reset(value)
        self.player.setPosition(value)

    def change_rate(self,text):
        rate=float(text.rstrip('×'))
        self.audio.setRate(rate)
        self.player.setPlaybackRate(rate)

    def seekable_changed(self, value):
        QTimer.singleShot(0, self, self.apply_resume)
        self.timeline.setEnabled(value)
        for button in self.seeking_buttons:
            button.setEnabled(value)

    def set_volume(self, value):
        self.audio.setVolume(value / 100)
        self.volume_label.setText(f'{value}%')
        self.volume_label.setStyleSheet('color: #e6ff43; font-weight: 700;' if value>100 else '')

    def toggle_mute(self):
        self.audio.setMuted(not self.audio.isMuted())
        self.mute.setText('Đang tắt tiếng' if self.audio.isMuted() else 'Âm thanh')

    def open_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Mở nhạc / video', '', 'Media (' + ' '.join('*'+e for e in sorted(MEDIA_EXTENSIONS)) + ');;Tất cả (*)')
        if paths:
            self.add_sources(paths, autoplay=True)

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Chọn thư mục nhạc / video')
        if folder:
            files = sorted((p for p in Path(folder).iterdir() if p.is_file() and p.suffix.lower() in MEDIA_EXTENSIONS), key=lambda p: p.name.casefold())
            self.add_sources(files, autoplay=not self.player.source().isValid())
            self.statusBar().showMessage(f'Đã thêm {len(files)} tệp trong thư mục.')

    def open_url(self):
        url, ok = QInputDialog.getText(self, 'Mở luồng mạng', 'Địa chỉ HTTP(S) trực tiếp tới tệp / luồng hỗ trợ:')
        if ok and url.strip():
            if not url.strip().startswith(('https://', 'http://')):
                QMessageBox.warning(self, 'Địa chỉ', 'Chỉ hỗ trợ địa chỉ HTTP(S) trực tiếp, không phải trang xem video.')
                return
            self.add_sources([url.strip()], autoplay=True)

    def remove_selected(self):
        rows = [self.list.row(item) for item in self.list.selectedItems()]
        if not rows:
            return
        changed = self.queue.remove(rows)
        if changed:
            self.player.stop()
            self.player.setSource(QUrl())
            self.now.setText('Bài đang phát đã được bỏ khỏi danh sách')
        self.refresh_list()

    def clear_queue(self):
        self.save_position()
        self.player.stop()
        self.player.setSource(QUrl())
        self.queue = Playlist()
        self.captions = []
        self.subtitle.clear()
        self.now.setText('Chưa có tệp — kéo nhạc hoặc video vào cửa sổ')
        self.refresh_list()

    def sort_playlist(self):
        self.queue.reorder(sorted(self.queue.items, key=lambda uri: source_title(uri).casefold()))
        self.refresh_list()

    def load_playlist(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Mở playlist', '', 'Playlist (*.m3u *.m3u8)')
        if path:
            try:
                self.add_sources(read_playlist(path))
            except (OSError, ValueError) as error:
                QMessageBox.warning(self, 'Không mở được playlist', str(error))

    def save_playlist(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Lưu playlist', 'Danh-sach.m3u8', 'Playlist UTF-8 (*.m3u8)')
        if path:
            try:
                write_playlist(path, self.queue.items)
            except OSError as error:
                QMessageBox.warning(self, 'Không lưu được', str(error))

    def open_subtitles(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Mở phụ đề', '', 'SubRip UTF-8 (*.srt)')
        if path:
            try:
                self.captions = read_srt(path)
                self.player.setActiveSubtitleTrack(-1)
                self.position_changed(self.player.position())
            except (OSError, ValueError) as error:
                QMessageBox.warning(self, 'Phụ đề', str(error))

    def clear_subtitles(self):
        self.captions = []
        self.player.setActiveSubtitleTrack(-1)
        self.subtitle.clear()

    def embedded_text(self, text):
        if not self.captions:
            self.subtitle.setText(text)

    def subtitle_offset_dialog(self):
        value, ok = QInputDialog.getInt(self, 'Đồng bộ phụ đề', 'Độ trễ SRT (ms): dương = hiện muộn hơn', self.subtitle_offset, -60000, 60000, 100)
        if ok:
            self.subtitle_offset = value
            self.position_changed(self.player.position())

    def _track_title(self, metadata, index):
        title = metadata.value(QMediaMetaData.Key.Title)
        language = metadata.value(QMediaMetaData.Key.Language)
        return f'{index+1}: {title or language or "Luồng " + str(index+1)}'

    def choose_audio(self):
        tracks = self.player.audioTracks()
        if not tracks:
            self.statusBar().showMessage('Tệp hiện tại không có luồng âm thanh.')
            return
        choices = [self._track_title(m, i) for i, m in enumerate(tracks)]
        choice, ok = QInputDialog.getItem(self, 'Chọn âm thanh', 'Luồng:', choices, max(0, self.player.activeAudioTrack()), False)
        if ok:
            self.audio.reset(self.player.position())
            self.player.setActiveAudioTrack(choices.index(choice))

    def choose_embedded_subtitle(self):
        tracks = self.player.subtitleTracks()
        choices = ['Tắt'] + [self._track_title(m, i) for i, m in enumerate(tracks)]
        choice, ok = QInputDialog.getItem(self, 'Phụ đề trong video', 'Luồng:', choices, 0, False)
        if ok:
            self.captions = []
            self.subtitle.clear()
            self.player.setActiveSubtitleTrack(choices.index(choice)-1)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.header.show()
            self.menuBar().show()
            self.list_panel.setVisible(self.show_list.isChecked())
        else:
            self.header.hide()
            self.menuBar().hide()
            self.list_panel.hide()
            self.showFullScreen()

    def always_on_top(self, checked):
        full = self.isFullScreen()
        self.setWindowFlag(Qt.WindowStaysOnTopHint, checked)
        self.showFullScreen() if full else self.show()

    def snapshot(self):
        image = self.video.videoSink().videoFrame().toImage()
        if image.isNull():
            self.statusBar().showMessage('Chưa có khung hình video để chụp.')
            return
        path, _ = QFileDialog.getSaveFileName(self, 'Lưu khung hình gốc', 'Khung-hinh.png', 'PNG (*.png)')
        if path:
            self.statusBar().showMessage('Đã lưu khung hình: ' + path if image.save(path) else 'Không lưu được ảnh.')

    def go_to(self):
        seconds, ok = QInputDialog.getInt(self, 'Đi đến thời gian', 'Số giây từ đầu tệp:', self.player.position()//1000, 0, self.player.duration()//1000)
        if ok and self.player.isSeekable():
            self.set_position(seconds*1000)

    def update_metadata(self):
        metadata = self.player.metaData()
        resolution = metadata.value(QMediaMetaData.Key.Resolution)
        if isinstance(resolution, QSize) and resolution.width() > 0:
            label = '8K' if resolution.width() >= 7680 else '4K' if resolution.width() >= 3840 else 'Full HD' if resolution.width() >= 1920 else 'Video'
            self.quality.setText(f'{label} · {resolution.width()} × {resolution.height()}')
        else:
            self.quality.setText('ÂM NHẠC / AUDIO' if self.player.hasAudio() else 'FULL HD · 4K · 8K')

    def media_info(self):
        m = self.player.metaData()
        lines = [source_title(self.player.source().toString()), 'Thời lượng: ' + time_label(self.player.duration())]
        for name, key in [('Độ phân giải', QMediaMetaData.Key.Resolution), ('FPS', QMediaMetaData.Key.VideoFrameRate),
                          ('Codec video', QMediaMetaData.Key.VideoCodec), ('Codec âm thanh', QMediaMetaData.Key.AudioCodec)]:
            value = m.value(key)
            if value is not None:
                lines.append(name + ': ' + (f'{value.width()} × {value.height()}' if isinstance(value, QSize) else str(value)))
        lines.append(f'Luồng âm thanh: {len(self.player.audioTracks())} · Phụ đề nhúng: {len(self.player.subtitleTracks())}')
        QMessageBox.information(self, 'Thông tin tệp', '\n'.join(lines))

    def help_dialog(self):
        QMessageBox.information(self, 'Phím tắt và khả năng phát',
            'Space: phát / tạm dừng · S: dừng · N/P hoặc PageDown/PageUp: chuyển bài\n'
            '←/→: 5 giây · Ctrl+←/→: 10 giây · Alt+←/→: 30 giây\n'
            'Shift+←/→: 1 phút · Ctrl+Shift+←/→: 5 phút · Alt+Shift+←/→: 10 phút\n'
            '↑/↓: âm lượng · M: tắt tiếng · Home: về đầu\nF/F11: toàn màn hình · Esc: thoát toàn màn hình\n'
            'Delete: bỏ các mục đã chọn khỏi playlist (không xóa tệp).\n\n'
            'FFmpeg hỗ trợ nguồn Full HD / 4K / 8K. Phát 8K mượt phụ thuộc CPU/GPU, codec, bitrate và driver. '
            'Ứng dụng không tự nâng độ phân giải hoặc giải mã nội dung DRM.')

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.WindowActivate,QEvent.WindowDeactivate):
            QTimer.singleShot(0,self.subtitle,self.subtitle.position_overlay)
        if watched in (self.video, self.music) and event.type() == QEvent.MouseButtonDblClick:
            self.toggle_fullscreen()
            return True
        if event.type() == QEvent.KeyPress and QApplication.activeWindow() == self:
            focus = QApplication.focusWidget()
            if isinstance(focus, (QLineEdit, QComboBox, QSpinBox)):
                return super().eventFilter(watched, event)
            key, mods = event.key(), event.modifiers()
            if key in (Qt.Key_Left, Qt.Key_Right):
                steps = {Qt.NoModifier: 5, Qt.ControlModifier: 10, Qt.AltModifier: 30,
                         Qt.ShiftModifier: 60, Qt.ControlModifier | Qt.ShiftModifier: 300,
                         Qt.AltModifier | Qt.ShiftModifier: 600}
                if mods in steps:
                    self.seek_by(steps[mods]*1000*(1 if key == Qt.Key_Right else -1))
                    return True
            elif mods == Qt.NoModifier:
                actions = {Qt.Key_Space: self.toggle_play, Qt.Key_M: self.toggle_mute,
                           Qt.Key_N: lambda: self.next_track(1), Qt.Key_P: lambda: self.next_track(-1),
                           Qt.Key_PageDown: lambda: self.next_track(1), Qt.Key_PageUp: lambda: self.next_track(-1),
                           Qt.Key_S: self.stop, Qt.Key_F: self.toggle_fullscreen,
                           Qt.Key_Home: lambda: self.set_position(0),
                           Qt.Key_Up: lambda: self.volume.setValue(self.volume.value()+5),
                           Qt.Key_Down: lambda: self.volume.setValue(self.volume.value()-5),
                           Qt.Key_Delete: self.remove_selected}
                if key == Qt.Key_Escape and self.isFullScreen():
                    self.toggle_fullscreen()
                    return True
                if key in actions:
                    actions[key]()
                    return True
        return super().eventFilter(watched, event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = []
        for url in event.mimeData().urls():
            if url.isLocalFile() and Path(url.toLocalFile()).is_dir():
                paths.extend(p for p in sorted(Path(url.toLocalFile()).iterdir()) if p.is_file() and p.suffix.lower() in MEDIA_EXTENSIONS)
            else:
                paths.append(url.toString())
        self.add_sources(paths, autoplay=not self.player.source().isValid())
        event.acceptProposedAction()

    def restore(self):
        try:
            self.volume.setValue(max(0, min(500, int(self.settings.value('volume', 70)))))
            self.remember.setChecked(str(self.settings.value('remember', 'true')).lower() == 'true')
            if self.remember.isChecked():
                self.add_sources(json.loads(self.settings.value('playlist', '[]')))
                self.queue.select(int(self.settings.value('index', -1)))
                self.list.setCurrentRow(self.queue.index)
                if self.queue.items and 0 <= self.queue.index < len(self.queue.items):
                    self.play_uri(self.queue.items[self.queue.index])
        except (ValueError, TypeError):
            self.statusBar().showMessage('Đã bỏ qua cài đặt cũ không hợp lệ.')

    def closeEvent(self, event):
        self.subtitle.hide()
        self.resume_timer.stop()
        self.save_position()
        self.settings.setValue('volume', self.volume.value())
        self.settings.setValue('remember', self.remember.isChecked())
        self.settings.setValue('playlist', json.dumps(self.queue.items if self.remember.isChecked() else []))
        self.settings.setValue('index', self.queue.index)
        self.settings.sync()
        self.audio.reset()
        self.player.stop()
        QApplication.instance().removeEventFilter(self)
        event.accept()

    def moveEvent(self,event):
        super().moveEvent(event)
        if hasattr(self,'subtitle'):self.subtitle.position_overlay()


def main():
    if sys.platform=='win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('BachThien.MediaPlayer.Cyber')
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(ASSETS/'app-icon.ico')))
    app.setApplicationName('Thiện Media Player')
    app.setApplicationDisplayName('Thiện Media Player')
    app.setOrganizationName('BachThien')
    window = MainWindow()
    window.show()
    paths = [arg for arg in sys.argv[1:] if not arg.startswith('-')]
    if paths:
        window.add_sources(paths, autoplay=True)
    sys.exit(app.exec())
