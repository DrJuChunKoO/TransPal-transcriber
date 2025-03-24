import os
import time
import modal
import librosa

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
        "ctranslate2==4.4.0",
        "transformers==4.48.0",
        "git+https://github.com/Hasan-Naseer/whisperX.git@release/latest-faster-whisper-version",
        "ffmpeg-python",
        "librosa",
    )
)


app = modal.App("whisperx-transpal", image=image)
GPU_CONFIG = ["A10G", "L4", "T4"]
CACHE_DIR = "/cache"
cache_vol = modal.Volume.from_name("whisper-cache", create_if_missing=True)


@app.function(
    gpu=GPU_CONFIG,
    volumes={CACHE_DIR: cache_vol},
    allow_concurrent_inputs=2,
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

    # Transcribe with original whisper (batched)
    model = whisperx.load_model(
        "large-v3", device,
        compute_type=compute_type,
        download_root=CACHE_DIR,
        asr_options={
            "no_speech_threshold": 0.5,
            "compression_ratio_threshold": 2.2,
            "condition_on_previous_text": True,
        }
    )

    diarize_model = whisperx.DiarizationPipeline(
        use_auth_token=os.environ["HUGGINGFACE_ACCESS_TOKEN"], device=device)

    batch_size = 16  # reduce if low on GPU mem

    # Download
    response = requests.get(audio_url, headers={
        "Authorization": f"Bearer {bot_token}"})
    with open("downloaded_audio.wav", "wb") as audio_file:
        audio_file.write(response.content)
    download_time = time.time() - start_time

    # Transcode
    transcode_start = time.time()
    audio, sr = librosa.load("downloaded_audio.wav", sr=16000)
    # 預處理
    # - 分離人聲和噪音
    harmonic, percussive = librosa.effects.hpss(audio)
    audio = harmonic  # 保留諧波部分(人聲)
    # - 增強高頻
    audio = librosa.effects.preemphasis(audio)
    # -  正規化
    audio = librosa.util.normalize(audio, norm=2)

    transcode_time = time.time() - transcode_start

    # Transcribe
    transcribe_start = time.time()
    result = model.transcribe(audio, batch_size=batch_size)
    print("Transcription done")
    transcribe_time = time.time() - transcribe_start

    # Diarize
    diarize_start = time.time()
    diarize_segments = diarize_model(audio, min_speakers=2)
    result = whisperx.assign_word_speakers(diarize_segments, result)
    diarize_time = time.time() - diarize_start

    print(f"Download time: {download_time:.2f}s")
    print(f"Transcode time: {transcode_time:.2f}s")
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
