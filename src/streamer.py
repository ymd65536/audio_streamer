
import json
import os
import queue
import threading
import time
import wave
from datetime import datetime
from pathlib import Path

import sounddevice as sd
import websocket

DEVICE_NAME = os.getenv("AUDIO_DEVICE", "BlackHole 2ch")
WS_URL = os.getenv("WS_URL", "ws://127.0.0.1:8765")

SAMPLE_RATE = 48000
CHANNELS = 2
BLOCK_SIZE = 4800  # 100ms
SAMPLE_WIDTH = 2   # int16

RECORD_SECONDS = 300  # 5分ごとにファイル分割
MAX_BYTES = (
    SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH
    * RECORD_SECONDS
)

record_queue = queue.Queue(maxsize=300)
stream_queue = queue.Queue(maxsize=100)

stats = {"record_overflows": 0, "stream_drops": 0}


def audio_callback(indata, frames, time_info, status):
    if status:
        print(f"Audio status: {status}")

    data = bytes(indata)

    try:
        record_queue.put_nowait(data)
    except queue.Full:
        stats["record_overflows"] += 1


def stream_worker():
    """ネットワーク接続を録音処理から分離する"""
    while True:
        ws = None
        try:
            ws = websocket.create_connection(
                WS_URL,
                timeout=5,
            )

            ws.send(json.dumps({
                "type": "audio.start",
                "format": "pcm_s16le",
                "sample_rate": SAMPLE_RATE,
                "channels": CHANNELS,
            }))

            print("WebSocket connected")

            while True:
                data = stream_queue.get()
                ws.send_binary(data)

        except Exception as exc:
            print(f"WebSocket disconnected: {exc}")
            time.sleep(3)
        finally:
            if ws:
                ws.close()


def open_recording():
    Path("recordings").mkdir(exist_ok=True)

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )
    path = Path("recordings") / f"{timestamp}.wav"

    wav = wave.open(str(path), "wb")
    wav.setnchannels(CHANNELS)
    wav.setsampwidth(SAMPLE_WIDTH)
    wav.setframerate(SAMPLE_RATE)

    print(f"Recording: {path}")
    return wav


def main():
    devices = sd.query_devices()
    matches = [
        i for i, dev in enumerate(devices)
        if DEVICE_NAME.lower() in dev["name"].lower()
        and dev["max_input_channels"] >= CHANNELS
    ]

    if not matches:
        raise RuntimeError(
            f"Input device not found: {DEVICE_NAME}"
        )

    device_id = matches[0]

    threading.Thread(
        target=stream_worker,
        daemon=True,
    ).start()

    wav = open_recording()
    written = 0

    try:
        with sd.RawInputStream(
            device=device_id,
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=BLOCK_SIZE,
            callback=audio_callback,
        ):
            print("Audio capture started")

            while True:
                data = record_queue.get()

                if written + len(data) > MAX_BYTES:
                    wav.close()
                    wav = open_recording()
                    written = 0

                wav.writeframesraw(data)
                written += len(data)

                try:
                    stream_queue.put_nowait(data)
                except queue.Full:
                    stats["stream_drops"] += 1

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        wav.close()
        print(f"Stats: {stats}")


if __name__ == "__main__":
    main()
