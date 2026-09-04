import os

BOT_TOKEN = os.environ["BOT_TOKEN"]
DATABASE_URL = os.environ["DATABASE_URL"]
GOOGLE_CREDS_JSON = os.environ.get("GOOGLE_CREDS_JSON", "")

# Bootstrap admin: Telegram ID di sini otomatis jadi admin approved saat /start pertama.
# Isi di Railway: ADMIN_IDS=123456789 (pisahkan koma kalau lebih dari satu)
ADMIN_IDS = {int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()}
