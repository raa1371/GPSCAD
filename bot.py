import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import os
from dotenv import load_dotenv

# بارگیری متغیرهای محیطی
load_dotenv()
TOKEN = os.getenv("TOKEN")
ADMIN_ID = "117345423"  # آی‌دی عددی تلگرام مدیر (باید عددی باشد)

# بررسی مقدار توکن
if TOKEN is None:
    print("❌ خطا: مقدار TOKEN مقداردهی نشده است!")
    exit(1)

# راه‌اندازی ربات و ذخیره‌سازی وضعیت
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# تعریف وضعیت‌ها
class GPSState(StatesGroup):
    collecting = State()
    confirming = State()

# ذخیره مختصات برای هر کاربر
user_data = {}

# شروع ربات
@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    user_data[message.chat.id] = []
    await state.set_state(GPSState.collecting)
    await message.answer("📍 لطفاً مختصات خود را **در قالب چند خطی** ارسال کنید.\n"
                         "هر خط یک نقطه باشد، مثال:\n\n"
                         "57 4 30.50 30 17 45.20\n"
                         "57 5 15.70 30 18 12.30\n\n"
                         "✅ برای تأیید، دستور `/done` را ارسال کنید.")

# دریافت چندین نقطه در یک پیام و ذخیره آن‌ها
@dp.message(GPSState.collecting)
async def collect_gps(message: types.Message, state: FSMContext):
    if message.text.strip() == "/done":  # اگر پیام /done باشد، تأیید مختصات اجرا شود
        await confirm_points(message, state)
        return

    points = message.text.strip().split("\n")  # جدا کردن مختصات‌ها در هر خط
    user_data[message.chat.id].extend(points)
    await message.answer(f"✅ {len(points)} نقطه ذخیره شد.\n"
                         "✉️ ارسال `/done` برای تأیید.")

# پایان دریافت و نمایش تأییدیه
@dp.message(Command("done"))
async def confirm_points(message: types.Message, state: FSMContext):
    if not user_data.get(message.chat.id):
        await message.answer("❌ شما هیچ مختصاتی ارسال نکرده‌اید.")
        return

    points = "\n".join(user_data[message.chat.id])
    await state.set_state(GPSState.confirming)
    await message.answer(f"🔍 لطفاً تأیید کنید:\n\n{points}\n\n"
                         "✅ ارسال `/confirm`\n"
                         "❌ لغو `/cancel`")

# ارسال مختصات به مدیر
@dp.message(Command("confirm"))
async def send_to_admin(message: types.Message, state: FSMContext):
    points = "\n".join(user_data.get(message.chat.id, []))
    await bot.send_message(ADMIN_ID, f"📌 مختصات جدید:\n\n{points}\n\n"
                                     "📷 لطفاً تصویر نقشه را ارسال کنید.")
    await message.answer("✅ مختصات شما به سامانه کاداستر معدن ایران ارسال شد. لطفاً منتظر پردازش باشید.")
    user_data[message.chat.id] = []  # پاک‌سازی لیست کاربر
    await state.clear()

# لغو فرآیند
@dp.message(Command("cancel"))
async def cancel_process(message: types.Message, state: FSMContext):
    user_data[message.chat.id] = []
    await state.clear()
    await message.answer("🚫 عملیات لغو شد.")

# دریافت عکس از مدیر و ارسال به کاربر
@dp.message(lambda msg: msg.chat.id == int(ADMIN_ID) and msg.photo)
async def receive_photo_from_admin(message: types.Message):
    photo_file_id = message.photo[-1].file_id  # دریافت بزرگ‌ترین نسخه تصویر
    for user_id in user_data.keys():
        await bot.send_photo(user_id, photo=photo_file_id, caption="📷 این نقاط GPS از سامانه کاداستر معدن گرفته شده است.")

# اجرای ربات
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
