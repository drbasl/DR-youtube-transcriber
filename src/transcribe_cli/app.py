"""
Streamlit UI for transcribe-cli
Provides a web interface for uploading and transcribing audio/video files
"""
import asyncio
import logging
import traceback
import shutil
import tempfile
import json
import os
import time
from pathlib import Path
from typing import Optional
import streamlit as st
import streamlit.components.v1 as components

from transcribe_cli.config import load_settings, TranscribeConfig
from transcribe_cli.core.pipeline import transcribe_file
from transcribe_cli.core.postprocess import normalize_whitespace, format_arabic_text
from transcribe_cli.utils.youtube import download_captions_text, download_audio, strip_captions_timestamps, strip_captions_timestamps_keep_lines
from transcribe_cli.core.ai_features import generate_summary, extract_key_points, convert_to_speech, rewrite_text, translate_text, generate_dubbing_audio
from transcribe_cli.utils.exporters import export_to_docx, export_to_pdf, export_to_excel

try:
    from streamlit_quill import st_quill
    HAS_QUILL = True
except ImportError:
    HAS_QUILL = False

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
        if "segments" in resp: return resp["segments"]
        if "data" in resp and isinstance(resp["data"], dict) and "segments" in resp["data"]: return resp["data"]["segments"]
        return []
    return getattr(resp, "segments", []) or []


def extract_text(resp):
    """Safely extract text from response"""
    if resp is None: return ""
    if isinstance(resp, dict): return resp.get("transcript", resp.get("text", ""))
    return getattr(resp, "transcript", getattr(resp, "text", ""))


def extract_metadata(resp, key, default=None):
    if resp is None: return default
    if isinstance(resp, dict): return resp.get(key, default)
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
    # Add more as needed
}

# Output formats
OUTPUT_FORMATS = {
    "نص (Text)": "text",
    "JSON (مع علامات زمنية)": "json",
    "SRT Subtitles": "srt",
    "WebVTT Subtitles": "vtt",
}


def cleanup_old_files(temp_dir="temp"):
    """Cleanup temporary files older than 1 hour"""
    try:
        if not os.path.exists(temp_dir): return
        
        now = time.time()
        for f in os.listdir(temp_dir):
            path = os.path.join(temp_dir, f)
            if os.stat(path).st_mtime < now - 3600:
                if os.path.isfile(path): os.remove(path)
                elif os.path.isdir(path): shutil.rmtree(path)
    except Exception as e:
        logger.warning(f"Cleanup failed: {e}")

