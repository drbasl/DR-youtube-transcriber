# إصلاح YouTube Audio Download

## المشكلة
كان خطأ "Audio download failed or WAV file not found" يحدث لأن:
1. yt-dlp كان يُنزّل ملفات بصيغات مختلفة (m4a, webm, opus) وليس WAV
2. الكود كان يبحث فقط عن ملفات WAV
3. لم يكن هناك تحويل من الصيغة المُنزَّلة إلى WAV
4. لم يكن هناك logging تشخيصي للأخطاء

## الحل المُطبَّق

### 1. تغيير في `build_ytdlp_audio_command()`
```python
# قبل:
"--audio-format", "wav"

# بعد:
"--audio-format", "best"  # نُنزّل أفضل جودة، ثم نُحوّل
```

### 2. تحسين `download_audio()` الشامل
الآن الوظيفة تقوم بـ:

#### خطوة 1: التنزيل
- تُنزّل الصوت بأي صيغة (m4a, webm, opus, mp3, etc.)
- تطبع exit code و stdout/stderr
- تتحقق من نجاح التنزيل

#### خطوة 2: البحث عن الملف
- تبحث عن أي صيغة صوتية: `['m4a', 'webm', 'opus', 'mp3', 'aac', 'wav', 'ogg']`
- تطبع مسار الملف المُنزَّل وحجمه

#### خطوة 3: التحويل إلى WAV
- تستخدم `convert_audio_format()` من ffmpeg.py
- تحويل إلى: 16kHz, mono, PCM WAV
- تطبع مسار WAV الناتج

#### خطوة 4: التحقق
- تتأكد من وجود WAV باستخدام `Path.exists()`
- تطبع حجم الملف النهائي

### 3. Logging آمن
```python
logger.info(f"yt-dlp exit code: {result.returncode}")
logger.debug(f"yt-dlp stdout (first 500 chars): {result.stdout[:500]}")
logger.debug(f"yt-dlp stderr (first 500 chars): {result.stderr[:500]}")
logger.info(f"Downloaded audio file: {downloaded_path} ({size} bytes)")
logger.info(f"WAV file ready: {wav_path} ({size} bytes)")
```

### 4. رسائل خطأ واضحة في Streamlit
```python
# في app.py - process_youtube()
except FileNotFoundError as e:
    if "yt-dlp failed" in error_msg:
        return None, f"❌ فشل yt-dlp في التنزيل:\n{error_msg}"
    elif "ffmpeg conversion failed" in error_msg:
        return None, f"❌ فشل تحويل ffmpeg:\n{error_msg}"
    elif "Audio download failed" in error_msg:
        return None, f"❌ فشل تنزيل الصوت:\n{error_msg}"
```

## الملفات المُعدَّلة

1. **src/transcribe_cli/utils/youtube.py**
   - إضافة `import logging` و `from ...ffmpeg import convert_audio_format`
   - تغيير `build_ytdlp_audio_command()` ليستخدم "best"
   - إعادة كتابة كاملة لـ `download_audio()` مع 4 خطوات واضحة
   - إضافة logging شامل

2. **src/transcribe_cli/app.py**
   - إضافة `import logging` وإعداد logger
   - تحسين معالجة الأخطاء في `process_youtube()`
   - إضافة logging للخطوات الحرجة

3. **tests/test_youtube_audio.py** (جديد)
   - 9 unit tests للوظائف المُحسَّنة
   - اختبارات للحالات: نجاح، فشل yt-dlp، لم يُعثر على ملف، فشل ffmpeg، WAV لم يُنشأ

## كيفية الاختبار

### 1. تشغيل Unit Tests
```bash
cd "C:\Users\basel\Downloads\OPEAN AI\transcribe-cli"
python -m pytest tests/test_youtube_audio.py -v
```

### 2. اختبار Streamlit (يدوي)
```bash
# تشغيل واجهة Streamlit
transcribe-ui

# في المتصفح:
1. انتقل إلى تبويب "YouTube"
2. اختر source = "audio"
3. الصق رابط YouTube
4. اضغط "ابدأ التفريغ"
```

