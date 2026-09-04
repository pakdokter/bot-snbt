"""Terima file dari admin (dipicu setelah admin menekan tombol Upload Soal/
Upload Materi di Manage Bot, yang menyetel context.user_data['upload_jenis']),
ekstrak teksnya, klasifikasikan, lalu serahkan ke admin_verify untuk
ditampilkan sebagai kartu verifikasi.
"""

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

from db import queries as db
from handlers.admin_verify import kb_verifikasi, ringkasan_teks
from handlers.auth import is_admin
from services import classify, extract


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
        media_type = "image/jpeg"
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
        media_type = "image/png" if nama.endswith(".png") else "image/jpeg"
    else:
        return

    status_msg = await msg.reply_text("⏳ Mengunduh & mengekstrak teks...")
    file_bytes = bytes(await tg_file.download_as_bytearray())

    intake = db.create_intake(update.effective_user.id, jenis, file_type, file_id_tg)

    try:
        if file_type == "foto":
            raw_text = extract.extract_from_image(file_bytes, media_type)
        elif file_type == "pdf":
            raw_text = extract.extract_from_pdf(file_bytes)
        else:
            raw_text = extract.extract_from_docx(file_bytes)
    except Exception as e:
        await status_msg.edit_text(f"❌ Gagal ekstraksi teks: {e}")
        db.update_intake_status(intake["id"], "ditolak")
        return

    if not raw_text.strip():
        await status_msg.edit_text("❌ Tidak ada teks yang terbaca dari file ini.")
        db.update_intake_status(intake["id"], "ditolak")
        return

    db.update_intake_raw(intake["id"], raw_text)
    await status_msg.edit_text("⏳ Mengklasifikasikan...")

    try:
        hasil = classify.klasifikasi(jenis, raw_text)
    except Exception as e:
        await status_msg.edit_text(f"❌ Gagal klasifikasi: {e}")
        db.update_intake_status(intake["id"], "ditolak")
        return

    tipe_sumber = hasil.get("tipe_sumber", "per_part")
    db.update_intake_klasifikasi(intake["id"], hasil, tipe_sumber, "menunggu_admin")

    await status_msg.edit_text(
        ringkasan_teks(intake["id"], hasil),
        parse_mode=ParseMode.HTML,
        reply_markup=kb_verifikasi(intake["id"], hasil),
    )


def register(app):
    app.add_handler(CommandHandler("batal", batal))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, terima_file))
