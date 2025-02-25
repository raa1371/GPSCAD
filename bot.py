import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import os
from dotenv import load_dotenv
import re
import folium
from io import BytesIO

# بارگیری متغیرهای محیطی
load_dotenv()
TOKEN = os.getenv("TOKEN")
ADMIN_ID = "117345423"  # آی‌دی عددی تلگرام مدیر

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

def dms_to_dd(dms_str):
    match = re.match(r"(\d+) (\d+) ([\d\.]+) (\d+) (\d+) ([\d\.]+)", dms_str)
    if match:
        lon_deg, lon_min, lon_sec, lat_deg, lat_min, lat_sec = map(float, match.groups())
        lon_dd = lon_deg + lon_min / 60 + lon_sec / 3600
        lat_dd = lat_deg + lat_min / 60 + lat_sec / 3600
        return lat_dd, lon_dd
    return None

def generate_map(points):
    if not points:
        return None
    
    m = folium.Map(location=points[0], zoom_start=12, tiles='Stamen Terrain')
    folium.PolyLine(points, color='blue', weight=2.5, opacity=1).add_to(m)
    
    for lat, lon in points:
        folium.Marker([lat, lon], tooltip=f"{lat}, {lon}").add_to(m)
    
    img_data = BytesIO()
    m.save(img_data, close_file=False)
    img_data.seek(0)
    return img_data

@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    user_data[message.chat.id] = []
    await state.set_state(GPSState.collecting)
    await message.answer("📍 لطفاً مختصات خود را **در قالب چند خطی** ارسال کنید.\n"
                         "هر خط یک نقطه باشد، مثال:\n\n"
                         "57 4 30.50 30 17 45.20\n"
                         "57 5 15.70 30 18 12.30\n\n"
                         "✅ برای تأیید، دستور `/done` را ارسال کنید.")

@dp.message(GPSState.collecting)
async def collect_gps(message: types.Message, state: FSMContext):
    if message.text.strip() == "/done":
        await confirm_points(message, state)
        return
    
    points = message.text.strip().split("\n")
    user_data[message.chat.id].extend(points)
    await message.answer(f"✅ {len(points)} نقطه ذخیره شد.\n"
                         "✉️ ارسال `/done` برای تأیید.")

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

@dp.message(Command("confirm"))
async def send_to_admin(message: types.Message, state: FSMContext):
    points_text = "\n".join(user_data.get(message.chat.id, []))
    converted_points = [dms_to_dd(p) for p in user_data.get(message.chat.id, []) if dms_to_dd(p)]
    
    await bot.send_message(ADMIN_ID, f"📌 مختصات جدید:\n\n{points_text}\n\n"
                                     "📷 لطفاً تصویر نقشه را ارسال کنید.")
    await message.answer("✅ مختصات شما به سامانه کاداستر معدن ایران ارسال شد. لطفاً منتظر پردازش باشید.با توجه به سرعت vpn و سایت مرجع بین 1 تا 120ثانیه طول می کشد")
    user_data[message.chat.id] = []
    await state.clear()

@dp.message(Command("cancel"))
async def cancel_process(message: types.Message, state: FSMContext):
    user_data[message.chat.id] = []
    await state.clear()
    await message.answer("🚫 عملیات لغو شد.")

@dp.message(lambda msg: msg.chat.id == int(ADMIN_ID) and msg.photo)
async def receive_photo_from_admin(message: types.Message):
    photo_file_id = message.photo[-1].file_id
    for user_id in user_data.keys():
        points = user_data.get(user_id, [])
        converted_points = [dms_to_dd(p) for p in points if dms_to_dd(p)]
        map_image = generate_map(converted_points)
        
        if map_image:
            await bot.send_photo(user_id, photo=photo_file_id, caption="📷 تصویر ارسال‌شده توسط مدیر.")
            await bot.send_document(user_id, document=types.BufferedInputFile(map_image.getvalue(), filename="map.html"), caption="📍 نقشه نقاط متصل‌شده.")

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
