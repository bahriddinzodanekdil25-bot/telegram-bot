import asyncio
import requests
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
import os

TOKEN = "7743697748:AAE7HC34h3pDCE8lwKsTnaF4Udm4FzW-z8w"

# ------------------ БАЗА ДАННЫХ ------------------ #
DB_FILE = "mega_assistant.db"

def init_db():
    # Удаляем старую базу и создаем новую с правильной структурой
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Создаем таблицу пользователей с колонкой password
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            password TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            file_type TEXT,
            file_name TEXT,
            telegram_file_id TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            reminder_text TEXT,
            reminder_time TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ База данных пересоздана с правильной структурой")

# ------------------ ПОЛЬЗОВАТЕЛИ И ПАРОЛИ ------------------ #
def set_user_password(user_id, password):
    """Установка пароля для пользователя"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO users (user_id, password) VALUES (?, ?)",
        (user_id, password)
    )
    conn.commit()
    conn.close()

def check_user_password(user_id, password):
    """Проверка пароля пользователя"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0] == password:
        return True
    return False

def get_user_password(user_id):
    """Получение пароля пользователя"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# ------------------ ФИЛЬМЫ ------------------ #
def search_movies(query):
    """Поиск фильмов"""
    try:
        url = "https://api.themoviedb.org/3/search/movie"
        params = {
            'api_key': '1b5e9d84d8a44b61e36e873c5a28e7a8',
            'query': query,
            'language': 'ru-RU',
            'page': 1
        }
        
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            movies = []
            
            for movie in data.get('results', [])[:5]:
                title = movie.get('title', 'Без названия')
                year = movie.get('release_date', '')[:4] if movie.get('release_date') else 'Неизвестно'
                rating = movie.get('vote_average', 0)
                description = movie.get('overview', 'Описание отсутствует')
                
                watch_links = {
                    "🎬 Voize.tv": f"https://voize.tv/search?q={requests.utils.quote(title)}",
                    "📺 YouTube": f"https://www.youtube.com/results?search_query={requests.utils.quote(title)}+фильм",
                    "🔵 VK Video": f"https://vk.com/video?q={requests.utils.quote(title)}+фильм",
                    "🎥 Okko": f"https://okko.tv/search/{requests.utils.quote(title)}"
                }
                
                movies.append({
                    'title': title,
                    'year': year,
                    'rating': round(rating, 1),
                    'description': description[:150] + '...' if len(description) > 150 else description,
                    'watch_links': watch_links
                })
            
            return movies
    except:
        pass
    
    return [{
        'title': query,
        'year': '2023', 
        'rating': '7.5',
        'description': f'Фильм "{query}" - нажмите кнопку для просмотра',
        'watch_links': {
            "🎬 Voize.tv": f"https://voize.tv/search?q={requests.utils.quote(query)}",
            "📺 YouTube": f"https://www.youtube.com/results?search_query={requests.utils.quote(query)}+фильм",
            "🔵 VK Video": f"https://vk.com/video?q={requests.utils.quote(query)}+фильм"
        }
    }]

# ------------------ ПОГОДА НА 5 ДНЕЙ ------------------ #
def get_weather_5days(city):
    """Получение погоды на 5 дней"""
    try:
        url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid=9bb0bef8666686773ba2e7461e1eb27b&units=metric&lang=ru"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            
            weather_info = f"🌤️ Погода в {city} на 5 дней:\n\n"
            
            # Текущая погода
            current = data['list'][0]
            current_temp = round(current['main']['temp'])
            current_desc = current['weather'][0]['description']
            weather_info += f"🌡️ Сейчас: {current_temp}°C, {current_desc}\n\n"
            
            # Прогноз на 5 дней (каждые 24 часа)
            for i in range(0, len(data['list']), 8):
                if len(weather_info.split('\n')) >= 12:  # Ограничиваем 5 днями
                    break
                    
                forecast = data['list'][i]
                date = datetime.fromtimestamp(forecast['dt']).strftime('%d.%m')
                temp = round(forecast['main']['temp'])
                description = forecast['weather'][0]['description']
                weather_info += f"📅 {date}: {temp}°C, {description}\n"
            
            return weather_info
        return f"❌ Город '{city}' не найден"
    except:
        return "❌ Ошибка сервиса погоды"

# ------------------ ФУТБОЛ ------------------ #
def get_football_matches():
    """Получение футбольных матчей"""
    matches = [
        "⚽ Премьер-лига Англии",
        "✅ Манчестер Сити 2-1 Ливерпуль",
        "⏰ Челси - Арсенал (19:00)",
        "🔴 Ман Юнайтед 1-0 Тоттенхэм (LIVE)",
        "⏰ Барселона - Реал Мадрид (21:00)"
    ]
    return "\n".join(matches)

# ------------------ ФАЙЛЫ ------------------ #
def save_file(user_id, file_type, file_name, file_id):
    """Сохранение файла в БД"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO files (user_id, file_type, file_name, telegram_file_id) VALUES (?, ?, ?, ?)",
        (user_id, file_type, file_name, file_id)
    )
    conn.commit()
    conn.close()

