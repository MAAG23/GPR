# Celebrity Voice Transformer

This application captures audio from a microphone, transcribes it to text, transforms it using OpenAI's API to mimic celebrity speech patterns, and then uses Fish Audio API to generate speech in the celebrity's voice.

## Features

-   Audio recording from external microphone
-   Speech-to-text conversion
-   Text transformation in the style of celebrities (currently Cristiano Ronaldo and Donald Trump)
-   Voice synthesis using Fish Audio API
-   Simple Streamlit UI

## Requirements

-   Raspberry Pi with Raspbian OS
-   External microphone
-   Python 3.9+
-   OpenAI API key
-   Fish Audio API key

## Installation

1. Clone this repository to your Raspberry Pi:

```
git clone <repository-url>
cd <repository-directory>
```

2. Install the required dependencies:

```
pip install -r requirements.txt
```

3. Install PortAudio (required for PyAudio):

```
sudo apt-get install portaudio19-dev
```

4. Create a `.env` file in the project root directory with your API keys:

```
OPENAI_API_KEY=your_openai_api_key
FISH_AUDIO_API_KEY=your_fish_audio_api_key
```

## Usage

1. Start the application:

```
streamlit run app.py
```

2. Access the application through a web browser at `http://localhost:8501` or the IP address of your Raspberry Pi.

3. Select a celebrity, record your voice, and enjoy the transformed output!

## Project Structure

-   `app.py`: Main Streamlit application
-   `audio_processor.py`: Audio recording and processing functions
-   `text_transformer.py`: OpenAI API integration for text transformation
-   `voice_synthesizer.py`: Fish Audio API integration for voice synthesis
-   `config.py`: Configuration settings
-   `utils.py`: Utility functions

## Troubleshooting

-   If you encounter issues with the microphone, check that it's properly connected and recognized by your Raspberry Pi.
-   Use `arecord -l` to list available recording devices.
-   Ensure your API keys are correctly set in the `.env` file.

## License

MIT License
