from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes
)
import os
from dotenv import load_dotenv
import datetime
import aiosqlite
import re

GROUP_CHAT_ID = int(os.getenv("CHAT_ID"))  # Укажи ID своей группы в .env

# 👋 Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
   await update.message.reply_text(
    "**👋 Я 𝗦𝗼𝘃𝗲𝘁𝗻𝗶𝗸𝗠𝗡 — помощник сообщества.**\n\n"
    "📌 *Команды:*\n"
    "`/add_birthday ДД.ММ` — добавить день рождения\n"
    "`/my_birthday` — узнать дату и сколько дней осталось\n"
    "`/del_birthday` — удалить дату\n"
    "`/birthdays` — список всех участников\n"
    "`/create_event Название ДД.ММ ЧЧ:ММ` — создать событие\n"
    "`/join_event Название` — присоединиться к событию\n"
    "`/events` — список предстоящих событий\n"
    "`/event Название` — участники события\n\n"
    "_𝐛𝐲 𝐠𝐫𝐚𝐟𝐨𝐧𝐢𝐮𝐦 𝐰𝐢𝐭𝐡 𝐥𝐨𝐯𝐞_ ❤️",
    parse_mode="Markdown"
)

# 🎂 Добавление дня рождения (одна дата + проверка)
async def add_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Используйте формат: /add_birthday ДД.ММ")

    date = context.args[0]

    # Строгая проверка формата даты
    if not re.match(r"^(0[1-9]|[12][0-9]|3[01])\.(0[1-9]|1[0-2])$", date):
        return await update.message.reply_text("❌ Неверный формат. Пример: 05.11")

    user_id = update.message.from_user.id
    username = update.message.from_user.full_name

    async with aiosqlite.connect("data.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS birthdays (user_id INTEGER PRIMARY KEY, name TEXT, date TEXT)")
        async with db.execute("SELECT date FROM birthdays WHERE user_id = ?", (user_id,)) as cursor:
            existing = await cursor.fetchone()
            if existing:
                return await update.message.reply_text("📌 У вас уже сохранена дата.\nИспользуйте /del_birthday для удаления.")

        await db.execute("INSERT INTO birthdays (user_id, name, date) VALUES (?, ?, ?)", (user_id, username, date))
        await db.commit()

    await update.message.reply_text(f"🎉 День рождения {date} сохранён!")

