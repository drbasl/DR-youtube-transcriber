"""
Streamlit UI for transcribe-cli
Provides a web interface for uploading and transcribing audio/video files
"""
import asyncio
import logging
import traceback
import shutil
import tempfile
from pathlib import Path
from typing import Optional
import streamlit as st
import streamlit.components.v1 as components

from transcribe_cli.config import load_settings, TranscribeConfig
from transcribe_cli.core.pipeline import transcribe_file
from transcribe_cli.core.postprocess import normalize_whitespace, format_arabic_text
from transcribe_cli.utils.youtube import download_captions_text, download_audio, strip_captions_timestamps, strip_captions_timestamps_keep_lines

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Helper functions for safe data extraction
def extract_segments(resp):
    """Safely extract segments from response (dict or object)"""
    if resp is None:
        return []
    if isinstance(resp, dict):
        # Check direct segments key
        if "segments" in resp:
            return resp["segments"]
        # Check nested data.segments
        if "data" in resp and isinstance(resp["data"], dict) and "segments" in resp["data"]:
            return resp["data"]["segments"]
        return []
    # Try as object attribute
    segments = getattr(resp, "segments", [])
    return segments or []


def extract_text(resp):
    """Safely extract text from response"""
    if resp is None:
        return ""
    if isinstance(resp, dict):
        return resp.get("transcript", resp.get("text", ""))
    return getattr(resp, "transcript", getattr(resp, "text", ""))


def extract_metadata(resp, key, default=None):
    """Safely extract metadata from response"""
    if resp is None:
        return default
    if isinstance(resp, dict):
        return resp.get(key, default)
    return getattr(resp, key, default)


# Supported formats
SUPPORTED_AUDIO_FORMATS = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]
SUPPORTED_VIDEO_FORMATS = ["mp4", "webm", "avi", "mov", "mkv"]
ALL_FORMATS = SUPPORTED_AUDIO_FORMATS + SUPPORTED_VIDEO_FORMATS

# Language options
LANGUAGES = {
    "تلقائي (Auto)": None,
    "العربية (Arabic)": "ar",
    "English": "en",
    "Español": "es",
    "Français": "fr",
    "Deutsch": "de",
    "Italiano": "it",
    "Português": "pt",
    "Русский": "ru",
    "日本語": "ja",
    "中文": "zh",
    "한국어": "ko",
}

# Output formats
OUTPUT_FORMATS = {
    "نص (Text)": "text",
    "JSON (مع علامات زمنية)": "json",
    "SRT Subtitles": "srt",
    "WebVTT Subtitles": "vtt",
}


