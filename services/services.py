"""Ekstraksi teks mentah dari file yang diunggah admin.

- Foto: OCR via Claude vision.
- PDF: teks langsung via pdfplumber; halaman hasil scan (tanpa layer teks)
  di-fallback ke OCR Claude vision per halaman.
- DOCX: baca paragraf via python-docx.
"""

import base64
import io

import anthropic
import pdfplumber
from docx import Document

from config import ANTHROPIC_API_KEY

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

OCR_PROMPT = (
    "Ini adalah scan/foto naskah soal atau materi ujian (UTBK/SNBT/Ujian Mandiri) "
    "berbahasa Indonesia. Baca dan tuliskan ulang SELURUH teks yang terlihat, apa "
    "adanya: nomor soal, teks soal, pilihan jawaban (A-E), dan kunci jawaban/"
    "pembahasan jika ada. Jangan meringkas, jangan menambah komentar apa pun di "
    "luar isi naskah. Jika ada tabel/gambar pendukung soal, deskripsikan singkat "
    "dalam tanda kurung siku, misal [gambar: grafik fungsi kuadrat]."
)


def extract_from_image(image_bytes: bytes, media_type: str = "image/jpeg") -> str:
    b64 = base64.b64encode(image_bytes).decode()
    resp = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                {"type": "text", "text": OCR_PROMPT},
            ],
        }],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


def extract_from_pdf(pdf_bytes: bytes) -> str:
    bagian = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            teks = page.extract_text() or ""
            if teks.strip():
                bagian.append(teks)
            else:
                # halaman kemungkinan hasil scan gambar tanpa layer teks
                gambar = page.to_image(resolution=200).original
                buf = io.BytesIO()
                gambar.save(buf, format="PNG")
                bagian.append(extract_from_image(buf.getvalue(), "image/png"))
    return "\n\n".join(bagian)


def extract_from_docx(docx_bytes: bytes) -> str:
    doc = Document(io.BytesIO(docx_bytes))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
