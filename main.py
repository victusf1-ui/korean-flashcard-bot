import os
import random
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# 🌐 Flask server (botni uyg‘on holda ushlab turadi)
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot ishlayapti va onlayn!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# 🔐 Token yuklash
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# 📘 So‘zlar bazasi
with open("words.txt", "r", encoding="utf-8") as f:
    lines = [line.strip().split(",") for line in f if line.strip() and len(line.split(",")) == 2]

# 🧭 Asosiy menyular
menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📘 So'z ko'rish"), KeyboardButton(text="🎯 Test rejimi")],
        [KeyboardButton(text="📊 Statistikam")]
    ],
    resize_keyboard=True
)

word_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💬 Tarjimasini ko'rish"), KeyboardButton(text="➡️ Keyingi")],
        [KeyboardButton(text="🔙 Ortga qaytish"), KeyboardButton(text="🏠 Asosiy menyu")]
    ],
    resize_keyboard=True
)

quiz_continue_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔁 Davom etish"), KeyboardButton(text="🔙 Ortga qaytish")],
        [KeyboardButton(text="🏠 Asosiy menyu")]
    ],
    resize_keyboard=True
)

# 👤 Foydalanuvchi ma’lumotlari
user_current = {}
user_stats = {}
user_mode = {}
quiz_count = {}
answered_questions = {}

# 🔰 START
@dp.message(Command("start"))
async def start(message: types.Message):
    if not message.from_user:
        return
    user_mode[message.from_user.id] = "menu"
    quiz_count[message.from_user.id] = 0
    await message.answer(
        "🇰🇷 *Koreys tili Flashcard botiga xush kelibsiz!* \n\nYangi so'zlarni o'rganing va test orqali mustahkamlang 👇",
        parse_mode="Markdown",
        reply_markup=menu
    )

# 📘 So‘z ko‘rish
@dp.message(F.text == "📘 So'z ko'rish")
async def show_word(message: types.Message):
    if not message.from_user:
        return
    user_mode[message.from_user.id] = "word"
    word = random.choice(lines)
    user_current[message.from_user.id] = word
    await message.answer(
        f"🇰🇷 *{word[0].strip()}*",
        parse_mode="Markdown",
        reply_markup=word_menu
    )

@dp.message(F.text == "💬 Tarjimasini ko'rish")
async def show_translation(message: types.Message):
    if not message.from_user:
        return
    word = user_current.get(message.from_user.id)
    if not word:
        await message.answer("Avval so'z tanlang 👇", reply_markup=menu)
        return
    await message.answer(f"📝 *{word[1].strip()}*", parse_mode="Markdown")

@dp.message(F.text == "➡️ Keyingi")
async def next_word(message: types.Message):
    if not message.from_user:
        return
    if user_mode.get(message.from_user.id) != "word":
        await message.answer("Bu tugma faqat so'z o'rganish rejimida ishlaydi 👇", reply_markup=menu)
        return
    await show_word(message)

# 🎯 Test rejimi
@dp.message(F.text == "🎯 Test rejimi")
async def start_quiz(message: types.Message):
    if not message.from_user:
        return
    user_mode[message.from_user.id] = "quiz"
    quiz_count[message.from_user.id] = 0
    await send_quiz(message)

async def send_quiz(message: types.Message):
    correct = random.choice(lines)
    wrongs = random.sample(lines, 3)
    options = [correct[1].strip()] + [w[1].strip() for w in wrongs]
    random.shuffle(options)

    question_id = f"{message.chat.id}_{message.message_id}"

    buttons = [[InlineKeyboardButton(text=opt, callback_data=f"answer|{question_id}|{correct[1].strip()}|{opt}")] for opt in options]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(
        f"🇰🇷 Bu so'z nimani anglatadi?\n\n👉 *{correct[0].strip()}*",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

# ✅ Javob tekshirish
@dp.callback_query(F.data.startswith("answer|"))
async def check_answer(callback: types.CallbackQuery):
    if not callback.data or not callback.from_user or not callback.message:
        await callback.answer()
        return

    parts = callback.data.split("|")
    if len(parts) != 4:
        await callback.answer()
        return

    _, question_id, correct, chosen = parts
    user_id = callback.from_user.id

    if question_id in answered_questions.get(user_id, set()):
        await callback.answer("Siz bu savolga allaqachon javob berdingiz!")
        return

    if user_id not in answered_questions:
        answered_questions[user_id] = set()
    answered_questions[user_id].add(question_id)

    if user_id not in user_stats:
        user_stats[user_id] = 0
    if user_id not in quiz_count:
        quiz_count[user_id] = 0

    quiz_count[user_id] += 1

    if chosen == correct:
        user_stats[user_id] += 1
        text = f"✅ To'g'ri javob!\n📗 So'z: *{correct}*"
    else:
        text = f"❌ Noto'g'ri!\nTo'g'ri javob: *{correct}*"

    try:
        await callback.message.edit_text(text, parse_mode="Markdown")
    except Exception:
        pass

    if quiz_count[user_id] >= 20:
        total_correct = user_stats[user_id]
        await callback.message.answer(
            f"🎯 Siz 20 ta testni yakunladingiz!\n✅ To'g'ri javoblar: *{total_correct} ta*",
            parse_mode="Markdown",
            reply_markup=quiz_continue_menu
        )
        quiz_count[user_id] = 0
        answered_questions[user_id].clear()
    else:
        await send_quiz(callback.message)

    await callback.answer()

# 📊 Statistikam
@dp.message(F.text == "📊 Statistikam")
async def stats(message: types.Message):
    if not message.from_user:
        return
    count = user_stats.get(message.from_user.id, 0)
    await message.answer(f"📈 Siz hozircha *{count} ta* so'zni to'g'ri topdingiz!", parse_mode="Markdown")

# 🔙 Ortga qaytish
@dp.message(F.text == "🔙 Ortga qaytish")
async def go_back(message: types.Message):
    if not message.from_user:
        return
    user_mode[message.from_user.id] = "menu"
    await message.answer("🔙 Ortga qaytdingiz!", reply_markup=menu)

# 🏠 Asosiy menyu
@dp.message(F.text == "🏠 Asosiy menyu")
async def main_menu(message: types.Message):
    if not message.from_user:
        return
    user_mode[message.from_user.id] = "menu"
    await message.answer("🏠 Asosiy menyuga qaytdingiz.", reply_markup=menu)

# 🚀 Ishga tushirish
async def main():
    print("Bot ishga tushdi...")
    keep_alive()  # 🔁 Flask serverni ishga tushiramiz
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
