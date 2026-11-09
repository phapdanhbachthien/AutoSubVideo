"""Entry point for the portable Windows runtime, launched by the native EXE."""
from pathlib import Path
import os
import sys
import traceback

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root))
os.chdir(root)
logs = Path(os.getenv("LOCALAPPDATA", str(root))) / "AutoSubVideo" / "logs"
logs.mkdir(parents=True, exist_ok=True)
stream = (logs / "startup.log").open("a", encoding="utf-8", buffering=1)
sys.stdout = stream
sys.stderr = stream
try:
    from autosub.gui import main
    main()
except BaseException:
    traceback.print_exc()
    raise
