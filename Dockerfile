# استخدم صورة Python الرسمية
FROM python:3.11-slim

# تثبيت ffmpeg و ca-certificates
RUN apt-get update && \
    apt-get install -y ffmpeg ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# إنشاء مجلد العمل
WORKDIR /app

# نسخ ملفات المشروع (يتعامل مع كلا الحالتين: من repo root أو من OPEAN AI)
COPY . /app/

# تحديث pip وتثبيت المكتبات
RUN pip install --upgrade pip && \
    pip install streamlit yt-dlp openai typer httpx python-dotenv pydantic pydantic-settings rich

# تعريف المنفذ (Render سيحدده تلقائياً)
ENV PORT=8501

# ضمان العثور على الحزمة بدون editable install
ENV PYTHONPATH=/app/src

# تشغيل Streamlit (اكتشاف تلقائي لمسار app.py)
CMD ["sh","-c", "\
set -e; \
echo 'Locating Streamlit entry...'; \
TARGET=$(find /app -maxdepth 6 -type f -name app.py | head -n 1); \
echo \"Found: $TARGET\"; \
test -n \"$TARGET\"; \
streamlit run \"$TARGET\" --server.address=0.0.0.0 --server.port=${PORT:-8501} --server.headless=true \
"]
