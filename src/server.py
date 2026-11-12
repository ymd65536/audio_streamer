
import asyncio
import json
import websockets


async def handle_audio(ws):
    total_bytes = 0
    metadata = None

    async for message in ws:
        if isinstance(message, str):
            metadata = json.loads(message)
            print("Metadata:", metadata)
        else:
            total_bytes += len(message)

            if total_bytes % 960000 < len(message):
                print(
                    f"Received: {total_bytes:,} bytes"
                )


async def main():
    async with websockets.serve(
        handle_audio,
        "127.0.0.1",
        8765,
    ):
        print("Listening on ws://127.0.0.1:8765")
        await asyncio.Future()


asyncio.run(main())