### 3. مراجعة Logs
الآن ستشاهد في terminal:
```
2026-01-30 10:15:23 - transcribe_cli.utils.youtube - INFO - Starting yt-dlp audio download to: C:\Users\...\tmp123
2026-01-30 10:15:23 - transcribe_cli.utils.youtube - DEBUG - yt-dlp command: yt-dlp --no-playlist -x ...
2026-01-30 10:15:45 - transcribe_cli.utils.youtube - INFO - yt-dlp exit code: 0
2026-01-30 10:15:45 - transcribe_cli.utils.youtube - INFO - Downloaded audio file: C:\...\xyz.m4a (5242880 bytes)
2026-01-30 10:15:45 - transcribe_cli.utils.youtube - INFO - Converting to WAV: xyz.m4a -> xyz.wav
2026-01-30 10:15:50 - transcribe_cli.utils.youtube - INFO - WAV file ready: xyz.wav (10485760 bytes)
```

### 4. حالة فشل (مثال log)
```
2026-01-30 10:20:11 - transcribe_cli.utils.youtube - INFO - yt-dlp exit code: 1
2026-01-30 10:20:11 - transcribe_cli.utils.youtube - DEBUG - yt-dlp stderr: ERROR: Video unavailable: This video is private
FileNotFoundError: yt-dlp failed with exit code 1. Check stderr: ERROR: Video unavailable: This video is private

# في Streamlit:
❌ فشل yt-dlp في التنزيل:
yt-dlp failed with exit code 1. Check stderr: ERROR: Video unavailable: This video is private
```

## المتطلبات
- **yt-dlp**: مُثبَّت ومُضاف إلى PATH
- **ffmpeg**: مُثبَّت ومُضاف إلى PATH (للتحويل)

تحقق بـ:
```bash
yt-dlp --version
ffmpeg -version
```

## ملاحظات هامة

### 1. المجلد المؤقت
- الملفات تُحفظ في `tempfile.mkdtemp()` (مجلد مؤقت نظام)
- يتم حذفها تلقائياً في `finally` block
- إذا أردت الاحتفاظ بالملفات للتشخيص، عطّل السطر: `shutil.rmtree(temp_dir, ignore_errors=True)`

### 2. أداء التحويل
- التحويل قد يستغرق وقتاً حسب حجم الملف (عادة 5-30 ثانية)
- التقدم يظهر في logs

### 3. الصيغات المدعومة
الكود يبحث عن هذه الصيغات بالترتيب:
```python
['m4a', 'webm', 'opus', 'mp3', 'aac', 'wav', 'ogg']
```
إذا كان yt-dlp يُنزّل صيغة أخرى، أضفها للقائمة.

## مثال استخدام كامل

```bash
# 1. تثبيت/تحديث المشروع
cd "C:\Users\basel\Downloads\OPEAN AI\transcribe-cli"
pip install -e .

# 2. تشغيل tests
pytest tests/test_youtube_audio.py -v

# 3. تشغيل Streamlit
transcribe-ui

# 4. في المتصفح - تبويب YouTube:
#    - URL: https://www.youtube.com/watch?v=dQw4w9WgXcQ
#    - Source: audio
#    - Language: en
#    - Output: text
#    - ابدأ التفريغ
```

## استكشاف الأخطاء

### خطأ: "yt-dlp failed with exit code 1"
- تحقق من صحة الرابط
- تحقق من توفر الفيديو (ليس خاصاً/محذوفاً)
- راجع stderr في logs

### خطأ: "ffmpeg conversion failed"
- تحقق من تثبيت ffmpeg: `ffmpeg -version`
- تحقق من PATH
- تحقق من مساحة القرص

### خطأ: "no audio files found"
- راجع stdout/stderr من yt-dlp في logs
- قد يكون الفيديو بدون صوت
- جرّب source="captions" بدلاً من "audio"

### خطأ: "WAV file not created after conversion"
- ffmpeg نفّذ لكن لم يُنشئ الملف
- تحقق من أذونات الكتابة في temp folder
- راجع ffmpeg stderr في logs
