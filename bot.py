import logging

from telegram.ext import Application

from config import BOT_TOKEN
from handlers import admin_menu, auth, user_menu

logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    auth.register(app)
    user_menu.register(app)
    admin_menu.register(app)
    # batch berikutnya:
    # admin_intake.register(app)
    # admin_verify.register(app)
    # admin_kunci.register(app)

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
