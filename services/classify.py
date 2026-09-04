"""Klasifikasi hasil ekstraksi via Claude API.

Untuk jenis='soal': model SELALU memecah teks jadi array `potongan` per soal
(baik uploadnya satu part maupun ujian full campuran), tiap potongan punya
klasifikasi mapel/part sendiri. Ini menyederhanakan alur simpan: baik
per_part maupun ujian_full sama-sama disimpan dari array potongan.

Untuk jenis='materi': tidak dipecah, cukup satu mapel_kode + part_kode
untuk keseluruhan dokumen.
"""

import json

import anthropic

from config import ANTHROPIC_API_KEY
from db import queries as db

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _taksonomi_text() -> str:
    baris = []
    for m in db.list_mapel():
        parts = db.list_part(m["id"])
        daftar = ", ".join(f"{p['kode']}={p['nama']}" for p in parts)
        baris.append(f"- {m['kode']} ({m['nama']}): {daftar}")
    return "\n".join(baris)


def _parse_json(teks: str) -> dict:
    teks = teks.strip()
    if teks.startswith("```"):
        teks = teks.split("```")[1]
        if teks.startswith("json"):
            teks = teks[4:]
    return json.loads(teks.strip())


def klasifikasi(jenis: str, raw_text: str) -> dict:
    taksonomi = _taksonomi_text()

    if jenis == "materi":
        prompt = f"""Kamu membantu admin bank soal UTBK/SNBT/Ujian Mandiri mengklasifikasikan MATERI belajar yang baru diunggah.

Daftar mata pelajaran dan bagian (kode=nama):
{taksonomi}

Teks hasil ekstraksi:
\"\"\"
{raw_text[:12000]}
\"\"\"

Tentukan mapel_kode dan part_kode yang paling cocok dari daftar di atas, dan confidence 0-1.
Balas HANYA dengan JSON valid, tanpa penjelasan, tanpa markdown fence:
{{"mapel_kode": "...", "part_kode": "...", "confidence": 0.0}}"""
    else:
        prompt = f"""Kamu membantu admin bank soal UTBK/SNBT/Ujian Mandiri mengklasifikasikan SOAL yang baru diunggah.

Daftar mata pelajaran dan bagian (kode=nama):
{taksonomi}

Teks hasil ekstraksi:
\"\"\"
{raw_text[:12000]}
\"\"\"

Tugasmu:
1. Pecah teks menjadi array "potongan", satu elemen per nomor soal.
2. Untuk tiap soal tentukan: mapel_kode, part_kode (paling cocok dari daftar),
   teks_soal (teks soal utuh apa adanya), opsi (objek {{"A":"...","B":"..."}} atau
   null jika bukan pilihan ganda), kunci (huruf kunci jawaban HANYA jika tertulis
   eksplisit di naskah, kalau tidak ada isi null — jangan menebak/mengerjakan sendiri).
3. Tentukan tipe_sumber: "per_part" jika semua soal berasal dari satu part yang sama,
   "ujian_full" jika soal tersebar di lebih dari satu part/mapel berbeda.
4. Beri confidence 0-1 untuk keseluruhan klasifikasi.

Balas HANYA dengan JSON valid, tanpa penjelasan, tanpa markdown fence:
{{
  "tipe_sumber": "per_part" atau "ujian_full",
  "confidence": 0.0,
  "potongan": [
    {{"mapel_kode": "...", "part_kode": "...", "teks_soal": "...", "opsi": null, "kunci": null}}
  ]
}}"""

    resp = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}],
    )
    teks = "".join(b.text for b in resp.content if b.type == "text")
    return _parse_json(teks)
