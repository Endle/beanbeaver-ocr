FROM python:3.12-slim
# https://pypi.org/project/paddlepaddle/ only supports 3.8-3.12

WORKDIR /app

# Install system dependencies for PaddleOCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Disable oneDNN and PIR executor to avoid PaddlePaddle 3.x compatibility issues
ENV FLAGS_use_mkldnn=0
ENV FLAGS_enable_pir_api=0
ENV FLAGS_enable_pir_in_executor=0

# Install Python dependencies
# https://github.com/PaddlePaddle/PaddleOCR/discussions/17350#discussioncomment-15545906
RUN pip install --no-cache-dir paddlepaddle==3.2.0
RUN pip install --no-cache-dir paddleocr==3.3.0

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    python-multipart \
    pillow


# Download models on build (avoids download on first request)
RUN FLAGS_use_mkldnn=0 FLAGS_enable_pir_api=0 FLAGS_enable_pir_in_executor=0 \
    python -c "from paddleocr import PaddleOCR; PaddleOCR(use_textline_orientation=True, lang='en', ocr_version='PP-OCRv5')"

#RUN ls
COPY ocr_service.py .

ENV BEANBEAVER_OCR_INTERNAL_PORT=8000

EXPOSE ${BEANBEAVER_OCR_INTERNAL_PORT}

CMD ["sh", "-c", "uvicorn ocr_service:app --host 0.0.0.0 --port ${BEANBEAVER_OCR_INTERNAL_PORT}"]