def configure_page():
    """Configure Streamlit page settings"""
    cleanup_old_files()

    st.set_page_config(
        page_title="تفريغ الصوت والفيديو | Audio Transcription",
        page_icon="🎙️",
        layout="wide",
        initial_sidebar_state="auto"  # Changed from "expanded" to "auto" for better mobile UX
    )
    
    # Custom CSS for Mobile Responsiveness and UI Polish
    st.markdown("""
        <style>
        /* Base Styles */
        * { box-sizing: border-box; }
        body { 
            overflow-x: hidden; 
            -webkit-text-size-adjust: 100%;
            -webkit-font-smoothing: antialiased;
        }
        
        /* Mobile-First Header */
        .main-header {
            text-align: center;
            padding: 0.75rem 0.5rem;
            background: linear-gradient(90deg, #FF4B4B 0%, #111827 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
            font-size: 1.5rem;
            line-height: 1.3;
        }
        
        .app-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 0.5rem;
        }
        
        /* Cards - Mobile Optimized */
        .card {
            background: #111827;
            border: 1px solid #374151;
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 1rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s;
        }
        
        .card h3 {
            font-size: 1.2rem;
            margin-bottom: 0.75rem;
        }
        
        /* Text Area - Touch Optimized */
        .stTextArea textarea {
            background-color: #1F2937 !important;
            color: #F9FAFB !important;
            border: 1px solid #374151 !important;
            border-radius: 8px;
            font-size: 1rem;
            line-height: 1.6;
            height: 350px !important;
            padding: 0.75rem;
            touch-action: manipulation;
        }

        /* Progress Bar - Enhanced */
        .stProgress > div > div {
            background: linear-gradient(90deg, #10B981 0%, #059669 100%);
            border-radius: 10px;
        }
        
        /* Buttons - Touch Friendly */
        .stButton button {
            padding: 0.65rem 1rem !important;
            font-size: 1rem !important;
            border-radius: 8px !important;
            touch-action: manipulation;
            min-height: 44px !important;
        }
        
        /* Download Buttons - Compact for Mobile */
        .stDownloadButton button {
            padding: 0.5rem 0.75rem !important;
            font-size: 0.9rem !important;
            min-height: 40px !important;
        }
        
        /* Sidebar - Mobile Friendly */
        [data-testid="stSidebar"] {
            background-color: #0E1117;
        }
        
        [data-testid="stSidebar"] .stSelectbox,
        [data-testid="stSidebar"] .stCheckbox {
            margin-bottom: 0.75rem;
        }

        /* File Uploader - Touch Optimized */
        [data-testid="stFileUploader"] {
            border: 2px dashed #374151;
            border-radius: 10px;
            padding: 1.5rem 1rem;
            text-align: center;
            background: #1F2937;
        }
        
        /* Input Fields - Better Mobile UX */
        .stTextInput input, .stSelectbox select {
            font-size: 1rem !important;
            padding: 0.65rem !important;
            min-height: 44px !important;
        }
        
        /* Tabs - Mobile Friendly */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
            flex-wrap: wrap;
        }
        
        .stTabs [data-baseweb="tab"] {
            padding: 0.5rem 1rem;
            font-size: 0.95rem;
            white-space: nowrap;
        }

        /* Responsive Design - Tablets */
        @media (max-width: 1024px) {
            .main-header { font-size: 1.6rem; }
            .card { padding: 1.25rem; }
        }

        /* Responsive Design - Mobile Phones */
        @media (max-width: 768px) {
            .main-header { 
                font-size: 1.4rem; 
                padding: 0.5rem;
            }
            
            .card { 
                padding: 0.75rem; 
                margin-bottom: 0.75rem;
                border-radius: 10px;
            }
            
            .card h3 {
                font-size: 1.1rem;
            }
            
            .stTextArea textarea { 
                height: 250px !important; 
                font-size: 0.95rem;
            }
            
            /* Force single column layout */
            [data-testid="column"] { 
                width: 100% !important; 
                display: block !important; 
                margin-bottom: 1rem;
            }
            
            /* Stack horizontal elements */
            div[data-testid="stHorizontalBlock"] { 
                flex-direction: column !important; 
                gap: 0.5rem;
            }
            
            /* Full width buttons */
            .stButton button, .stDownloadButton button { 
                width: 100% !important;
            }
            
            /* Adjust export toolbar for mobile */
            .stDownloadButton {
                margin-bottom: 0.5rem;
            }
            
            /* Compact sidebar on mobile */
            [data-testid="stSidebar"] {
                min-width: 0 !important;
            }
        }
        
        /* Extra Small Devices */
        @media (max-width: 480px) {
            .main-header { 
                font-size: 1.2rem;
                padding: 0.4rem;
            }
            
            .card {
                padding: 0.6rem;
            }
            
            .stTextArea textarea {
                font-size: 0.9rem;
                height: 200px !important;
            }
            
            .stButton button {
                font-size: 0.9rem !important;
                padding: 0.5rem 0.75rem !important;
            }
            
            .stDownloadButton button {
                font-size: 0.85rem !important;
            }
        }

        /* Success/Error/Info Boxes - Mobile Optimized */
        .success-box { 
            background-color: #064E3B; 
            color: #D1FAE5; 
            padding: 0.75rem; 
            border-radius: 8px; 
            font-size: 0.95rem;
        }
        
        .error-box { 
            background-color: #7F1D1D; 
            color: #FEE2E2; 
            padding: 0.75rem; 
            border-radius: 8px;
            font-size: 0.95rem;
        }
        
        /* Touch-friendly spacing */
        .element-container {
            margin-bottom: 0.5rem;
        }
        
        /* Prevent zoom on input focus (iOS) */
        @media screen and (max-width: 768px) {
            input, select, textarea {
                font-size: 16px !important;
            }
        }
        
        /* Better scrolling on mobile */
        .main {
            -webkit-overflow-scrolling: touch;
        }
        </style>
    """, unsafe_allow_html=True)