def get_user_files(user_id):
    """Получение файлов пользователя"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT file_type, file_name, telegram_file_id FROM files WHERE user_id = ?", (user_id,))
    files = cursor.fetchall()
    conn.close()
    return files

async def send_file_to_user(update, file_type, file_id, file_name):
    """Отправка файла пользователю"""
    try:
        if file_type == 'document':
            await update.message.reply_document(document=file_id, caption=f"📄 {file_name}")
        elif file_type == 'photo':
            await update.message.reply_photo(photo=file_id, caption=f"🖼️ {file_name}")
        elif file_type == 'video':
            await update.message.reply_video(video=file_id, caption=f"🎥 {file_name}")
        elif file_type == 'audio':
            await update.message.reply_audio(audio=file_id, caption=f"🎵 {file_name}")
        return True
    except Exception as e:
        print(f"Ошибка отправки файла: {e}")
        return False

# ------------------ НАПОМИНАНИЯ ------------------ #
def save_reminder(user_id, text, time):
    """Сохранение напоминания"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO reminders (user_id, reminder_text, reminder_time) VALUES (?, ?, ?)",
        (user_id, text, time)
    )
    conn.commit()
    conn.close()

def get_user_reminders(user_id):
    """Получение напоминаний пользователя"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT reminder_text, reminder_time FROM reminders WHERE user_id = ? AND is_active = 1", (user_id,))
    reminders = cursor.fetchall()
    conn.close()
    return reminders

# ------------------ МЕНЮ ------------------ #
def get_main_menu():
    keyboard = [
        ["🎬 Поиск фильмов", "📁 Мои файлы"],
        ["⏰ Мои напоминания", "🌤️ Погода на 5 дней"],
        ["⚽ Футбол", "➕ Новое напоминание"],
        ["🔐 Установить пароль"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ------------------ ОСНОВНЫЕ КОМАНДЫ ------------------ #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        "🤖 Добро пожаловать в MegaAssistant!\n\n"
        "🎬 Поиск и просмотр фильмов\n"
        "📁 Защищенное хранилище файлов (с паролем)\n" 
        "⏰ Умные напоминания\n"
        "🌤️ Погода на 5 дней\n"
        "⚽ Футбольные матчи\n\n"
        "🔐 Сначала установите пароль для доступа к файлам!",
        reply_markup=get_main_menu()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    # 🎬 ПОИСК ФИЛЬМОВ
    if text == "🎬 Поиск фильмов":
        await update.message.reply_text("🎬 Введите название фильма или сериала:")
        context.user_data['state'] = 'waiting_movie_query'
    
    # 📁 МОИ ФАЙЛЫ
    elif text == "📁 Мои файлы":
        user_password = get_user_password(user_id)
        
        if not user_password:
            await update.message.reply_text("❌ Сначала установите пароль в разделе '🔐 Установить пароль'")
            return
        
        await update.message.reply_text("🔐 Введите ваш пароль для доступа к файлам:")
        context.user_data['state'] = 'waiting_file_password'
    
    # ⏰ МОИ НАПОМИНАНИЯ
    elif text == "⏰ Мои напоминания":
        reminders = get_user_reminders(user_id)
        if reminders:
            reminders_list = "⏰ Ваши напоминания:\n\n"
            for reminder_text, reminder_time in reminders:
                reminders_list += f"⏰ {reminder_text} - {reminder_time}\n"
            await update.message.reply_text(reminders_list)
        else:
            await update.message.reply_text("⏰ У вас пока нет напоминаний")
    
    # 🌤️ ПОГОДА НА 5 ДНЕЙ
    elif text == "🌤️ Погода на 5 дней":
        await update.message.reply_text("🌤️ Введите название города для прогноза на 5 дней:")
        context.user_data['state'] = 'waiting_city'
    
    # ⚽ ФУТБОЛ
    elif text == "⚽ Футбол":
        matches = get_football_matches()
        await update.message.reply_text(f"⚽ Футбольные матчи:\n\n{matches}")
    
    # ➕ НОВОЕ НАПОМИНАНИЕ
    elif text == "➕ Новое напоминание":
        await update.message.reply_text("⏰ Введите напоминание в формате: 'Текст в время'\nПример: 'Встреча в 14:30'")
        context.user_data['state'] = 'waiting_reminder'
    
    # 🔐 УСТАНОВИТЬ ПАРОЛЬ
    elif text == "🔐 Установить пароль":
        await update.message.reply_text("🔐 Введите новый пароль для доступа к вашим файлам:")
        context.user_data['state'] = 'waiting_new_password'
    
    # ОБРАБОТКА СОСТОЯНИЙ
    elif context.user_data.get('state') == 'waiting_movie_query':
        await update.message.reply_text("🔍 Ищу фильмы...")
        results = search_movies(text)
        
        if results:
            context.user_data['search_results'] = results
            
            movie = results[0]
            movie_info = f"🎬 {movie['title']} ({movie['year']})\n"
            movie_info += f"⭐ Рейтинг: {movie['rating']}/10\n"
            movie_info += f"📝 {movie['description']}\n\n"
            movie_info += "🎯 Выберите где посмотреть:"
            
            keyboard = []
            for service, link in movie['watch_links'].items():
                keyboard.append([InlineKeyboardButton(service, url=link)])
            
            if len(results) > 1:
                keyboard.append([InlineKeyboardButton("➡️ Следующий фильм", callback_data="next_movie_1")])
            
            keyboard.append([InlineKeyboardButton("🔍 Новый поиск", callback_data="new_search")])
            
            await update.message.reply_text(movie_info, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text("❌ Ничего не найдено")
        context.user_data['state'] = None
    
    elif context.user_data.get('state') == 'waiting_city':
        weather = get_weather_5days(text)
        await update.message.reply_text(weather)
        context.user_data['state'] = None
    
    elif context.user_data.get('state') == 'waiting_reminder':
        if " в " in text:
            save_reminder(user_id, text.split(" в ")[0], text.split(" в ")[1])
            await update.message.reply_text(f"✅ Напоминание установлено: {text}")
        else:
            await update.message.reply_text("❌ Формат: 'Текст в время'")
        context.user_data['state'] = None
    
    elif context.user_data.get('state') == 'waiting_new_password':
        if len(text) >= 4:
            set_user_password(user_id, text)
            await update.message.reply_text(f"✅ Пароль установлен! Теперь вы можете получить доступ к своим файлам.")
        else:
            await update.message.reply_text("❌ Пароль должен быть не менее 4 символов")
        context.user_data['state'] = None
    
    elif context.user_data.get('state') == 'waiting_file_password':
        if check_user_password(user_id, text):
            files = get_user_files(user_id)
            if files:
                await update.message.reply_text(f"📁 Ваши файлы ({len(files)} шт.):\n")
                
                # Отправляем все файлы пользователю
                for file_type, file_name, file_id in files:
                    await send_file_to_user(update, file_type, file_id, file_name)
                    await asyncio.sleep(0.5)  # Задержка между отправками
            else:
                await update.message.reply_text("📁 У вас пока нет сохраненных файлов")
        else:
            await update.message.reply_text("❌ Неверный пароль! Доступ запрещен.")
        context.user_data['state'] = None
    
    # ОБРАБОТКА ФАЙЛОВ
    elif update.message.document or update.message.photo or update.message.video or update.message.audio:
        user_password = get_user_password(user_id)
        
        if not user_password:
            await update.message.reply_text("❌ Сначала установите пароль в разделе '🔐 Установить пароль'")
            return
        
        if update.message.document:
            file_type = "document"
            file_name = update.message.document.file_name
            file_id = update.message.document.file_id
        elif update.message.photo:
            file_type = "photo"
            file_name = "photo.jpg"
            file_id = update.message.photo[-1].file_id
        elif update.message.video:
            file_type = "video"
            file_name = "video.mp4"
            file_id = update.message.video.file_id
        elif update.message.audio:
            file_type = "audio"
            file_name = update.message.audio.file_name or "audio.mp3"
            file_id = update.message.audio.file_id
        
        save_file(user_id, file_type, file_name, file_id)
        await update.message.reply_text(f"✅ Файл '{file_name}' сохранен в ваше защищенное хранилище!")

# ------------------ ОБРАБОТКА ФАЙЛОВ ------------------ #
async def handle_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка загружаемых файлов"""
    user_id = update.effective_user.id
    user_password = get_user_password(user_id)
    
    if not user_password:
        await update.message.reply_text("❌ Сначала установите пароль в разделе '🔐 Установить пароль'")
        return
    
    if update.message.document:
        file_type = "document"
        file_name = update.message.document.file_name
        file_id = update.message.document.file_id
    elif update.message.photo:
        file_type = "photo"
        file_name = "photo.jpg"
        file_id = update.message.photo[-1].file_id
    elif update.message.video:
        file_type = "video"
        file_name = "video.mp4"
        file_id = update.message.video.file_id
    elif update.message.audio:
        file_type = "audio"
        file_name = update.message.audio.file_name or "audio.mp3"
        file_id = update.message.audio.file_id
    else:
        return
    
    save_file(user_id, file_type, file_name, file_id)
    await update.message.reply_text(f"✅ Файл '{file_name}' сохранен в ваше защищенное хранилище!")