# 📅 Просмотр своей даты + сколько дней осталось
async def my_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    today = datetime.datetime.now()

    async with aiosqlite.connect("data.db") as db:
        async with db.execute("SELECT date FROM birthdays WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return await update.message.reply_text("❌ День рождения не найден. Используйте /add_birthday")

            date_str = row[0]
            bday_this_year = datetime.datetime.strptime(f"{date_str}.{today.year}", "%d.%m.%Y")
            if bday_this_year < today:
                bday_next = bday_this_year.replace(year=today.year + 1)
            else:
                bday_next = bday_this_year

            days_left = (bday_next - today).days
            await update.message.reply_text(f"📅 Ваш день рождения: {date_str}\nДо него осталось {days_left} дней 🎈")

# 🗑 Удаление дня рождения
async def delete_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    async with aiosqlite.connect("data.db") as db:
        await db.execute("DELETE FROM birthdays WHERE user_id = ?", (user_id,))
        await db.commit()
    await update.message.reply_text("🗑 Дата дня рождения удалена.")

# 🎂 Список всех дней рождений
async def all_birthdays(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with aiosqlite.connect("data.db") as db:
        async with db.execute("SELECT name, date FROM birthdays") as cursor:
            rows = await cursor.fetchall()
            if not rows:
                return await update.message.reply_text("😶 Пока никто не добавил день рождения.")
            msg = "🎂 Дни рождения участников:\n"
            for name, date in rows:
                msg += f"• {name} — {date}\n"
            await update.message.reply_text(msg)

# 📅 Создание события (только для админов)
async def create_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.effective_chat.type
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if chat_type not in ["group", "supergroup"]:
        return await update.message.reply_text("🚫 Команда доступна только в группе.")

    admins = await context.bot.get_chat_administrators(chat_id)
    is_admin = any(admin.user.id == user_id for admin in admins)

    if not is_admin:
        return await update.message.reply_text("🚫 Только админ может создавать события.")

    if len(context.args) < 3:
        return await update.message.reply_text("Пример: /create_event Кино 10.07 20:00")

    name, date, time = context.args[0], context.args[1], context.args[2]

    async with aiosqlite.connect("data.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS events (name TEXT, date TEXT, time TEXT)")
        await db.execute("INSERT INTO events (name, date, time) VALUES (?, ?, ?)", (name, date, time))
        await db.commit()

    await context.bot.send_message(chat_id, f"📌 Событие: {name} — {date} в {time}\nПрисоединяйтесь через /join_event {name}")

# ✅ Присоединение к событию или список доступных
async def join_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        async with aiosqlite.connect("data.db") as db:
            async with db.execute("SELECT name, date, time FROM events") as cursor:
                rows = await cursor.fetchall()
                if not rows:
                    return await update.message.reply_text("Нет предстоящих событий.")
                msg = "📅 Доступные события:\n"
                for name, date, time in rows:
                    msg += f"• {name} — {date} в {time}\n"
                msg += "\nДля участия: /join_event Название"
                return await update.message.reply_text(msg)

    event_name = context.args[0]
    user_id = update.message.from_user.id
    username = update.message.from_user.full_name

    async with aiosqlite.connect("data.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS participants (event TEXT, user_id INTEGER, name TEXT)")
        await db.execute("INSERT INTO participants (event, user_id, name) VALUES (?, ?, ?)", (event_name, user_id, username))
        await db.commit()

    await update.message.reply_text(f"✅ Вы присоединились к событию: {event_name}!")

# 📋 Список событий — только будущие
async def list_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now()
    year = now.year

    async with aiosqlite.connect("data.db") as db:
        async with db.execute("SELECT name, date, time FROM events") as cursor:
            rows = await cursor.fetchall()

        upcoming = []
        for name, date_str, time_str in rows:
            try:
                # Обработка времени
                time_clean = time_str.strip()
                if len(time_clean) == 5:
                    time_clean += ":00"  # → 23:30 → 23:30:00

                # Подставляем текущий год для обработки полной даты
                event_dt = datetime.datetime.strptime(f"{date_str}.{year} {time_clean}", "%d.%m.%Y %H:%M:%S")

                if event_dt >= now:
                    upcoming.append((name, date_str, time_str))
                else:
                    # Удаляем событие, если оно прошло
                    await db.execute(
                        "DELETE FROM events WHERE name = ? AND date = ? AND time = ?",
                        (name, date_str, time_str)
                    )
            except Exception as e:
                print(f"⚠️ Ошибка при обработке события '{name}':", e)

        await db.commit()

    if not upcoming:
        return await update.message.reply_text("😕 Нет предстоящих событий.")

    msg = "📅 Предстоящие события:\n"
    for name, date, time in upcoming:
        msg += f"• {name} — {date} в {time}\n"
    await update.message.reply_text(msg)
    
# команда проверки численности и конкретных участников, присоденившихся к конкретному евенту
async def event_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Укажите название события: /event Название")

    event_name = context.args[0]
    now = datetime.datetime.now()
    year = now.year

    async with aiosqlite.connect("data.db") as db:
        # Проверка: существует ли событие и оно в будущем
        async with db.execute("SELECT date, time FROM events WHERE name = ?", (event_name,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return await update.message.reply_text(f"❌ Событие '{event_name}' не найдено.")

            date_str, time_str = row
            time_clean = time_str.strip()
            if len(time_clean) == 5:
                time_clean += ":00"

            try:
                event_dt = datetime.datetime.strptime(f"{date_str}.{year} {time_clean}", "%d.%m.%Y %H:%M:%S")
                if event_dt < now:
                    return await update.message.reply_text(f"🕓 Событие '{event_name}' уже прошло.")
            except Exception as e:
                print(f"⚠️ Ошибка при проверке события '{event_name}':", e)
                return await update.message.reply_text("❌ Невозможно обработать дату события.")

        # Получение участников
        async with db.execute("SELECT name FROM participants WHERE event = ?", (event_name,)) as cursor:
            participants = await cursor.fetchall()

    count = len(participants)

    if count == 0:
        return await update.message.reply_text(f"👥 К событию '{event_name}' пока никто не присоединился.")

    msg = f"👥 Участники события '{event_name}' ({count} чел.):\n"
    for (name,) in participants:
        msg += f"• {name}\n"

    await update.message.reply_text(msg)

# Загружаем переменные из .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_birthday", add_birthday))
    app.add_handler(CommandHandler("my_birthday", my_birthday))
    app.add_handler(CommandHandler("del_birthday", delete_birthday))
    app.add_handler(CommandHandler("birthdays", all_birthdays))
    app.add_handler(CommandHandler("create_event", create_event))
    app.add_handler(CommandHandler("join_event", join_event))
    app.add_handler(CommandHandler("events", list_events))
    app.add_handler(CommandHandler("event", event_members))

    print("🤖 SovetnikMN запущен...")
    app.run_polling()

main()
