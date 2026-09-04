"""Terima file dari admin (dipicu setelah admin menekan tombol Upload Soal/
Upload Materi di Manage Bot, yang menyetel context.user_data['upload_jenis']),
OCR/ekstrak teksnya (tanpa AI, lihat services/extract.py), lalu serahkan ke
admin_verify untuk dipilih mapel/part-nya secara manual.
"""

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

from db import queries as db
from handlers.admin_verify import kb_mode_split, tampil_pilih_mapel
from handlers.auth import is_admin
from services import extract, parse_soal


async def batal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.pop("upload_jenis", None):
        await update.message.reply_text("Dibatalkan.")


async def terima_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    jenis = context.user_data.pop("upload_jenis", None)
    if not jenis:
        return  # admin kirim file di luar alur upload, abaikan

    msg = update.message

    if msg.photo:
        file_type = "foto"
        tg_file = await msg.photo[-1].get_file()
        file_id_tg = msg.photo[-1].file_id
    elif msg.document:
        nama = (msg.document.file_name or "").lower()
        if nama.endswith(".pdf"):
            file_type = "pdf"
        elif nama.endswith(".docx"):
            file_type = "docx"
        elif nama.endswith((".jpg", ".jpeg", ".png")):
            file_type = "foto"
        else:
            await msg.reply_text("Format tidak didukung. Kirim foto, PDF, atau DOCX.")
            return
        tg_file = await msg.document.get_file()
        file_id_tg = msg.document.file_id
    else:
        return

    status_msg = await msg.reply_text("⏳ Mengunduh & OCR (bisa 10-30 detik untuk file besar)...")
    file_bytes = bytes(await tg_file.download_as_bytearray())

    intake = db.create_intake(update.effective_user.id, jenis, file_type, file_id_tg)

    try:
        if file_type == "foto":
            raw_text = extract.extract_from_image_bytes(file_bytes)
        elif file_type == "pdf":
            raw_text = extract.extract_from_pdf(file_bytes)
        else:
            raw_text = extract.extract_from_docx(file_bytes)
    except Exception as e:
        await status_msg.edit_text(f"❌ Gagal ekstraksi teks: {e}")
        db.update_intake_status(intake["id"], "ditolak")
        return

    if not raw_text.strip():
        await status_msg.edit_text(
            "❌ Tidak ada teks yang terbaca dari file ini. Kalau ini scan tulisan "
            "tangan atau kualitas foto buram, OCR gratis (Tesseract) sering gagal baca — "
            "coba foto ulang lebih jelas, atau ketik manual.")
        db.update_intake_status(intake["id"], "ditolak")
        return

    db.update_intake_raw(intake["id"], raw_text)

    if jenis == "materi":
        db.update_intake_klasifikasi(intake["id"], {}, "manual", "menunggu_admin")
        await status_msg.edit_text("📚 Teks berhasil diekstrak.")
        await tampil_pilih_mapel(status_msg, intake["id"], "materi", 0,
                                  f"Panjang teks: {len(raw_text)} karakter.")
        return

    # jenis soal: pecah berdasarkan pola penomoran
    potongan = parse_soal.split_soal(raw_text)
    db.update_intake_klasifikasi(intake["id"], {"potongan": potongan}, "manual", "menunggu_admin")
    await status_msg.edit_text(
        f"📄 Teks diekstrak. Terdeteksi <b>{len(potongan)} soal</b> berdasarkan pola "
        "penomoran. Kalau jumlah ini kelihatan salah (misal soal tidak diberi nomor "
        "di naskah aslinya), semua tetap bisa disimpan sebagai satu blok.\n\n"
        "Semua soal ini dari bagian yang sama?",
        parse_mode="HTML",
        reply_markup=kb_mode_split(intake["id"], len(potongan)),
    )


def register(app):
    app.add_handler(CommandHandler("batal", batal))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, terima_file))
