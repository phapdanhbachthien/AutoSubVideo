"""Run on the destination Windows machine to verify native imports and Tcl/Tk."""
from pathlib import Path
import importlib
import json
import os
import platform
import sys
import traceback

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root))
os.chdir(root)
os.environ.setdefault("TCL_LIBRARY", str(root / "python/tcl/tcl8.6"))
os.environ.setdefault("TK_LIBRARY", str(root / "python/tcl/tk8.6"))
report = {"platform": platform.platform(), "python": sys.version, "checks": {}}
for name in ("tkinter", "numpy", "onnxruntime", "soundfile", "sea_g2p", "tokenizers", "rapidocr", "cv2", "faster_whisper", "ctranslate2", "av", "edge_tts", "autosub.gui"):
    try:
        importlib.import_module(name)
        report["checks"][name] = "passed"
    except Exception:
        report["checks"][name] = traceback.format_exc()
try:
    import tkinter
    window = tkinter.Tk()
    window.withdraw()
    window.update()
    window.destroy()
    report["checks"]["Tcl/Tk display"] = "passed"
except Exception:
    report["checks"]["Tcl/Tk display"] = traceback.format_exc()
try:
    from autosub.resources import default_bundle, verify_bundle
    from autosub.speech import list_voices
    report["verified_tts_files"] = verify_bundle(default_bundle())
    report["original_voices"] = [v.id for v in list_voices("local", default_bundle())]
except Exception:
    report["checks"]["original bundle"] = traceback.format_exc()
path = root / "diagnostics.json"
path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=True, indent=2))
print("Saved: " + str(path))
sys.exit(1 if any(v != "passed" for v in report["checks"].values()) else 0)
