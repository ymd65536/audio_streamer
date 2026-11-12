
import sounddevice as sd
import wave

DEVICE = 0
SAMPLE_RATE = 48000
CHANNELS = 2
SECONDS = 10

print("Recording...")

audio = sd.rec(
    int(SECONDS * SAMPLE_RATE),
    samplerate=SAMPLE_RATE,
    channels=CHANNELS,
    dtype="int16",
    device=DEVICE,
)

sd.wait()

with wave.open("test.wav", "wb") as wav:
    wav.setnchannels(CHANNELS)
    wav.setsampwidth(2)
    wav.setframerate(SAMPLE_RATE)
    wav.writeframes(audio.tobytes())

print("Saved: test.wav")
