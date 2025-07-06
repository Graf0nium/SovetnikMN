# 📦 Используем официальный образ Python 3.10
FROM python:3.10

# 🗂 Папка внутри контейнера
WORKDIR /app

# 📂 Копируем все файлы проекта
COPY . /app

# 📡 Обновляем pip + ставим зависимости
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 🚀 Запуск Telegram-бота
CMD ["python", "bot.py"]
