import os
import streamlit as st
import time
import threading
import atexit
from pathlib import Path
import base64

from audio_processor import AudioProcessor
from text_transformer import TextTransformer
from voice_synthesizer import VoiceSynthesizer
from config import CELEBRITIES, RECORD_SECONDS
from utils import cleanup_temp_files

# Initialize components
audio_processor = AudioProcessor()
text_transformer = TextTransformer()
voice_synthesizer = VoiceSynthesizer()

# Set page config
st.set_page_config(
    page_title="Celebrity Voice Transformer",
    page_icon="🎤",
    layout="wide"
)

# Helper functions


def autoplay_audio(file_path):
    """Autoplay audio in Streamlit"""
    with open(file_path, "rb") as f:
        audio_bytes = f.read()

    audio_base64 = base64.b64encode(audio_bytes).decode()
    html = f"""
    <audio autoplay>
      <source src="data:audio/wav;base64,{audio_base64}" type="audio/wav">
    </audio>
    """
    st.markdown(html, unsafe_allow_html=True)


# App UI
st.title("Celebrity Voice Transformer 🎤")
st.subheader("Speak like your favorite celebrity!")

# Create tabs for different modes
tab1, tab2, tab3 = st.tabs(
    ["Microphone Input", "Text Input (Test)", "Settings"])

# Sidebar
st.sidebar.title("Settings")

# Celebrity selection
celebrity_options = {id: info["name"] for id, info in CELEBRITIES.items()}
selected_celebrity = st.sidebar.selectbox(
    "Select a celebrity voice",
    list(celebrity_options.keys()),
    format_func=lambda x: celebrity_options[x]
)

# Show celebrity info
st.sidebar.markdown(f"### {CELEBRITIES[selected_celebrity]['name']}")
st.sidebar.markdown(CELEBRITIES[selected_celebrity]['description'])

# About section
st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.info(
    "This app uses your microphone to record audio, "
    "transcribes it to text, transforms it using OpenAI, "
    "and generates speech in a celebrity's voice using Fish Audio API."
)

# Tab 1: Microphone Input
with tab1:
    # Show current transcription service
    current_service = audio_processor.get_current_transcription_service()
    st.info(f"Currently using {current_service} for speech recognition")

    # Record duration slider (only shown in the microphone tab)
    record_duration = st.slider(
        "Recording Duration (seconds)",
        min_value=2,
        max_value=10,
        value=RECORD_SECONDS,
        step=1
    )

    col1, col2 = st.columns(2)

    with col1:
        st.header("Your Voice")

        # Record button
        if st.button("🎙️ Record Audio", key="record_button", use_container_width=True):
            with st.spinner(f"Recording for {record_duration} seconds..."):
                audio_file = audio_processor.record_audio(record_duration)

            st.session_state["audio_file"] = audio_file
            st.session_state["processing_complete"] = False

            with st.spinner(f"Transcribing audio using {audio_processor.get_current_transcription_service()}..."):
                transcribed_text = audio_processor.transcribe_audio(audio_file)

            st.session_state["transcribed_text"] = transcribed_text

            # Display original audio
            st.audio(audio_file)

            # Display transcribed text
            st.text_area("Transcribed Text", transcribed_text, height=150)

            # Process text and generate speech
            with st.spinner("Transforming text in celebrity style..."):
                transformed_text = text_transformer.transform_text(
                    transcribed_text, selected_celebrity
                )

            st.session_state["transformed_text"] = transformed_text

            with st.spinner("Generating celebrity voice..."):
                output_file = voice_synthesizer.synthesize_speech(
                    transformed_text, selected_celebrity
                )

            if output_file:
                st.session_state["output_file"] = output_file
                st.session_state["processing_complete"] = True

    with col2:
        st.header(f"{CELEBRITIES[selected_celebrity]['name']}'s Voice")

        # Show transformed text and audio if processing is complete
        if "processing_complete" in st.session_state and st.session_state["processing_complete"]:
            # Display transformed text
            st.text_area(
                f"Text in {CELEBRITIES[selected_celebrity]['name']}'s Style",
                st.session_state["transformed_text"],
                height=150
            )

            # Display and autoplay celebrity audio
            st.audio(st.session_state["output_file"])
            autoplay_audio(st.session_state["output_file"])

            # Download button
            with open(st.session_state["output_file"], "rb") as f:
                st.download_button(
                    label="💾 Download Audio",
                    data=f,
                    file_name=f"{CELEBRITIES[selected_celebrity]['name']}_voice.wav",
                    mime="audio/wav",
                    use_container_width=True
                )
        else:
            st.info("Record your voice to transform it into the celebrity's voice!")

