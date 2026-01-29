# 🚀 دليل التشغيل الكامل - transcribe-cli

## ✅ المشروع جاهز - أوامر التشغيل

### 1. التثبيت والإعداد

```powershell
# الانتقال إلى مجلد المشروع
cd "C:\Users\basel\Downloads\OPEAN AI\transcribe-cli"

# إنشاء البيئة الافتراضية
python -m venv .venv

# تفعيل البيئة (Windows PowerShell)
.venv\Scripts\Activate.ps1

# أو (Windows CMD)
.venv\Scripts\activate.bat

# تثبيت المشروع
pip install -e .

# تثبيت مع أدوات التطوير (للاختبارات)
pip install -e ".[dev]"
```

### 2. إعداد البيئة

```powershell
# نسخ ملف البيئة
copy .env.example .env

# تحرير .env وإضافة مفتاح OpenAI
notepad .env
# ضع: OPENAI_API_KEY=sk-your-actual-key-here
```

**محتوى ملف .env:**
```env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
# OPENAI_MODEL=whisper-1
# OPENAI_API_BASE=https://api.openai.com/v1
```

### 3. التشغيل - أمثلة عملية

#### أ) تحويل ملف واحد

```powershell
# عرض المساعدة
transcribe --help

# تحويل ملف صوتي إلى نص عربي
transcribe ".\samples\sample.wav" --lang ar --format text --out .\out

# تحويل فيديو إلى نص عربي
transcribe ".\video.mp4" --lang ar --format text --out .\out

# تحويل مع ترجمة SRT (للفيديوهات)
transcribe ".\video.mp4" --lang ar --format srt --out .\out

# تحويل مع JSON (يحتوي على كل البيانات + timestamps)
transcribe ".\audio.mp3" --lang ar --format json --out .\out

# تحويل مع VTT (Web Video Text Tracks)
transcribe ".\video.mp4" --lang ar --format vtt --out .\out

# نص إنجليزي
transcribe ".\english_audio.wav" --lang en --format text --out .\out
```

#### ب) معالجة مجلد كامل

```powershell
# معالجة جميع الملفات في مجلد
transcribe batch ".\samples" --lang ar --format text --out .\out

# معالجة مجلد مع SRT
transcribe batch ".\videos" --lang ar --format srt --out .\out
```

#### ج) خيارات متقدمة

```powershell
# مع diarization (فصل المتحدثين - إن كان مدعوماً)
transcribe ".\meeting.mp4" --lang ar --format text --diarize true --out .\out

# تقسيم إلى أجزاء أكبر (10 دقائق بدلاً من 5)
transcribe ".\long_video.mp4" --lang ar --chunk-minutes 10 --out .\out

# استخدام نموذج مخصص
transcribe ".\audio.wav" --lang ar --model whisper-1 --out .\out

# مع glossary (لاستبدال مصطلحات محددة)
transcribe ".\lecture.mp4" --lang ar --glossary .\terms.txt --format text --out .\out

# مع verbose (لرؤية التفاصيل)
transcribe ".\file.mp4" --lang ar --format text --verbose --out .\out

# بدون استئناف (إعادة المعالجة من البداية)
transcribe ".\file.mp4" --lang ar --resume false --out .\out
```

#### د) إنشاء ملف Glossary

إنشاء ملف `terms.txt` لاستبدال المصطلحات:

```text
AI => الذكاء الاصطناعي
machine learning => تعلم الآلة
deep learning => التعلم العميق
API => واجهة برمجية
```

ثم استخدمه:
```powershell
transcribe ".\lecture.mp4" --glossary .\terms.txt --lang ar --format text
```

### 4. تشغيل الاختبارات

```powershell
# تشغيل جميع الاختبارات
pytest

# مع تقرير التغطية
pytest --cov=transcribe_cli --cov-report=html

# اختبار ملف محدد
pytest tests/test_cli_args.py

# مع verbose
pytest -v

# فتح تقرير التغطية
start htmlcov\index.html
```

---

## ⚠️ أهم 3 نقاط فشل محتملة وكيفية إصلاحها

### **1. خطأ: ffmpeg not found**

**الرسالة:**
```
FFmpegError: ffmpeg is not installed or not in PATH.
Install ffmpeg: Download ffmpeg from https://ffmpeg.org/download.html and add to PATH
```

**السبب:** ffmpeg غير مثبت أو غير موجود في PATH

**الحل للـ Windows:**

