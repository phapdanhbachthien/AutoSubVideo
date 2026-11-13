from pathlib import Path
import os
import sys
import traceback

root=Path(__file__).resolve().parent
sys.path.insert(0,str(root))
os.chdir(root)
os.environ.setdefault('QT_MEDIA_BACKEND','ffmpeg')
os.environ.setdefault('QT_PLUGIN_PATH',str(root/'python/Lib/site-packages/PySide6/plugins'))
logs=Path(os.getenv('LOCALAPPDATA',str(root)))/'ThienMediaPlayer/logs'
logs.mkdir(parents=True,exist_ok=True)
stream=(logs/'startup.log').open('a',encoding='utf-8',buffering=1)
sys.stdout=stream
sys.stderr=stream
try:
    from player.app import main
    main()
except BaseException:
    traceback.print_exc()
    raise
