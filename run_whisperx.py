import os
import time
import modal

cuda_version = "12.4.0"  # should be no greater than host CUDA version
flavor = "devel"  # includes full CUDA toolkit
operating_sys = "ubuntu22.04"
tag = f"{cuda_version}-{flavor}-{operating_sys}"


image = (
    modal.Image.from_registry(f"nvidia/cuda:{tag}", add_python="3.11")
    .apt_install("git", "ffmpeg")
    .pip_install(
        "torch==2.0.0",
        "torchaudio==2.0.0",
        "numpy<2.0",
        index_url="https://download.pytorch.org/whl/cu118",
    )
    .pip_install(
        "git+https://github.com/Hasan-Naseer/whisperX.git@release/latest-faster-whisper-version",
        "ffmpeg-python",
        "ctranslate2==4.4.0",
    )
)


app = modal.App("whisperx-transpal", image=image)
GPU_CONFIG = ["A10G", "L4", "T4"]
CACHE_DIR = "/cache"
cache_vol = modal.Volume.from_name("whisper-cache", create_if_missing=True)


@app.function(
    gpu=GPU_CONFIG,
    volumes={CACHE_DIR: cache_vol},
    allow_concurrent_inputs=1,
    scaledown_window=30,
    timeout=60 * 60,
    secrets=[modal.Secret.from_name("my-huggingface-secret")],
)
def transcribe(audio_url, bot_token):
    import whisperx
    import requests
    start_time = time.time()

    device = "cuda"
    compute_type = (
        # change to "int8" if low on GPU mem (may reduce accuracy)
        "float16"
    )

    # 1. Transcribe with original whisper (batched)
    model = whisperx.load_model("large-v3", device, compute_type=compute_type, download_root=CACHE_DIR, asr_options={
        "no_speech_threshold": 0.5,
        "compression_ratio_threshold": 2.2,
    })

    diarize_model = whisperx.DiarizationPipeline(
        use_auth_token=os.environ["HUGGINGFACE_ACCESS_TOKEN"], device=device)

    batch_size = 16  # reduce if low on GPU mem

    response = requests.get(audio_url, headers={
        "Authorization": f"Bearer {bot_token}"})
    # Save the audio file locally
    with open("downloaded_audio.wav", "wb") as audio_file:
        audio_file.write(response.content)

    download_time = time.time() - start_time
    print(f"Download time: {download_time:.2f}s")

    # Changed from audio_file to the actual file path
    audio = whisperx.load_audio("downloaded_audio.wav")

    transcode_time = time.time() - start_time - download_time

    # 1. Transcribe audio to text
    result = model.transcribe(audio, batch_size=batch_size)
    print("Transcription done")
    transcribe_time = time.time() - start_time - download_time - transcode_time

    # 2. Assign speaker labels
    diarize_segments = diarize_model(audio, min_speakers=2)
    result = whisperx.assign_word_speakers(diarize_segments, result)

    print(diarize_segments)
    print("Diarization done")

    diarize_time = time.time() - start_time - transcribe_time - \
        download_time - transcode_time

    print(f"Transcribe time: {transcribe_time:.2f}s")
    print(f"Diarize time: {diarize_time:.2f}s")
    print(f"Total time: {time.time() - start_time:.2f}s")
    result = {
        "segments": result["segments"],
        "info": {
            "transcribe_time": transcribe_time,
            "diarize_time": diarize_time,
            "transcode_time": transcode_time,
            "download_time": download_time,
        }
    }

    return result
