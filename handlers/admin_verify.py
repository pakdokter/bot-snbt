"""Verifikasi admin atas hasil klasifikasi AI (dipicu dari admin_intake.py
setelah ekstraksi+klasifikasi selesai, atau dibuka ulang dari Antrian
Verifikasi di Manage Bot).

callback_data:
  ver:ok:<intake_id>                      konfirmasi, commit ke bank soal
  ver:tolak:<intake_id>                   buang intake ini
  ver:mapel:<intake_id>                   mulai revisi mapel (hanya per_part)
  ver:setmapel:<intake_id>:<mapel_id>     pilih mapel baru → lanjut pilih part
  ver:setpart:<intake_id>:<part_id>       pilih part baru → update & tampil ulang
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler, ContextTypes

from db import queries as db
from handlers.auth import is_admin
from services import gdocs
from services import kode as kode_svc


def ringkasan_teks(intake_id: int, hasil: dict) -> str:
    conf = round((hasil.get("confidence") or 0) * 100)

    if "potongan" in hasil:  # jenis soal
        potongan = hasil.get("potongan") or []
        if hasil.get("tipe_sumber") == "ujian_full":
            per_part = {}
            for p in potongan:
                k = f"{p.get('mapel_kode')}-{p.get('part_kode')}"
                per_part[k] = per_part.get(k, 0) + 1
            rincian = "\n".join(f"  • {k}: {v} soal" for k, v in per_part.items())
            return (
                f"📦 <b>Terdeteksi: Paket Ujian Full</b> (confidence {conf}%)\n"
                f"Total {len(potongan)} soal, tersebar di:\n{rincian}\n\n"
                "Konfirmasi untuk memecah dan menyimpan ke masing-masing bagian? "
                "Klasifikasi tiap soal dipercayakan ke AI; kalau ada yang salah "
                "kelompok bisa direvisi belakangan lewat Bank Soal."
            )
        mapel_kode = potongan[0]["mapel_kode"] if potongan else "?"
        part_kode = potongan[0]["part_kode"] if potongan else "?"
        return (
            f"📄 Terdeteksi: <b>{mapel_kode} / {part_kode}</b> (confidence {conf}%)\n"
            f"Jumlah soal terdeteksi: {len(potongan)}\n\n"
            "Konfirmasi klasifikasi ini?"
        )

    # jenis materi
    return (
        f"📄 Terdeteksi materi: <b>{hasil.get('mapel_kode')} / {hasil.get('part_kode')}</b> "
        f"(confidence {conf}%)\n\nKonfirmasi klasifikasi ini?"
    )


def kb_verifikasi(intake_id: int, hasil: dict) -> InlineKeyboardMarkup:
    baris = [[InlineKeyboardButton("✅ Konfirmasi", callback_data=f"ver:ok:{intake_id}")]]
    if hasil.get("tipe_sumber") != "ujian_full":
        baris.append([InlineKeyboardButton("✏️ Ubah Mapel/Part", callback_data=f"ver:mapel:{intake_id}")])
    baris.append([InlineKeyboardButton("❌ Tolak", callback_data=f"ver:tolak:{intake_id}")])
    return InlineKeyboardMarkup(baris)


async def _simpan_soal(query, intake, hasil):
    potongan = hasil.get("potongan") or []
    if not potongan:
        potongan = [{"mapel_kode": hasil.get("mapel_kode"), "part_kode": hasil.get("part_kode"),
                     "teks_soal": intake["raw_text"], "opsi": None, "kunci": None}]

    ringkasan = {}
    dilewati = 0
    for p in potongan:
        mapel = db.find_mapel_by_kode(p.get("mapel_kode"))
        part = db.find_part_by_kode(mapel["id"], p.get("part_kode")) if mapel else None
        if not mapel or not part:
            dilewati += 1
            continue
        seq = db.next_seq_soal(part["id"])
        kode = kode_svc.kode_soal(mapel["kode"], part["kode"], seq)
        row = db.insert_soal(kode, part["id"], intake["id"], p["teks_soal"], p.get("opsi"),
                              p.get("kunci"), "verified", verified_by_tid=query.from_user.id)
        try:
            doc_id = gdocs.get_or_create_doc({**part, "mapel_nama": mapel["nama"]}, "soal")
            gdocs.append_text(doc_id, f"[{kode}]\n{p['teks_soal']}")
            db.set_soal_google_doc(row["id"], doc_id)
        except Exception:
            pass  # jangan gagalkan penyimpanan hanya karena Google Docs error
        key = f"{mapel['nama']} — {part['nama']}"
        ringkasan[key] = ringkasan.get(key, 0) + 1

    db.update_intake_status(intake["id"], "selesai")
    teks = "✅ Tersimpan ke bank soal:\n" + "\n".join(f"  • {k}: {v} soal" for k, v in ringkasan.items())
    if dilewati:
        teks += f"\n\n⚠️ {dilewati} soal dilewati (mapel/part tidak dikenali)."
    await query.edit_message_text(teks)


async def _simpan_materi(query, intake, hasil):
    mapel = db.find_mapel_by_kode(hasil.get("mapel_kode"))
    part = db.find_part_by_kode(mapel["id"], hasil.get("part_kode")) if mapel else None
    if not mapel or not part:
        await query.edit_message_text("⚠️ Mapel/part tidak dikenali, tidak bisa disimpan. Coba Ubah Mapel/Part dulu.")
        return

    seq = db.next_seq_materi(part["id"])
    kode = kode_svc.kode_materi(mapel["kode"], part["kode"], seq)
    judul = f"Materi {part['nama']} #{seq}"
    row = db.insert_materi(kode, part["id"], intake["id"], judul, intake["raw_text"],
                            "verified", verified_by_tid=query.from_user.id)
    try:
        doc_id = gdocs.get_or_create_doc({**part, "mapel_nama": mapel["nama"]}, "materi")
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

    elif aksi == "ok":
        intake = db.get_intake(intake_id)
        hasil = intake["klasifikasi_ai"]
        if intake["jenis"] == "materi":
            await _simpan_materi(query, intake, hasil)
        else:
            await _simpan_soal(query, intake, hasil)

    elif aksi == "mapel":
        rows = db.list_mapel()
        kb = [[InlineKeyboardButton(m["nama"], callback_data=f"ver:setmapel:{intake_id}:{m['id']}")]
              for m in rows]
        await query.edit_message_text("Pilih mapel yang benar:", reply_markup=InlineKeyboardMarkup(kb))

    elif aksi == "setmapel":
        mapel_id = int(data[3])
        rows = db.list_part(mapel_id)
        kb = [[InlineKeyboardButton(p["nama"], callback_data=f"ver:setpart:{intake_id}:{p['id']}")]
              for p in rows]
        await query.edit_message_text("Pilih bagian yang benar:", reply_markup=InlineKeyboardMarkup(kb))

    elif aksi == "setpart":
        part_id = int(data[3])
        part = db.get_part(part_id)
        intake = db.get_intake(intake_id)
        hasil = intake["klasifikasi_ai"]
        if "potongan" in hasil:
            hasil["tipe_sumber"] = "per_part"
            for p in (hasil.get("potongan") or []):
                p["mapel_kode"] = part["mapel_kode"]
                p["part_kode"] = part["kode"]
            if not hasil.get("potongan"):
                hasil["potongan"] = [{"mapel_kode": part["mapel_kode"], "part_kode": part["kode"],
                                       "teks_soal": intake["raw_text"], "opsi": None, "kunci": None}]
        else:
            hasil["mapel_kode"] = part["mapel_kode"]
            hasil["part_kode"] = part["kode"]
        db.update_intake_klasifikasi(intake_id, hasil, hasil.get("tipe_sumber", "per_part"), "menunggu_admin")
        await query.edit_message_text(ringkasan_teks(intake_id, hasil), parse_mode=ParseMode.HTML,
                                       reply_markup=kb_verifikasi(intake_id, hasil))

    await query.answer()


def register(app):
    app.add_handler(CallbackQueryHandler(verify_callback, pattern=r"^ver:"))