# Tab 2: Text Input (Test)
with tab2:
    st.header("Test with Text Input")
    st.markdown(
        "Type text directly instead of using the microphone. Useful for testing without audio recording.")

    col1, col2 = st.columns(2)

    with col1:
        st.header("Your Text")

        # Text input area
        user_text = st.text_area(
            "Enter text to transform:",
            placeholder="Type something here to transform into the celebrity's voice...",
            height=150
        )

        # Transform button
        if st.button("🔄 Transform Text", key="transform_button", use_container_width=True) and user_text:
            st.session_state["text_input"] = user_text
            st.session_state["text_processing_complete"] = False

            # Process text and generate speech
            with st.spinner("Transforming text in celebrity style..."):
                transformed_text = text_transformer.transform_text(
                    user_text, selected_celebrity
                )

            st.session_state["text_transformed"] = transformed_text

            with st.spinner("Generating celebrity voice..."):
                output_file = voice_synthesizer.synthesize_speech(
                    transformed_text, selected_celebrity
                )

            if output_file:
                st.session_state["text_output_file"] = output_file
                st.session_state["text_processing_complete"] = True

    with col2:
        st.header(f"{CELEBRITIES[selected_celebrity]['name']}'s Voice")

        # Show transformed text and audio if processing is complete
        if "text_processing_complete" in st.session_state and st.session_state["text_processing_complete"]:
            # Display transformed text
            st.text_area(
                f"Text in {CELEBRITIES[selected_celebrity]['name']}'s Style",
                st.session_state["text_transformed"],
                height=150
            )

            # Display and autoplay celebrity audio
            st.audio(st.session_state["text_output_file"])
            autoplay_audio(st.session_state["text_output_file"])

            # Download button
            with open(st.session_state["text_output_file"], "rb") as f:
                st.download_button(
                    label="💾 Download Audio",
                    data=f,
                    file_name=f"{CELEBRITIES[selected_celebrity]['name']}_text_voice.wav",
                    mime="audio/wav",
                    use_container_width=True
                )
        else:
            st.info(
                "Enter text and click 'Transform Text' to convert it to the celebrity's voice.")

# Tab 3: Settings
with tab3:
    st.header("Application Settings")

    # Transcription service section
    st.subheader("Speech-to-Text Service")

    st.write(
        f"Currently using: **{audio_processor.get_current_transcription_service()}**")

    # Toggle transcription service
    if st.button("Toggle Speech Recognition Service", key="toggle_service"):
        new_service = audio_processor.toggle_transcription_service()
        st.success(f"Switched to {new_service} for speech recognition")

    st.markdown("""
    ### About the Speech Recognition Services
    
    **Fish Audio Speech-to-Text:** Advanced speech recognition using Fish Audio's API. 
    Provides high-quality transcription with optional detailed timestamp information.
    
    **Google Speech Recognition:** Traditional speech recognition using Google's service.
    Used as a fallback if Fish Audio is unavailable.
    """)

    # API Information
    st.subheader("API Information")
    st.info("""
    This application uses two external APIs:
    
    1. **OpenAI API** - For text transformation to match celebrity speaking styles
    2. **Fish Audio API** - For voice synthesis and speech recognition
    
    Make sure your API keys are correctly configured in the .env file.
    """)

# Cleanup temp files when app is closed (this won't always work in Streamlit)


def cleanup():
    if "audio_file" in st.session_state:
        cleanup_temp_files(st.session_state["audio_file"])


# Register cleanup function
atexit.register(cleanup)

# Add footer
st.markdown("---")
st.caption("Powered by OpenAI and Fish Audio API | Made for Raspberry Pi")