#### الطريقة 1: تحميل يدوي
```powershell
# 1. حمّل ffmpeg من: https://www.gyan.dev/ffmpeg/builds/
#    اختر: ffmpeg-release-essentials.zip

# 2. استخرج إلى: C:\ffmpeg

# 3. أضف إلى PATH مؤقتاً (للجلسة الحالية):
$env:Path += ";C:\ffmpeg\bin"

# 4. للتحقق:
ffmpeg -version
```

#### الطريقة 2: إضافة دائمة لـ PATH
```
1. اضغط Windows + R
2. اكتب: sysdm.cpl
3. تبويب Advanced > Environment Variables
4. تحت System Variables، اختر Path > Edit
5. اضغط New وأضف: C:\ffmpeg\bin
6. اضغط OK وأعد فتح PowerShell
7. تحقق: ffmpeg -version
```

#### الطريقة 3: باستخدام Chocolatey (إن كان مثبتاً)
```powershell
choco install ffmpeg
```

**الحل للـ macOS:**
```bash
brew install ffmpeg
```

**الحل للـ Linux:**
```bash
sudo apt-get install ffmpeg  # Ubuntu/Debian
sudo yum install ffmpeg       # CentOS/RHEL
```

**التحقق من التثبيت:**
```powershell
ffmpeg -version
# يجب أن يظهر:
# ffmpeg version 6.x.x ...
```

---

### **2. خطأ: OPENAI_API_KEY not set**

**الرسالة:**
```
ValueError: Configuration error: 1 validation error for Settings
openai_api_key
  Value error, OPENAI_API_KEY not set. Please create a .env file and set your API key.
```

**السبب:** ملف `.env` غير موجود أو المفتاح خاطئ أو فارغ

**الحل:**

#### الخطوة 1: إنشاء ملف .env
```powershell
# تأكد من وجود ملف .env
if (!(Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "تم إنشاء ملف .env - يرجى تحريره وإضافة المفتاح"
}

# افتح الملف
notepad .env
```

#### الخطوة 2: أضف المفتاح الصحيح
يجب أن يكون محتوى الملف:
```env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**ملاحظات مهمة:**
- ✅ لا تضع المفتاح بين علامات تنصيص
- ✅ لا توجد مسافات قبل أو بعد علامة =
- ✅ المفتاح يبدأ عادة بـ `sk-` أو `sk-proj-`
- ❌ لا تترك القيمة `your-api-key-here`

#### الخطوة 3: احصل على المفتاح من OpenAI
```
1. اذهب إلى: https://platform.openai.com/api-keys
2. سجل الدخول
3. اضغط "Create new secret key"
4. انسخ المفتاح وضعه في .env
```

#### التحقق من المفتاح:
```powershell
# اختبر أن المفتاح موجود
python -c "from transcribe_cli.config import load_settings; s = load_settings(); print('API Key loaded:', s.openai_api_key[:20] + '...')"

# يجب أن يظهر:
# API Key loaded: sk-proj-xxxxxxxxxxxx...
```

---

### **3. خطأ: Model not supported / Diarization failed**

**الرسالة:**
```
OpenAITranscriptionError: API error 400: Model 'gpt-4o-mini-transcribe' not found
# أو
WARNING: Diarization not supported, using standard transcription
```

**السبب:** النموذج المحدد غير موجود أو diarization غير مدعوم حالياً

**الحل:**

#### استخدم النموذج الافتراضي
```powershell
# استخدم whisper-1 (الأكثر استقرارًا وتوفراً)
transcribe ".\file.mp4" --model whisper-1 --lang ar --format text --out .\out
```

#### النماذج الموصى بها (2026)
```powershell
# النموذج الافتراضي (موثوق، متاح دائماً)
--model whisper-1

# للتحقق من النماذج المتاحة:
# راجع: https://platform.openai.com/docs/models/whisper
```

#### إذا فشل Diarization
```powershell
# البرنامج سيتراجع تلقائياً إلى transcription عادي
# ستظهر رسالة تحذير فقط:
# "Diarization not supported, using standard transcription"

# لتجنب المحاولة من الأساس:
transcribe ".\file.mp4" --diarize false --lang ar --out .\out
```

#### استكشاف المشكلة
```powershell
# استخدم verbose لرؤية التفاصيل
transcribe ".\file.mp4" --model whisper-1 --verbose --out .\out

