/**
 * ElevenLabs STT — Scribe v1
 * Buffers PCM audio (s16le, 16kHz, mono) and sends to ElevenLabs Scribe REST API.
 */

const SAMPLE_RATE = 16000;
const CHANNELS = 1;
const BITS_PER_SAMPLE = 16;

// Buffer 5 seconds of audio before sending
const CHUNK_DURATION_S = 5;
const CHUNK_SIZE_BYTES = SAMPLE_RATE * CHANNELS * (BITS_PER_SAMPLE / 8) * CHUNK_DURATION_S;

class ElevenLabsSTT {
    constructor() {
        this.apiKey = null;
        this._buffer = [];
        this._bufferSize = 0;
        this._active = false;

        // Callbacks
        this.onTranscript = null;   // (text) => void
        this.onError = null;        // (error) => void
        this.onStatusChange = null; // (status) => void
    }

    configure({ apiKey }) {
        this.apiKey = apiKey;
    }

    start() {
        this._buffer = [];
        this._bufferSize = 0;
        this._active = true;
        this._setStatus('connected');
    }

    stop() {
        this._active = false;
        this._buffer = [];
        this._bufferSize = 0;
        this._setStatus('disconnected');
    }

    /** Feed raw PCM data (Uint8Array, s16le 16kHz mono) */
    feedAudio(pcmData) {
        if (!this._active) return;

        this._buffer.push(pcmData);
        this._bufferSize += pcmData.byteLength;

        if (this._bufferSize >= CHUNK_SIZE_BYTES) {
            this._flushBuffer();
        }
    }

    _flushBuffer() {
        if (this._buffer.length === 0) return;

        const total = new Uint8Array(this._bufferSize);
        let offset = 0;
        for (const chunk of this._buffer) {
            total.set(chunk, offset);
            offset += chunk.byteLength;
        }

        this._buffer = [];
        this._bufferSize = 0;

        // Fire and forget — don't block audio ingestion
        this._transcribe(total);
    }

    async _transcribe(pcmData) {
        if (!this.apiKey || !this._active) return;

        try {
            const wavBlob = new Blob([this._buildWav(pcmData)], { type: 'audio/wav' });

            const formData = new FormData();
            formData.append('file', wavBlob, 'audio.wav');
            formData.append('model_id', 'scribe_v1');

            const response = await fetch('https://api.elevenlabs.io/v1/speech-to-text', {
                method: 'POST',
                headers: { 'xi-api-key': this.apiKey },
                body: formData,
            });

            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                const msg = err?.detail?.message || response.statusText;
                this.onError?.(`STT error ${response.status}: ${msg}`);
                return;
            }

            const data = await response.json();
            const text = data.text?.trim();
            if (text) {
                this.onTranscript?.(text);
            }
        } catch (e) {
            this.onError?.(`STT request failed: ${e.message}`);
        }
    }

    /** Build WAV header + PCM data */
    _buildWav(pcmData) {
        const dataLen = pcmData.byteLength;
        const buf = new ArrayBuffer(44 + dataLen);
        const view = new DataView(buf);

        const str = (offset, s) => { for (let i = 0; i < s.length; i++) view.setUint8(offset + i, s.charCodeAt(i)); };

        str(0, 'RIFF');
        view.setUint32(4, 36 + dataLen, true);
        str(8, 'WAVE');
        str(12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);                                    // PCM
        view.setUint16(22, CHANNELS, true);
        view.setUint32(24, SAMPLE_RATE, true);
        view.setUint32(28, SAMPLE_RATE * CHANNELS * BITS_PER_SAMPLE / 8, true);
        view.setUint16(32, CHANNELS * BITS_PER_SAMPLE / 8, true);
        view.setUint16(34, BITS_PER_SAMPLE, true);
        str(36, 'data');
        view.setUint32(40, dataLen, true);
        new Uint8Array(buf, 44).set(pcmData);

        return buf;
    }

    _setStatus(status) {
        this.onStatusChange?.(status);
    }
}

export const elevenLabsSTT = new ElevenLabsSTT();
