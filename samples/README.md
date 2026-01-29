# transcribe-cli samples

This directory is for sample audio/video files for testing.

## Adding Samples

Place your test media files here:
- `sample.wav` - Sample audio file (recommended: short, 10-30 seconds)
- `sample.mp4` - Sample video file
- `sample_arabic.wav` - Arabic speech sample
- `sample_english.wav` - English speech sample

## Creating Test Samples

You can create test samples using:

**Generate test audio with ffmpeg:**
```bash
# Generate 10 seconds of silence
ffmpeg -f lavfi -i anullsrc=r=16000:cl=mono -t 10 -acodec pcm_s16le sample.wav

# Or record from microphone
ffmpeg -f avfoundation -i ":0" -t 10 sample.wav  # macOS
ffmpeg -f dshow -i audio="Microphone" -t 10 sample.wav  # Windows
```

**Use existing media:**
- Extract short clips from longer videos/audio
- Use royalty-free samples from freesound.org or similar

## Running Tests

```bash
# Single file
transcribe ./samples/sample.wav --lang ar --format text --out ./out

# With SRT output
transcribe ./samples/sample.wav --lang ar --format srt --out ./out

# Batch processing
transcribe batch ./samples --lang ar --format text --out ./out
```

## Note

Sample files are typically added to `.gitignore` to avoid committing large media files to the repository.
