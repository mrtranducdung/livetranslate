"""
Test Soniox STT — sends a few seconds of silence to check connection & balance
"""
import asyncio
import json
import os
from dotenv import load_dotenv
import websockets

load_dotenv()

API_KEY = os.getenv("SONIOX_API_KEY", "")
SONIOX_URL = "wss://stt-rt.soniox.com/transcribe-websocket"


async def test():
    print(f"API key: {API_KEY[:8]}...")
    print("Connecting to Soniox...")

    async with websockets.connect(SONIOX_URL) as ws:
        config = {
            "api_key": API_KEY,
            "model": "stt-rt-v4",
            "audio_format": "pcm_s16le",
            "sample_rate": 16000,
            "num_channels": 1,
            "translation": {"type": "one_way", "target_language": "vi"},
        }
        await ws.send(json.dumps(config))
        print("Config sent, waiting for response...")

        # Send 1 second of silence (16000 samples * 2 bytes = 32000 bytes)
        silence = b"\x00" * 32000
        await ws.send(silence)
        print("Sent 1s of silence")

        # Send EOS
        await ws.send(b"")
        print("Sent EOS, waiting for final response...")

        async for msg in ws:
            data = json.loads(msg)
            if data.get("error_code"):
                print(f"ERROR {data['error_code']}: {data.get('error_message')}")
                break
            tokens = data.get("tokens", [])
            if tokens:
                print(f"Tokens received: {tokens}")
            else:
                print("Empty response (expected for silence)")
                break

    print("Done.")

asyncio.run(test())
