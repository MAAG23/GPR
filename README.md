# Voice Processing Application

This application captures audio from a microphone, transcribes it to text using Fish Audio's ASR API, and then synthesizes speech using Fish Audio's TTS API.

## Features

-   Audio recording with device selection (USB, built-in, or other microphones)
-   Speech-to-text conversion using Fish Audio ASR API (with Google Speech Recognition fallback)
-   Text-to-speech synthesis using Fish Audio API
-   Remote access through ngrok tunneling
-   Modern Streamlit UI with settings management
-   Support for multiple languages

## Requirements

-   Raspberry Pi with Raspbian OS (or any Linux/macOS system)
-   Microphone (USB or built-in)
-   Python 3.9+
-   Fish Audio API key
-   Ngrok auth token (optional, for remote access)

## Installation

1. Clone this repository:

```bash
git clone https://github.com/marcelofeitoza/gestao-redes-projeto.git
cd gestao-redes-projeto
```

2. Run the setup script (this will install all dependencies):

```bash
sudo ./setup_raspberry_pi.sh
```

The setup script will:

-   Install system dependencies
-   Create a Python virtual environment
-   Install Python packages
-   Set up ngrok for remote access
-   Create necessary directories
-   Generate a template .env file

3. Configure your API key in the `.env` file:

```bash
# Fish Audio API Key for voice synthesis and speech recognition
FISH_API_KEY=your_fish_audio_api_key_here

# Ngrok auth token (optional, for remote access)
NGROK_AUTH_TOKEN=your_ngrok_auth_token_here
```

## Usage

1. Start the application:

```bash
./launch.sh
```

2. The app will:

    - Start the Streamlit interface
    - Set up an ngrok tunnel (if configured)
    - Display both local and public URLs

3. Access the application through:
    - Local network: `http://localhost:8501` or `http://raspberry-pi-IP:8501`
    - Remote access: Use the ngrok URL provided in the console

## Features Guide

### Microphone Input

-   Select your preferred audio input device in the Settings tab
-   Record your voice using the selected device
-   View the transcription in real-time

### Text Input

-   Type or paste text directly
-   Convert text to speech

### Settings

-   Toggle between Fish Audio and Google Speech Recognition
-   Select audio input devices
-   View API and connection status

## Project Structure

-   `app.py`: Main Streamlit application
-   `audio_processor.py`: Audio recording and device management
-   `voice_synthesizer.py`: Fish Audio API integration for voice synthesis
-   `speech_recognizer.py`: Fish Audio ASR integration
-   `tunnel.py`: Ngrok tunnel management
-   `config.py`: Configuration settings
-   `utils.py`: Utility functions
-   `run.py`: Application launcher with tunnel setup

## Troubleshooting

-   If you encounter issues with the microphone:

    -   Check the Settings tab for available devices
    -   Select the appropriate input device
    -   Verify system permissions for audio access

-   For remote access issues:

    -   Try the HTTP URL if HTTPS doesn't work
    -   If behind a corporate firewall, try a personal network
    -   Check your ngrok authentication token

-   For API-related issues:
    -   Verify your API key in the .env file
    -   Check your API usage quota
    -   Ensure network connectivity

## License

MIT License
