# استخدم صورة Python الرسمية
FROM python:3.11-slim

# تثبيت ffmpeg و ca-certificates
RUN apt-get update && \
    apt-get install -y ffmpeg ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# إنشاء مجلد العمل
WORKDIR /app

# نسخ ملفات المشروع
COPY . /app

# تحديث pip وتثبيت المكتبات
RUN pip install --upgrade pip && \
    pip install -e . && \
    pip install streamlit yt-dlp

# تعريف المنفذ (Render سيحدده تلقائياً)
ENV PORT=8501

# تشغيل Streamlit
CMD streamlit run src/transcribe_cli/app.py \
    --server.address=0.0.0.0 \
    --server.port=${PORT}
