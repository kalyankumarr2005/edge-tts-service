from flask import Flask, request, jsonify
import edge_tts
import asyncio
import base64
import os

app = Flask(__name__)


async def synthesize(text: str, voice: str) -> bytes:
    """Generates speech entirely in memory - no temp files, no disk writes."""
    communicate = edge_tts.Communicate(text, voice)
    audio_bytes = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes.extend(chunk["data"])
    return bytes(audio_bytes)


@app.route("/tts", methods=["POST"])
def tts():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    voice = data.get("voice", "en-US-GuyNeural")

    if not text:
        return jsonify({"error": "text field is required"}), 400

    try:
        audio_bytes = asyncio.run(synthesize(text, voice))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Same response shape as Google Cloud TTS (audioContent, base64) so the
    # rest of the n8n workflow - the Decode Narration Audio node - needs no changes.
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    return jsonify({"audioContent": audio_b64})


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "edge-tts-cloud"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port)
