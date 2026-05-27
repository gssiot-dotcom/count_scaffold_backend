# myapp/utils/detect_ai.py

import os
import uuid
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "best1.pt")

# =========================
# 🔥 파이프 개수 보정 함수
# =========================
def estimate_pipe_count(objects):
    import numpy as np  # ✅ 여기서 import

    pipe_boxes = [o for o in objects if o["label"] == "IQA950"]

    if len(pipe_boxes) < 3:
        return len(pipe_boxes)

    widths, heights = [], []

    for o in pipe_boxes:
        b = o["bbox"]
        widths.append(b["x2"] - b["x1"])
        heights.append(b["y2"] - b["y1"])

    avg_w = np.mean(widths)
    avg_h = np.mean(heights)
    single_area = avg_w * avg_h

    platform = next((o for o in objects if o["label"] == "Platform"), None)
    if not platform:
        return len(pipe_boxes)

    pb = platform["bbox"]
    total_area = (pb["x2"] - pb["x1"]) * (pb["y2"] - pb["y1"])

    estimated = int(total_area / single_area * 0.9)
    return max(estimated, len(pipe_boxes))


# =========================
# 메인 AI 추론 함수
# =========================
def detect_ai(file, run_yolo=True, run_ocr=False):
    import torch
    import numpy as np
    from ultralytics import YOLO
    from .ocr_runner import run_ocr

    model = YOLO("best1.pt")

    temp_path = f"temp_{uuid.uuid4().hex}_{file.name}"

    try:
        with open(temp_path, "wb+") as dest:
            for chunk in file.chunks():
                dest.write(chunk)

        result = {
            "summary": {},
            "objects": [],
            "texts": []
        }

        if run_yolo:
            with torch.no_grad():
                results = model.predict(temp_path, conf=0.25)

            res = results[0]

            cls_indices = res.boxes.cls.cpu().numpy().astype(int)
            labels = [res.names[c] for c in cls_indices]
            result["summary"] = dict(Counter(labels))

            boxes = res.boxes.xyxy.cpu().numpy()
            confs = res.boxes.conf.cpu().numpy()

            for i, ((x1, y1, x2, y2), conf, cls) in enumerate(
                zip(boxes, confs, cls_indices)
            ):
                result["objects"].append({
                    "id": i,
                    "label": res.names[int(cls)],
                    "confidence": float(conf),
                    "bbox": {
                        "x1": int(x1), "y1": int(y1),
                        "x2": int(x2), "y2": int(y2)
                    }
                })

            result["summary"]["IQA950_estimated"] = estimate_pipe_count(
                result["objects"]
            )

        if run_ocr:
            result["texts"] = run_ocr(temp_path)

        return result

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
