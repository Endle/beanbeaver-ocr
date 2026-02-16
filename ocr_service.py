"""OCR service using PaddleOCR - runs inside container."""

import io
import logging
import sys

import numpy as np
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from paddleocr import PaddleOCR
from PIL import Image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Receipt OCR Service")


def _parse_required_port_arg(argv: list[str]) -> int:
    """Require explicit --port argument when service starts."""
    for idx, arg in enumerate(argv):
        if arg == "--port":
            if idx + 1 >= len(argv):
                raise RuntimeError("Missing value for required '--port' argument.")
            try:
                return int(argv[idx + 1])
            except ValueError as exc:
                raise RuntimeError(
                    "Invalid '--port' value. Expected an integer."
                ) from exc
        if arg.startswith("--port="):
            raw_value = arg.split("=", 1)[1]
            try:
                return int(raw_value)
            except ValueError as exc:
                raise RuntimeError(
                    "Invalid '--port' value. Expected an integer."
                ) from exc
    raise RuntimeError(
        "ocr_service requires explicit '--port <number>' in the startup command."
    )


SERVER_PORT = _parse_required_port_arg(sys.argv)

# Load model once at startup
logger.info("Loading PaddleOCR model...")
ocr = PaddleOCR(use_textline_orientation=True, lang='en',
                device="cpu",
                ocr_version="PP-OCRv5")
logger.info("PaddleOCR model loaded")


@app.post("/ocr")
async def perform_ocr(file: UploadFile = File(...)):
    """
    Perform OCR on uploaded image.

    Returns raw PaddleOCR results with text and bounding boxes.
    Result format: List of detections, where each detection is:
        [bbox, (text, confidence)]
        - bbox: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]] in pixels
        - text: detected text string
        - confidence: float between 0 and 1
    """
    contents = await file.read()

    # Load image via PIL and convert to numpy array
    image = Image.open(io.BytesIO(contents)).convert("RGB")
    img_array = np.array(image)
    image_height, image_width = img_array.shape[:2]

    # Run OCR
    result = ocr.ocr(img_array)

    # Convert to JSON-serializable format
    detections = []
    try:
        # PaddleOCR 3.x returns generator of OCRResult objects
        result_list = list(result)  # Consume generator
        print(f"DEBUG: result_list length: {len(result_list)}", flush=True)

        for i, ocr_result in enumerate(result_list):
            print(f"DEBUG: OCRResult[{i}] type: {type(ocr_result)}", flush=True)
            print(f"DEBUG: OCRResult[{i}] keys: {list(ocr_result.keys())}", flush=True)

            # It's a dict-like object, check for OCR data keys
            for key in ocr_result.keys():
                val = ocr_result[key]
                val_type = type(val).__name__
                if isinstance(val, (list, tuple)) and len(val) > 0:
                    print(f"DEBUG:   {key}: {val_type} len={len(val)}, first={type(val[0]).__name__}", flush=True)
                elif hasattr(val, 'shape'):
                    print(f"DEBUG:   {key}: {val_type} shape={val.shape}", flush=True)
                elif isinstance(val, dict):
                    print(f"DEBUG:   {key}: {val_type} keys={list(val.keys())[:5]}", flush=True)
                else:
                    print(f"DEBUG:   {key}: {val_type} = {repr(val)[:100]}", flush=True)

            # Try dict access for OCR results
            boxes = ocr_result.get('dt_polys') or ocr_result.get('boxes') or ocr_result.get('rec_boxes')
            texts = ocr_result.get('rec_texts') or ocr_result.get('texts')
            scores = ocr_result.get('rec_scores') or ocr_result.get('scores')

            print(f"DEBUG: boxes={boxes is not None}, texts={texts is not None}, scores={scores is not None}", flush=True)

            if boxes is not None and texts is not None and scores is not None:
                for bbox, text, conf in zip(boxes, texts, scores):
                    # Convert numpy arrays to lists
                    if hasattr(bbox, 'tolist'):
                        bbox = bbox.tolist()
                    detections.append([bbox, [text, float(conf)]])

        print(f"DEBUG: Total detections: {len(detections)}", flush=True)
    except Exception as e:
        print(f"DEBUG ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()

    # Return raw PaddleOCR results with image dimensions
    return JSONResponse(
        {
            "status": "success",
            "image_width": image_width,
            "image_height": image_height,
            "detections": detections,
        }
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "model": "paddleocr",
        "internal_port": SERVER_PORT,
    }
