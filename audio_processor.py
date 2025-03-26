import os
import tempfile
import pyaudio
import wave
import speech_recognition as sr
from pydub import AudioSegment
import io
import numpy as np
import logging

from config import SAMPLE_RATE, CHANNELS, CHUNK_SIZE, RECORD_SECONDS, FORMAT, TEMP_AUDIO_DIR
from utils import generate_unique_filename, ensure_directory_exists
from speech_recognizer import SpeechRecognizer

# Configure logger
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("audio_processor")


class AudioProcessor:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.fish_recognizer = SpeechRecognizer()  # Initialize Fish Audio recognizer
        self.p = pyaudio.PyAudio()
        self.use_fish_audio = True  # Set to True to use Fish Audio, False to use Google
        self.selected_device_index = None  # Default to system default device
        ensure_directory_exists(TEMP_AUDIO_DIR)

    def __del__(self):
        """Clean up PyAudio when the object is destroyed"""
        if hasattr(self, 'p'):
            self.p.terminate()

    def get_available_input_devices(self):
        """Get a list of available audio input devices"""
        input_devices = []
        for i in range(self.p.get_device_count()):
            device_info = self.p.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:  # If it's an input device
                name = device_info['name']
                input_devices.append({
                    'index': i,
                    'name': name,
                    'channels': device_info['maxInputChannels'],
                    'sample_rate': int(device_info['defaultSampleRate'])
                })
        return input_devices

    def set_input_device(self, device_index):
        """Set the audio input device by its index"""
        if device_index is not None:
            device_info = self.p.get_device_info_by_index(device_index)
            if device_info['maxInputChannels'] > 0:
                self.selected_device_index = device_index
                logger.info(f"Selected input device: {device_info['name']}")
                return True
        return False

    def get_current_device_info(self):
        """Get information about the currently selected input device"""
        if self.selected_device_index is not None:
            return self.p.get_device_info_by_index(self.selected_device_index)
        return self.p.get_default_input_device_info()

    def record_audio(self, seconds=None):
        """Record audio from the selected microphone and save to a temporary WAV file"""
        if seconds is None:
            seconds = RECORD_SECONDS

        # Get device info for the selected or default device
        device_info = self.get_current_device_info()
        logger.info(f"Recording using device: {device_info['name']}")

        # Open stream with the selected device
        stream = self.p.open(
            format=self.p.get_format_from_width(2),  # 16-bit format
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            input_device_index=self.selected_device_index,  # Use selected device
            frames_per_buffer=CHUNK_SIZE
        )

        logger.info(f"Recording audio for {seconds} seconds...")

        frames = []
        for i in range(0, int(SAMPLE_RATE / CHUNK_SIZE * seconds)):
            data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            frames.append(data)

        logger.info("Recording finished.")

        stream.stop_stream()
        stream.close()

        # Save to temporary file
        temp_filename = generate_unique_filename(TEMP_AUDIO_DIR, FORMAT)

        with wave.open(temp_filename, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(self.p.get_sample_size(
                self.p.get_format_from_width(2)))
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b''.join(frames))

        logger.info(f"Saved recording to: {temp_filename}")
        return temp_filename

    def transcribe_audio(self, audio_file):
        """
        Transcribe the recorded audio using either Fish Audio or Google Speech Recognition

        Args:
            audio_file (str): Path to the audio file

        Returns:
            str: Transcribed text
        """
        if self.use_fish_audio:
            logger.info("Transcribing audio using Fish Audio API...")
            try:
                # Use Fish Audio for transcription
                transcribed_text = self.fish_recognizer.transcribe_audio(
                    audio_file)
                if transcribed_text:
                    logger.info("Fish Audio transcription successful")
                    return transcribed_text
                else:
                    logger.warning(
                        "Fish Audio transcription returned empty result, falling back to Google")
            except Exception as e:
                logger.error(
                    f"Error with Fish Audio transcription: {str(e)}, falling back to Google")

        # Fallback to Google Speech Recognition
        logger.info("Transcribing audio using Google Speech Recognition...")
        with sr.AudioFile(audio_file) as source:
            audio_data = self.recognizer.record(source)
            try:
                text = self.recognizer.recognize_google(audio_data)
                logger.info("Google transcription successful")
                return text
            except sr.UnknownValueError:
                logger.error(
                    "Google Speech Recognition could not understand audio")
                return "Speech Recognition could not understand audio"
            except sr.RequestError as e:
                logger.error(
                    f"Could not request results from Google Speech Recognition service; {e}")
                return f"Could not request results from Speech Recognition service; {e}"

    def toggle_transcription_service(self):
        """Toggle between Fish Audio and Google Speech Recognition"""
        self.use_fish_audio = not self.use_fish_audio
        service = "Fish Audio" if self.use_fish_audio else "Google Speech Recognition"
        logger.info(f"Switched transcription service to: {service}")
        return service

    def get_current_transcription_service(self):
        """Get the name of the current transcription service"""
        return "Fish Audio" if self.use_fish_audio else "Google Speech Recognition"

    def play_audio(self, audio_file):
        """Play audio file using PyAudio"""
        with wave.open(audio_file, 'rb') as wf:
            # Open stream
            stream = self.p.open(
                format=self.p.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True
            )

            # Read data in chunks
            chunk_size = 1024
            data = wf.readframes(chunk_size)

            # Play audio
            while data:
                stream.write(data)
                data = wf.readframes(chunk_size)

            # Stop stream
            stream.stop_stream()
            stream.close()

    def save_audio_from_bytes(self, audio_bytes, output_file=None):
        """Save audio bytes to a file"""
        if output_file is None:
            output_file = generate_unique_filename(TEMP_AUDIO_DIR, FORMAT)

        with open(output_file, 'wb') as f:
            f.write(audio_bytes)

        return output_file
