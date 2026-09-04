"""Menu Manage Bot (khusus admin).

Aktif sekarang : Kelola User, Statistik.
Placeholder    : Upload, Antrian Verifikasi, Bank Soal, Kelola Materi,
                 Kunci & Pembahasan (hidup di batch intake).
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler, ContextTypes

from db import queries as db
from handlers.auth import is_admin

BELUM_AKTIF = "⏳ Fitur ini menyusul di batch intake."


def _kb_home():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Upload Soal", callback_data="adm:upload:soal"),
         InlineKeyboardButton("📤 Upload Materi", callback_data="adm:upload:materi")],
        [InlineKeyboardButton("🔎 Antrian Verifikasi", callback_data="adm:verif")],
        [InlineKeyboardButton("🗂 Bank Soal", callback_data="adm:bank"),
         InlineKeyboardButton("📚 Kelola Materi", callback_data="adm:materi")],
        [InlineKeyboardButton("🔑 Kunci & Pembahasan", callback_data="adm:kunci")],
        [InlineKeyboardButton("👥 Kelola User", callback_data="adm:user")],
        [InlineKeyboardButton("📊 Statistik", callback_data="adm:stat")],
        [InlineKeyboardButton("« Menu Utama", callback_data="menu:home")],
    ])


async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teks = "🛠 <b>Manage Bot</b>\nPilih yang mau dikelola:"
    if update.callback_query:
        await update.callback_query.edit_message_text(
            teks, parse_mode=ParseMode.HTML, reply_markup=_kb_home())
    else:
        await update.message.reply_text(
            teks, parse_mode=ParseMode.HTML, reply_markup=_kb_home())


# ---------- Kelola User ----------

def _kb_user_home():
    n_pending = len(db.list_users("pending"))
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"⏳ Menunggu verifikasi ({n_pending})",
                              callback_data="adm:user:pending")],
        [InlineKeyboardButton("✅ User aktif", callback_data="adm:user:approved")],
        [InlineKeyboardButton("🚫 Diblokir", callback_data="adm:user:blocked")],
        [InlineKeyboardButton("« Manage Bot", callback_data="adm:home")],
    ])


async def _tampil_daftar_user(query, context, status: str):
    rows = db.list_users(status)
    if not rows:
        await query.answer("Kosong.", show_alert=True)
        return
    label = {"pending": "⏳ Menunggu", "approved": "✅ Aktif", "blocked": "🚫 Diblokir"}[status]
    await query.message.reply_text(f"{label}: {len(rows)} user")
    for r in rows[:30]:  # batasi biar tidak banjir
        if status == "pending":
            tombol = [
                InlineKeyboardButton("✅ Approve", callback_data=f"auth:approve:{r['telegram_id']}"),
                InlineKeyboardButton("🚫 Tolak", callback_data=f"auth:tolak:{r['telegram_id']}"),
            ]
        elif status == "approved":
            tombol = [InlineKeyboardButton("🚫 Blokir", callback_data=f"auth:tolak:{r['telegram_id']}")]
        else:  # blocked
            tombol = [InlineKeyboardButton("✅ Aktifkan lagi", callback_data=f"auth:approve:{r['telegram_id']}")]
        peran = " 🔑admin" if r["role"] == "admin" else ""
        await query.message.reply_text(
            f"👤 {r['nama']} (@{r['username'] or '-'}){peran}\n"
            f"ID: <code>{r['telegram_id']}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([tombol]),
        )


# ---------- Statistik ----------

async def _tampil_statistik(query):
    s = db.get_stats()
    per_mapel = "\n".join(
        f"  • {r['nama']}: {r['jumlah']} soal" for r in s["soal_per_mapel"]
    ) or "  (belum ada soal)"
    teks = (
        "📊 <b>Statistik</b>\n\n"
        f"👥 User aktif: {s['user_approved']}\n"
        f"⏳ Menunggu verifikasi: {s['user_pending']}\n\n"
        f"🗂 Bank soal (verified): {s['soal_verified']}\n"
        f"{per_mapel}\n\n"
        f"🔑 Soal tanpa kunci: {s['soal_tanpa_kunci']}\n"
        f"♻️ Variasi dibuat: {s['jumlah_variasi']}\n"
        f"📄 Paket PDF terkirim: {s['jumlah_paket']}\n"
        f"📚 Materi (verified): {s['materi_verified']}"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("« Manage Bot", callback_data="adm:home")]])
    await query.edit_message_text(teks, parse_mode=ParseMode.HTML, reply_markup=kb)


# ---------- router ----------

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("Khusus admin.", show_alert=True)
        return

    data = query.data.split(":")
    aksi = data[1]

    if aksi == "home":
        await show_admin_menu(update, context)

    elif aksi == "user":
        if len(data) == 2:
            await query.edit_message_text(
                "👥 <b>Kelola User</b>", parse_mode=ParseMode.HTML,
                reply_markup=_kb_user_home())
        else:
            await _tampil_daftar_user(query, context, data[2])

    elif aksi == "stat":
        await _tampil_statistik(query)

    elif aksi in ("upload", "verif", "bank", "materi", "kunci"):
        await query.answer(BELUM_AKTIF, show_alert=True)

    await query.answer()


def register(app):
    app.add_handler(CallbackQueryHandler(admin_callback, pattern=r"^adm:"))
