import logging
import json
import os
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    ContextTypes, ConversationHandler, filters
)

# --- НАСТРОЙКИ ---
# Вставьте сюда ваши ключи внутрь кавычек!
TELEGRAM_BOT_TOKEN = "8395064309:AAGUiTCNdmyJNOS_LOHY4Gp-OkP95onmfVk"
WEATHER_API_KEY = "4711b9817b39eb1aa4ae907c2702032d"
CITY = "Moscow"
DB_FILE = "perfumes.json"

# Начальная база данных парфюмов
DEFAULT_PERFUMES = [
    {
        "name": "Hermès Terre d'Hermès EDP",
        "seasons": ["осень", "весна", "лето"],
        "temp_min": 10,
        "temp_max": 20,
        "rain_friendly": True,
        "style": "офис / стритвеар",
        "sprays": "2–3 спрея",
        "why": "Идеально раскрывается во влажную прохладную погоду, древесно-минеральный шлейф."
    },
    {
        "name": "Afnan Turathi Blue / Bvlgari Tygar",
        "seasons": ["лето", "весна"],
        "temp_min": 15,
        "temp_max": 28,
        "rain_friendly": True,
        "style": "офис / каждый день",
        "sprays": "3 спрея",
        "why": "Яркий грейпфрут и амброксан отлично звучат во время дождя и не утомляют в помещении."
    },
    {
        "name": "Chanel Bleu de Chanel EDP",
        "seasons": ["осень", "весна"],
        "temp_min": 15,
        "temp_max": 22,
        "rain_friendly": False,
        "style": "деловой статус / встречи",
        "sprays": "3 спрея",
        "why": "Классика статусности, идеально держит баланс при перепадах от +16°C до +21°C."
    },
    {
        "name": "Lattafa Dynasty EDP",
        "seasons": ["осень", "весна"],
        "temp_min": 12,
        "temp_max": 21,
        "rain_friendly": True,
        "style": "статус / универсальный",
        "sprays": "2–3 спрея",
        "why": "Плотный, богатый шлейф для прохладных дней и статусной обстановки."
    },
    {
        "name": "French Avenue Paradigm Extrait",
        "seasons": ["осень"],
        "temp_min": 10,
        "temp_max": 18,
        "rain_friendly": False,
        "style": "вечер / статус",
        "sprays": "2 спрея",
        "why": "Глубокий вечерний вариант для осеннего перехода температур."
    }
]

# --- СОСТОЯНИЯ ДЛЯ ДИАЛОГА ДОБАВЛЕНИЯ ---
NAME, SEASONS, TEMP, RAIN, STYLE, SPRAYS, WHY = range(7)

# --- РАБОТА С БАЗОЙ ДАННЫХ (JSON) ---
def load_perfumes():
    if not os.path.exists(DB_FILE):
        save_perfumes(DEFAULT_PERFUMES)
        return DEFAULT_PERFUMES
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_PERFUMES

def save_perfumes(perfumes):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(perfumes, f, ensure_ascii=False, indent=2)

# --- ПОГОДА И РЕКОМЕНДАЦИИ ---
def get_weather():
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={WEATHER_API_KEY}&units=metric&lang=ru"
        res = requests.get(url).json()
        temp = round(res["main"]["temp"])
        desc = res["weather"][0]["description"]
        is_rain = any(word in desc for word in ["дождь", "морось", "ливень"])
        return temp, desc, is_rain
    except Exception:
        return None, None, False

def recommend_perfume(temp, is_rain=False):
    perfumes = load_perfumes()
    results = []
    for p in perfumes:
        if p.get("temp_min", -50) <= temp <= p.get("temp_max", 50):
            if is_rain and not p.get("rain_friendly", True):
                continue
            results.append(p)
    return results[:3]

# --- ОБРАБОТЧИКИ КОМАНД И МЕНЮ ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [
        ['☀️ Погода и Парфюм дня', '📦 Моя коллекция'],
        ['➕ Добавить парфюм', '❌ Удалить парфюм']
    ]
    markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "👋 **Личный Парфюмерный Ассистент**\n\n"
        "• Нажмите **'☀️ Погода и Парфюм дня'** для автоподбора.\n"
        "• Добавляйте и удаляйте флаконы кнопками ниже.\n"
        "• Или отправьте условия текстом (например: `Осень +15 дождь`).",
        reply_markup=markup,
        parse_mode="Markdown"
    )

async def list_perfumes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    perfumes = load_perfumes()
    if not perfumes:
        await update.message.reply_text("Коллекция пуста. Нажмите '➕ Добавить парфюм'.")
        return

    msg = f"<b>📦 Ваша коллекция ({len(perfumes)} шт.):</b>\n\n"
    for i, p in enumerate(perfumes, 1):
        msg += f"<b>{i}. {p['name']}</b> ({p['temp_min']}°C...{p['temp_max']}°C)\n"
    await update.message.reply_text(msg, parse_mode="HTML")

# --- СЦЕНАРИЙ ДОБАВЛЕНИЯ ПАРФЮМА ---
async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите **название парфюма** (например: *Dior Homme Cologne*):", parse_mode="Markdown")
    return NAME

async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_p'] = {'name': update.message.text}
    await update.message.reply_text("Укажите **сезоны** через запятую (например: *лето, весна*):", parse_mode="Markdown")
    return SEASONS

