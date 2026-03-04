import streamlit as st
import soundfile as sf
import io
import os
import zipfile
import numpy as np
import av

st.title("Audio File Converter")

if "zip_buffer" not in st.session_state:
    st.session_state.zip_buffer = None

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
            resampled = resampler.resample(frame)
            for f in resampled:
                samples.append(f.to_ndarray())

        # Flush resampler
        for f in resampler.resample(None):
            samples.append(f.to_ndarray())

        audio_array = np.concatenate(samples, axis=1)

        if audio_array.shape[0] == 1:
            audio_data = audio_array[0]       # mono → 1D
        else:
            audio_data = audio_array.T        # stereo → (samples, 2)

        audio_data = audio_data.astype(np.float32)

    else:
        audio_data, sample_rate = sf.read(io.BytesIO(file_bytes))

    return audio_data, sample_rate

uploads = st.file_uploader("Upload audio files", type=["mp3", "wav", "ogg", "flac", "m4a"], accept_multiple_files=True)

if uploads:
    os.makedirs("output", exist_ok=True)

    st.subheader(f"📁 Files ({len(uploads)})")
    file_status = []
    for i, upload in enumerate(uploads, 1):
        size_kb = round(upload.size / 1024, 1)
        status = st.empty()
        status.write(f"{i}. {upload.name} — {size_kb} KB")
        file_status.append(status)

    st.divider()

    output_format = st.selectbox("Select output format", ["wav", "flac", "ogg"])
    subtype_map = {"wav": "PCM_16", "flac": "PCM_16", "ogg": "VORBIS"}

    if st.button("Convert All"):
        st.session_state.zip_buffer = None
        converted_files = []
        overall_progress = st.progress(0, text="Starting conversion...")

        for idx, upload in enumerate(uploads):
            size_kb = round(upload.size / 1024, 1)
            file_status[idx].write(f"⏳ {idx+1}. {upload.name} — {size_kb} KB  `converting...`")

            try:
                audio_data, sample_rate = read_audio(upload)
                output_filename = f"{os.path.splitext(upload.name)[0]}.{output_format}"
                output_path = os.path.join("output", output_filename)
                sf.write(output_path, audio_data, sample_rate, subtype=subtype_map[output_format])
                converted_files.append((output_path, output_filename))
                file_status[idx].write(f"✅ {idx+1}. {upload.name} — {size_kb} KB")

            except Exception as e:
                file_status[idx].write(f"❌ {idx+1}. {upload.name} — {size_kb} KB  `{e}`")

            overall_progress.progress((idx + 1) / len(uploads), text=f"Converted {idx+1} of {len(uploads)} files")

        overall_progress.progress(1.0, text="✅ All conversions complete!")

        if converted_files:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for output_path, output_filename in converted_files:
                    zf.write(output_path, output_filename)
            zip_buffer.seek(0)
            st.session_state.zip_buffer = zip_buffer

    if st.session_state.zip_buffer is not None:
        st.download_button(
            label="⬇️ Download All as ZIP",
            data=st.session_state.zip_buffer,
            file_name="converted_audio.zip",
            mime="application/zip"
        )