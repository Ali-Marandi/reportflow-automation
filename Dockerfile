# استفاده از نسخه سبک پایتون
FROM python:3.11-slim

# تنظیم دایرکتوری کاری
WORKDIR /app

# نصب پیش‌نیازهای سیستم برای پانداز
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# کپی فایل‌های پروژه
COPY . .

# نصب پکیج و وابستگی‌ها
RUN pip install --no-cache-dir .
RUN pip install --no-cache-dir schedule

# ایجاد دایرکتوری برای داده‌ها و گزارش‌ها
RUN mkdir -p /app/data /app/reports

# اجرای اسکریپت زمان‌بندی به عنوان نقطه شروع
# شما می‌توانید این را به اجرای مستقیم CLI تغییر دهید
CMD ["python", "tools/automate_scheduling.py"]
