"""Menu user (approved): Soal/Materi → Mapel → Part.

Navigasi sudah jalan penuh. Aksi terakhir (generate variasi + PDF) masih
placeholder, diisi di batch berikutnya (services/variasi.py + pdf_render.py).
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from db import queries as db


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Latihan Soal", callback_data="menu:soal")],
        [InlineKeyboardButton("📚 Materi", callback_data="menu:materi")],
    ])
    teks = "Mau latihan soal atau baca materi?"
    if update.callback_query:
        await update.callback_query.edit_message_text(teks, reply_markup=kb)
    else:
        await update.message.reply_text(teks, reply_markup=kb)


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = db.get_user(query.from_user.id)
    if not user or user["status"] != "approved":
        await query.answer("Akunmu belum diverifikasi.", show_alert=True)
        return

    data = query.data.split(":")
    # menu:<jenis>                      → pilih mapel
    # menu:<jenis>:<mapel_id>           → pilih part
    # menu:<jenis>:<mapel_id>:<part_id> → eksekusi
    # menu:home                         → kembali ke awal

    if data[1] == "home":
        await show_main_menu(update, context)
        await query.answer()
        return

    jenis = data[1]  # 'soal' | 'materi'

    if len(data) == 2:
        rows = db.list_mapel()
        kb = [[InlineKeyboardButton(m["nama"], callback_data=f"menu:{jenis}:{m['id']}")]
              for m in rows]
        kb.append([InlineKeyboardButton("« Kembali", callback_data="menu:home")])
        await query.edit_message_text(
            f"Pilih mata pelajaran ({'soal' if jenis == 'soal' else 'materi'}):",
            reply_markup=InlineKeyboardMarkup(kb))

    elif len(data) == 3:
        mapel_id = int(data[2])
        rows = db.list_part(mapel_id)
        kb = [[InlineKeyboardButton(p["nama"], callback_data=f"menu:{jenis}:{mapel_id}:{p['id']}")]
              for p in rows]
        kb.append([InlineKeyboardButton("« Kembali", callback_data=f"menu:{jenis}")])
        await query.edit_message_text("Pilih bagian:", reply_markup=InlineKeyboardMarkup(kb))

    elif len(data) == 4:
        part_id = int(data[3])
        part = db.get_part(part_id)
        # TODO batch berikutnya:
        #   jenis == 'soal'   → ambil soal random verified, generate variasi, render PDF, kirim
        #   jenis == 'materi' → kirim materi verified untuk part ini
        await query.edit_message_text(
            f"✅ Kamu memilih: {part['mapel_nama']} — {part['nama']}\n\n"
            "⏳ Fitur generate belum aktif di versi ini.")

    await query.answer()


def register(app):
    app.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^menu:"))
