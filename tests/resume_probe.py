"""A fresh application process for each side of an actual shutdown/restart."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import time
from PySide6.QtCore import QSettings, QUrl
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from player.app import MainWindow

app = QApplication([])
app.setQuitOnLastWindowClosed(False)
settings_path, mode, source, target = sys.argv[1:5]
target = int(target)
w = MainWindow(QSettings(settings_path,QSettings.IniFormat))
w.show()

def until(condition):
    end = time.monotonic()+15
    while time.monotonic()<end:
        app.processEvents()
        if condition():
            return
        QTest.qWait(20)
    raise AssertionError(f'{mode}: position={w.player.position()}, pending={w.pending_position}, error={w.player.errorString()}')

try:
    if mode == 'save':
        if w.player.source().isEmpty():
            w.add_sources([source],autoplay=True)
        until(lambda:w.player.isSeekable() and w.player.position()>=200)
        w.player.pause()
        w.set_position(target)
        QTest.qWait(200)
        assert abs(w.player.position()-target)<1000
    else:
        until(lambda:target-1000<=w.player.position()<=target+2500)
        assert w.player.source().toString(QUrl.FullyEncoded)==QUrl.fromLocalFile(source).toString(QUrl.FullyEncoded)
        QTest.qWait(250)
        assert w.player.position()>=target-1000
finally:
    w.close()
    app.processEvents()
print('Shutdown/restart phase passed',mode,target)