# جرّب بدون خيارات إضافية
transcribe ".\file.mp4" --lang ar --format text --out .\out
```

---

## 🔧 مشاكل إضافية محتملة

### خطأ: Permission denied عند الكتابة

**الحل:**
```powershell
# تأكد من صلاحيات الكتابة على مجلد الإخراج
New-Item -ItemType Directory -Force -Path .\out

# امنح صلاحيات كاملة
icacls .\out /grant "$env:USERNAME:(OI)(CI)F"

# أو اختر مجلد آخر لديك صلاحيات عليه
transcribe ".\file.mp4" --out "$env:USERPROFILE\Documents\transcriptions"
```

### خطأ: Module not found

**الحل:**
```powershell
# تأكد من تفعيل البيئة الافتراضية
.venv\Scripts\Activate.ps1

# أعد التثبيت
pip uninstall transcribe-cli -y
pip install -e .

# تحقق من التثبيت
transcribe --help
```

### خطأ: Request timeout

**الحل:**
```powershell
# أضف إلى ملف .env لزيادة timeout
echo "REQUEST_TIMEOUT=600" >> .env

# أو قلل حجم الأجزاء
transcribe ".\file.mp4" --chunk-minutes 3 --out .\out
```

### خطأ: Rate limit (429 Too Many Requests)

**الحل:**
```
البرنامج يعيد المحاولة تلقائياً مع exponential backoff
إذا استمر الخطأ:
- انتظر دقائق قليلة
- تحقق من حد الاستخدام في: https://platform.openai.com/usage
- قد تحتاج لترقية الحساب
```

### خطأ: File too large

**الحل:**
```powershell
# قلل حجم الأجزاء
transcribe ".\large_file.mp4" --chunk-minutes 3 --max-bytes-per-chunk 10485760 --out .\out

# أو عالج الملف يدوياً لتقسيمه أولاً
```

---

## 📊 بنية المشروع

```
transcribe-cli/
├── .env.example              # مثال على ملف البيئة
├── .gitignore               # ملفات Git المستثناة
├── README.md                # الوثائق الرئيسية
├── SETUP_GUIDE.md           # هذا الملف
├── pyproject.toml           # إعدادات المشروع
├── samples/                 # مجلد للملفات التجريبية
│   └── README.md
├── src/transcribe_cli/
│   ├── __init__.py
│   ├── cli.py               # واجهة CLI الرئيسية
│   ├── config.py            # إدارة الإعدادات
│   ├── adapters/
│   │   ├── __init__.py
│   │   └── openai_client.py # OpenAI API client (مع retries)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── chunking.py      # تقسيم الصوت + checkpoint/resume
│   │   ├── pipeline.py      # Pipeline رئيسي للمعالجة
│   │   └── postprocess.py   # معالجة النصوص + glossary
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── ffmpeg.py        # استخراج الصوت من الفيديو
│   │   ├── fs.py            # عمليات الملفات الآمنة
│   │   └── logging.py       # نظام Logging
│   └── writers/
│       ├── __init__.py
│       ├── text_writer.py   # كتابة نص عادي
│       ├── json_writer.py   # كتابة JSON مع metadata
│       ├── srt_writer.py    # كتابة ترجمة SRT
│       └── vtt_writer.py    # كتابة ترجمة VTT
└── tests/
    ├── __init__.py
    ├── test_cli_args.py          # اختبار CLI arguments
    ├── test_chunking_stitch.py   # اختبار التقسيم والدمج
    └── test_writers.py           # اختبار الكتابة

الملفات المُنشأة عند التشغيل:
├── .env                     # مفتاح API (لا يُرفع لـ Git)
├── out/                     # مجلد الإخراج
│   ├── .checkpoints/        # نقاط الاستئناف
│   └── [output files]       # الملفات الناتجة
└── .venv/                   # البيئة الافتراضية
```

---

## 🎯 سيناريوهات استخدام عملية

### السيناريو 1: تفريغ محاضرة مسجلة

```powershell
# محاضرة فيديو طويلة (ساعة مثلاً)
transcribe ".\lecture_arabic.mp4" `
  --lang ar `
  --format text `
  --chunk-minutes 10 `
  --out .\lectures

# النتيجة: lectures\lecture_arabic_transcript.txt
```

### السيناريو 2: ترجمة فيديو YouTube (بعد تحميله)

```powershell
# افترض أنك حملت الفيديو
transcribe ".\downloaded_video.mp4" `
  --lang ar `
  --format srt `
  --out .\subtitles

# النتيجة: subtitles\downloaded_video_transcript.srt
# يمكنك رفعه كترجمة للفيديو
```

