import requests
from datetime import datetime
import pytz
from timezonefinderL import TimezoneFinder
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import openai

# ================== ВСТАВЬ СВОИ ТОКЕНЫ ==================
TELEGRAM_TOKEN = '7743697748:AAE7HC34h3pDCE8lwKsTnaF4Udm4FzW-z8w'
OPENAI_API_KEY = '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'  # ⚠️ обязательно вставь настоящий API ключ, не ссылку!
WEATHER_API_KEY = '9bb0bef8666686773ba2e7461e1eb27b'
# ==========================================================

openai.api_key = OPENAI_API_KEY

# Главное меню
main_menu = [
    [KeyboardButton("💬 GPT-чат")],
    [KeyboardButton("🕒 Время")],
    [KeyboardButton("🌦 Погода")]
]
reply_markup = ReplyKeyboardMarkup(main_menu, resize_keyboard=True)

# ===== /start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я твой помощник 🤖\nВыбери действие:",
        reply_markup=reply_markup
    )

# ===== Обработка сообщений =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "💬 GPT-чат":
        await update.message.reply_text("Напиши свой вопрос 💭")
        context.user_data["mode"] = "gpt"

    elif text == "🕒 Время":
        await update.message.reply_text("Введите город, чтобы узнать текущее время ⏰")
        context.user_data["mode"] = "time"

    elif text == "🌦 Погода":
        await update.message.reply_text("Введите город для прогноза погоды 🌦")
        context.user_data["mode"] = "weather"

    elif context.user_data.get("mode") == "gpt":
        await gpt_reply(update, text)

    elif context.user_data.get("mode") == "time":
        await send_time(update, text)

    elif context.user_data.get("mode") == "weather":
        await send_weather(update, text)

    else:
        await update.message.reply_text("Пожалуйста, выбери команду из меню 🙂")

# ===== GPT-ответ (для openai>=1.0.0) =====
async def gpt_reply(update: Update, user_text: str):
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": user_text}],
            max_tokens=500
        )
        text = response.choices[0].message.content
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"Ошибка GPT: {e}")

# ===== Текущее время =====
async def send_time(update: Update, city: str):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}"
        res = requests.get(url).json()
        if res.get('cod') != 200:
            await update.message.reply_text("❌ Город не найден. Попробуй ещё раз.")
            return
        lat = res['coord']['lat']
        lon = res['coord']['lon']

        tz = TimezoneFinder().timezone_at(lat=lat, lng=lon)
        local_time = datetime.now(pytz.timezone(tz)).strftime("%H:%M")
        await update.message.reply_text(f"⏰ Текущее время в {city}: {local_time}")

    except Exception as e:
        await update.message.reply_text(f"Ошибка при получении времени: {e}")

# ===== Погода и прогноз =====
async def send_weather(update: Update, city: str):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=ru"
        response = requests.get(url)
        data = response.json()

        if data["cod"] != "200":
            await update.message.reply_text("❌ Город не найден. Попробуй ещё раз.")
            return

        city_name = data["city"]["name"]
        country = data["city"]["country"]
        lat, lon = data["city"]["coord"]["lat"], data["city"]["coord"]["lon"]

        tz = TimezoneFinder().timezone_at(lat=lat, lng=lon)
        local_time = datetime.now(pytz.timezone(tz)).strftime("%H:%M")

        current = data["list"][0]
        temp = current["main"]["temp"]
        desc = current["weather"][0]["description"]

        forecast_text = f"📍 {city_name}, {country}\n⏰ Местное время: {local_time}\n🌡 Текущая погода: {temp}°C, {desc}\n\nПрогноз на 5 дней:\n"
        for i in range(0, len(data["list"]), 8):
            day = data["list"][i]
            date = datetime.fromtimestamp(day["dt"]).strftime("%d.%m")
            temp = day["main"]["temp"]
            desc = day["weather"][0]["description"]
            forecast_text += f"{date}: {temp}°C, {desc}\n"

        await update.message.reply_text(forecast_text)

    except Exception as e:
        await update.message.reply_text(f"Ошибка при получении погоды: {e}")

# ===== Запуск бота =====
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
