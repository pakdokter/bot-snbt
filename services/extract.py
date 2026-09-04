"""Ekstraksi teks mentah dari file yang diunggah admin — tanpa AI, tanpa biaya API.

- Foto: OCR via Tesseract (pytesseract), perlu binary `tesseract-ocr` ter-install
  di sistem (lihat Dockerfile).
- PDF: teks langsung via PyMuPDF (fitz) untuk halaman bertipe teks; halaman hasil
  scan (tanpa layer teks) dirender jadi gambar lalu di-OCR Tesseract juga.
- DOCX: baca paragraf via python-docx.
"""

import io

import fitz  # PyMuPDF
import pytesseract
from docx import Document
from PIL import Image

LANG = "ind+eng"  # butuh paket bahasa tesseract-ocr-ind + tesseract-ocr-eng


def extract_from_image_bytes(image_bytes: bytes) -> str:
    img = Image.open(io.BytesIO(image_bytes))
    return pytesseract.image_to_string(img, lang=LANG)


def extract_from_pdf(pdf_bytes: bytes) -> str:
    bagian = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    for page in doc:
        teks = page.get_text().strip()
        if teks:
            bagian.append(teks)
        else:
            # halaman kemungkinan hasil scan gambar tanpa layer teks
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            bagian.append(pytesseract.image_to_string(img, lang=LANG))
    doc.close()
    return "\n\n".join(bagian)


def extract_from_docx(docx_bytes: bytes) -> str:
    doc = Document(io.BytesIO(docx_bytes))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