def configure_page():
    """Configure Streamlit page settings"""
    st.set_page_config(
        page_title="تفريغ الصوت والفيديو | Audio Transcription",
        page_icon="🎙️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
        <style>
        .main-header {
            text-align: center;
            padding: 0.75rem 0;
        }
        .app-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 0.5rem;
        }
        .card {
            background: #111827;
            border: 1px solid #1f2937;
            border-radius: 14px;
            padding: 1rem;
            box-shadow: 0 8px 20px rgba(0,0,0,0.2);
        }
        .toolbar {
            display: block;
            margin-top: 0.5rem;
        }
        .result-card textarea {
            height: 420px !important;
            overflow-y: auto !important;
            line-height: 1.8;
        }
        .success-box {
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            margin: 1rem 0;
        }
        .error-box {
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
            margin: 1rem 0;
        }
        .info-box {
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: #d1ecf1;
            border: 1px solid #bee5eb;
            color: #0c5460;
            margin: 1rem 0;
        }
        @media (max-width: 768px) {
            .main-header {
                font-size: 1.4rem;
            }
            .block-container {
                padding-left: 0.75rem !important;
                padding-right: 0.75rem !important;
            }
            .result-card textarea {
                height: 280px !important;
            }
            .toolbar [data-testid="stButton"] button,
            .toolbar [data-testid="stDownloadButton"] button {
                width: 100% !important;
            }
            [data-testid="column"] {
                width: 100% !important;
                flex: 1 1 100% !important;
            }
        }
        body { overflow-x: hidden; }
        </style>
    """, unsafe_allow_html=True)


def validate_settings() -> bool:
    """Validate OpenAI API key is configured"""
    try:
        settings = load_settings()
        if not settings.openai_api_key or settings.openai_api_key == "your-api-key-here":
            st.error("⚠️ **خطأ:** لم يتم تعيين مفتاح OpenAI API")
            st.info("""
                **لتشغيل التطبيق:**
                1. افتح ملف `.env` في مجلد المشروع
                2. أضف مفتاح API الخاص بك: `OPENAI_API_KEY=sk-...`
                3. احفظ الملف وأعد تشغيل التطبيق
                
                **للحصول على مفتاح API:** https://platform.openai.com/api-keys
            """)
            return False
        return True
    except Exception as e:
        st.error(f"❌ خطأ في التحقق من الإعدادات: {str(e)}")
        return False


def process_file(
    uploaded_file,
    language: Optional[str],
    output_format: str,
    enable_diarization: bool,
    max_chunk_size_mb: int,
    postprocess_enabled: bool,
    postprocess_mode: str
) -> tuple[Optional[dict], Optional[str]]:
    """
    Process uploaded file and return transcription result
    Returns: (result_text, error_message)
    """
    try:
        # Save uploaded file to temp directory
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = Path(tmp_file.name)
        
        try:
            # Create temp output directory
            output_dir = Path(tempfile.mkdtemp())
            
            # Create config
            settings = load_settings()
            config = TranscribeConfig(
                input_path=tmp_path,
                output_dir=output_dir,
                language=language if language else "ar",
                model=settings.openai_model,
                output_format=output_format,  # Pass format to enable verbose_json for SRT/VTT
                diarize=enable_diarization,
                max_bytes_per_chunk=max_chunk_size_mb * 1024 * 1024  # Convert MB to bytes
            )
            
            # Run transcription
            result = asyncio.run(transcribe_file(config))
            
            # Ensure chunking succeeded
            chunks_count = extract_metadata(result, "chunks_count", extract_metadata(result, "chunks"))
            if chunks_count is None:
                raise ValueError("chunking failed; check ffmpeg extraction")

            # Extract segments safely
            segments = extract_segments(result)
            if segments is None:
                if output_format in ["srt", "vtt"]:
                    return None, "❌ لا توجد timestamps/segments. استخدم صيغة 'نص' أو 'JSON' بدلاً من SRT/VTT."
                segments = []
            raw_text = extract_text(result)

            # Apply optional post-processing
            if postprocess_enabled and postprocess_mode == "formatted":
                processed_text = format_arabic_text(raw_text, language=language or "ar")
            else:
                processed_text = raw_text
            
            # Format output based on selected format
            if output_format == "text":
                output = processed_text
                
            elif output_format == "json":
                import json
                output = json.dumps({
                    "language": extract_metadata(result, "language"),
                    "duration": extract_metadata(result, "duration"),
                    "text": processed_text,
                    "segments": segments
                }, ensure_ascii=False, indent=2)
                
            elif output_format == "srt":
                if not segments:
                    return None, "❌ لا توجد timestamps/segments. استخدم صيغة 'نص' أو 'JSON' بدلاً من SRT. للحصول على timestamps، تأكد من استخدام response_format=verbose_json في API."
                # Generate SRT format
                output_lines = []
                seg_count = 0
                for seg in segments:
                    # Handle both dict and object
                    if isinstance(seg, dict):
                        text = seg.get("text", "")
                        start = seg.get("start")
                        end = seg.get("end")
                        speaker = seg.get("speaker")
                    else:
                        text = getattr(seg, "text", "")
                        start = getattr(seg, "start", None)
                        end = getattr(seg, "end", None)
                        speaker = getattr(seg, "speaker", None)
                    
                    if start is None or end is None:
                        continue
                    seg_count += 1
                    # Convert to SRT time format
                    start_time = f"{int(start // 3600):02d}:{int((start % 3600) // 60):02d}:{int(start % 60):02d},{int((start % 1) * 1000):03d}"
                    end_time = f"{int(end // 3600):02d}:{int((end % 3600) // 60):02d}:{int(end % 60):02d},{int((end % 1) * 1000):03d}"
                    speaker_prefix = f"[{speaker}] " if speaker else ""
                    output_lines.extend([
                        str(seg_count),
                        f"{start_time} --> {end_time}",
                        f"{speaker_prefix}{text}",
                        ""
                    ])
                output = "\n".join(output_lines) if output_lines else processed_text
                
            elif output_format == "vtt":
                if not segments:
                    return None, "❌ لا توجد timestamps/segments. استخدم صيغة 'نص' أو 'JSON' بدلاً من VTT. للحصول على timestamps، تأكد من استخدام response_format=verbose_json في API."
                # Generate WebVTT format
                output_lines = ["WEBVTT", ""]
                for seg in segments:
                    # Handle both dict and object
                    if isinstance(seg, dict):
                        text = seg.get("text", "")
                        start = seg.get("start")
                        end = seg.get("end")
                        speaker = seg.get("speaker")
                    else:
                        text = getattr(seg, "text", "")
                        start = getattr(seg, "start", None)
                        end = getattr(seg, "end", None)
                        speaker = getattr(seg, "speaker", None)
                    
                    if start is None or end is None:
                        continue
                    # Convert to WebVTT time format
                    start_time = f"{int(start // 3600):02d}:{int((start % 3600) // 60):02d}:{int(start % 60):02d}.{int((start % 1) * 1000):03d}"
                    end_time = f"{int(end // 3600):02d}:{int((end % 3600) // 60):02d}:{int(end % 60):02d}.{int((end % 1) * 1000):03d}"
                    speaker_prefix = f"[{speaker}] " if speaker else ""
                    output_lines.extend([
                        f"{start_time} --> {end_time}",
                        f"{speaker_prefix}{text}",
                        ""
                    ])
                output = "\n".join(output_lines) if len(output_lines) > 2 else processed_text
                
            else:
                output = processed_text

            # Prepare download JSON (text + metadata)
            import json
            download_json = json.dumps({
                "text": processed_text,
                "model": extract_metadata(result, "model"),
                "lang": extract_metadata(result, "language"),
                "duration_seconds": extract_metadata(result, "duration_seconds", extract_metadata(result, "duration")),
                "chunks_count": extract_metadata(result, "chunks_count", extract_metadata(result, "chunks", 0))
            }, ensure_ascii=False, indent=2)

            return {
                "display_text": output,
                "text": processed_text,
                "text_download": processed_text,
                "json_download": download_json,
                "output_format": output_format
            }, None
            
        finally:
            # Clean up temp files
            if tmp_path.exists():
                tmp_path.unlink()
            if output_dir.exists():
                shutil.rmtree(output_dir, ignore_errors=True)
                
    except ValueError as e:
        return None, f"خطأ في التحقق: {str(e)}"
    except Exception as e:
        return None, f"خطأ في المعالجة: {str(e)}"


def process_youtube(
    url: str,
    language: Optional[str],
    output_format: str,
    source: str,
    max_chunk_size_mb: int,
    postprocess_enabled: bool,
    postprocess_mode: str,
    raw_captions: bool = False,
    remove_timestamps: bool = True
) -> tuple[Optional[dict], Optional[str]]:
    """
    Process YouTube URL and return transcription result
    Returns: (result_dict, error_message)
    """
    try:
        temp_dir = Path(tempfile.mkdtemp())

        try:
            lang = language if language else "ar"

            if source == "captions":
                cleaned_text, segments, used_auto, raw_text = download_captions_text(url, lang, temp_dir)
                clean_text = strip_captions_timestamps(raw_text)
                clean_text = normalize_whitespace(clean_text)
                line_text = strip_captions_timestamps_keep_lines(raw_text)
                text = clean_text

                if postprocess_enabled and postprocess_mode == "formatted":
                    processed_text = format_arabic_text(text, language=lang)
                else:
                    processed_text = text

                if output_format in ["srt", "vtt"] and not segments:
                    return None, "❌ لا توجد timestamps/segments. استخدم صيغة 'نص' أو 'JSON' بدلاً من SRT/VTT."

                # Build output for display
                if output_format == "text":
                    if raw_captions:
                        display_text = raw_text
                    else:
                        display_text = clean_text if remove_timestamps else line_text
                elif output_format == "json":
                    import json
                    payload = {
                        "language": lang,
                        "text": clean_text,
                        "segments": segments,
                        "source": "captions",
                        "cleaned": bool(remove_timestamps)
                    }
                    if raw_captions:
                        payload["raw_text"] = raw_text
                    display_text = json.dumps(payload, ensure_ascii=False, indent=2)
                elif output_format == "srt":
                    output_lines = []
                    seg_count = 0
                    for seg in segments:
                        start = seg.get("start")
                        end = seg.get("end")
                        if start is None or end is None:
                            continue
                        seg_count += 1
                        start_time = f"{int(start // 3600):02d}:{int((start % 3600) // 60):02d}:{int(start % 60):02d},{int((start % 1) * 1000):03d}"
                        end_time = f"{int(end // 3600):02d}:{int((end % 3600) // 60):02d}:{int(end % 60):02d},{int((end % 1) * 1000):03d}"
                        output_lines.extend([
                            str(seg_count),
                            f"{start_time} --> {end_time}",
                            seg.get("text", ""),
                            ""
                        ])
                    display_text = "\n".join(output_lines)
                else:  # vtt
                    output_lines = ["WEBVTT", ""]
                    for seg in segments:
                        start = seg.get("start")
                        end = seg.get("end")
                        if start is None or end is None:
                            continue
                        start_time = f"{int(start // 3600):02d}:{int((start % 3600) // 60):02d}:{int(start % 60):02d}.{int((start % 1) * 1000):03d}"
                        end_time = f"{int(end // 3600):02d}:{int((end % 3600) // 60):02d}:{int(end % 60):02d}.{int((end % 1) * 1000):03d}"
                        output_lines.extend([
                            f"{start_time} --> {end_time}",
                            seg.get("text", ""),
                            ""
                        ])
                    display_text = "\n".join(output_lines)

                duration_seconds = None
                if segments:
                    duration_seconds = max(seg.get("end", 0) for seg in segments)

                import json
                download_payload = {
                    "text": clean_text,
                    "model": "youtube-captions",
                    "lang": lang,
                    "duration_seconds": duration_seconds,
                    "chunks_count": 0,
                    "source": "captions",
                    "cleaned": bool(remove_timestamps)
                }
                if raw_captions:
                    download_payload["raw_captions"] = raw_text

                download_json = json.dumps(download_payload, ensure_ascii=False, indent=2)

                warning = "⚠️ تم استخدام الترجمة التلقائية (دقة أقل)." if used_auto else None

                return {
                    "display_text": display_text,
                    "text": clean_text,
                    "text_download": clean_text if remove_timestamps else line_text,
                    "json_download": download_json,
                    "output_format": output_format,
                    "warning": warning,
                    "source": "captions",
                    "raw_text": raw_text,
                    "clean_text": clean_text,
                    "cleaned": bool(remove_timestamps)
                }, None

            # Audio path: download audio and use pipeline
            logger.info(f"Starting YouTube audio download for: {url}")
            audio_path = download_audio(url, temp_dir)
            logger.info(f"Audio downloaded successfully: {audio_path}")

            settings = load_settings()
            config = TranscribeConfig(
                input_path=audio_path,
                output_dir=temp_dir,
                language=lang,
                model=settings.openai_model,
                output_format=output_format,
                diarize=False,
                max_bytes_per_chunk=max_chunk_size_mb * 1024 * 1024
            )

            result = asyncio.run(transcribe_file(config))
            # Ensure chunking succeeded
            chunks_count = extract_metadata(result, "chunks_count", extract_metadata(result, "chunks"))
            if chunks_count is None:
                raise ValueError("chunking failed; check ffmpeg extraction")

            segments = extract_segments(result)
            if segments is None:
                if output_format in ["srt", "vtt"]:
                    return None, "❌ لا توجد timestamps/segments. استخدم صيغة 'نص' أو 'JSON' بدلاً من SRT/VTT."
                segments = []
            raw_text = extract_text(result)

            if postprocess_enabled and postprocess_mode == "formatted":
                processed_text = format_arabic_text(raw_text, language=lang)
            else:
                processed_text = raw_text

            if output_format in ["srt", "vtt"] and not segments:
                return None, "❌ لا توجد timestamps/segments. استخدم صيغة 'نص' أو 'JSON' بدلاً من SRT/VTT."

            # Reuse formatting logic from file path
            if output_format == "text":
                display_text = processed_text
            elif output_format == "json":
                import json
                display_text = json.dumps({
                    "language": extract_metadata(result, "language"),
                    "duration": extract_metadata(result, "duration"),
                    "text": processed_text,
                    "segments": segments
                }, ensure_ascii=False, indent=2)
            elif output_format == "srt":
                output_lines = []
                seg_count = 0
                for seg in segments:
                    start = seg.get("start") if isinstance(seg, dict) else getattr(seg, "start", None)
                    end = seg.get("end") if isinstance(seg, dict) else getattr(seg, "end", None)
                    text = seg.get("text", "") if isinstance(seg, dict) else getattr(seg, "text", "")
                    if start is None or end is None:
                        continue
                    seg_count += 1
                    start_time = f"{int(start // 3600):02d}:{int((start % 3600) // 60):02d}:{int(start % 60):02d},{int((start % 1) * 1000):03d}"
                    end_time = f"{int(end // 3600):02d}:{int((end % 3600) // 60):02d}:{int(end % 60):02d},{int((end % 1) * 1000):03d}"
                    output_lines.extend([
                        str(seg_count),
                        f"{start_time} --> {end_time}",
                        text,
                        ""
                    ])
                display_text = "\n".join(output_lines)
            else:  # vtt
                output_lines = ["WEBVTT", ""]
                for seg in segments:
                    start = seg.get("start") if isinstance(seg, dict) else getattr(seg, "start", None)
                    end = seg.get("end") if isinstance(seg, dict) else getattr(seg, "end", None)
                    text = seg.get("text", "") if isinstance(seg, dict) else getattr(seg, "text", "")
                    if start is None or end is None:
                        continue
                    start_time = f"{int(start // 3600):02d}:{int((start % 3600) // 60):02d}:{int(start % 60):02d}.{int((start % 1) * 1000):03d}"
                    end_time = f"{int(end // 3600):02d}:{int((end % 3600) // 60):02d}:{int(end % 60):02d}.{int((end % 1) * 1000):03d}"
                    output_lines.extend([
                        f"{start_time} --> {end_time}",
                        text,
                        ""
                    ])
                display_text = "\n".join(output_lines)

            import json
            download_json = json.dumps({
                "text": processed_text,
                "model": extract_metadata(result, "model"),
                "lang": extract_metadata(result, "language"),
                "duration_seconds": extract_metadata(result, "duration_seconds", extract_metadata(result, "duration")),
                "chunks_count": extract_metadata(result, "chunks_count", extract_metadata(result, "chunks", 0))
            }, ensure_ascii=False, indent=2)

            return {
                "display_text": display_text,
                "text": processed_text,
                "text_download": processed_text,
                "json_download": download_json,
                "output_format": output_format
            }, None

        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    except FileNotFoundError as e:
        error_msg = str(e)
        if "yt-dlp failed" in error_msg:
            return None, f"❌ فشل yt-dlp في التنزيل:\n{error_msg}"
        elif "ffmpeg conversion failed" in error_msg:
            return None, f"❌ فشل تحويل ffmpeg:\n{error_msg}"
        elif "Audio download failed" in error_msg or "not found" in error_msg:
            return None, f"❌ فشل تنزيل الصوت:\n{error_msg}"
        else:
            return None, f"❌ خطأ: {error_msg}"
    except Exception as e:
        return None, f"خطأ في المعالجة: {str(e)}"


def main():
    """Main Streamlit app"""
    configure_page()
    
    # Header
    st.markdown('<h1 class="main-header">🎙️ تفريغ الصوت والفيديو | Audio Transcription</h1>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Validate settings
    if not validate_settings():
        st.stop()
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ الإعدادات | Settings")
        
        # Language selection
        language_display = st.selectbox(
            "🌐 اللغة | Language",
            options=list(LANGUAGES.keys()),
            index=0,
            help="اختر لغة الصوت، أو اترك 'تلقائي' للكشف التلقائي"
        )
        language_code = LANGUAGES[language_display]
        
        # Output format
        format_display = st.selectbox(
            "📄 صيغة الخرج | Output Format",
            options=list(OUTPUT_FORMATS.keys()),
            index=0,
            help="اختر صيغة النص الناتج. ملاحظة: SRT/VTT يتطلبان timestamps من API"
        )
        output_format = OUTPUT_FORMATS[format_display]

        # Post-processing
        postprocess_enabled = st.checkbox(
            "🧹 تفعيل معالجة النص | Enable Post-processing",
            value=False,
            help="تفعيل تحسين النص العربي بشكل اختياري"
        )
        postprocess_mode_label = st.selectbox(
            "📝 نمط المعالجة | Mode",
            options=["Literal", "Formatted"],
            index=0,
            disabled=not postprocess_enabled,
            help="Literal = النص كما هو. Formatted = تنسيق خفيف (مسافات + إزالة تكرار + علامات بسيطة)"
        )
        postprocess_mode = "formatted" if postprocess_mode_label == "Formatted" else "literal"
        
        # Show warning for SRT/VTT
        if output_format in ["srt", "vtt"]:
            st.info("ℹ️ صيغ SRT/VTT تتطلب timestamps من API. إذا لم تتوفر، سيتم عرض النص العادي.")
        
        # Diarization
        enable_diarization = st.checkbox(
            "👥 تمييز المتحدثين | Speaker Diarization",
            value=False,
            help="محاولة تمييز المتحدثين المختلفين (تجريبي)"
        )
        
        # Advanced settings
        with st.expander("⚙️ إعدادات متقدمة | Advanced"):
            max_chunk_size = st.slider(
                "حجم القطعة الأقصى (MB) | Max Chunk Size",
                min_value=5,
                max_value=24,
                value=20,
                help="حجم القطع للملفات الكبيرة (الحد الأقصى لـ OpenAI: 25MB)"
            )
        
        st.markdown("---")
        st.markdown("**ℹ️ ملاحظات:**")
        st.markdown("""
        - **لا يوجد حد لحجم الملف** - التقسيم التلقائي مدعوم
        - كل جزء يُرسل للـ API: **< 25 MB** (حد OpenAI)
        - الصيغ المدعومة: MP3, MP4, WAV, M4A, WebM
        - SRT/VTT يتطلبان علامات زمنية من API
        """)
    
    # Main content
    st.markdown('<div class="app-container">', unsafe_allow_html=True)
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📁 رفع الملف | Upload File")

        tab_upload, tab_youtube = st.tabs(["📁 ملف", "▶️ YouTube"])

        with tab_upload:
            uploaded_file = st.file_uploader(
                "اختر ملف صوتي أو فيديو",
                type=ALL_FORMATS,
                help=f"الصيغ المدعومة: {', '.join(ALL_FORMATS)} | لا يوجد حد لحجم الملف - الملفات الكبيرة يتم تقسيمها تلقائياً"
            )

            if uploaded_file:
                # Display file info
                file_size_mb = uploaded_file.size / (1024 * 1024)
                st.info(f"""
                    **معلومات الملف:**
                    - الاسم: `{uploaded_file.name}`
                    - الحجم: `{file_size_mb:.2f} MB`
                    - النوع: `{uploaded_file.type}`
                """)

                # Check file size and show helpful info
                if file_size_mb > 100:
                    st.warning("⚠️ ملف كبير جداً! سيتم تقسيمه تلقائياً إلى أجزاء صغيرة للمعالجة. قد يستغرق بعض الوقت...")
                elif file_size_mb > 25:
                    st.info("ℹ️ سيتم تقسيم الملف تلقائياً إلى أجزاء < 25MB للتوافق مع OpenAI API")

                # Process button
                if st.button("🚀 ابدأ التفريغ | Start Transcription", type="primary", use_container_width=True):
                    with st.spinner("⏳ جارٍ المعالجة... | Processing..."):
                        try:
                            result, error = process_file(
                                uploaded_file,
                                language_code,
                                output_format,
                                enable_diarization,
                                max_chunk_size,
                                postprocess_enabled,
                                postprocess_mode
                            )

                            if error:
                                st.error(f"❌ {error}")
                            else:
                                if result.get("warning"):
                                    st.warning(result.get("warning"))
                                st.session_state['transcription_result'] = result
                                st.session_state['output_format'] = output_format
                                st.success("✅ تم التفريغ بنجاح! | Transcription completed!")
                        except Exception:
                            logger.exception("Upload transcription failed")
                            traceback.print_exc()
                            st.error("❌ حدث خطأ غير متوقع. راجع سجل التشغيل في الطرفية.")

        with tab_youtube:
            st.markdown("**تفريغ روابط YouTube**")
            youtube_url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")
            source_option = st.selectbox(
                "المصدر | Source",
                options=["captions", "audio"],
                index=0,
                help="captions أسرع إذا كانت الترجمة متوفرة. audio أبطأ لكنه يعمل مع أي فيديو."
            )

            remove_timestamps = True
            raw_captions = False
            if source_option == "captions":
                remove_timestamps = st.checkbox(
                    "إزالة التوقيت والوسوم",
                    value=True,
                    help="تنظيف النص بإزالة timestamps ووسوم VTT افتراضيًا"
                )
                raw_captions = st.checkbox(
                    "Raw captions",
                    value=False,
                    help="عرض/تنزيل النص الخام من VTT بدون تنظيف. الافتراضي: نص نظيف"
                )

                if st.button("مسح التوقيت الآن", use_container_width=True):
                    if "transcription_result" in st.session_state:
                        current = st.session_state["transcription_result"]
                        if current.get("source") == "captions" and current.get("raw_text"):
                            raw_text = current.get("raw_text", "")
                            clean_text = strip_captions_timestamps(raw_text)
                            clean_text = normalize_whitespace(clean_text)
                            line_text = strip_captions_timestamps_keep_lines(raw_text)

                            display_text = raw_text if raw_captions else (clean_text if remove_timestamps else line_text)
                            current["display_text"] = display_text
                            current["text"] = clean_text
                            current["text_download"] = clean_text if remove_timestamps else line_text
                            current["clean_text"] = clean_text
                            current["cleaned"] = bool(remove_timestamps)
                            st.session_state["transcription_result"] = current

            if st.button("🚀 ابدأ التفريغ من YouTube", type="primary", use_container_width=True):
                if not youtube_url.strip():
                    st.error("❌ الرجاء إدخال رابط YouTube صحيح")
                else:
                    with st.spinner("⏳ جارٍ المعالجة... | Processing..."):
                        try:
                            result, error = process_youtube(
                                youtube_url.strip(),
                                language_code,
                                output_format,
                                source_option,
                                max_chunk_size,
                                postprocess_enabled,
                                postprocess_mode,
                                raw_captions,
                                remove_timestamps
                            )

                            if error:
                                st.error(f"❌ {error}")
                            else:
                                if result.get("warning"):
                                    st.warning(result.get("warning"))
                                st.session_state['transcription_result'] = result
                                st.session_state['output_format'] = output_format
                                st.success("✅ تم التفريغ بنجاح! | Transcription completed!")
                        except Exception:
                            logger.exception("YouTube transcription failed")
                            traceback.print_exc()
                            st.error("❌ حدث خطأ غير متوقع. راجع سجل التشغيل في الطرفية.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="card result-card">', unsafe_allow_html=True)
        st.subheader("📝 النتيجة | Result")
        
        if 'transcription_result' in st.session_state:
            result = st.session_state['transcription_result']
            output_fmt = st.session_state.get('output_format', 'text')

            display_text = result.get("display_text", "")
            text_download = result.get("text_download", "")
            json_download = result.get("json_download", "")
            
            # Display result
            st.text_area(
                "النص المفرغ | Transcribed Text",
                value=display_text,
                height=420,
                key="result_display"
            )

            st.markdown('<div class="toolbar">', unsafe_allow_html=True)
            col_main, col_txt, col_json, col_copy = st.columns(4)

            # Main download for selected format
            file_extension = output_fmt if output_fmt in ['srt', 'vtt', 'json'] else 'txt'
            with col_main:
                st.download_button(
                    label=f"⬇️ تحميل | Download {file_extension.upper()}",
                    data=display_text,
                    file_name=f"transcription.{file_extension}",
                    mime="text/plain",
                    use_container_width=True
                )

            with col_txt:
                st.download_button(
                    label="⬇️ Download TXT",
                    data=text_download,
                    file_name="transcription.txt",
                    mime="text/plain",
                    use_container_width=True
                )

            with col_json:
                st.download_button(
                    label="⬇️ Download JSON",
                    data=json_download,
                    file_name="transcription.json",
                    mime="application/json",
                    use_container_width=True
                )

            with col_copy:
                import json
                copy_payload = json.dumps(display_text)
                components.html(
                    f"""
                    <div style="display:flex;justify-content:center;align-items:center;height:100%;">
                        <button id="copy-btn" style="width:100%;padding:0.6rem 1rem;border-radius:8px;border:1px solid #d1d5db;background:#111827;color:#fff;cursor:pointer;">
                            📋 نسخ النص
                        </button>
                    </div>
                    <script>
                    (function() {{
                        const btn = document.getElementById('copy-btn');
                        const text = {copy_payload};
                        if (!btn) return;
                        btn.addEventListener('click', async () => {{
                            try {{
                                if (navigator?.clipboard?.writeText) {{
                                    await navigator.clipboard.writeText(text);
                                }} else {{
                                    const ta = document.createElement('textarea');
                                    ta.value = text;
                                    document.body.appendChild(ta);
                                    ta.select();
                                    document.execCommand('copy');
                                    document.body.removeChild(ta);
                                }}
                                const original = btn.textContent;
                                btn.textContent = '✅ تم النسخ';
                                setTimeout(() => (btn.textContent = original), 1500);
                            }} catch (e) {{
                                btn.textContent = '⚠️ فشل النسخ';
                            }}
                        }});
                    }})();
                    </script>
                    """,
                    height=48
                )
                st.info("إذا لم ينجح النسخ التلقائي، انسخ يدويًا من المربع التالي:")
                st.text_area("نسخ يدوي", value=display_text, height=120, key="copy_fallback")

            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("👆 ارفع ملفاً واضغط 'ابدأ التفريغ' لعرض النتائج")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    # Footer
    st.markdown("---")
    st.markdown(
        '<div style="text-align: center; color: gray;">Powered by OpenAI Whisper | Made with ❤️ using Streamlit</div>',
        unsafe_allow_html=True
    )


def run():
    """Entry point for console script"""
    import sys
    import subprocess
    from pathlib import Path
    
    # Get the path to this file
    app_file = Path(__file__).resolve()
    
    # Run streamlit on this file
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_file)] + sys.argv[1:])


if __name__ == "__main__":
    main()
