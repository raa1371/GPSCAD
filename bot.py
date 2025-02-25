import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import os
from dotenv import load_dotenv

# بارگیری متغیرهای محیطی
load_dotenv()
TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")  # مقدار را در ENV تنظیم کنید

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
    await message.answer("📍 لطفاً مختصات خود را در قالب DMS ارسال کنید.\nمثال: 35°41'21\"N 51°24'19\"E")

# دریافت مختصات و ذخیره در لیست
@dp.message(GPSState.collecting)
async def collect_gps(message: types.Message, state: FSMContext):
    if message.text.strip().lower() == "/done":
        # اگر کاربر /done ارسال کرد، تأیید را شروع کند
        await confirm_points(message, state)
    else:
        user_data[message.chat.id].append(message.text)
        await message.answer("✅ مختصات ذخیره شد.\n✉️ ارسال `/done` برای تأیید.")

# پایان دریافت و نمایش تأییدیه
async def confirm_points(message: types.Message, state: FSMContext):
    if not user_data.get(message.chat.id):
        await message.answer("❌ شما هیچ مختصاتی ارسال نکرده‌اید.")
        return
    
    points = "\n".join(user_data[message.chat.id])
    await state.set_state(GPSState.confirming)
    await message.answer(f"🔍 لطفاً تأیید کنید:\n\n{points}\n\n✅ ارسال `/confirm`\n❌ لغو `/cancel`")

# ارسال مختصات به مدیر
@dp.message(Command("confirm"))
async def send_to_admin(message: types.Message, state: FSMContext):
    points = "\n".join(user_data.get(message.chat.id, []))
    await bot.send_message(ADMIN_ID, f"📌 مختصات جدید:\n\n{points}\n\n📷 لطفاً تصویر نقشه را ارسال کنید.")
    await message.answer("✅ مختصات شما برای مدیر ارسال شد. لطفاً منتظر دریافت عکس باشید.")
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
        await bot.send_photo(user_id, photo=photo_file_id, caption="📷 این تصویر از مدیر ارسال شده است.")

# اجرای ربات
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
