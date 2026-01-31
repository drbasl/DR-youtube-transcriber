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
from pathlib import Path
from typing import Optional
import streamlit as st
import streamlit.components.v1 as components

from transcribe_cli.config import load_settings, TranscribeConfig
from transcribe_cli.core.pipeline import transcribe_file
from transcribe_cli.core.postprocess import normalize_whitespace, format_arabic_text
from transcribe_cli.utils.youtube import download_captions_text, download_audio, strip_captions_timestamps, strip_captions_timestamps_keep_lines
from transcribe_cli.core.ai_features import generate_summary, extract_key_points, convert_to_speech, rewrite_text
from transcribe_cli.utils.exporters import export_to_docx, export_to_pdf

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


def configure_page():
    """Configure Streamlit page settings"""
    st.set_page_config(
        page_title="تفريغ الصوت والفيديو | Audio Transcription",
        page_icon="🎙️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for Mobile Responsiveness and UI Polish
    st.markdown("""
        <style>
        /* Base Styles */
        body { overflow-x: hidden; }
        .main-header {
            text-align: center;
            padding: 1rem 0;
            background: linear-gradient(90deg, #FF4B4B 0%, #111827 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
        }
        .app-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 0.5rem;
        }
        
        /* Cards */
        .card {
            background: #111827;
            border: 1px solid #374151;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            transition: transform 0.2s;
        }
        
        /* Result Area */
        .stTextArea textarea {
            background-color: #1F2937 !important;
            color: #F9FAFB !important;
            border: 1px solid #374151 !important;
            border-radius: 8px;
            font-size: 1.1rem;
            line-height: 1.8;
            height: 450px !important;
        }

        /* Responsive Design */
        @media (max-width: 768px) {
            .main-header { font-size: 1.8rem; }
            .card { padding: 1rem; }
            .stTextArea textarea { height: 300px !important; font-size: 1rem; }
            
            /* Stack columns on mobile */
            [data-testid="column"] { width: 100% !important; display: block !important; }
            
            /* Buttons full width */
            .stButton button { width: 100% !important; }
            div[data-testid="stHorizontalBlock"] { flex-direction: column; gap: 0.5rem; }
        }

        /* Success/Error/Info Boxes */
        .success-box { background-color: #064E3B; color: #D1FAE5; padding: 1rem; border-radius: 8px; }
        .error-box { background-color: #7F1D1D; color: #FEE2E2; padding: 1rem; border-radius: 8px; }
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
    
    if not text:
        st.warning("لا يوجد نص للمعالجة")
        return

    with st.expander("✨ أدوات الذكاء الاصطناعي (تلخيص، صياغة، تحويل)", expanded=True):
        tab_sum, tab_points, tab_speech, tab_rewrite = st.tabs([
            "📝 تلخيص", "📌 نقاط رئيسية", "🗣️ تحويل لخطاب", "✍️ إعادة صياغة"
        ])
        
        # Summary
        with tab_sum:
            length = st.select_slider("الطول", options=["short", "medium", "detailed"], format_func=lambda x: {"short":"قصير", "medium":"متوسط", "detailed":"مفصل"}[x])
            if st.button("لخص النص"):
                with st.spinner("جارٍ التلخيص..."):
                    try:
                        summary = asyncio.run(generate_summary(text, length))
                        st.text_area("الملخص", value=summary, height=200)
                    except Exception as e:
                        st.error(f"فشل التلخيص: {e}")

        # Key Points
        with tab_points:
            if st.button("استخرج النقاط"):
                with st.spinner("جارٍ التحليل..."):
                    try:
                        points = asyncio.run(extract_key_points(text))
                        st.text_area("النقاط الرئيسية", value=points, height=300)
                    except Exception as e:
                        st.error(f"فشل الاستخراج: {e}")

        # Speech
        with tab_speech:
            audience = st.text_input("الجمهور المستهدف", value="فريق العمل")
            if st.button("حول لخطاب"):
                with st.spinner("جارٍ التحويل..."):
                    try:
                        speech = asyncio.run(convert_to_speech(text, audience))
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
                        rewritten = asyncio.run(rewrite_text(text, style, structure, options))
                        st.text_area("النص الجديد", value=rewritten, height=400)
                    except Exception as e:
                        st.error(f"فشل إعادة الصياغة: {e}")


def main():
    """Main App"""
    configure_page()
    st.markdown('<h1 class="main-header">🎙️ Transcribe CLI 2.0</h1>', unsafe_allow_html=True)
    st.markdown("---")
    
    if not validate_settings(): st.stop()

    # Sidebar
    with st.sidebar:
        st.header("⚙️ الإعدادات")
        lang_key = st.selectbox("🌐 اللغة", list(LANGUAGES.keys()))
        lang_code = LANGUAGES[lang_key]
        
        fmt_key = st.selectbox("📄 صيغة العرض", list(OUTPUT_FORMATS.keys()))
        out_fmt = OUTPUT_FORMATS[fmt_key]
        
        diarize = st.checkbox("👥 تمييز المتحدثين")
        
        with st.expander("خيارات متقدمة"):
            enable_post = st.checkbox("تفعيل المعالجة", True)
            mode = "formatted" if enable_post else "literal"
            chunk_size = st.slider("Max Chunk (MB)", 5, 24, 20)

    # Main UI
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        st.markdown('<div class="card"><h3>📥 الإدخال | Input</h3>', unsafe_allow_html=True)
        tab_file, tab_url = st.tabs(["📁 رفع ملف", "🔗 رابط فيديو"])
        
        # File Upload
        with tab_file:
            uploaded = st.file_uploader("اختر ملفاً", type=ALL_FORMATS)
            if uploaded and st.button("🚀 ابدأ (ملف)", key="btn_file", type="primary", use_container_width=True):
                with st.spinner("جارٍ المعالجة..."):
                    res, err = process_file(uploaded, lang_code, out_fmt, diarize, chunk_size, enable_post, mode)
                    if res:
                        st.session_state['transcription_result'] = res
                        st.success("تم بنجاح!")
                    else:
                        st.error(err)

        # URL Input
        with tab_url:
            st.markdown("يدعم: YouTube, TikTok, Instagram, Twitter/X")
            url = st.text_input("رابط الفيديو")
            source = st.selectbox("المصدر", ["audio", "captions"], help="Captions (YouTube Only) اسرع")
            
            if st.button("🚀 ابدأ (رابط)", key="btn_url", type="primary", use_container_width=True):
                if not url: st.error("الرابط مطلوب")
                else:
                    with st.spinner("جارٍ التحميل والمعالجة..."):
                        res, err = process_url(url, lang_code, out_fmt, source, chunk_size, enable_post, mode)
                        if res:
                            st.session_state['transcription_result'] = res
                            st.success("تم بنجاح!")
                        else:
                            st.error(err)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="card"><h3>📝 النتيجة | Result</h3>', unsafe_allow_html=True)
        if 'transcription_result' in st.session_state:
            res = st.session_state['transcription_result']
            final_text = res.get("display_text", "")
            raw_text = res.get("text", "")
            
            # Editable Text Area
            edited_text = st.text_area("النص المفرغ", value=final_text, height=450)
            
            # Export Toolbar
            c1, c2, c3, c4 = st.columns(4)
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
            
            # Copy Button
            import json
            js_text = json.dumps(edited_text)
            components.html(f"""
                <button onclick="navigator.clipboard.writeText({js_text}).then(()=>this.innerText='✅').catch(()=>this.innerText='❌')"
                style="width:100%;padding:8px;border:1px solid #444;border-radius:4px;background:#222;color:white;cursor:pointer;">
                📋 نسخ للحافظة
                </button>
            """, height=40)

        else:
            st.info("النتائج ستظهر هنا...")
        st.markdown('</div>', unsafe_allow_html=True)

    # AI Features Section
    ai_features_ui()

if __name__ == "__main__":
    main()
