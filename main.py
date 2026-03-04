import streamlit as st
import soundfile as sf
import io
import os
import zipfile
import numpy as np
import av

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Audio Converter", page_icon="🎵", layout="centered")

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=DM+Mono:wght@300;400&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Mono', monospace;
    background-color: #0d0d0d;
    color: #f0ede6;
}

.stApp {
    background: #0d0d0d;
}

h1, h2, h3 {
    font-family: 'Space Grotesk', sans-serif !important;
}

.main-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.8rem;
    font-weight: 700;
    letter-spacing: -1px;
    background: linear-gradient(135deg, #f0ede6 0%, #c8b89a 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
    width: fit-content;
}

.sub-title {
    font-family: 'DM Mono', monospace;
    font-size: 0.78rem;
    color: #666;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-bottom: 2rem;
}

.file-card {
    background: #161616;
    border: 1px solid #2a2a2a;
    border-radius: 10px;
    padding: 12px 16px;
    margin: 6px 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.82rem;
    transition: border-color 0.2s;
}

.file-card:hover { border-color: #c8b89a44; }
.file-name { color: #f0ede6; font-weight: 400; }
.file-size { color: #555; font-size: 0.75rem; }
.badge-waiting  { color: #555; }
.badge-loading  { color: #c8b89a; }
.badge-done     { color: #6fcf97; }
.badge-error    { color: #eb5757; }

.section-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.68rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #444;
    margin: 1.4rem 0 0.6rem;
}

hr { border-color: #1f1f1f !important; margin: 1.5rem 0 !important; }

.stButton > button {
    background: #f0ede6 !important;
    color: #0d0d0d !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    letter-spacing: 1px !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.55rem 1.6rem !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.85 !important; }

.stDownloadButton > button {
    background: linear-gradient(135deg, #c8b89a, #a89070) !important;
    color: #0d0d0d !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    letter-spacing: 1px !important;
    border: none !important;
    border-radius: 8px !important;
    width: 100% !important;
    padding: 0.65rem 0 !important;
}

.stSelectbox label {
    color: #555 !important;
    font-size: 0.72rem !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
}

.stFileUploader label {
    color: #555 !important;
    font-size: 0.72rem !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
}

[data-testid="stFileUploaderDropzone"] {
    background: #161616 !important;
    border: 1px dashed #333 !important;
    border-radius: 10px !important;
}

.stProgress > div > div {
    background: linear-gradient(90deg, #c8b89a, #f0ede6) !important;
    border-radius: 4px !important;
}

.stAlert { border-radius: 8px !important; font-size: 0.8rem !important; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "zip_buffer" not in st.session_state:
    st.session_state.zip_buffer = None

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">🎵 Audio Converter</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Convert · Transform · Download</div>', unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def format_size(byte_size):
    mb = byte_size / (1024 * 1024)
    if mb >= 1:
        return f"{round(mb, 2)} MB"
    else:
        return f"{round(byte_size / 1024, 1)} KB"

def read_audio(upload):
    file_bytes = upload.read()
    ext = os.path.splitext(upload.name)[1].lower().strip(".")

    if ext in ["m4a", "mp3"]:
        buf = io.BytesIO(file_bytes)
        container = av.open(buf)
        stream = container.streams.audio[0]
        sample_rate = stream.codec_context.sample_rate
        resampler = av.AudioResampler(format='fltp', rate=sample_rate)

        samples = []
        for frame in container.decode(stream):
            for f in resampler.resample(frame):
                samples.append(f.to_ndarray())
        for f in resampler.resample(None):
            samples.append(f.to_ndarray())

        audio_array = np.concatenate(samples, axis=1)
        audio_data = audio_array[0] if audio_array.shape[0] == 1 else audio_array.T
        return audio_data.astype(np.float32), sample_rate
    else:
        return sf.read(io.BytesIO(file_bytes))

def cleanup_output():
    if os.path.exists("output"):
        for f in os.listdir("output"):
            try:
                os.remove(os.path.join("output", f))
            except Exception:
                pass
        try:
            os.rmdir("output")
        except Exception:
            pass

# ── Upload ────────────────────────────────────────────────────────────────────
uploads = st.file_uploader(
    "Drop your audio files here",
    type=["mp3", "wav", "ogg", "flac", "m4a"],
    accept_multiple_files=True,
    key="uploader"
)

if uploads:
    os.makedirs("output", exist_ok=True)

    st.markdown(f'<div class="section-label">📁 Queued files — {len(uploads)}</div>', unsafe_allow_html=True)
    file_status = []
    for i, upload in enumerate(uploads, 1):
        size_display = format_size(upload.size)
        placeholder = st.empty()
        placeholder.markdown(
            f'<div class="file-card">'
            f'<span class="file-name">{i}. {upload.name}</span>'
            f'<span class="file-size badge-waiting">{size_display} &nbsp;·&nbsp; waiting</span>'
            f'</div>',
            unsafe_allow_html=True
        )
        file_status.append((placeholder, upload.name, size_display))

    st.markdown("---")

    col1, col2 = st.columns([2, 1])
    with col1:
        output_format = st.selectbox("Output format", ["wav", "flac", "ogg"])
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        convert_clicked = st.button("▶ Convert All", use_container_width=True)

    subtype_map = {"wav": "PCM_16", "flac": "PCM_16", "ogg": "VORBIS"}

    # ── Conversion ────────────────────────────────────────────────────────────
    if convert_clicked:
        st.session_state.zip_buffer = None
        converted_files = []
        overall_progress = st.progress(0, text="Starting…")

        for idx, upload in enumerate(uploads):
            placeholder, name, size_display = file_status[idx]

            placeholder.markdown(
                f'<div class="file-card">'
                f'<span class="file-name">{idx+1}. {name}</span>'
                f'<span class="file-size badge-loading">{size_display} &nbsp;·&nbsp; ⏳ converting…</span>'
                f'</div>',
                unsafe_allow_html=True
            )

            try:
                audio_data, sample_rate = read_audio(upload)
                output_filename = f"{os.path.splitext(name)[0]}.{output_format}"
                output_path = os.path.join("output", output_filename)
                sf.write(output_path, audio_data, sample_rate, subtype=subtype_map[output_format])
                converted_files.append((output_path, output_filename))

                placeholder.markdown(
                    f'<div class="file-card">'
                    f'<span class="file-name">{idx+1}. {name}</span>'
                    f'<span class="file-size badge-done">{size_display} &nbsp;·&nbsp; ✅ done</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            except Exception as e:
                placeholder.markdown(
                    f'<div class="file-card">'
                    f'<span class="file-name">{idx+1}. {name}</span>'
                    f'<span class="file-size badge-error">{size_display} &nbsp;·&nbsp; ❌ {e}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )

            overall_progress.progress((idx + 1) / len(uploads), text=f"Converted {idx+1} of {len(uploads)} files")

        overall_progress.progress(1.0, text="✅ All done!")

        if converted_files:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for output_path, output_filename in converted_files:
                    zf.write(output_path, output_filename)
                    os.remove(output_path)  # ── delete file right after zipping
            zip_buffer.seek(0)
            st.session_state.zip_buffer = zip_buffer

            # ── Remove output folder if empty
            try:
                os.rmdir("output")
            except Exception:
                pass

    # ── Download + Reset ──────────────────────────────────────────────────────
    if st.session_state.zip_buffer is not None:
        st.markdown("---")
        st.download_button(
            label="⬇️  Download All as ZIP",
            data=st.session_state.zip_buffer,
            file_name="converted_audio.zip",
            mime="application/zip",
            use_container_width=True
        )
        if st.button("🔄  Convert Again", use_container_width=True):
            cleanup_output()
            st.session_state.zip_buffer = None
            st.rerun()