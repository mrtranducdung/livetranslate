"""
FastAPI server:
- /ws/translate  : WebSocket proxy → Soniox real-time STT + translation
- /api/tts       : proxy → ElevenLabs TTS
- /              : serve test_web.html
"""
import asyncio
import json
import os
from pathlib import Path

import websockets
from fastapi import FastAPI, Form, WebSocket
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import httpx

load_dotenv()

SONIOX_KEY  = os.getenv("SONIOX_API_KEY", "")
EL_KEY      = os.getenv("ELEVENLABS_API_KEY", "")
EL_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
SONIOX_URL  = "wss://stt-rt.soniox.com/transcribe-websocket"

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/", response_class=HTMLResponse)
async def index():
    return Path("test_web.html").read_text()


@app.websocket("/ws/translate")
async def ws_translate(ws: WebSocket):
    await ws.accept()

    try:
        cfg_raw = await asyncio.wait_for(ws.receive_text(), timeout=10)
        cfg = json.loads(cfg_raw)
    except Exception:
        await ws.close()
        return

    source_lang = cfg.get("source_language", "auto")
    target_lang = cfg.get("target_language", "vi")

    soniox_config = {
        "api_key": SONIOX_KEY,
        "model": "stt-rt-v4",
        "audio_format": "pcm_s16le",
        "sample_rate": 16000,
        "num_channels": 1,
        "enable_endpoint_detection": True,
        "max_endpoint_delay_ms": 1500,
        "enable_speaker_diarization": False,
    }
    if source_lang != "auto":
        soniox_config["language_hints"] = [source_lang]
    if target_lang:
        soniox_config["translation"] = {"type": "one_way", "target_language": target_lang}

    try:
        async with websockets.connect(SONIOX_URL) as soniox:
            await soniox.send(json.dumps(soniox_config))
            print(f"[Soniox] Connected: src={source_lang} tgt={target_lang}")

            stop_event = asyncio.Event()

            async def forward_audio():
                try:
                    while not stop_event.is_set():
                        msg = await ws.receive()
                        data_bytes = msg.get("bytes")
                        data_text  = msg.get("text")
                        if data_bytes:
                            await soniox.send(data_bytes)
                        elif data_text:
                            parsed = json.loads(data_text)
                            if parsed.get("type") == "stop":
                                await soniox.send(b"")
                                break
                except Exception as e:
                    print(f"[forward_audio] {type(e).__name__}: {e}")
                finally:
                    stop_event.set()

            async def forward_results():
                try:
                    async for raw in soniox:
                        data = json.loads(raw)
                        if data.get("error_code"):
                            msg = data.get("error_message", "Soniox error")
                            print(f"[Soniox] error: {msg}")
                            await ws.send_text(json.dumps({"type": "error", "message": msg}))
                            break

                        original = translation = provisional = ""
                        for token in data.get("tokens", []):
                            if token["text"] == "<end>":
                                continue
                            status = token.get("translation_status", "")
                            if status == "original":
                                if token.get("is_final"): original += token["text"]
                                else: provisional += token["text"]
                            elif status == "translation" and token.get("is_final"):
                                translation += token["text"]

                        if original or translation:
                            print(f"[Soniox] original={original!r} translation={translation!r}")

                        out = {"type": "result"}
                        if original:    out["original"]    = original
                        if translation: out["translation"] = translation
                        if provisional: out["provisional"] = provisional
                        if len(out) > 1:
                            await ws.send_text(json.dumps(out))
                except Exception as e:
                    print(f"[forward_results] {type(e).__name__}: {e}")
                finally:
                    stop_event.set()

            audio_task  = asyncio.create_task(forward_audio())
            result_task = asyncio.create_task(forward_results())
            await stop_event.wait()
            audio_task.cancel()
            result_task.cancel()
            await asyncio.gather(audio_task, result_task, return_exceptions=True)

    except Exception as e:
        print(f"[Soniox] Connection error: {type(e).__name__}: {e}")
        try:
            await ws.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass


@app.post("/api/tts")
async def tts(text: str = Form(...), voice_id: str = Form(None)):
    vid = voice_id or EL_VOICE_ID
    print(f"[TTS] {text[:60]!r}")
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
            headers={"xi-api-key": EL_KEY, "Content-Type": "application/json"},
            json={"text": text, "model_id": "eleven_multilingual_v2", "output_format": "mp3_44100_128"},
        )
    if res.status_code != 200:
        print(f"[TTS] error {res.status_code}: {res.text[:200]}")
    return StreamingResponse(iter([res.content]), media_type="audio/mpeg")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
