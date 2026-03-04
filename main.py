import streamlit as st
import soundfile as sf
import io
import os
import zipfile

st.title("Audio File Converter")

uploads = st.file_uploader("Upload audio files", type=["mp3", "wav", "ogg", "flac", "m4a"], accept_multiple_files=True)

if uploads:
    os.makedirs("output", exist_ok=True)

    output_format = st.selectbox("Select output format", ["wav", "flac", "ogg"])
    subtype_map = {"wav": "PCM_16", "flac": "PCM_16", "ogg": "VORBIS"}

    if st.button("Convert All"):
        converted_files = []

        for upload in uploads:
            try:
                file_bytes = upload.read()
                audio_data, sample_rate = sf.read(io.BytesIO(file_bytes))

                output_filename = f"{os.path.splitext(upload.name)[0]}.{output_format}"
                output_path = os.path.join("output", output_filename)

                sf.write(output_path, audio_data, sample_rate, subtype=subtype_map[output_format])
                converted_files.append((output_path, output_filename))
                st.success(f"✅ {upload.name} converted successfully!")

            except Exception as e:
                st.error(f"❌ Failed to convert {upload.name}: {e}")

        # Zip all converted files for a single download
        if converted_files:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for output_path, output_filename in converted_files:
                    zf.write(output_path, output_filename)
            zip_buffer.seek(0)

            st.download_button(
                label="Download All as ZIP",
                data=zip_buffer,
                file_name="converted_audio.zip",
                mime="application/zip"
            )