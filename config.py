import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenAI API configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Fish Audio API configuration
FISH_AUDIO_API_KEY = os.getenv("FISH_API_KEY")
FISH_AUDIO_API_URL = "https://api.fish.audio/v1/tts"

# Audio recording configuration
SAMPLE_RATE = 44100
CHANNELS = 1
CHUNK_SIZE = 1024
RECORD_SECONDS = 5
FORMAT = "wav"

# Celebrities configuration
CELEBRITIES = {
    "cristiano_ronaldo": {
        "name": "Cristiano Ronaldo",
        "description": "Portuguese football player, known for his confidence, determination, and 'Siuuu' celebration.",
        # Actual voice ID from Fish Audio
        "fish_audio_voice_id": "86304d8fa1734bd89291acf4060d8a5e"
    },
    "donald_trump": {
        "name": "Donald Trump",
        "description": "Former US President, known for his unique speaking style, repetition, and use of superlatives.",
        # Actual voice ID from Fish Audio
        "fish_audio_voice_id": "5196af35f6ff4a0dbf541793fc9f2157"
    }
}

# File paths
TEMP_AUDIO_DIR = "temp_audio"
OUTPUT_AUDIO_DIR = "output_audio"

# Create directories if they don't exist
for directory in [TEMP_AUDIO_DIR, OUTPUT_AUDIO_DIR]:
    os.makedirs(directory, exist_ok=True)
