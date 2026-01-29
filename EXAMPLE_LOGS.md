# مثال Logs - سيناريوهات مختلفة

## سيناريو 1: تنزيل ناجح ✅

```
2026-01-30 14:32:11 - transcribe_cli.app - INFO - Starting YouTube audio download for: https://www.youtube.com/watch?v=dQw4w9WgXcQ
2026-01-30 14:32:11 - transcribe_cli.utils.youtube - INFO - Starting yt-dlp audio download to: C:\Users\basel\AppData\Local\Temp\tmpabcd1234
2026-01-30 14:32:11 - transcribe_cli.utils.youtube - DEBUG - yt-dlp command: yt-dlp --no-playlist -x --audio-format best --audio-quality 0 -o C:\Users\basel\AppData\Local\Temp\tmpabcd1234\%(id)s.%(ext)s https://www.youtube.com/watch?v=dQw4w9WgXcQ
2026-01-30 14:32:34 - transcribe_cli.utils.youtube - INFO - yt-dlp exit code: 0
2026-01-30 14:32:34 - transcribe_cli.utils.youtube - DEBUG - yt-dlp stdout (first 500 chars): [youtube] Extracting URL: https://www.youtube.com/watch?v=dQw4w9WgXcQ
[youtube] dQw4w9WgXcQ: Downloading webpage
[youtube] dQw4w9WgXcQ: Downloading ios player API JSON
[youtube] dQw4w9WgXcQ: Downloading m3u8 information
[info] dQw4w9WgXcQ: Downloading 1 format(s): 251
[download] Destination: C:\Users\basel\AppData\Local\Temp\tmpabcd1234\dQw4w9WgXcQ.webm
[download] 100% of    3.28MiB in 00:00:02 at 1.52MiB/s
[ExtractAudio] Destination: C:\Users\basel\AppData\Local\Temp\tmpabcd1234\dQw4w9WgXcQ.opus
Deleting original file C:\Users\basel\AppData\Local\Temp\tmpabcd1234\dQw4w9WgXcQ.webm
2026-01-30 14:32:34 - transcribe_cli.utils.youtube - INFO - Downloaded audio file: C:\Users\basel\AppData\Local\Temp\tmpabcd1234\dQw4w9WgXcQ.opus (3441234 bytes)
2026-01-30 14:32:34 - transcribe_cli.utils.youtube - INFO - Converting to WAV: C:\Users\basel\AppData\Local\Temp\tmpabcd1234\dQw4w9WgXcQ.opus -> C:\Users\basel\AppData\Local\Temp\tmpabcd1234\dQw4w9WgXcQ.wav
2026-01-30 14:32:47 - transcribe_cli.utils.youtube - INFO - WAV file ready: C:\Users\basel\AppData\Local\Temp\tmpabcd1234\dQw4w9WgXcQ.wav (11289600 bytes)
2026-01-30 14:32:47 - transcribe_cli.app - INFO - Audio downloaded successfully: C:\Users\basel\AppData\Local\Temp\tmpabcd1234\dQw4w9WgXcQ.wav
```

**في Streamlit UI:**
```
✅ تم التفريغ بنجاح!
```

---

## سيناريو 2: فيديو غير متاح ❌

```
2026-01-30 14:35:22 - transcribe_cli.app - INFO - Starting YouTube audio download for: https://www.youtube.com/watch?v=PRIVATE_VIDEO
2026-01-30 14:35:22 - transcribe_cli.utils.youtube - INFO - Starting yt-dlp audio download to: C:\Users\basel\AppData\Local\Temp\tmpxyz5678
2026-01-30 14:35:22 - transcribe_cli.utils.youtube - DEBUG - yt-dlp command: yt-dlp --no-playlist -x --audio-format best --audio-quality 0 -o C:\Users\basel\AppData\Local\Temp\tmpxyz5678\%(id)s.%(ext)s https://www.youtube.com/watch?v=PRIVATE_VIDEO
2026-01-30 14:35:25 - transcribe_cli.utils.youtube - INFO - yt-dlp exit code: 1
2026-01-30 14:35:25 - transcribe_cli.utils.youtube - DEBUG - yt-dlp stdout (first 500 chars): 
2026-01-30 14:35:25 - transcribe_cli.utils.youtube - DEBUG - yt-dlp stderr (first 500 chars): ERROR: [youtube] PRIVATE_VIDEO: Video unavailable. This video is private
```

**في Streamlit UI:**
```
❌ فشل yt-dlp في التنزيل:
yt-dlp failed with exit code 1. Check stderr: ERROR: [youtube] PRIVATE_VIDEO: Video unavailable. This video is private
```

---

## سيناريو 3: فشل ffmpeg (ملف تالف) ❌

