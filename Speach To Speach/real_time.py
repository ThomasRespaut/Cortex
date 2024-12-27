import sounddevice as sd
import numpy as np
import asyncio
import websockets
import json
import base64
import struct


# Fonction pour convertir Float32 en PCM16
def float32_to_pcm16(float32_array):
    pcm16_data = struct.pack('<' + ('h' * len(float32_array)), *(int(sample * 32767.0) for sample in float32_array))
    return pcm16_data


# Fonction pour encoder l'audio en base64
def base64_encode_audio(float32_array):
    pcm16_data = float32_to_pcm16(float32_array)
    return base64.b64encode(pcm16_data).decode('utf-8')


# Fonction pour enregistrer 3 secondes d'audio
def record_audio(duration=3, samplerate=24000):
    audio = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='float32')
    sd.wait()  # Attendre la fin de l'enregistrement
    return audio.flatten()


# Fonction pour envoyer l'audio via WebSocket
async def send_audio_via_websocket(audio_data):
    url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
    headers = {
        "Authorization": "Bearer your_openai_api_key",
        "OpenAI-Beta": "realtime=v1",
    }

    async with websockets.connect(url, extra_headers=headers) as ws:
        base64_audio = base64_encode_audio(audio_data)
        await ws.send(json.dumps({
            "type": "input_audio_buffer.append",
            "audio": base64_audio
        }))
        await ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
        await ws.send(json.dumps({"type": "response.create"}))

        async for message in ws:
            print("Message reçu :", message)


# Fonction principale pour capturer et envoyer l'audio
async def main():
    while True:
        print("Enregistrement de 3 secondes d'audio...")
        audio_data = record_audio()
        await send_audio_via_websocket(audio_data)


asyncio.run(main())