def validate_settings() -> bool:
    """Validate OpenAI API key is configured"""
    try:
        settings = load_settings()
        if not settings.openai_api_key or settings.openai_api_key == "your-api-key-here":
            st.error("⚠️ **خطأ:** لم يتم تعيين مفتاح OpenAI API")
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
    """Process uploaded file"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = Path(tmp_file.name)
        
        try:
            output_dir = Path(tempfile.mkdtemp())
            settings = load_settings()
            config = TranscribeConfig(
                input_path=tmp_path,
                output_dir=output_dir,
                language=language if language else "ar",
                model=settings.openai_model,
                output_format=output_format,
                diarize=enable_diarization,
                max_bytes_per_chunk=max_chunk_size_mb * 1024 * 1024
            )
            
            result = asyncio.run(transcribe_file(config))
            chunks_count = extract_metadata(result, "chunks_count", extract_metadata(result, "chunks"))
            if chunks_count is None: raise ValueError("chunking failed")

            segments = extract_segments(result) or []
            if output_format in ["srt", "vtt"] and not segments: segments = []
                
            raw_text = extract_text(result)
            processed_text = format_arabic_text(raw_text, language=language or "ar") if postprocess_enabled and postprocess_mode == "formatted" else raw_text
            
            display_text = format_output(processed_text, segments, output_format)
            
            import json
            download_json = json.dumps({
                "text": processed_text,
                "model": extract_metadata(result, "model"),
                "lang": extract_metadata(result, "language"),
                "segments": segments
            }, ensure_ascii=False, indent=2)

            return {
                "display_text": display_text,
                "text": processed_text,
                "segments": segments,
                "json_download": download_json,
                "output_format": output_format
            }, None
            
        finally:
            if tmp_path.exists(): tmp_path.unlink()
            if output_dir.exists(): shutil.rmtree(output_dir, ignore_errors=True)
                
    except Exception as e:
        return None, f"خطأ في المعالجة: {str(e)}"


def format_output(text, segments, fmt):
    if fmt == "text": return text
    if fmt == "json":
        import json
        return json.dumps({"text": text, "segments": segments}, ensure_ascii=False, indent=2)
    
    if not segments: return text  # Fallback
    
    lines = []
    if fmt == "srt":
        for i, seg in enumerate(segments, 1):
            s, e, t = seg.get("start"), seg.get("end"), seg.get("text", "")
            if s is None or e is None: continue
            st_str = f"{int(s//3600):02d}:{int((s%3600)//60):02d}:{int(s%60):02d},{int((s%1)*1000):03d}"
            et_str = f"{int(e//3600):02d}:{int((e%3600)//60):02d}:{int(e%60):02d},{int((e%1)*1000):03d}"
            lines.extend([str(i), f"{st_str} --> {et_str}", t, ""])
        return "\n".join(lines)
    
    elif fmt == "vtt":
        lines = ["WEBVTT", ""]
        for seg in segments:
            s, e, t = seg.get("start"), seg.get("end"), seg.get("text", "")
            if s is None or e is None: continue
            st_str = f"{int(s//3600):02d}:{int((s%3600)//60):02d}:{int(s%60):02d}.{int((s%1)*1000):03d}"
            et_str = f"{int(e//3600):02d}:{int((e%3600)//60):02d}:{int(e%60):02d}.{int((e%1)*1000):03d}"
            lines.extend([f"{st_str} --> {et_str}", t, ""])
        return "\n".join(lines)
        
    return text


def process_url(
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
    """Process Video URL (YouTube, TikTok, etc.)"""
    try:
        temp_dir = Path(tempfile.mkdtemp())
        try:
            lang = language if language else "ar"
            
            # For non-YouTube URLs or when "audio" source is selected, use audio pipeline
            # 'captions' mode is mainly for YouTube where we can grab subs directly.
            # If default is 'captions' but it's not YouTube, we might fallback or fail.
            # For now, let's trust the user choice or fallback.
            
            is_youtube = "youtube.com" in url or "youtu.be" in url
            
            if source == "captions" and is_youtube:
                # YouTube Captions Path
                cleaned_text, segments, used_auto, raw_text = download_captions_text(url, lang, temp_dir)
                clean_text = strip_captions_timestamps(raw_text)
                
                processed_text = format_arabic_text(clean_text, language=lang) if postprocess_enabled and postprocess_mode == "formatted" else clean_text
                
                display_text = format_output(processed_text, segments, output_format)
                if output_format == "text":
                    display_text = raw_text if raw_captions else (clean_text if remove_timestamps else raw_text)

                import json
                download_json = json.dumps({"text": processed_text, "source": "captions"}, ensure_ascii=False, indent=2)

                return {
                    "display_text": display_text,
                    "text": processed_text,
                    "json_download": download_json,
                    "output_format": output_format,
                    "source": "captions"
                }, None

            else:
                # Audio Download Path (Generic for all platforms)
                logger.info(f"Downloading audio from URL: {url}")
                audio_path = download_audio(url, temp_dir)
                
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
                chunks = extract_metadata(result, "chunks_count")
                if chunks is None: raise ValueError("processing failed")
                
                raw_text = extract_text(result)
                segments = extract_segments(result) or []
                
                processed_text = format_arabic_text(raw_text, language=lang) if postprocess_enabled and postprocess_mode == "formatted" else raw_text
                display_text = format_output(processed_text, segments, output_format)
                
                import json
                download_json = json.dumps({"text": processed_text, "segments": segments}, ensure_ascii=False, indent=2)

                return {
                    "display_text": display_text,
                    "text": processed_text,
                    "segments": segments,
                    "json_download": download_json,
                    "output_format": output_format
                }, None

        finally:
            if temp_dir.exists(): shutil.rmtree(temp_dir, ignore_errors=True)

    except Exception as e:
        return None, f"خطأ: {str(e)}"


def ai_features_ui():
    """Render AI Features Section"""
    if 'transcription_result' not in st.session_state: return

    st.markdown("---")
    st.markdown("### 🤖 معالجة بالذكاء الاصطناعي | AI Processing")
    
    result = st.session_state['transcription_result']
    text = result.get("text", "")
    current_model = st.session_state.get('model_name', "gpt-3.5-turbo")
    
    if not text:
        st.warning("لا يوجد نص للمعالجة")
        return

    with st.expander("✨ أدوات الذكاء الاصطناعي (تلخيص، صياغة، تحويل، دبلجة)", expanded=True):
        tab_sum, tab_points, tab_speech, tab_rewrite, tab_dub = st.tabs([
            "📝 تلخيص", "📌 نقاط رئيسية", "🗣️ تحويل لخطاب", "✍️ إعادة صياغة", "🎬 دبلجة وترجمة"
        ])
        
        # Summary
        with tab_sum:
            length = st.select_slider("الطول", options=["short", "medium", "detailed"], format_func=lambda x: {"short":"قصير", "medium":"متوسط", "detailed":"مفصل"}[x])
            if st.button("لخص النص"):
                with st.spinner(f"جارٍ التلخيص باستخدام {current_model}..."):
                    try:
                        summary = asyncio.run(generate_summary(text, length, model=current_model))
                        st.text_area("الملخص", value=summary, height=200)
                    except Exception as e:
                        st.error(f"فشل التلخيص: {e}")

        # Key Points
        with tab_points:
            if st.button("استخرج النقاط"):
                with st.spinner("جارٍ التحليل..."):
                    try:
                        points = asyncio.run(extract_key_points(text, model=current_model))
                        st.text_area("النقاط الرئيسية", value=points, height=300)
                    except Exception as e:
                        st.error(f"فشل الاستخراج: {e}")

        # Speech
        with tab_speech:
            audience = st.text_input("الجمهور المستهدف", value="فريق العمل")
            if st.button("حول لخطاب"):
                with st.spinner("جارٍ التحويل..."):
                    try:
                        speech = asyncio.run(convert_to_speech(text, audience, model=current_model))
                        st.text_area("الخطاب المقترح", value=speech, height=400)
                    except Exception as e:
                        st.error(f"فشل التحويل: {e}")

        # Rewrite
        with tab_rewrite:
            col_style, col_struct = st.columns(2)
            style = col_style.selectbox("الأسلوب", ["رسمي", "بسيط", "أكاديمي", "صحفي", "تسويقي", "محادثة"])
            structure = col_struct.selectbox("الهيكل", ["فقرات منظمة", "نقاط مرقمة", "سؤال وجواب", "قصة", "ملخص تنفيذي"])
            options = st.multiselect("خيارات إضافية", ["تحسين القواعد", "إزالة التكرار", "تحسين الوضوح"])
            
            if st.button("أعد الصياغة"):
                with st.spinner("جارٍ إعادة الصياغة..."):
                    try:
                        rewritten = asyncio.run(rewrite_text(text, style, structure, options, model=current_model))
                        st.text_area("النص الجديد", value=rewritten, height=400)
                    except Exception as e:
                        st.error(f"فشل إعادة الصياغة: {e}")

        # Dubbing & Translation
        with tab_dub:
            st.markdown("##### 🌍 ترجمة ودبلجة صوتية")
            target_lang = st.selectbox("لغة الهدف", ["English", "Spanish", "French", "German", "Chinese"])
            voice = st.selectbox("الصوت", ["alloy", "echo", "fable", "onyx", "nova", "shimmer"])
            
            if st.button("ترجمة ودبلجة"):
                with st.spinner("جارٍ الترجمة وتوليد الصوت..."):
                    try:
                        # 1. Translate
                        st.info("مرحلة 1: ترجمة النص...")
                        translated_text = asyncio.run(translate_text(text, target_lang, model=current_model))
                        st.text_area(f"الترجمة ({target_lang})", value=translated_text, height=150)
                        
                        # 2. TTS
                        st.info("مرحلة 2: توليد الصوت...")
                        audio_bytes = asyncio.run(generate_dubbing_audio(translated_text, voice))
                        
                        st.audio(audio_bytes, format="audio/mp3")
                        st.download_button("⬇️ تحميل الصوت المدبلج", audio_bytes, "dubbed_audio.mp3", "audio/mpeg")
                        
                    except Exception as e:
                        st.error(f"فشل العملية: {e}")



def main():
    """Main App"""
    configure_page()
    st.markdown('<h1 class="main-header">🎙️ Transcribe CLI 2.0</h1>', unsafe_allow_html=True)
    st.markdown("---")
    
    if not validate_settings(): st.stop()


    if 'model_name' not in st.session_state:
        st.session_state['model_name'] = "gpt-3.5-turbo"

    def update_model():
        st.session_state['model_name'] = st.session_state.box_model_select

    # Sidebar
    with st.sidebar:
        st.header("⚙️ الإعدادات")
        lang_key = st.selectbox("🌐 اللغة", list(LANGUAGES.keys()))
        lang_code = LANGUAGES[lang_key]
        
        fmt_key = st.selectbox("📄 صيغة العرض", list(OUTPUT_FORMATS.keys()))
        out_fmt = OUTPUT_FORMATS[fmt_key]
        
        # AI Model Selector
        st.selectbox(
            "🧠 نموذج الذكاء الاصطناعي", 
            ["gpt-3.5-turbo", "gpt-4-turbo", "gpt-4o"], 
            key="box_model_select",
            on_change=update_model
        )
        
        diarize = st.checkbox("👥 تمييز المتحدثين")
        
        with st.expander("خيارات متقدمة"):
            enable_post = st.checkbox("تفعيل المعالجة", True)
            mode = "formatted" if enable_post else "literal"
            chunk_size = st.slider("Max Chunk (MB)", 5, 24, 20)
            
            st.divider()
            st.markdown("##### 🔍 أدوات التحرير")
            show_search = st.checkbox("تفعيل البحث والاستبدال", value=False, key="show_search_tool")

    # Main UI
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        st.markdown('<div class="card"><h3>📥 الإدخال | Input</h3>', unsafe_allow_html=True)
        tab_file, tab_url = st.tabs(["📁 رفع ملف", "🔗 رابط فيديو"])
        
        # File Upload
        with tab_file:
            uploaded = st.file_uploader("اختر ملفاً", type=ALL_FORMATS)
            if uploaded and st.button("🚀 ابدأ (ملف)", key="btn_file", type="primary", use_container_width=True):
                progress_bar = st.progress(0, text="جارٍ التحضير...")
                with st.spinner("جارٍ المعالجة..."):
                    progress_bar.progress(25, text="📤 رفع الملف...")
                    res, err = process_file(uploaded, lang_code, out_fmt, diarize, chunk_size, enable_post, mode)
                    progress_bar.progress(75, text="⚙️ معالجة النص...")
                    if res:
                        progress_bar.progress(100, text="✅ اكتمل!")
                        st.session_state['transcription_result'] = res
                        st.success("تم بنجاح!")
                    else:
                        st.error(f"❌ خطأ في المعالجة: {err}")

        # URL Input
        with tab_url:
            st.markdown("يدعم: YouTube, TikTok, Instagram, Twitter/X")
            url = st.text_input("رابط الفيديو")
            source = st.selectbox("المصدر", ["audio", "captions"], help="Captions (YouTube Only) اسرع")
            
            if st.button("🚀 ابدأ (رابط)", key="btn_url", type="primary", use_container_width=True):
                if not url: 
                    st.error("❌ الخطأ: الرابط مطلوب")
                else:
                    progress_bar = st.progress(0, text="جارٍ الاتصال...")
                    with st.spinner("جارٍ التحميل والمعالجة..."):
                        progress_bar.progress(20, text="📥 تحميل الفيديو...")
                        res, err = process_url(url, lang_code, out_fmt, source, chunk_size, enable_post, mode)
                        progress_bar.progress(80, text="⚙️ معالجة الصوت...")
                        if res:
                            progress_bar.progress(100, text="✅ اكتمل!")
                            st.session_state['transcription_result'] = res
                            st.success("تم بنجاح!")
                        else:
                            st.error(f"❌ خطأ: {err}")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        # Header with Close Button
        r_head_col1, r_head_col2 = st.columns([0.85, 0.15])
        with r_head_col1:
            st.markdown('<h3>📝 النتيجة | Result</h3>', unsafe_allow_html=True)
        with r_head_col2:
            if st.button("❌", key="close_res", help="إغلاق و مسح النتائج"):
                if 'transcription_result' in st.session_state:
                    del st.session_state['transcription_result']
                st.rerun()

        if 'transcription_result' in st.session_state:
            res = st.session_state['transcription_result']
            final_text = res.get("display_text", "")
            
            # Search and Replace Tool (if enabled)
            if st.session_state.get('show_search_tool', False):
                with st.expander("🔍 البحث والاستبدال", expanded=True):
                    col_search, col_replace, col_btn = st.columns([2, 2, 1])
                    with col_search:
                        search_term = st.text_input("ابحث عن", key="search_text")
                    with col_replace:
                        replace_term = st.text_input("استبدل بـ", key="replace_text")
                    with col_btn:
                        st.write("")  # spacer
                        if st.button("استبدل الكل", use_container_width=True):
                            if search_term:
                                final_text = final_text.replace(search_term, replace_term)
                                res["display_text"] = final_text
                                st.session_state['transcription_result'] = res
                                st.success(f"✅ تم الاستبدال")
                                st.rerun()
            
            # Editable Text Area
            if HAS_QUILL:
                st.markdown("##### المحرر المتقدم")
                edited_text = st_quill(
                    value=final_text, 
                    html=False, 
                    readonly=False, 
                    key="quill_editor",
                    placeholder="النص المفرغ يظهر هنا...",
                )
            else:
                st.warning("لتفعيل المحرر المتقدم: pip install streamlit-quill")
                edited_text = st.text_area("النص المفرغ", value=final_text, height=450)
            
            # Export Toolbar
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.download_button("⬇️ TXT", final_text, "transcription.txt", use_container_width=True)
            with c2:
                st.download_button("⬇️ JSON", res.get("json_download", "{}"), "data.json", "application/json", use_container_width=True)
            with c3:
                try:
                    docx_file = export_to_docx(edited_text)
                    st.download_button("⬇️ DOCX", docx_file, "transcription.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
                except Exception as e:
                    st.error("DOCX Error")
            with c4:
                try:
                    pdf_file = export_to_pdf(edited_text)
                    st.download_button("⬇️ PDF", pdf_file, "transcription.pdf", "application/pdf", use_container_width=True)
                except Exception as e:
                    st.error("PDF Error")
            with c5:
                try:
                    segments = res.get("segments", [])
                    excel_file = export_to_excel(edited_text, segments)
                    st.download_button("⬇️ XLSX", excel_file, "transcription.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                except Exception as e:
                    st.error("Excel Error")
            
            # Copy Button (Robust Implementation)
            import json
            js_text_dump = json.dumps(edited_text)
            components.html(f"""
                <div style="display: flex; justify-content: center; margin-top: 10px;">
                    <button id="copyBtn" onclick="copyText()" style="
                        width: 100%;
                        padding: 10px;
                        background-color: #374151; /* Gray-700 */
                        color: white;
                        border: 1px solid #4B5563;
                        border-radius: 6px;
                        cursor: pointer;
                        font-family: sans-serif;
                        font-weight: bold;
                        transition: background 0.2s;
                    ">📋 نسخ النص بالكامل</button>
                    <script>
                        const textToCopy = {js_text_dump};
                        function copyText() {{
                            navigator.clipboard.writeText(textToCopy).then(function() {{
                                const btn = document.getElementById("copyBtn");
                                btn.innerText = "✅ تم النسخ بنجاح";
                                btn.style.backgroundColor = "#065F46"; /* Green-800 */
                                setTimeout(() => {{
                                    btn.innerText = "📋 نسخ النص بالكامل";
                                    btn.style.backgroundColor = "#374151";
                                }}, 2000);
                            }}, function(err) {{
                                console.error('فشل النسخ', err);
                                const btn = document.getElementById("copyBtn");
                                btn.innerText = "❌ فشل النسخ (جرب يدوياً)";
                                btn.style.backgroundColor = "#7F1D1D"; /* Red-900 */
                            }});
                        }}
                    </script>
                </div>
            """, height=60)

        else:
            st.info("النتائج ستظهر هنا...")
        st.markdown('</div>', unsafe_allow_html=True)

    # AI Features Section
    ai_features_ui()

if __name__ == "__main__":
    main()
