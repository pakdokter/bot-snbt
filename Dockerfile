FROM python:3.13-slim

# tesseract-ocr = mesin OCR gratis, ind/eng = paket bahasa Indonesia & Inggris
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-ind \
    tesseract-ocr-eng \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["python", "bot.py"]
