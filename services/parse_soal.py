"""Pecah teks hasil OCR jadi daftar soal berdasarkan pola penomoran di awal
baris ("1.", "2)", dst). Murni regex, tidak ada AI, tidak ada biaya.
"""

import re

_POLA_NOMOR = re.compile(r"^\s*(\d{1,3})[.\)]\s+", re.MULTILINE)


def split_soal(raw_text: str) -> list[str]:
    """Kalau pola penomoran terdeteksi (>=2 match), pecah per nomor.
    Kalau tidak, anggap seluruh teks adalah satu soal/blok."""
    matches = list(_POLA_NOMOR.finditer(raw_text))
    if len(matches) < 2:
        blok = raw_text.strip()
        return [blok] if blok else []

    potongan = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)
        teks = raw_text[start:end].strip()
        if teks:
            potongan.append(teks)
    return potongan
