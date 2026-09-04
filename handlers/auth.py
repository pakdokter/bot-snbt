"""Registrasi user + verifikasi admin.

Alur:
1. User kirim /start → tercatat status 'pending', semua admin dapat notifikasi
   dengan tombol Approve / Tolak.
2. Admin tekan tombol → status user berubah, user dapat kabar.
3. Telegram ID yang ada di env ADMIN_IDS otomatis jadi admin approved.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from config import ADMIN_IDS
from db import queries as db

# ---------- helper ----------

def is_admin(telegram_id: int) -> bool:
    user = db.get_user(telegram_id)
    return bool(user and user["role"] == "admin" and user["status"] == "approved")


async def _notify_admins_new_user(context: ContextTypes.DEFAULT_TYPE, user_row):
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve", callback_data=f"auth:approve:{user_row['telegram_id']}"),
        InlineKeyboardButton("🚫 Tolak", callback_data=f"auth:tolak:{user_row['telegram_id']}"),
    ]])
    teks = (
        "👤 <b>Pendaftar baru</b>\n"
        f"Nama: {user_row['nama']}\n"
        f"Username: @{user_row['username'] or '-'}\n"
        f"Telegram ID: <code>{user_row['telegram_id']}</code>"
    )
    for admin_id in db.list_admin_ids():
        try:
            await context.bot.send_message(admin_id, teks, parse_mode=ParseMode.HTML, reply_markup=kb)
        except Exception:
            pass  # admin belum pernah chat bot / blokir bot


# ---------- /start ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg = update.effective_user
    user = db.get_user(tg.id)

    # Bootstrap admin dari env
    if user is None and tg.id in ADMIN_IDS:
        db.create_user(tg.id, tg.full_name, tg.username, role="admin", status="approved")
        await update.message.reply_text(
            "🔑 Kamu terdaftar sebagai admin.\n\n"
            "Perintah admin:\n"
            "/pending — daftar user menunggu verifikasi\n"
            "Kirim file soal/materi langsung ke chat ini untuk mulai intake."
        )
        return

    if user is None:
        baru = db.create_user(tg.id, tg.full_name, tg.username)
        if baru:
            await update.message.reply_text(
                "Halo! Pendaftaranmu sudah dicatat.\n"
                "Tunggu verifikasi admin dulu ya, nanti dapat notifikasi di sini."
            )
            await _notify_admins_new_user(context, baru)
        return

    if user["status"] == "pending":
        await update.message.reply_text("Pendaftaranmu masih menunggu verifikasi admin. Sabar dulu ya 🙏")
        return

    if user["status"] == "blocked":
        return  # diam saja

    # approved → serahkan ke menu utama
    from handlers.user_menu import show_main_menu
    await show_main_menu(update, context)


# ---------- callback approve/tolak ----------

async def auth_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("Khusus admin.", show_alert=True)
        return

    _, aksi, tgid = query.data.split(":")
    tgid = int(tgid)

    if aksi == "approve":
        db.set_user_status(tgid, "approved", admin_id=query.from_user.id)
        await query.edit_message_text(query.message.text_html + "\n\n✅ <b>Di-approve</b>",
                                      parse_mode=ParseMode.HTML)
        try:
            await context.bot.send_message(
                tgid, "✅ Akunmu sudah diverifikasi! Kirim /start untuk mulai.")
        except Exception:
            pass
    elif aksi == "tolak":
        db.set_user_status(tgid, "blocked", admin_id=query.from_user.id)
        await query.edit_message_text(query.message.text_html + "\n\n🚫 <b>Ditolak</b>",
                                      parse_mode=ParseMode.HTML)
    await query.answer()


# ---------- /pending ----------

async def pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    rows = db.list_users("pending")
    if not rows:
        await update.message.reply_text("Tidak ada user menunggu verifikasi.")
        return
    for r in rows:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve", callback_data=f"auth:approve:{r['telegram_id']}"),
            InlineKeyboardButton("🚫 Tolak", callback_data=f"auth:tolak:{r['telegram_id']}"),
        ]])
        await update.message.reply_text(
            f"👤 {r['nama']} (@{r['username'] or '-'})\nID: <code>{r['telegram_id']}</code>",
            parse_mode=ParseMode.HTML, reply_markup=kb,
        )


def register(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pending", pending))
    app.add_handler(CallbackQueryHandler(auth_callback, pattern=r"^auth:"))
