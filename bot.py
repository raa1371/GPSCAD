import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

# بارگیری متغیرهای محیطی
load_dotenv()
TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")  # مقدار را در .env مشخص کنید

# تنظیمات ربات
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# تعریف وضعیت‌ها
class GPSState(StatesGroup):
    collecting = State()
    confirming = State()

# ذخیره مختصات کاربران
user_data = {}

# شروع ربات
@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    user_data[message.chat.id] = []
    await state.set_state(GPSState.collecting)
    await message.answer("📍 لطفاً مختصات خود را به‌صورت چندخطی ارسال کنید.\n\n"
                         "مثال:\n"
                         "57 4 30.50 30 17 45.20\n"
                         "57 5 15.70 30 18 12.30\n\n"
                         "پس از ارسال نقاط، دستور `/done` را بزنید.")

# دریافت مختصات GPS (اضافه کردن به لیست به‌جای جایگزینی)
@dp.message(GPSState.collecting)
async def collect_gps(message: types.Message, state: FSMContext):
    points = message.text.strip().split("\n")
    user_data.setdefault(message.chat.id, []).extend(points)
    await message.answer("✅ مختصات ذخیره شد.\n"
                         "✉️ ارسال `/done` برای تأیید.")

# نمایش تأییدیه قبل از ارسال به مدیر
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

# ارسال مختصات به مدیر و گرفتن اسکرین‌شات
@dp.message(Command("confirm"))
async def send_to_admin(message: types.Message, state: FSMContext):
    points = "\n".join(user_data.get(message.chat.id, []))
    await bot.send_message(ADMIN_ID, f"📌 مختصات جدید:\n\n{points}\n\n📷 لطفاً تصویر نقشه را ارسال کنید.")
    
    # اجرای Selenium برای گرفتن اسکرین‌شات
    screenshot_path = take_screenshot(user_data[message.chat.id])
    if screenshot_path:
        photo = FSInputFile(screenshot_path)
        await message.answer_photo(photo, caption="📷 این تصویر از سایت گرفته شده است.")
    
    user_data[message.chat.id] = []  # پاک کردن داده‌ها
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

# اجرای Selenium برای ثبت نقاط و گرفتن اسکرین‌شات
def take_screenshot(points):
    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        url = "https://cadastre.mimt.gov.ir/Map/Map.aspx?PNid=0"
        driver.get(url)
        driver.implicitly_wait(5)

        # یافتن فیلد مختصات و ارسال نقاط
        input_field = driver.find_element(By.ID, "txtLatLon")  # بررسی ID یا XPath مناسب
        input_field.clear()

        for point in points:
            lat, lat_min, lat_sec, lon, lon_min, lon_sec = map(float, point.split())
            lat_dms = f"{int(lat)}°{int(lat_min)}'{lat_sec:.2f}\"N"
            lon_dms = f"{int(lon)}°{int(lon_min)}'{lon_sec:.2f}\"E"

            input_field.send_keys(f"{lat_dms}, {lon_dms}")
            input_field.send_keys(Keys.RETURN)  # ارسال به سایت

        # گرفتن اسکرین‌شات
        screenshot_path = "map_screenshot.png"
        driver.save_screenshot(screenshot_path)
        driver.quit()
        return screenshot_path

    except Exception as e:
        logging.error(f"خطا در Selenium: {e}")
        return None

# اجرای ربات
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
