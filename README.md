# transcribe-cli

أداة CLI محلية لتحويل الفيديو/الصوت إلى نص باستخدام OpenAI Speech-to-Text API.

## المتطلبات

- **Python 3.11+**
- **ffmpeg** (لاستخراج الصوت من الفيديو)
- **yt-dlp** (لتفريغ روابط YouTube - يعتمد على ffmpeg في وضع الصوت)

### تثبيت ffmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg
```

**Windows:**
قم بتحميل ffmpeg من [ffmpeg.org](https://ffmpeg.org/download.html) وأضف المجلد إلى PATH.

### ملاحظة خاصة بـ YouTube

ميزة تفريغ YouTube تستخدم **yt-dlp** وتحتاج **ffmpeg** عند استخدام المصدر `audio`.
تأكد من أن ffmpeg متاح في PATH وإلا سيفشل تنزيل/تحويل الصوت.

## التثبيت

1. **استنسخ المشروع أو حمّله:**
   ```bash
   cd transcribe-cli
   ```

2. **أنشئ بيئة افتراضية:**
   ```bash
   python -m venv .venv
   ```

3. **فعّل البيئة الافتراضية:**
   
   **macOS/Linux:**
   ```bash
   source .venv/bin/activate
   ```
   
   **Windows (CMD):**
   ```cmd
   .venv\Scripts\activate.bat
   ```
   
   **Windows (PowerShell):**
   ```powershell
   .venv\Scripts\Activate.ps1
   ```

4. **ثبّت الحزمة:**
   ```bash
   pip install -e .
   ```

5. **للتطوير (مع أدوات الاختبار):**
   ```bash
   pip install -e ".[dev]"
   ```

## إعداد البيئة

### الخطوة 1: إنشاء ملف .env

انسخ ``.env.example`` إلى ``.env``:

**Windows (CMD):**
```cmd
copy .env.example .env
```

**Windows (PowerShell):**
```powershell
cp .env.example .env
```

**macOS/Linux:**
```bash
cp .env.example .env
```

### الخطوة 2: إضافة مفتاح OpenAI API

افتح ملف ``.env`` وأضف مفتاح API الخاص بك:

**Windows (CMD):**
```cmd
notepad .env
```

**Windows (PowerShell):**
```powershell
code .env
# أو
notepad .env
```

**macOS/Linux:**
```bash
nano .env
```

**محتوى الملف:**
```env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# اختياري:
# OPENAI_MODEL=whisper-1
# OPENAI_API_BASE=https://api.openai.com/v1
```

### الخطوة 3: الحصول على مفتاح API

1. اذهب إلى: https://platform.openai.com/api-keys
2. سجّل الدخول بحسابك
3. اضغط **"Create new secret key"**
4. انسخ المفتاح (يبدأ بـ `sk-proj-`)
5. ألصقه في ملف `.env`

### التحقق من الإعداد

```powershell
# بعد تعيين الملف، جرّب:
transcribe --help

# يجب أن يظهر دون أخطاء
```

## الاستخدام

### واجهة الويب (Streamlit) 🌐

**أسهل طريقة للاستخدام - واجهة بصرية في المتصفح:**

```powershell
# تشغيل الواجهة
transcribe-ui
```

**سيتم فتح المتصفح تلقائياً مع الواجهة التي تحتوي على:**
- 📤 رفع الملفات (drag & drop)
- 🌐 اختيار اللغة
- 📄 اختيار صيغة الخرج (Text, JSON, SRT, VTT)
- 👥 تمييز المتحدثين
- ⬇️ تحميل النتائج مباشرة

**مميزات الواجهة:**
- ✅ سهلة الاستخدام - لا حاجة لكتابة أوامر
- ✅ معاينة مباشرة للنتائج
- ✅ دعم العربية والإنجليزية
- ✅ تصميم احترافي مع Streamlit

---

### سطر الأوامر (CLI) 💻

### اختبار سريع (Smoke Test)

**على Windows:**
```powershell
# 1. تأكد من إعداد .env مع مفتاح API

# 2. اختبر الأمر
transcribe --help

# 3. إذا كان لديك ملف صوتي تجريبي:
transcribe "./samples/sample.wav" --lang ar --format text --out ./out