### السيناريو 3: تفريغ اجتماع

```powershell
# تسجيل اجتماع Zoom
transcribe ".\meeting_recording.mp4" `
  --lang ar `
  --format json `
  --diarize true `
  --out .\meetings

# النتيجة: meetings\meeting_recording_transcript.json
# يحتوي على النص + timestamps + metadata
```

### السيناريو 4: معالجة دفعة من البودكاست

```powershell
# مجلد به عدة حلقات
transcribe batch ".\podcast_episodes" `
  --lang ar `
  --format text `
  --out .\transcripts

# ستتم معالجة كل حلقة وإنشاء ملف نصي لكل منها
```

### السيناريو 5: مع مصطلحات تقنية

```powershell
# أنشئ ملف tech_terms.txt:
# Machine Learning => تعلم الآلة
# API => واجهة برمجية
# Cloud Computing => الحوسبة السحابية

transcribe ".\tech_talk.mp4" `
  --lang ar `
  --glossary .\tech_terms.txt `
  --format text `
  --out .\tech_transcripts
```

---

## 🔒 الأمان والخصوصية

### ✅ ما يفعله البرنامج:
- قراءة API key من `.env` فقط (لا يطبع في logs)
- إنشاء ملفات مؤقتة في مجلد آمن
- حذف الملفات المؤقتة تلقائياً بعد الانتهاء
- التحقق من المسارات (path traversal protection)
- عدم طباعة محتوى النصوص في console

### ❌ ما لا يفعله:
- لا يرسل بياناتك لأي طرف ثالث (فقط OpenAI API)
- لا يخزن API key في أي مكان غير `.env`
- لا يحفظ نسخ من الملفات المؤقتة

### 🔐 توصيات:
1. **لا تشارك ملف `.env`** أبداً
2. أضف `.env` إلى `.gitignore` (موجود أصلاً)
3. احذف الملفات الحساسة بعد المعالجة
4. استخدم مفاتيح API منفصلة لكل مشروع

---

## 📈 تحسين الأداء

### لتسريع المعالجة:
```powershell
# أجزاء أكبر (أقل requests)
transcribe ".\file.mp4" --chunk-minutes 10

# معالجة متوازية (في المستقبل - حالياً متسلسلة)
# يمكنك تشغيل عدة نوافذ terminal لملفات مختلفة
```

### لتقليل التكلفة:
```powershell
# استخدم النموذج الأرخص
transcribe ".\file.mp4" --model whisper-1

# قلل حجم الملف قبل المعالجة باستخدام ffmpeg:
ffmpeg -i input.mp4 -ac 1 -ar 16000 output.wav
transcribe ".\output.wav"
```

---

## 🆘 الحصول على المساعدة

### الأوامر المفيدة:
```powershell
# عرض المساعدة العامة
transcribe --help

# عرض مساعدة أمر batch
transcribe batch --help

# تشغيل مع verbose لرؤية التفاصيل
transcribe ".\file.mp4" --verbose

# تشغيل الاختبارات للتأكد من سلامة التثبيت
pytest -v
```

### معلومات المشروع:
- **الإصدار:** 1.0.0
- **Python:** 3.11+
- **الترخيص:** MIT
- **المتطلبات:** Python 3.11+, ffmpeg

### روابط مفيدة:
- OpenAI Whisper API: https://platform.openai.com/docs/guides/speech-to-text
- OpenAI Usage: https://platform.openai.com/usage
- ffmpeg Downloads: https://ffmpeg.org/download.html

---

## ✨ الخلاصة

### التثبيت السريع (3 خطوات):
```powershell
# 1. التثبيت
cd "C:\Users\basel\Downloads\OPEAN AI\transcribe-cli"
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .

# 2. الإعداد
copy .env.example .env
notepad .env  # ضع API key

# 3. التشغيل
transcribe ".\your_file.mp4" --lang ar --format text --out .\out
```

### الاستخدام اليومي:
```powershell
# فيديو -> نص
transcribe ".\video.mp4" --lang ar --format text

# فيديو -> ترجمة
transcribe ".\video.mp4" --lang ar --format srt

# مجلد كامل
transcribe batch ".\folder" --lang ar --format text
```

**جاهز للاستخدام! 🎉**
