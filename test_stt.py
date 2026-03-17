from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
import os

load_dotenv()

elevenlabs = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
)

# Test with a local audio file
AUDIO_FILE = "test_output.mp3"  # reuse the TTS output from test_tts.py

with open(AUDIO_FILE, "rb") as f:
    result = elevenlabs.speech_to_text.convert(
        file=f,
        model_id="scribe_v1",
        language_code="en",  # change to "vi" for Vietnamese
    )

print("Transcript:", result.text)