# أو فقط لعرض مساعدة الأمر:
transcribe --help
```

### تفريغ YouTube

**Captions (سريع):**
```bash
transcribe youtube "https://www.youtube.com/watch?v=VIDEO_ID" --source captions --lang ar --out ./out
```

**Audio (مرن):**
```bash
transcribe youtube "https://www.youtube.com/watch?v=VIDEO_ID" --source audio --lang ar --format text --out ./out
```

### تحويل ملف واحد

**فيديو:**
```bash
transcribe ./video.mp4 --lang ar --format text --out ./output
```

**صوت:**
```bash
transcribe ./audio.wav --lang ar --format srt --out ./output
```

**مع diarization (فصل المتحدثين):**
```bash
transcribe ./meeting.mp4 --lang en --diarize true --format text --out ./output
```

### معالجة دفعة من الملفات

```bash
transcribe batch ./media_folder --lang ar --format text --out ./output
```

## الخيارات المتاحة

| الخيار | الوصف | القيمة الافتراضية |
|--------|-------|-------------------|
| `--lang` | اللغة (ar, en, fr, etc.) | `ar` |
| `--model` | نموذج OpenAI (**whisper-1 موصى به**) | `whisper-1` |
| `--format` | تنسيق الإخراج (text, json, srt, vtt) | `text` |
| `--out` | مجلد الإخراج | `./out` |
| `--diarize` | فصل المتحدثين (true/false) | `false` |
| `--chunk-minutes` | حجم القطعة بالدقائق | `5` |
| `--max-bytes-per-chunk` | الحد الأقصى (يُفرض حد نهائي 25MB) | `25MB` |
| `--glossary` | ملف مصطلحات للاستبدال | - |
| `--resume` | استئناف من نقطة التوقف | `true` |
| `--verbose` | إظهار معلومات تفصيلية | `false` |

## قيود مهمة ⚠️

### حد حجم الملف: 25MB
- **OpenAI Transcriptions API**: تقبل ملفات صوتية **حد أقصى 25MB** لكل طلب
- **آلية الـ chunking**: يتم تقسيم الملفات تلقائياً إلى أجزاء < 25MB
- **الملفات الطويلة**: مدة القطعة تُقلّل تلقائياً لضمان عدم تجاوز 25MB

### تنسيقات الإخراج
- **text** ✅: دائماً متاح
- **json** ✅: النص + metadata + timestamps (إن توفرت)
- **srt/vtt** ⚠️: **يتطلب timestamps من API**
  - إذا لم تتوفر: `ValueError: SRT format requires timestamps/segments`
  - الحل: استخدم `--format text` أو `--format json`

### النماذج والمتطلبات
- **Default Model**: `whisper-1` (الأكثر استقراراً) ✅
- **Diarization**: إذا فشل → **fallback تلقائي** إلى transcription عادي (مع تحذير واحد)

## أمثلة متقدمة

**مع glossary لاستبدال المصطلحات:**
```bash
transcribe ./lecture.mp4 --glossary ./terms.txt --format text
```

ملف `terms.txt`:
```
AI => الذكاء الاصطناعي
machine learning => تعلم الآلة
```

**استئناف عملية متوقفة:**
```bash
transcribe ./large_file.mp4 --resume true
```

**تنسيق JSON مع metadata كامل:**
```bash
transcribe ./interview.wav --format json --out ./output
```

## البنية

```
transcribe-cli/
├── src/transcribe_cli/
│   ├── cli.py              # واجهة CLI
│   ├── config.py           # إعدادات التطبيق
│   ├── core/               # منطق المعالجة
│   ├── adapters/           # OpenAI API client
│   ├── utils/              # أدوات مساعدة
│   └── writers/            # كتابة الملفات
└── tests/                  # الاختبارات
```

## الاختبارات

```bash
pytest
```

**مع coverage:**
```bash
pytest --cov=transcribe_cli --cov-report=html
```

## النشر على Render (Deploy to Render)

يمكنك نشر التطبيق على Render باستخدام Docker:

### 1. رفع المشروع إلى GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/transcribe-cli.git
git push -u origin main
```

### 2. إنشاء Web Service على Render

1. اذهب إلى [Render Dashboard](https://dashboard.render.com/)
2. اضغط **New** → **Web Service**
3. اربط مستودع GitHub الخاص بك
4. اختر **Docker** كبيئة التشغيل (Runtime)
5. سيكتشف Render ملف `Dockerfile` تلقائياً

### 3. إضافة Environment Variables

في إعدادات Web Service، أضف المتغيرات التالية:

| Key | Value | ملاحظات |
|-----|-------|---------|
| `OPENAI_API_KEY` | `sk-proj-...` | **إلزامي** - مفتاح OpenAI API الخاص بك |
| `OPENAI_MODEL` | `whisper-1` | اختياري - النموذج الافتراضي (whisper-1) |
| `PORT` | `8501` | اختياري - Render يحدده تلقائياً |

### 4. النشر والاختبار

1. اضغط **Create Web Service**
2. انتظر حتى يكتمل البناء (Build) والنشر (Deploy)
3. افتح الرابط الرئيسي (Main URL) الذي يوفره Render
4. اختبر التطبيق:
   - ✅ رفع ملف صوت/فيديو محلي
   - ✅ تفريغ رابط YouTube (audio أو captions)
   - ✅ تنزيل النتائج (TXT, JSON, SRT, VTT)
   - ✅ نسخ النص باستخدام زر النسخ

### اختبار محلي باستخدام Docker

قبل النشر، يمكنك اختبار Docker محلياً:

```bash
# بناء الصورة
docker build -t transcribe-ui .

# تشغيل الحاوية
docker run -p 8501:8501 -e OPENAI_API_KEY=sk-proj-XXX transcribe-ui
```

ثم افتح المتصفح على `http://localhost:8501`

## الأمان

- ✅ لا يتم تخزين API key في الكود
- ✅ التحقق من صحة المسارات (path traversal protection)
- ✅ حذف الملفات المؤقتة تلقائيًا
- ✅ لا يتم طباعة محتوى النصوص في console
- ✅ Sanitization لأسماء الملفات

## استكشاف الأخطاء

### خطأ: ffmpeg not found
تأكد من تثبيت ffmpeg وإضافته إلى PATH.

### خطأ: API key missing
تحقق من وجود ملف `.env` وأن `OPENAI_API_KEY` مضبوط بشكل صحيح.

### خطأ: ValueError - Timestamps not available
```
SRT format requires timestamps/segments.
Use --format text/json or choose a model/response_format that returns segments.
```
**الحل**: استخدم `--format text` أو `--format json` بدلاً من `--format srt/vtt`

## الترخيص

MIT License