```
2026-01-30 14:40:15 - transcribe_cli.app - INFO - Starting YouTube audio download for: https://www.youtube.com/watch?v=CORRUPT_FILE
2026-01-30 14:40:15 - transcribe_cli.utils.youtube - INFO - Starting yt-dlp audio download to: C:\Users\basel\AppData\Local\Temp\tmpdef9012
2026-01-30 14:40:15 - transcribe_cli.utils.youtube - DEBUG - yt-dlp command: yt-dlp --no-playlist -x --audio-format best --audio-quality 0 -o C:\Users\basel\AppData\Local\Temp\tmpdef9012\%(id)s.%(ext)s https://www.youtube.com/watch?v=CORRUPT_FILE
2026-01-30 14:40:28 - transcribe_cli.utils.youtube - INFO - yt-dlp exit code: 0
2026-01-30 14:40:28 - transcribe_cli.utils.youtube - DEBUG - yt-dlp stdout (first 500 chars): [youtube] Extracting URL...
[download] 100% of 2.15MiB in 00:00:01
2026-01-30 14:40:28 - transcribe_cli.utils.youtube - INFO - Downloaded audio file: C:\Users\basel\AppData\Local\Temp\tmpdef9012\CORRUPT_FILE.m4a (2254848 bytes)
2026-01-30 14:40:28 - transcribe_cli.utils.youtube - INFO - Converting to WAV: C:\Users\basel\AppData\Local\Temp\tmpdef9012\CORRUPT_FILE.m4a -> C:\Users\basel\AppData\Local\Temp\tmpdef9012\CORRUPT_FILE.wav
2026-01-30 14:40:28 - transcribe_cli.utils.youtube - ERROR - ffmpeg conversion failed: Audio conversion failed: [error msg from ffmpeg stderr]
```

**في Streamlit UI:**
```
❌ فشل تحويل ffmpeg:
ffmpeg conversion failed: Audio conversion failed: Invalid data found when processing input
```

---

## سيناريو 4: ملف WAV لم يُنشأ ❌

```
2026-01-30 14:45:33 - transcribe_cli.utils.youtube - INFO - Starting yt-dlp audio download to: C:\Users\basel\AppData\Local\Temp\tmpghi3456
2026-01-30 14:45:45 - transcribe_cli.utils.youtube - INFO - yt-dlp exit code: 0
2026-01-30 14:45:45 - transcribe_cli.utils.youtube - INFO - Downloaded audio file: C:\Users\basel\AppData\Local\Temp\tmpghi3456\video123.webm (5120000 bytes)
2026-01-30 14:45:45 - transcribe_cli.utils.youtube - INFO - Converting to WAV: video123.webm -> video123.wav
# (ffmpeg يعمل لكن لا ينشئ ملف)
2026-01-30 14:45:55 - transcribe_cli.utils.youtube - ERROR - ffmpeg conversion failed: WAV file not created after conversion: C:\Users\basel\AppData\Local\Temp\tmpghi3456\video123.wav
```

**في Streamlit UI:**
```
❌ فشل تنزيل الصوت:
ffmpeg conversion failed: WAV file not created after conversion: C:\Users\basel\AppData\Local\Temp\tmpghi3456\video123.wav
```

---

## سيناريو 5: لم يُعثر على ملفات صوتية ❌

```
2026-01-30 14:50:11 - transcribe_cli.utils.youtube - INFO - Starting yt-dlp audio download to: C:\Users\basel\AppData\Local\Temp\tmpjkl7890
2026-01-30 14:50:11 - transcribe_cli.utils.youtube - DEBUG - yt-dlp command: yt-dlp ...
2026-01-30 14:50:18 - transcribe_cli.utils.youtube - INFO - yt-dlp exit code: 0
2026-01-30 14:50:18 - transcribe_cli.utils.youtube - DEBUG - yt-dlp stdout (first 500 chars): [download] 100% complete
# (لكن لم يُنزّل ملفات - ربما فيديو بدون صوت)
```

**في Streamlit UI:**
```
❌ فشل تنزيل الصوت:
Audio download failed: no audio files found in C:\Users\basel\AppData\Local\Temp\tmpjkl7890. Expected formats: m4a, webm, opus, mp3, etc.
```

---

## ملاحظات للتشخيص

### 1. مستويات Logging
- **INFO**: خطوات رئيسية (بدء التنزيل، exit codes، أحجام الملفات)
- **DEBUG**: تفاصيل كاملة (أوامر yt-dlp، stdout/stderr)
- **ERROR**: أخطاء فشل (ffmpeg errors)

### 2. تفعيل DEBUG logging
لرؤية كل التفاصيل، عدّل في `app.py`:
```python
logging.basicConfig(
    level=logging.DEBUG,  # بدل INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 3. فحص الملفات المؤقتة
لحفظ الملفات المؤقتة للفحص، عطّل السطر في `process_youtube()`:
```python
# finally:
#     if temp_dir.exists():
#         shutil.rmtree(temp_dir, ignore_errors=True)
```

ثم ابحث عن المجلد في: `C:\Users\basel\AppData\Local\Temp\tmp*`

### 4. أوامر تشخيص يدوية
```bash
# اختبر yt-dlp يدوياً:
yt-dlp --no-playlist -x --audio-format best --audio-quality 0 -o "test_%(id)s.%(ext)s" "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# اختبر ffmpeg يدوياً:
ffmpeg -i test_dQw4w9WgXcQ.opus -acodec pcm_s16le -ar 16000 -ac 1 -y test_output.wav
```

### 5. سيناريوهات شائعة

| الخطأ | السبب | الحل |
|------|-------|------|
| `exit code 1` | فيديو خاص/محذوف | تحقق من الرابط |
| `Video unavailable` | قيود جغرافية | استخدم VPN أو جرّب فيديو آخر |
| `ffmpeg not found` | ffmpeg غير مثبت | ثبّت ffmpeg وأضفه لـ PATH |
| `no audio files found` | فيديو بدون صوت | جرّب source="captions" |
| `Timeout` | اتصال بطيء | زد timeout في subprocess.run |
