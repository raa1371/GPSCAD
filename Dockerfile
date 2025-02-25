# استفاده از تصویر پایه رسمی پایتون
FROM python:3.9

# نصب وابستگی‌های مورد نیاز
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libgbm1 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libxss1 \
    libxtst6 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# تنظیم متغیرهای محیطی برای استفاده از Chromium در Selenium
ENV CHROMIUM_PATH="/usr/bin/chromium"
ENV CHROMEDRIVER_PATH="/usr/bin/chromedriver"

# تنظیم مسیر اجرایی Selenium
ENV PATH="$PATH:/usr/bin"

# ایجاد دایرکتوری برای پروژه
WORKDIR /app

# کپی فایل‌های مورد نیاز
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# کپی سورس‌کد ربات
COPY . .

# اجرای ربات تلگرام
CMD ["python", "bot.py"]