async def add_seasons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_p']['seasons'] = [s.strip().lower() for s in update.message.text.split(',')]
    await update.message.reply_text("Укажите **диапазон температур** (например: *15 25* или *15-25*):", parse_mode="Markdown")
    return TEMP

async def add_temp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        nums = [int(s) for s in update.message.text.replace('-', ' ').split() if s.lstrip('-').isdigit()]
        context.user_data['new_p']['temp_min'] = min(nums)
        context.user_data['new_p']['temp_max'] = max(nums)
    except Exception:
        context.user_data['new_p']['temp_min'] = 10
        context.user_data['new_p']['temp_max'] = 25
    
    await update.message.reply_text("Подходит для **дождя**? Напишите *да* или *нет*:", parse_mode="Markdown")
    return RAIN

async def add_rain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text.strip().lower()
    context.user_data['new_p']['rain_friendly'] = answer in ['да', 'yes', '+']
    await update.message.reply_text("Укажите **стиль/назначение** (например: *офис, вечер, статус*):", parse_mode="Markdown")
    return STYLE

async def add_style(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_p']['style'] = update.message.text
    await update.message.reply_text("Укажите **дозировку** (например: *2-3 спрея*):", parse_mode="Markdown")
    return SPRAYS

async def add_sprays(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_p']['sprays'] = update.message.text
    await update.message.reply_text("Коротко укажите, **почему/как раскрывается**:", parse_mode="Markdown")
    return WHY

async def add_why(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_p']['why'] = update.message.text
    
    perfumes = load_perfumes()
    perfumes.append(context.user_data['new_p'])
    save_perfumes(perfumes)

    await update.message.reply_text(f"✅ Парфюм **{context.user_data['new_p']['name']}** успешно добавлен в базу!", parse_mode="Markdown")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Действие отменено.")
    return ConversationHandler.END

# --- СЦЕНАРИЙ УДАЛЕНИЯ ПАРФЮМА ---
async def delete_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    perfumes = load_perfumes()
    if not perfumes:
        await update.message.reply_text("Коллекция пуста.")
        return

    msg = "Отправьте **номер** парфюма для удаления (или /cancel для отмены):\n\n"
    for i, p in enumerate(perfumes, 1):
        msg += f"{i}. {p['name']}\n"
    
    await update.message.reply_text(msg, parse_mode="Markdown")
    context.user_data['deleting'] = True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if context.user_data.get('deleting'):
        context.user_data['deleting'] = False
        if text.isdigit():
            idx = int(text) - 1
            perfumes = load_perfumes()
            if 0 <= idx < len(perfumes):
                removed = perfumes.pop(idx)
                save_perfumes(perfumes)
                await update.message.reply_text(f"❌ Парфюм **{removed['name']}** удален из базы.", parse_mode="Markdown")
                return
        await update.message.reply_text("Некорректный номер. Удаление отменено.")
        return

    if text == '☀️ Погода и Парфюм дня':
        temp, desc, is_rain = get_weather()
        if temp is None:
            await update.message.reply_text("Ошибка сервиса погоды. Проверьте ваш WEATHER_API_KEY.")
            return

        rain_str = "🌧️ Осадки" if is_rain else "☁️ Без осадков"
        msg = f"<b>Погода в {CITY}:</b> {temp}°C, {desc} ({rain_str})\n\n<b>Рекомендуемые ароматы:</b>\n\n"
        recs = recommend_perfume(temp, is_rain)

        if not recs:
            msg += "В базе нет подхдящих ароматов под текущую температуру."
        else:
            for i, r in enumerate(recs, 1):
                msg += f"<b>{i}. {r['name']}</b>\n• Назначение: {r['style']}\n• Дозировка: {r['sprays']}\n• Аргумент: {r['why']}\n\n"

        await update.message.reply_text(msg, parse_mode="HTML")

    elif text == '📦 Моя коллекция':
        await list_perfumes(update, context)

    else:
        words = text.lower().split()
        temp = 18
        for w in words:
            clean_w = w.replace("+", "").replace("°c", "").replace("°", "")
            if clean_w.lstrip('-').isdigit():
                temp = int(clean_w)
                break
        
        is_rain = "дождь" in text.lower() or "ливень" in text.lower()
        recs = recommend_perfume(temp, is_rain)

        msg = f"<b>Подбор ({temp}°C, {'дождь' if is_rain else 'без осадков'}):</b>\n\n"
        if not recs:
            msg += "Нет подходящих парфюмов под эти условия в базе."
        else:
            for i, r in enumerate(recs, 1):
                msg += f"<b>{i}. {r['name']}</b>\n• Назначение: {r['style']}\n• Спреи: {r['sprays']}\n• Аргумент: {r['why']}\n\n"
        
        await update.message.reply_text(msg, parse_mode="HTML")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    add_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^➕ Добавить парфюм$'), add_start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
            SEASONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_seasons)],
            TEMP: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_temp)],
            RAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_rain)],
            STYLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_style)],
            SPRAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_sprays)],
            WHY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_why)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(add_handler)
    app.add_handler(MessageHandler(filters.Regex('^❌ Удалить парфюм$'), delete_start))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен...")
    app.run_polling()
