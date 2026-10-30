import os
import re
import time
from datetime import datetime

import streamlit as st
from sarvamai import SarvamAI

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Bharat Voice · Indian Language TTS",
    page_icon="🎙️",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Styling (works in light & dark themes)
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    #MainMenu, footer {visibility: hidden;}
    .block-container {padding-top: 1.8rem; max-width: 860px;}

    .hero {
        background: linear-gradient(135deg, #FF9933 0%, #FF6B35 50%, #138808 135%);
        padding: 2rem 2rem 1.5rem 2rem; border-radius: 20px; color: #fff;
        margin-bottom: 1.4rem; box-shadow: 0 12px 32px rgba(255,107,53,.28);
    }
    .hero h1 {margin:0; font-size:2.2rem; font-weight:800; color:#fff;}
    .hero p  {margin:.4rem 0 0 0; font-size:1.02rem; opacity:.95;}
    .hero .badges {margin-top:.9rem;}
    .hero .badge {
        display:inline-block; background:rgba(255,255,255,.22); backdrop-filter:blur(4px);
        padding:3px 12px; border-radius:999px; font-size:.78rem; font-weight:600; margin-right:6px;
    }

    .card {
        border:1px solid rgba(128,128,128,.28); border-radius:16px;
        padding:1.1rem 1.3rem; margin:.8rem 0; background:rgba(128,128,128,.06);
    }
    .chip {
        display:inline-block; padding:2px 10px; border-radius:999px; font-size:.76rem;
        font-weight:600; background:rgba(255,153,51,.2); color:#FF8A1F; margin-right:6px;
    }
    .stat {
        border:1px solid rgba(128,128,128,.25); border-radius:12px; padding:.6rem .8rem;
        text-align:center; background:rgba(128,128,128,.05);
    }
    .stat b {font-size:1.25rem; display:block;}
    .stat span {font-size:.74rem; opacity:.7; text-transform:uppercase; letter-spacing:.04em;}

    div.stButton > button[kind="primary"] {
        width:100%; border-radius:12px; height:3rem; font-weight:700; font-size:1.05rem;
        border:none; background:linear-gradient(90deg,#FF9933,#FF6B35); color:#fff;
        transition:transform .15s ease, box-shadow .15s ease;
    }
    div.stButton > button[kind="primary"]:hover {
        transform:translateY(-2px); box-shadow:0 8px 22px rgba(255,107,53,.38); color:#fff;
    }
    .stDownloadButton > button {border-radius:12px; width:100%;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
LANGUAGES = {
    "हिन्दी · Hindi": "hi-IN",
    "தமிழ் · Tamil": "ta-IN",
    "తెలుగు · Telugu": "te-IN",
    "বাংলা · Bengali": "bn-IN",
    "मराठी · Marathi": "mr-IN",
    "ગુજરાતી · Gujarati": "gu-IN",
    "ಕನ್ನಡ · Kannada": "kn-IN",
    "മലയാളം · Malayalam": "ml-IN",
    "ਪੰਜਾਬੀ · Punjabi": "pa-IN",
    "English (India)": "en-IN",
}

SAMPLES = {
    "hi-IN": "नमस्ते! आपका स्वागत है। यह एक एआई द्वारा बनाई गई आवाज़ है।",
    "ta-IN": "வணக்கம்! உங்களை வரவேற்கிறோம். இது ஒரு செயற்கை நுண்ணறிவு குரல்.",
    "te-IN": "నమస్కారం! మీకు స్వాగతం. ఇది ఏఐ రూపొందించిన స్వరం.",
    "bn-IN": "নমস্কার! আপনাকে স্বাগতম। এটি একটি এআই-তৈরি কণ্ঠস্বর।",
    "mr-IN": "नमस्कार! तुमचे स्वागत आहे. हा एआय ने तयार केलेला आवाज आहे.",
    "gu-IN": "નમસ્તે! તમારું સ્વાગત છે. આ એઆઈ દ્વારા બનાવેલ અવાજ છે.",
    "kn-IN": "ನಮಸ್ಕಾರ! ನಿಮಗೆ ಸ್ವಾಗತ. ಇದು ಎಐ ರಚಿಸಿದ ಧ್ವನಿ.",
    "ml-IN": "നമസ്കാരം! സ്വാഗതം. ഇത് എഐ നിർമ്മിച്ച ശബ്ദമാണ്.",
    "pa-IN": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ! ਤੁਹਾਡਾ ਸਵਾਗਤ ਹੈ। ਇਹ ਏਆਈ ਦੁਆਰਾ ਬਣੀ ਆਵਾਜ਼ ਹੈ।",
    "en-IN": "Hello! Welcome. This is an AI generated voice.",
}

MODEL = "bulbul:v4-flash"
CHUNK_LIMIT = 450          # characters per API request (long text is split automatically)
MAX_TOTAL_CHARS = 10_000   # safety cap for the whole input
WORDS_PER_MIN = 150        # rough speaking rate for duration estimate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_api_key():
    try:
        if "SARVAM_API_KEY" in st.secrets:
            return st.secrets["SARVAM_API_KEY"]
    except Exception:
        pass
    return os.getenv("SARVAM_API_KEY")


def split_text(text: str, limit: int = CHUNK_LIMIT) -> list[str]:
    """Split on sentence boundaries (. ! ? । ॥ newlines) into chunks <= limit chars."""
    sentences = re.split(r"(?<=[.!?।॥])\s+|\n+", text.strip())
    chunks, current = [], ""
    for s in filter(None, (x.strip() for x in sentences)):
        # hard-split any single sentence that is too long
        while len(s) > limit:
            cut = s.rfind(" ", 0, limit)
            cut = cut if cut > 0 else limit
            if current:
                chunks.append(current)
                current = ""
            chunks.append(s[:cut].strip())
            s = s[cut:].strip()
        if len(current) + len(s) + 1 <= limit:
            current = f"{current} {s}".strip()
        else:
            if current:
                chunks.append(current)
            current = s
    if current:
        chunks.append(current)
    return chunks


def synthesize_chunk(client, text, lang_code, speaker, pace):
    """Call the API; only send optional params when the user changed them."""
    kwargs = dict(text=text, language_code=lang_code, model=MODEL)
    if speaker:
        kwargs["speaker"] = speaker
    if pace and abs(pace - 1.0) > 0.01:
        kwargs["pace"] = pace
    try:
        stream = client.text_to_speech.convert_stream(**kwargs)
    except TypeError:
        # SDK version doesn't support the optional params -> retry with basics
        stream = client.text_to_speech.convert_stream(
            text=text, language_code=lang_code, model=MODEL
        )
    return b"".join(chunk for chunk in stream)


def est_duration(text: str) -> str:
    words = max(len(text.split()), 1)
    secs = int(words / WORDS_PER_MIN * 60 / 1.0)
    return f"{secs // 60}m {secs % 60}s" if secs >= 60 else f"{secs}s"


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
st.session_state.setdefault("history", [])
st.session_state.setdefault("text_input", "")
st.session_state.setdefault("cache", {})

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    lang_label = st.selectbox("Language", list(LANGUAGES.keys()))
    lang_code = LANGUAGES[lang_label]

    with st.expander("🎛️ Advanced voice options"):
        pace = st.slider("Speaking pace", 0.5, 2.0, 1.0, 0.05,
                         help="1.0 is normal speed. Only sent to the API if changed.")
        speaker = st.text_input(
            "Speaker / voice name (optional)",
            placeholder="leave blank for default",
            help="Enter a speaker name supported by your Sarvam model.",
        ).strip()

    st.caption(f"Model: `{MODEL}`")
    st.divider()

    if st.button("✨ Load sample text", use_container_width=True):
        st.session_state.text_input = SAMPLES[lang_code]
        st.rerun()

    if st.session_state.history and st.button("🗑️ Clear history", use_container_width=True):
        st.session_state.history = []
        st.session_state.cache = {}
        st.rerun()

    st.divider()
    st.markdown("**💡 Tips**")
    st.caption(
        "• Use proper punctuation for natural pauses.\n\n"
        "• Long text is split automatically.\n\n"
        "• Match the text script to the chosen language."
    )
    st.caption("Powered by Sarvam AI · Built with Streamlit")

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero">
        <h1>🎙️ Bharat Voice</h1>
        <p>Turn any text into natural-sounding speech in 10 Indian languages.</p>
        <div class="badges">
            <span class="badge">10 languages</span>
            <span class="badge">Long-text support</span>
            <span class="badge">MP3 download</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Input tabs
# ---------------------------------------------------------------------------
tab_type, tab_file = st.tabs(["✍️ Type or paste", "📄 Upload .txt file"])

with tab_type:
    st.text_area(
        "Your text",
        key="text_input",
        placeholder="यहाँ अपना टेक्स्ट लिखें… / Type or paste your text here…",
        height=180,
        label_visibility="collapsed",
    )
    if st.button("🧹 Clear text"):
        st.session_state.text_input = ""
        st.rerun()

uploaded_text = ""
with tab_file:
    up = st.file_uploader("Upload a UTF-8 text file", type=["txt"])
    if up is not None:
        try:
            uploaded_text = up.read().decode("utf-8")
            st.success(f"Loaded **{up.name}** ({len(uploaded_text):,} characters)")
            with st.expander("Preview"):
                st.write(uploaded_text[:1000] + ("…" if len(uploaded_text) > 1000 else ""))
        except UnicodeDecodeError:
            st.error("Couldn't read that file. Please save it as UTF-8.")

# File upload takes priority when present
final_text = (uploaded_text or st.session_state.text_input).strip()

# Live stats
n_chars, n_words = len(final_text), len(final_text.split())
n_chunks = len(split_text(final_text)) if final_text else 0
s1, s2, s3, s4 = st.columns(4)
for col, val, lbl in [
    (s1, f"{n_chars:,}", "Characters"),
    (s2, f"{n_words:,}", "Words"),
    (s3, n_chunks, "Segments"),
    (s4, est_duration(final_text) if final_text else "–", "Est. length"),
]:
    col.markdown(f'<div class="stat"><b>{val}</b><span>{lbl}</span></div>', unsafe_allow_html=True)

st.write("")
st.caption(f"🌐 Output language: **{lang_label}**")
generate = st.button("🔊 Generate Speech", type="primary")

# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------
if generate:
    api_key = get_api_key()
    if not api_key:
        st.error(
            "No API key found. Add `SARVAM_API_KEY` to `.streamlit/secrets.toml` "
            "or set it as an environment variable."
        )
    elif not final_text:
        st.warning("Please enter or upload some text first.")
    elif n_chars > MAX_TOTAL_CHARS:
        st.error(f"Text is too long ({n_chars:,} chars). Please keep it under {MAX_TOTAL_CHARS:,}.")
    else:
        cache_key = (final_text, lang_code, speaker, round(pace, 2))
        try:
            if cache_key in st.session_state.cache:
                audio_bytes = st.session_state.cache[cache_key]
                st.toast("Loaded from cache — no API call used.", icon="⚡")
            else:
                client = SarvamAI(api_subscription_key=api_key)
                chunks = split_text(final_text)
                progress = st.progress(0.0, text="Starting…")
                parts, t0 = [], time.time()
                for i, chunk in enumerate(chunks, start=1):
                    progress.progress((i - 1) / len(chunks), text=f"Synthesizing segment {i} of {len(chunks)}…")
                    parts.append(synthesize_chunk(client, chunk, lang_code, speaker, pace))
                progress.progress(1.0, text=f"Done in {time.time() - t0:.1f}s")
                time.sleep(0.4)
                progress.empty()
                audio_bytes = b"".join(parts)
                st.session_state.cache[cache_key] = audio_bytes

            st.session_state.history.insert(0, {
                "time": datetime.now().strftime("%d %b, %I:%M %p"),
                "lang": lang_label,
                "text": final_text,
                "audio": audio_bytes,
                "size": len(audio_bytes) / 1024,
            })
            st.toast("Audio generated!", icon="✅")
        except Exception as e:
            st.error(f"API Error: {e}")

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
if st.session_state.history:
    latest = st.session_state.history[0]
    st.markdown("### 🎧 Your audio")
    preview = latest["text"][:220] + ("…" if len(latest["text"]) > 220 else "")
    st.markdown(
        f'<div class="card"><span class="chip">{latest["lang"]}</span>'
        f'<span class="chip">{latest["time"]}</span>'
        f'<span class="chip">{latest["size"]:.0f} KB</span>'
        f'<p style="margin:.7rem 0 0 0;">{preview}</p></div>',
        unsafe_allow_html=True,
    )
    st.audio(latest["audio"], format="audio/mp3")
    st.download_button("⬇️ Download MP3", data=latest["audio"],
                       file_name="bharat_voice.mp3", mime="audio/mp3", key="dl_latest")

    if len(st.session_state.history) > 1:
        with st.expander(f"🕘 Previous generations ({len(st.session_state.history) - 1})"):
            for i, item in enumerate(st.session_state.history[1:], start=1):
                st.markdown(
                    f'<span class="chip">{item["lang"]}</span><span class="chip">{item["time"]}</span>',
                    unsafe_allow_html=True,
                )
                st.caption(item["text"][:150] + ("…" if len(item["text"]) > 150 else ""))
                st.audio(item["audio"], format="audio/mp3")
                st.download_button("Download", data=item["audio"],
                                   file_name=f"bharat_voice_{i}.mp3", mime="audio/mp3", key=f"dl_{i}")
                st.divider()
else:
    st.info("👈 Pick a language, enter text (or upload a file), then hit **Generate Speech**. "
            "Try *Load sample text* in the sidebar.")