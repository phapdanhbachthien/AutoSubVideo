"""Generate a real offline sample for every preset in the original bundle."""
from pathlib import Path
import argparse
import json
import sys
import time
import wave

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from autosub.resources import default_bundle, original_catalog
from autosub.speech import SpeechSettings, preview


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", default=default_bundle())
    parser.add_argument("--output", required=True)
    parser.add_argument("--precision", choices=("fp32", "int8"), default="fp32")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for name in original_catalog(args.bundle)["presets"]:
        started = time.monotonic()
        path = output / (name + ".wav")
        try:
            preview("Xin chào, chúc bạn một ngày tốt lành.", path,
                    SpeechSettings("local", name, 0, args.bundle, args.precision))
            with wave.open(str(path)) as audio:
                duration = audio.getnframes() / audio.getframerate()
                if duration < .2 or not any(audio.readframes(audio.getnframes())):
                    raise ValueError("Empty or silent output")
            result = dict(name=name, status="passed", seconds=duration, elapsed=round(time.monotonic() - started, 2))
        except Exception as exc:
            result = dict(name=name, status="failed", error=str(exc))
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        (output / "report.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.exit(1 if any(r["status"] != "passed" for r in results) else 0)
