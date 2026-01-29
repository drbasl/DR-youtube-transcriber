# خطوات اختبار سريعة - YouTube Audio Fix

## التحضير

### 1. تثبيت المتطلبات
```bash
# تحديث المشروع
cd "C:\Users\basel\Downloads\OPEAN AI\transcribe-cli"
pip install -e .

# تثبيت أدوات الاختبار
pip install pytest pytest-mock pytest-cov
```

### 2. التحقق من الأدوات الخارجية
```bash
# تحقق من yt-dlp
yt-dlp --version
# يجب أن يظهر: yt-dlp 2024.10.7 أو أحدث

# تحقق من ffmpeg
ffmpeg -version
# يجب أن يظهر: ffmpeg version ...
```

---

## الاختبار 1: Unit Tests ✅

```bash
cd "C:\Users\basel\Downloads\OPEAN AI\transcribe-cli"
python -m pytest tests/test_youtube_audio.py -v
```

**النتيجة المتوقعة:**
```
test_build_ytdlp_audio_command PASSED                   [ 12%]
test_build_ytdlp_audio_command_output_template PASSED   [ 25%]
test_download_audio_success PASSED                      [ 37%]
test_download_audio_ytdlp_failure PASSED                [ 50%]
test_download_audio_no_file_found PASSED                [ 62%]
test_download_audio_ffmpeg_failure PASSED               [ 75%]
test_download_audio_wav_not_created PASSED              [ 87%]
test_download_audio_handles_multiple_formats PASSED     [100%]

===== 8 passed in 1.75s =====
```

✅ **إذا نجحت جميع الاختبارات:** الكود يعمل بشكل صحيح

❌ **إذا فشل أي اختبار:** راجع الرسالة وأبلغ عنها

---

## الاختبار 2: Streamlit UI (يدوي) 🖥️

### خطوة 1: تشغيل الواجهة
```bash
transcribe-ui
```

