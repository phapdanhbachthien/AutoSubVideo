"""Read burned-in captions with the original bundle's ONNX OCR models."""
from functools import lru_cache
from pathlib import Path
from difflib import SequenceMatcher
import math
import re
import hashlib
import json

from .core import Cue


@lru_cache(maxsize=1)
def ocr_engine(bundle, model="universal"):
    from rapidocr import RapidOCR
    from rapidocr.utils.typings import OCRVersion, ModelType
    models = Path(bundle).resolve() / "ocr/rapidocr/models"
    names = {"Det": "PP-OCRv6_det_small.onnx", "Rec": "PP-OCRv6_rec_small.onnx", "Cls": "ch_ppocr_mobile_v2.0_cls_mobile.onnx"}
    params = {"Global.log_level": "error", "EngineConfig.onnxruntime.intra_op_num_threads": 2,
              "EngineConfig.onnxruntime.inter_op_num_threads": 1}
    for key, name in names.items():
        path = models / name
        if not path.is_file():
            raise ValueError("Thiếu mô hình OCR gốc. Chạy scripts/import-resources.py trước: " + name)
        params[key + ".model_path"] = str(path)
    model_root = Path(bundle) / "ocr/recognition-models"
    manifest = model_root / "manifest.json"
    if manifest.is_file():
        entries = json.loads(manifest.read_text())["models"]
        if model not in entries:
            raise ValueError("Không tìm thấy bộ nhận dạng OCR: " + model)
        spec = entries[model]
        rec_path = model_root / spec["file"]
        with rec_path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != spec["sha256"]:
                raise ValueError("Mô hình nhận dạng OCR không khớp SHA-256.")
        params["Rec.model_path"] = str(rec_path.resolve())
        params["Rec.ocr_version"] = OCRVersion("PP-OCRv6" if model.startswith("universal") else "PP-OCRv4")
        params["Rec.model_type"] = ModelType({"universal": "small", "universal_medium": "medium", "compact": "mobile", "quality": "server"}[model])
    return RapidOCR(params=params)


def extract_captions(video, bundle, *, interval=.5, top=.65, model="universal", correct_typos=False, log=print, engine=None):
    import cv2
    if not math.isfinite(interval) or not .1 <= interval <= 5 or not 0 <= top < .95:
        raise ValueError("OCR: khoảng lấy mẫu từ 0,1–5 giây; vùng bắt đầu từ 0–94% chiều cao.")
    engine = engine if engine is not None else ocr_engine(str(Path(bundle).resolve()), model)
    corrections = {}
    if correct_typos:
        dictionary = Path(bundle) / "reference/runtime/resources/backend/configs/typoMap.json"
        if dictionary.is_file():
            corrections = json.loads(dictionary.read_text(encoding="utf-8-sig"))
            if not isinstance(corrections, dict) or not all(isinstance(k, str) and k and isinstance(v, str) for k, v in corrections.items()):
                raise ValueError("Từ điển sửa OCR không hợp lệ.")
    capture = cv2.VideoCapture(str(Path(video).resolve()))
    if not capture.isOpened():
        raise ValueError("Không mở được video để OCR.")
    fps, frames = capture.get(cv2.CAP_PROP_FPS), capture.get(cv2.CAP_PROP_FRAME_COUNT)
    if not fps or not math.isfinite(fps) or frames <= 0:
        capture.release()
        raise ValueError("Không xác định được thời lượng video.")
    duration = frames / fps
    cues = []
    active = None
    active_score = 0
    try:
        for index in range(math.ceil(duration / interval)):
            stamp = index * interval
            capture.set(cv2.CAP_PROP_POS_MSEC, stamp * 1000)
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Không đọc được khung hình tại {stamp:.2f}s; OCR chưa hoàn tất.")
            result = engine(frame[int(frame.shape[0] * top):])
            texts = list(getattr(result, "txts", None) or [])
            scores = list(getattr(result, "scores", None) or [])
            boxes = getattr(result, "boxes", None)
            rows = []
            for i, (text, score) in enumerate(zip(texts, scores)):
                if score >= .5 and str(text).strip():
                    y = float(boxes[i][:, 1].mean()) if boxes is not None else i
                    x = float(boxes[i][:, 0].mean()) if boxes is not None else 0
                    rows.append((y, x, str(text).strip(), float(score)))
            rows.sort(key=lambda row: (round(row[0] / 15), row[1]))
            text = "\n".join(row[2] for row in rows)
            for wrong, replacement in corrections.items():
                text = text.replace(wrong, replacement)
            score = sum(row[3] for row in rows) / len(rows) if rows else 0
            end = min(duration, stamp + interval)
            normalized = lambda s: re.sub(r"\s+", "", s).casefold()
            same = active is not None and text and SequenceMatcher(None, normalized(active.text), normalized(text)).ratio() >= .9
            if same:
                active = Cue(active.start, end, text if score > active_score else active.text)
                active_score = max(active_score, score)
            else:
                if active:
                    cues.append(active)
                active = Cue(stamp, end, text) if text else None
                active_score = score
            if index % max(1, round(5 / interval)) == 0:
                log(f"OCR {stamp:.1f}/{duration:.1f}s — {len(cues)} câu.")
        if active:
            cues.append(active)
    finally:
        capture.release()
    if not cues:
        raise ValueError("OCR không tìm thấy phụ đề trong vùng quét. Thử mở rộng vùng hoặc tăng chất lượng hình.")
    return cues
