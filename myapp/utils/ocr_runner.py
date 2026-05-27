# myapp/utils/ocr_runner.py

_ocr_model = None


def run_ocr(img_path):
    """
    PaddleOCR을 이용해 이미지에서 텍스트 추출
    - Django 시작 시 paddle import 방지
    - OCR 모델 1회만 로드 (캐싱)
    - 에러 발생 시 서버 죽지 않게 빈 리스트 반환
    """
    global _ocr_model

    try:
        from paddleocr import PaddleOCR
    except ImportError:
        # paddle 미설치 환경에서도 Django 동작하게
        return []

    # OCR 모델 최초 1회만 생성
    if _ocr_model is None:
        _ocr_model = PaddleOCR(
            use_angle_cls=True,
            lang="korean",
            show_log=False
        )

    try:
        result = _ocr_model.ocr(img_path, cls=True)
    except Exception:
        # OCR 실행 중 에러 → 서버 보호
        return []

    texts = []

    if result and result[0]:
        for line in result[0]:
            coords = line[0]
            text_info = line[1]

            x_coords = [c[0] for c in coords]
            y_coords = [c[1] for c in coords]

            texts.append({
                "text": text_info[0],
                "confidence": float(text_info[1]),
                "bbox": {
                    "x1": int(min(x_coords)),
                    "y1": int(min(y_coords)),
                    "x2": int(max(x_coords)),
                    "y2": int(max(y_coords)),
                }
            })

    return texts
