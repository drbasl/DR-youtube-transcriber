# استخدم صورة Python الرسمية
FROM python:3.11-slim

# تثبيت ffmpeg و ca-certificates
RUN apt-get update && \
    apt-get install -y ffmpeg ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# إنشاء مجلد العمل
WORKDIR /app

# نسخ الملفات المطلوبة للتشغيل (من جذر المشروع)
COPY pyproject.toml /app/
COPY src/ /app/src/

# تحديث pip وتثبيت الحزمة
RUN pip install --upgrade pip && \
    pip install -e .

# تعريف المنفذ (Render سيحدده تلقائياً)
ENV PORT=8501

# ضمان العثور على الحزمة بدون editable install
ENV PYTHONPATH=/app/src

# تحقق من وجود المسار المطلوب أثناء البناء
RUN test -f /app/src/transcribe_cli/app.py

# تشغيل Streamlit
CMD ["sh","-c", "streamlit run src/transcribe_cli/app.py --server.port ${PORT:-8501} --server.address 0.0.0.0"]