انتظر حتى تفتح نافذة المتصفح (http://localhost:8501)

### خطوة 2: اختبار YouTube - Captions (سريع)
1. انتقل إلى تبويب **"YouTube"**
2. املأ الحقول:
   - **رابط YouTube**: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`
   - **Source**: `captions` (اختبار سريع)
   - **Language**: `en`
   - **Output Format**: `text`
3. اضغط **"ابدأ التفريغ"**

**النتيجة المتوقعة:**
- يظهر النص المُفرّغ من الترجمات
- لا توجد رسائل خطأ
- يمكن تنزيل TXT و JSON

### خطوة 3: اختبار YouTube - Audio (اختبار كامل)
1. في نفس التبويب
2. املأ الحقول:
   - **رابط YouTube**: `https://www.youtube.com/watch?v=jNQXAC9IVRw`
     (أغنية قصيرة - "Me at the zoo" - أول فيديو على YouTube)
   - **Source**: `audio` ⚠️ هذا ما نختبره!
   - **Language**: `en`
   - **Output Format**: `text`
3. اضغط **"ابدأ التفريغ"**

**مراقبة Terminal:**
ابحث عن هذه السطور في terminal:
```
INFO - Starting YouTube audio download for: https://...
INFO - Starting yt-dlp audio download to: C:\Users\...\tmp...
INFO - yt-dlp exit code: 0
INFO - Downloaded audio file: ...\xyz.opus (... bytes)
INFO - Converting to WAV: ...
INFO - WAV file ready: ...\xyz.wav (... bytes)
INFO - Audio downloaded successfully: ...
```

**النتيجة المتوقعة:**
- ✅ النص يظهر بعد 30-60 ثانية (حسب سرعة الإنترنت)
- ✅ لا توجد رسائل خطأ
- ✅ حجم الملف المُنزَّل منطقي (> 0 bytes)
- ✅ WAV تم إنشاؤه بنجاح

---

## الاختبار 3: سيناريوهات الأخطاء 🚨

### اختبار 3A: فيديو خاص
```
رابط: https://www.youtube.com/watch?v=PRIVATE_VIDEO
Source: audio
```

**النتيجة المتوقعة:**
```
❌ فشل yt-dlp في التنزيل:
yt-dlp failed with exit code 1. Check stderr: ERROR: ... Video unavailable. This video is private
```

### اختبار 3B: رابط غير صحيح
```
رابط: https://www.youtube.com/watch?v=INVALID_LINK
Source: audio
```

**النتيجة المتوقعة:**
```
❌ فشل yt-dlp في التنزيل:
yt-dlp failed with exit code 1. Check stderr: ERROR: ... Video not found
```

### اختبار 3C: فيديو بدون صوت (نادر)
إذا وجدت فيديو بدون صوت:
```
Source: audio
```

**النتيجة المتوقعة:**
```
❌ فشل تنزيل الصوت:
Audio download failed: no audio files found in ... Expected formats: m4a, webm, opus, mp3, etc.
```

---

## الاختبار 4: تحقق من التنسيقات المختلفة 📝

اختبر مع نفس الفيديو لكن صيغات مختلفة:

| Output Format | متوقع |
|---------------|--------|
| `text` | نص عادي |
| `json` | JSON مع metadata |
| `srt` | SRT subtitles مع timestamps |
| `vtt` | WebVTT مع timestamps |

---

## الاختبار 5: Post-processing (اختياري) ✨

للفيديوهات العربية:
```
رابط: (فيديو عربي من اختيارك)
Source: audio
Language: ar
Post-processing: ✅ Enabled
Mode: Formatted
```

**تحقق من:**
- تصحيح الكلمات المتكررة
- تنسيق النص العربي

---

## استكشاف الأخطاء

### مشكلة: "yt-dlp not found"
```bash
# تثبيت yt-dlp
pip install yt-dlp

# أو عبر winget (Windows):
winget install yt-dlp

# تحقق:
yt-dlp --version
```

### مشكلة: "ffmpeg not found"
```bash
# تحميل من: https://ffmpeg.org/download.html
# أو عبر winget:
winget install ffmpeg

# أضف إلى PATH
# تحقق:
ffmpeg -version
```

### مشكلة: الاختبارات تفشل
```bash
# تأكد من تثبيت المشروع:
pip install -e .

# تأكد من تثبيت dependencies:
pip install pytest pytest-mock pytest-cov

# شغّل الاختبارات بـ verbose:
pytest tests/test_youtube_audio.py -vv
```

### مشكلة: Streamlit لا يعمل
```bash
# تأكد من تثبيت streamlit:
pip install streamlit

# شغّل يدوياً:
streamlit run src/transcribe_cli/app.py
```

---

## تقرير النتائج

بعد إجراء الاختبارات، املأ:

### ✅ Unit Tests
- [ ] جميع الاختبارات نجحت (8/8)
- [ ] بعض الاختبارات فشلت: ___/8

### ✅ Streamlit - Captions
- [ ] نجح التنزيل
- [ ] فشل: __________________

### ✅ Streamlit - Audio
- [ ] نجح التنزيل والتحويل
- [ ] فشل: __________________
- حجم الملف المُنزَّل: ______ KB
- وقت التحويل: ______ ثانية

### ✅ سيناريوهات الأخطاء
- [ ] رسائل الخطأ واضحة ومُفصَّلة
- [ ] رسائل الخطأ غير واضحة: __________________

### 📋 Logs مُفيدة؟
- [ ] نعم، الـ logs تُظهر كل الخطوات
- [ ] لا، الـ logs غير كافية: __________________

---

## الأمر النهائي: كل شيء في أمر واحد ⚡

```bash
cd "C:\Users\basel\Downloads\OPEAN AI\transcribe-cli" ; `
pip install -e . ; `
pip install pytest pytest-mock pytest-cov ; `
pytest tests/test_youtube_audio.py -v ; `
transcribe-ui
```

هذا الأمر:
1. يُثبّت المشروع
2. يُثبّت أدوات الاختبار
3. يُشغّل Unit Tests
4. يفتح Streamlit للاختبار اليدوي

---

## نصائح إضافية

### 1. حفظ الملفات المؤقتة للفحص
عطّل السطر التالي في [app.py](src/transcribe_cli/app.py#L507):
```python
# finally:
#     if temp_dir.exists():
#         shutil.rmtree(temp_dir, ignore_errors=True)
```

### 2. تفعيل DEBUG logging
في [app.py](src/transcribe_cli/app.py#L17):
```python
logging.basicConfig(
    level=logging.DEBUG,  # بدل INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 3. اختبار سريع بـ curl (بدون Streamlit)
```bash
# تنزيل يدوي:
yt-dlp --no-playlist -x --audio-format best --audio-quality 0 "https://www.youtube.com/watch?v=jNQXAC9IVRw"

# تحويل يدوي:
ffmpeg -i "Me at the zoo [jNQXAC9IVRw].opus" -ar 16000 -ac 1 test_output.wav
```

---

**ملاحظة نهائية:** إذا واجهت أي مشكلة، راجع:
- [YOUTUBE_AUDIO_FIX.md](YOUTUBE_AUDIO_FIX.md) - شرح الإصلاح
- [EXAMPLE_LOGS.md](EXAMPLE_LOGS.md) - أمثلة الـ logs
