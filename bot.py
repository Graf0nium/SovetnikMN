import asyncio
import os
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")


async def start(update, context):
    await update.message.reply_text("Привет! Я работаю без run_polling()!")


async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    print("Бот запущен")
    await app.updater.wait_until_closed()
    await app.stop()
    await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