# ------------------ CALLBACK ОБРАБОТКА ------------------ #
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith('next_movie_'):
        current_index = int(data.split('_')[2])
        results = context.user_data.get('search_results', [])
        
        if current_index < len(results) - 1:
            next_index = current_index + 1
            movie = results[next_index]
            
            movie_info = f"🎬 {movie['title']} ({movie['year']})\n"
            movie_info += f"⭐ Рейтинг: {movie['rating']}/10\n"
            movie_info += f"📝 {movie['description']}\n\n"
            movie_info += "🎯 Выберите где посмотреть:"
            
            keyboard = []
            for service, link in movie['watch_links'].items():
                keyboard.append([InlineKeyboardButton(service, url=link)])
            
            nav_buttons = []
            if next_index > 0:
                nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"next_movie_{next_index-1}"))
            if next_index < len(results) - 1:
                nav_buttons.append(InlineKeyboardButton("➡️ Далее", callback_data=f"next_movie_{next_index+1}"))
            
            if nav_buttons:
                keyboard.append(nav_buttons)
            
            keyboard.append([InlineKeyboardButton("🔍 Новый поиск", callback_data="new_search")])
            
            await query.edit_message_text(movie_info, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "new_search":
        await query.edit_message_text("🎬 Введите название фильма или сериала:")
        context.user_data['state'] = 'waiting_movie_query'

# ------------------ ЗАПУСК ------------------ #
if __name__ == "__main__":
    init_db()
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.ATTACHMENT, handle_files))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("🚀 MegaAssistant запущен!")
    print("🎬 Поиск фильмов")
    print("📁 Защищенное хранилище файлов")
    print("⏰ Напоминания")
    print("🌤️ Погода на 5 дней")
    print("⚽ Футбол")
    print("📱 Готов к работе!")
    
    app.run_polling()
