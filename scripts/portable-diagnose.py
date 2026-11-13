from pathlib import Path
import json
import os
import platform
import sys
import traceback

root=Path(__file__).resolve().parent
sys.path.insert(0,str(root))
os.chdir(root)
os.environ.setdefault('QT_MEDIA_BACKEND','ffmpeg')
os.environ.setdefault('QT_PLUGIN_PATH',str(root/'python/Lib/site-packages/PySide6/plugins'))
report={'platform':platform.platform(),'python':sys.version}
try:
    import PySide6
    from PySide6.QtWidgets import QApplication
    from PySide6.QtMultimedia import QMediaPlayer,QMediaFormat,QAudioOutput
    from player.app import MainWindow
    app=QApplication([])
    report['qt']=PySide6.__version__
    report['video_codecs']=[str(c) for c in QMediaFormat().supportedVideoCodecs(QMediaFormat.Decode)]
    report['audio_codecs']=[str(c) for c in QMediaFormat().supportedAudioCodecs(QMediaFormat.Decode)]
    report['native_imports']='passed'
except Exception:
    report['error']=traceback.format_exc()
path=root/'diagnostics.json'
path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True,indent=2))
sys.exit(1 if 'error' in report else 0)
