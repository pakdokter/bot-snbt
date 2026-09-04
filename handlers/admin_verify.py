"""Verifikasi admin — sepenuhnya manual, tanpa AI/klasifikasi otomatis.

Alur untuk jenis SOAL, setelah OCR (dipicu dari admin_intake.py):
  1. Teks dipecah jadi daftar "potongan" via services.parse_soal (regex nomor).
  2. Admin pilih: semua potongan ke satu bagian yang sama, atau assign satu-satu.
  3. Admin pilih mapel → part (menu bertingkat) untuk tiap potongan/kelompok.
  4. Simpan ke tabel soal, kode otomatis, arsip ke Google Docs.

Alur untuk jenis MATERI: langsung pilih mapel → part sekali, simpan seluruh
teks sebagai satu entri materi.

callback_data:
  ver:mapel:<intake_id>:<mode>:<idx>              tampilkan daftar mapel
  ver:part:<intake_id>:<mode>:<idx>:<mapel_id>     tampilkan daftar part
  ver:save:<intake_id>:<mode>:<idx>:<part_id>      simpan & lanjut/selesai
  ver:tolak:<intake_id>                            buang intake ini
  ver:resume:<intake_id>                           buka ulang dari Antrian Verifikasi

mode: 'satu' (semua potongan ke 1 part) | 'per' (assign satu-satu) | 'materi'
idx : indeks potongan yang sedang diproses (dipakai mode 'per')
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler, ContextTypes

from db import queries as db
from handlers.auth import is_admin
from services import gdocs
from services import kode as kode_svc

POTONGAN_PREVIEW = 700  # batas karakter teks soal yang ditampilkan saat assign


def kb_mode_split(intake_id: int, n: int) -> InlineKeyboardMarkup:
    baris = [[InlineKeyboardButton(f"✅ Semua {n} soal, bagian yang sama",
                                    callback_data=f"ver:mapel:{intake_id}:satu:0")]]
    if n > 1:
        baris.append([InlineKeyboardButton("🔀 Beda-beda, assign satu per satu",
                                            callback_data=f"ver:mapel:{intake_id}:per:0")])
    baris.append([InlineKeyboardButton("❌ Batal", callback_data=f"ver:tolak:{intake_id}")])
    return InlineKeyboardMarkup(baris)


def _kb_mapel(intake_id: int, mode: str, idx: int) -> InlineKeyboardMarkup:
    rows = db.list_mapel()
    kb = [[InlineKeyboardButton(m["nama"], callback_data=f"ver:part:{intake_id}:{mode}:{idx}:{m['id']}")]
          for m in rows]
    kb.append([InlineKeyboardButton("❌ Batal", callback_data=f"ver:tolak:{intake_id}")])
    return InlineKeyboardMarkup(kb)


def _kb_part(intake_id: int, mode: str, idx: int, mapel_id: int) -> InlineKeyboardMarkup:
    rows = db.list_part(mapel_id)
    kb = [[InlineKeyboardButton(p["nama"], callback_data=f"ver:save:{intake_id}:{mode}:{idx}:{p['id']}")]
          for p in rows]
    kb.append([InlineKeyboardButton("« Pilih mapel lain", callback_data=f"ver:mapel:{intake_id}:{mode}:{idx}")])
    return InlineKeyboardMarkup(kb)


async def tampil_pilih_mapel(query_or_msg, intake_id: int, mode: str, idx: int, header: str = ""):
    teks = header + "\n\nPilih mapel:" if header else "Pilih mapel:"
    kb = _kb_mapel(intake_id, mode, idx)
    if hasattr(query_or_msg, "edit_message_text"):
        await query_or_msg.edit_message_text(teks, reply_markup=kb)
    else:
        await query_or_msg.reply_text(teks, reply_markup=kb)


def _arsip_soal(part, kode, teks_soal, soal_id):
    try:
        doc_id = gdocs.get_or_create_doc(part, "soal")
        gdocs.append_text(doc_id, f"[{kode}]\n{teks_soal}")
        db.set_soal_google_doc(soal_id, doc_id)
    except Exception:
        pass  # jangan gagalkan penyimpanan hanya karena Google Docs error


def _simpan_soal_satu(query, intake, part_id) -> str:
    part = db.get_part(part_id)
    potongan = (intake["klasifikasi_ai"] or {}).get("potongan", [])
    n = 0
    for teks_soal in potongan:
        seq = db.next_seq_soal(part_id)
        kode = kode_svc.kode_soal(part["mapel_kode"], part["kode"], seq)
        row = db.insert_soal(kode, part_id, intake["id"], teks_soal, None, None,
                              "verified", verified_by_tid=query.from_user.id)
        _arsip_soal(part, kode, teks_soal, row["id"])
        n += 1
    db.update_intake_status(intake["id"], "selesai")
    return f"✅ Tersimpan {n} soal ke {part['mapel_nama']} — {part['nama']}."


def _simpan_soal_per(query, intake, idx, part_id) -> str:
    part = db.get_part(part_id)
    potongan = (intake["klasifikasi_ai"] or {}).get("potongan", [])
    teks_soal = potongan[idx]
    seq = db.next_seq_soal(part_id)
    kode = kode_svc.kode_soal(part["mapel_kode"], part["kode"], seq)
    row = db.insert_soal(kode, part_id, intake["id"], teks_soal, None, None,
                          "verified", verified_by_tid=query.from_user.id)
    _arsip_soal(part, kode, teks_soal, row["id"])
    return kode


async def _simpan_materi(query, intake, part_id):
    part = db.get_part(part_id)
    seq = db.next_seq_materi(part_id)
    kode = kode_svc.kode_materi(part["mapel_kode"], part["kode"], seq)
    judul = f"Materi {part['nama']} #{seq}"
    row = db.insert_materi(kode, part_id, intake["id"], judul, intake["raw_text"],
                            "verified", verified_by_tid=query.from_user.id)
    try:
        doc_id = gdocs.get_or_create_doc(part, "materi")
        gdocs.append_text(doc_id, f"[{kode}] {judul}\n{intake['raw_text']}")
        db.set_materi_google_doc(row["id"], doc_id)
    except Exception:
        pass
    db.update_intake_status(intake["id"], "selesai")
    await query.edit_message_text(f"✅ Materi tersimpan dengan kode <code>{kode}</code>", parse_mode=ParseMode.HTML)


async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("Khusus admin.", show_alert=True)
        return

    data = query.data.split(":")
    aksi = data[1]
    intake_id = int(data[2])

    if aksi == "tolak":
        db.update_intake_status(intake_id, "ditolak")
        await query.edit_message_text("❌ Intake ditolak dan tidak disimpan.")
        await query.answer()
        return

    if aksi == "resume":
        intake = db.get_intake(intake_id)
        if intake["jenis"] == "materi":
            await tampil_pilih_mapel(query, intake_id, "materi", 0, "📚 Lanjutkan verifikasi materi.")
        else:
            n = len((intake["klasifikasi_ai"] or {}).get("potongan", []))
            await query.edit_message_text(
                f"📄 Terdeteksi {n} soal. Semua dari bagian yang sama?",
                reply_markup=kb_mode_split(intake_id, n))
        await query.answer()
        return

    mode, idx = data[3], int(data[4])

    if aksi == "mapel":
        intake = db.get_intake(intake_id)
        header = ""
        if mode == "per":
            potongan = (intake["klasifikasi_ai"] or {}).get("potongan", [])
            cuplikan = potongan[idx][:POTONGAN_PREVIEW]
            header = f"📝 Soal #{idx + 1}/{len(potongan)}:\n{cuplikan}"
        await _tampil_pilih_mapel(query, intake_id, mode, idx, header)

    elif aksi == "part":
        mapel_id = int(data[5])
        await query.edit_message_text("Pilih bagian:", reply_markup=_kb_part(intake_id, mode, idx, mapel_id))

    elif aksi == "save":
        part_id = int(data[5])
        intake = db.get_intake(intake_id)

        if mode == "materi":
            await _simpan_materi(query, intake, part_id)

        elif mode == "satu":
            teks = _simpan_soal_satu(query, intake, part_id)
            await query.edit_message_text(teks)

        elif mode == "per":
            kode = _simpan_soal_per(query, intake, idx, part_id)
            potongan = (intake["klasifikasi_ai"] or {}).get("potongan", [])
            idx_baru = idx + 1
            if idx_baru < len(potongan):
                cuplikan = potongan[idx_baru][:POTONGAN_PREVIEW]
                header = f"✅ Tersimpan {kode}.\n\n📝 Soal #{idx_baru + 1}/{len(potongan)}:\n{cuplikan}"
                await query.edit_message_text(header, reply_markup=_kb_mapel(intake_id, "per", idx_baru))
            else:
                db.update_intake_status(intake_id, "selesai")
                ringkas = db.count_soal_by_intake(intake_id)
                rincian = "\n".join(f"  • {r['mapel_nama']} — {r['part_nama']}: {r['jumlah']} soal"
                                    for r in ringkas)
                await query.edit_message_text(f"✅ Semua soal tersimpan:\n{rincian}")

    await query.answer()


def register(app):
    app.add_handler(CallbackQueryHandler(verify_callback, pattern=r"^ver:"))
