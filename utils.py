import os
import time
import uuid
from pathlib import Path
import wave


def generate_unique_filename(directory, extension):
    """Generate a unique filename using timestamp and UUID"""
    timestamp = int(time.time())
    unique_id = str(uuid.uuid4())[:8]
    filename = f"{timestamp}_{unique_id}.{extension}"
    return os.path.join(directory, filename)


def get_wav_duration(wav_file):
    """Get the duration of a WAV file in seconds"""
    with wave.open(wav_file, 'rb') as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        duration = frames / float(rate)
    return duration


def ensure_directory_exists(directory):
    """Ensure that a directory exists, create if it doesn't"""
    Path(directory).mkdir(parents=True, exist_ok=True)


def cleanup_temp_files(file_path, delay=0):
    """Delete temporary files after a delay"""
    if delay > 0:
        time.sleep(delay)

    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return True
        except Exception as e:
            print(f"Error deleting file {file_path}: {str(e)}")
            return False
    return False
